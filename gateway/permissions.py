"""
Permission enforcement layer.

Reads the user's manifest and gates access to MCP servers, tables, and
operations. This is the single enforcement point — MCP servers themselves
are dumb executors that trust whatever the gateway sends them.
"""

from __future__ import annotations

import logging
import re

from fastapi import HTTPException

from .models import MCPServerScope, PermissionManifest, UserContext

logger = logging.getLogger(__name__)


class PermissionDenied(HTTPException):
    """Raised when a user tries to access something they shouldn't."""

    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


# ---------------------------------------------------------------------------
# Top-level enforcement
# ---------------------------------------------------------------------------

def enforce_server_access(user: UserContext, server_name: str) -> None:
    """
    Check that the user has access to the named MCP server.
    Raises PermissionDenied if not.
    """
    if user.is_owner:
        return  # Owner bypasses all checks

    if not user.manifest.server_enabled(server_name):
        logger.warning(
            f"Access denied: {user.email} tried to access MCP server '{server_name}'"
        )
        raise PermissionDenied(
            f"You do not have access to the '{server_name}' server"
        )


def enforce_table_access(user: UserContext, server_name: str, table: str) -> None:
    """
    Check that the user has access to a specific table on the MariaDB MCP server.
    Only relevant for the mariadb server; no-ops for others.
    """
    if user.is_owner:
        return

    perm = user.manifest.get_server_permission(server_name)
    if perm is None:
        raise PermissionDenied(f"No permissions for server '{server_name}'")

    if perm.tables is not None and table not in perm.tables:
        logger.warning(
            f"Table denied: {user.email} tried to access table '{table}' "
            f"(allowed: {perm.tables})"
        )
        raise PermissionDenied(
            f"You do not have access to the '{table}' table"
        )


def enforce_write_access(user: UserContext, server_name: str) -> None:
    """
    Check that the user has write access to the named MCP server.
    Raises PermissionDenied if the user is read-only.
    """
    if user.is_owner:
        return

    perm = user.manifest.get_server_permission(server_name)
    if perm is None:
        raise PermissionDenied(f"No permissions for server '{server_name}'")

    if perm.scope == MCPServerScope.READ_ONLY:
        logger.warning(
            f"Write denied: {user.email} tried to write to '{server_name}' (read-only)"
        )
        raise PermissionDenied(
            f"You have read-only access to '{server_name}'"
        )


# ---------------------------------------------------------------------------
# SQL-level enforcement for MariaDB
# ---------------------------------------------------------------------------

# Write operations that should be blocked for read-only users
_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)

# Extract table names from common SQL patterns
_TABLE_PATTERN = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+`?(\w+)`?",
    re.IGNORECASE,
)


def enforce_sql_permissions(
    user: UserContext, server_name: str, sql: str
) -> None:
    """
    Parse a SQL query and enforce table-level and read/write permissions.

    This is deliberately simple — production would use a proper SQL parser.
    For the POC, regex-based extraction is sufficient to demonstrate the
    permission model.
    """
    if user.is_owner:
        return

    perm = user.manifest.get_server_permission(server_name)
    if perm is None:
        raise PermissionDenied(f"No permissions for server '{server_name}'")

    # Check write operations
    if _WRITE_KEYWORDS.search(sql):
        if perm.scope == MCPServerScope.READ_ONLY:
            raise PermissionDenied(
                "Write operations are not allowed — you have read-only access"
            )

    # Check table access
    if perm.tables is not None:
        referenced_tables = _TABLE_PATTERN.findall(sql)
        for table in referenced_tables:
            table_lower = table.lower()
            allowed_lower = [t.lower() for t in perm.tables]
            if table_lower not in allowed_lower:
                raise PermissionDenied(
                    f"You do not have access to the '{table}' table. "
                    f"Allowed tables: {', '.join(perm.tables)}"
                )


# ---------------------------------------------------------------------------
# High-level permission check (used by MCP router)
# ---------------------------------------------------------------------------

def check_mcp_call_permissions(
    user: UserContext,
    server_name: str,
    tool_name: str,
    arguments: dict,
) -> None:
    """
    Comprehensive permission check for an MCP tool call.

    Checks server access, and for MariaDB specifically, checks table-level
    and read/write permissions on any SQL in the arguments.
    """
    # 1. Server-level access
    enforce_server_access(user, server_name)

    # 2. MariaDB-specific: SQL-level enforcement
    if server_name == "mariadb":
        sql = arguments.get("query") or arguments.get("sql") or ""
        if sql:
            enforce_sql_permissions(user, server_name, sql)

    # 3. Memory server: namespace enforcement (personal_only)
    if server_name == "memory":
        perm = user.manifest.get_server_permission(server_name)
        if perm and perm.scope == MCPServerScope.READ_ONLY:
            # Read-only memory users can search but not store
            if tool_name in ("store_memory", "store", "write"):
                raise PermissionDenied(
                    "You have read-only access to memory"
                )
