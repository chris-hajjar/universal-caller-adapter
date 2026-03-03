"""
MCP Router — routes tool calls to backend MCP servers.

The gateway acts as a single MCP server to clients. Internally it
maintains connections to multiple backend MCP servers and routes
calls based on the tool's server_name, applying permission enforcement
before forwarding.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .models import MCPServerInfo, MCPToolCall, MCPToolInfo, MCPToolResult, UserContext
from .permissions import check_mcp_call_permissions

logger = logging.getLogger(__name__)


class MCPRouter:
    """Routes MCP tool calls to registered backend servers."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerInfo] = {}
        self._http = httpx.AsyncClient(timeout=30.0)

    def register_server(self, name: str, url: str, description: str = "") -> None:
        """Register a backend MCP server."""
        self._servers[name] = MCPServerInfo(
            name=name, url=url, description=description
        )
        logger.info(f"Registered MCP server: {name} -> {url}")

    def get_server(self, name: str) -> MCPServerInfo | None:
        return self._servers.get(name)

    @property
    def server_names(self) -> list[str]:
        return list(self._servers.keys())

    # ------------------------------------------------------------------
    # Tool listing (aggregated across allowed servers)
    # ------------------------------------------------------------------

    async def list_tools(self, user: UserContext) -> list[MCPToolInfo]:
        """
        List all tools the user has access to, aggregated across all
        MCP servers they're allowed to use.
        """
        tools: list[MCPToolInfo] = []

        for name, server in self._servers.items():
            if not user.manifest.server_enabled(name) and not user.is_owner:
                continue

            server_tools = await self._fetch_server_tools(name, server)
            tools.extend(server_tools)

        return tools

    async def _fetch_server_tools(
        self, name: str, server: MCPServerInfo
    ) -> list[MCPToolInfo]:
        """Fetch tool list from a backend MCP server."""
        try:
            resp = await self._http.post(
                f"{server.url}/tools/list",
                json={},
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                MCPToolInfo(
                    name=f"{name}.{tool['name']}",
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
                for tool in data.get("tools", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list tools from {name}: {e}")
            return []

    # ------------------------------------------------------------------
    # Tool calling (with permission enforcement)
    # ------------------------------------------------------------------

    async def call_tool(
        self, user: UserContext, call: MCPToolCall
    ) -> MCPToolResult:
        """
        Route an MCP tool call to the appropriate backend server,
        enforcing permissions before forwarding.
        """
        # 1. Permission check (raises HTTPException on deny)
        check_mcp_call_permissions(
            user, call.server_name, call.tool_name, call.arguments
        )

        # 2. Look up the server
        server = self.get_server(call.server_name)
        if server is None:
            return MCPToolResult(
                server_name=call.server_name,
                tool_name=call.tool_name,
                error=f"Unknown MCP server: {call.server_name}",
            )

        # 3. Inject user namespace for memory server
        arguments = dict(call.arguments)
        if call.server_name == "memory":
            arguments["user_id"] = user.user_id

        # 4. Forward to backend server
        return await self._forward_call(server, call.tool_name, arguments)

    async def _forward_call(
        self,
        server: MCPServerInfo,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Forward a tool call to a backend MCP server via HTTP."""
        try:
            resp = await self._http.post(
                f"{server.url}/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return MCPToolResult(
                server_name=server.name,
                tool_name=tool_name,
                result=data.get("result", data.get("content")),
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP server {server.name} returned {e.response.status_code}")
            return MCPToolResult(
                server_name=server.name,
                tool_name=tool_name,
                error=f"Server error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Failed to call {server.name}.{tool_name}: {e}")
            return MCPToolResult(
                server_name=server.name,
                tool_name=tool_name,
                error=str(e),
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()


# ---------------------------------------------------------------------------
# Singleton router — configured from environment
# ---------------------------------------------------------------------------

def create_router() -> MCPRouter:
    """
    Create and configure the MCP router from environment variables.

    Expected env vars:
        MCP_MARIADB_URL  — URL of the MariaDB MCP server
        MCP_MEMORY_URL   — URL of the Memory MCP server
        MCP_SLACK_URL    — URL of the Slack MCP server
        MCP_REPORTS_URL  — URL of the Reports MCP server
    """
    router = MCPRouter()

    mariadb_url = os.getenv("MCP_MARIADB_URL", "http://localhost:8001")
    memory_url = os.getenv("MCP_MEMORY_URL", "http://localhost:8002")
    slack_url = os.getenv("MCP_SLACK_URL", "http://localhost:8003")
    reports_url = os.getenv("MCP_REPORTS_URL", "http://localhost:8004")

    router.register_server("mariadb", mariadb_url, "MariaDB business data")
    router.register_server("memory", memory_url, "Conversation memory (pgvector)")
    router.register_server("slack", slack_url, "Slack messaging")
    router.register_server("reports", reports_url, "Report generation")

    return router
