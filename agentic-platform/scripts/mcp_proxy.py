"""
MCP Proxy — thin MCP server that forwards to the gateway REST API.

This script is what Claude Desktop actually connects to. It speaks
the MCP protocol (JSON-RPC over stdio) and forwards every tool call
to the gateway, including the user's auth token.

Configured via environment variables:
    GATEWAY_URL  — Gateway API URL (default: http://localhost:8000)
    AUTH_TOKEN   — User's auth token for the gateway
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import httpx

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    filename=os.path.expanduser("~/.mcp_proxy.log"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Gateway communication
# ---------------------------------------------------------------------------

def list_tools() -> list[dict[str, Any]]:
    """Fetch available tools from the gateway."""
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{GATEWAY_URL}/mcp/tools", headers=_headers())
            resp.raise_for_status()
            tools = resp.json()

            # Convert to MCP tool format
            return [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("input_schema", {"type": "object", "properties": {}}),
                }
                for tool in tools
            ]
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return []


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Call a tool through the gateway."""
    # Parse server_name.tool_name format
    parts = name.split(".", 1)
    if len(parts) == 2:
        server_name, tool_name = parts
    else:
        server_name = "mariadb"  # Default server
        tool_name = name

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{GATEWAY_URL}/mcp/call",
                headers=_headers(),
                json={
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            )

            if resp.status_code == 403:
                error = resp.json().get("detail", "Permission denied")
                return {"isError": True, "content": [{"type": "text", "text": f"Permission denied: {error}"}]}

            resp.raise_for_status()
            data = resp.json()

            if data.get("error"):
                return {"isError": True, "content": [{"type": "text", "text": data["error"]}]}

            result = data.get("result", data)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2) if not isinstance(result, str) else result}]}

    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"isError": True, "content": [{"type": "text", "text": f"Error: {detail}"}]}
    except Exception as e:
        logger.error(f"Failed to call tool {name}: {e}")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}


# ---------------------------------------------------------------------------
# JSON-RPC stdio transport (MCP protocol)
# ---------------------------------------------------------------------------

def _read_message() -> dict[str, Any] | None:
    """Read a JSON-RPC message from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def _write_message(msg: dict[str, Any]) -> None:
    """Write a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _jsonrpc_response(id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "agentic-gateway-proxy",
                "version": "0.1.0",
            },
        })

    elif method == "notifications/initialized":
        # No response needed for notifications
        return None

    elif method == "tools/list":
        tools = list_tools()
        return _jsonrpc_response(req_id, {"tools": tools})

    elif method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = call_tool(name, arguments)
        return _jsonrpc_response(req_id, result)

    elif method == "ping":
        return _jsonrpc_response(req_id, {})

    else:
        logger.warning(f"Unknown method: {method}")
        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


def main():
    """Run the MCP proxy server (stdio transport)."""
    logger.info(f"MCP proxy starting — gateway: {GATEWAY_URL}")

    while True:
        message = _read_message()
        if message is None:
            break

        logger.info(f"Request: {message.get('method')}")

        response = handle_request(message)
        if response is not None:
            _write_message(response)

    logger.info("MCP proxy shutting down")


if __name__ == "__main__":
    main()
