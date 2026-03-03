"""
MCP Router — routes requests to the correct MCP server.

Each MCP server is an external process or HTTP endpoint.
The router manages connections and forwards requests.
"""

import os
import logging
from typing import Any

import httpx

from gateway.auth import UserToken

logger = logging.getLogger(__name__)


class MCPRouter:
    """Routes requests to registered MCP servers."""

    def __init__(self):
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._server_urls: dict[str, str] = {}

    async def initialize(self):
        """Load MCP server URLs from environment and create HTTP clients."""
        self._server_urls = {
            "mariadb": os.getenv("MCP_MARIADB_URL", "http://localhost:8001"),
            "memory": os.getenv("MCP_MEMORY_URL", "http://localhost:8002"),
            "slack": os.getenv("MCP_SLACK_URL", "http://localhost:8003"),
            "reports": os.getenv("MCP_REPORTS_URL", "http://localhost:8004"),
        }

        for name, url in self._server_urls.items():
            self._clients[name] = httpx.AsyncClient(
                base_url=url,
                timeout=30.0,
            )
            logger.info("Registered MCP server: %s → %s", name, url)

    async def shutdown(self):
        """Close all HTTP clients."""
        for client in self._clients.values():
            await client.aclose()

    async def route(
        self,
        server_name: str,
        action: str,
        body: dict,
        user: UserToken,
    ) -> Any:
        """
        Route a request to the named MCP server.

        Args:
            server_name: Which MCP server (mariadb, memory, slack, reports)
            action: The action to perform (e.g. query, search, send)
            body: Request payload
            user: Authenticated user
        """
        client = self._clients.get(server_name)
        if client is None:
            raise ValueError(f"Unknown MCP server: {server_name}")

        # Add user context to the request
        payload = {
            **body,
            "_user_id": user.user_id,
            "_user_email": user.email,
        }

        try:
            response = await client.post(f"/{action}", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error("Cannot connect to MCP server %s at %s", server_name, self._server_urls[server_name])
            return {"error": f"MCP server '{server_name}' is not reachable", "status": "unavailable"}
        except httpx.HTTPStatusError as e:
            logger.error("MCP server %s returned %s: %s", server_name, e.response.status_code, e.response.text)
            return {"error": f"MCP server error: {e.response.status_code}", "detail": e.response.text}
