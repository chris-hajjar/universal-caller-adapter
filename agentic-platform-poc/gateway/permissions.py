"""
Permission engine — reads manifests and enforces MCP access rules.

Manifests are stored as Okta user profile attributes.
In dev mode, they can be loaded from a local JSON file.
"""

import json
import os
import logging
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Local fallback manifests for development
_DEV_MANIFESTS_PATH = Path(__file__).parent.parent / "manifests"


async def load_manifest_for_user(user_id: str) -> dict:
    """
    Load permission manifest for a user.

    In dev mode: reads from manifests/<user_id>.json
    In prod mode: fetches from Okta user profile attributes
    """
    if os.getenv("GATEWAY_DEV_MODE", "").lower() == "true":
        return _load_dev_manifest(user_id)

    from gateway.okta_client import OktaClient
    okta = OktaClient()
    return await okta.get_user_manifest(user_id)


def _load_dev_manifest(user_id: str) -> dict:
    """Load manifest from local JSON file for development."""
    # Try exact match first, then try email prefix
    candidates = [
        _DEV_MANIFESTS_PATH / f"{user_id}.json",
        _DEV_MANIFESTS_PATH / f"{user_id.replace('@', '_at_')}.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path) as f:
                return json.load(f)

    logger.warning("No manifest found for %s, returning empty manifest", user_id)
    return {"user_id": user_id, "role": "none", "mcp_servers": {}}


class PermissionEngine:
    """Evaluate permissions from a manifest."""

    def __init__(self, manifest: dict):
        self.manifest = manifest
        self.role = manifest.get("role", "none")
        self.servers = manifest.get("mcp_servers", {})

    def is_owner(self) -> bool:
        return self.role == "owner"

    def can_access_server(self, server_name: str) -> bool:
        server = self.servers.get(server_name, {})
        return server.get("enabled", False)

    def get_server_scope(self, server_name: str) -> str:
        server = self.servers.get(server_name, {})
        return server.get("scope", "none")

    def get_allowed_tables(self, server_name: str) -> list[str]:
        server = self.servers.get(server_name, {})
        return server.get("tables", [])

    def enforce_mariadb(self, action: str, body: dict):
        """
        Enforce MariaDB-specific permissions: table access and read/write scope.

        Parses SQL to extract referenced tables and checks against the manifest.
        """
        scope = self.get_server_scope("mariadb")
        allowed_tables = self.get_allowed_tables("mariadb")

        # Extract tables from the request
        sql = body.get("sql", body.get("query", ""))
        referenced_tables = _extract_tables_from_sql(sql)

        # Check table access
        for table in referenced_tables:
            if table not in allowed_tables:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: table '{table}' is not in your allowed tables {allowed_tables}",
                )

        # Check write scope
        if scope == "read_only":
            sql_upper = sql.strip().upper()
            write_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
            for kw in write_keywords:
                if sql_upper.startswith(kw):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied: your scope is read_only, cannot execute {kw} statements",
                    )


def _extract_tables_from_sql(sql: str) -> list[str]:
    """
    Simple SQL table extraction. Handles common patterns:
      SELECT ... FROM table
      INSERT INTO table
      UPDATE table
      DELETE FROM table
      JOIN table
    """
    import re

    tables = set()
    sql_clean = sql.strip()

    # FROM <table>
    for match in re.finditer(r'\bFROM\s+(\w+)', sql_clean, re.IGNORECASE):
        tables.add(match.group(1).lower())

    # JOIN <table>
    for match in re.finditer(r'\bJOIN\s+(\w+)', sql_clean, re.IGNORECASE):
        tables.add(match.group(1).lower())

    # INSERT INTO <table>
    for match in re.finditer(r'\bINTO\s+(\w+)', sql_clean, re.IGNORECASE):
        tables.add(match.group(1).lower())

    # UPDATE <table>
    for match in re.finditer(r'\bUPDATE\s+(\w+)', sql_clean, re.IGNORECASE):
        tables.add(match.group(1).lower())

    return list(tables)
