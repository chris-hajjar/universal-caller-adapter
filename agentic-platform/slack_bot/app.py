"""
Slack Bot — routes user messages through the gateway.

Uses Bolt for Python (slack_bolt). Messages from Slack users are
routed through the same gateway as Claude Desktop, so permissions
and memory sync work identically.

The bot:
  1. Receives a Slack message
  2. Looks up the Slack user's email → maps to their Okta identity
  3. Calls the gateway API with the user's scoped token
  4. Returns the result in Slack

Usage:
    python -m slack_bot.app
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")  # xapp-... for socket mode
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

# Map Slack user IDs to gateway auth tokens (set via env or config)
# In production, this would do an Okta lookup by Slack email
SLACK_USER_TOKENS: dict[str, str] = {}

# Load user token mappings from env
# Format: SLACK_USER_MAP=U01ABC:token1,U02DEF:token2
_user_map = os.getenv("SLACK_USER_MAP", "")
if _user_map:
    for pair in _user_map.split(","):
        if ":" in pair:
            slack_id, token = pair.split(":", 1)
            SLACK_USER_TOKENS[slack_id.strip()] = token.strip()

# ---------------------------------------------------------------------------
# Slack app
# ---------------------------------------------------------------------------

app = App(token=SLACK_BOT_TOKEN)


def _get_user_token(slack_user_id: str) -> str | None:
    """Get the gateway auth token for a Slack user."""
    return SLACK_USER_TOKENS.get(slack_user_id)


async def _call_gateway(
    token: str,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call the gateway API with the user's token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/mcp/call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
            },
            timeout=30.0,
        )
        return resp.json()


def _call_gateway_sync(
    token: str,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Synchronous version of _call_gateway for Bolt handlers."""
    with httpx.Client() as client:
        resp = client.post(
            f"{GATEWAY_URL}/mcp/call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
            },
            timeout=30.0,
        )
        return resp.json()


# ---------------------------------------------------------------------------
# Message handler — interprets natural language into MCP calls
# ---------------------------------------------------------------------------

@app.message("")
def handle_message(message, say, client):
    """
    Handle incoming Slack messages.

    For the POC, this uses simple keyword matching to route to MCP tools.
    In production, this would use an LLM to interpret the message and
    decide which tools to call.
    """
    slack_user_id = message.get("user", "")
    text = message.get("text", "").strip()

    if not text:
        return

    # Get the user's gateway token
    token = _get_user_token(slack_user_id)
    if not token:
        say(
            f"I don't have credentials configured for your account. "
            f"Please ask the admin to set up your access."
        )
        return

    logger.info(f"Message from {slack_user_id}: {text}")

    # Simple command routing for the POC
    try:
        if text.lower().startswith("query "):
            _handle_query(token, text[6:].strip(), say)
        elif text.lower().startswith("remember "):
            _handle_remember(token, text[9:].strip(), say)
        elif text.lower().startswith("recall"):
            _handle_recall(token, text[6:].strip(), say)
        elif text.lower() == "help":
            _handle_help(say)
        else:
            # Default: store as memory and acknowledge
            _call_gateway_sync(token, "memory", "store", {"content": text})
            say("Got it, I'll remember that.")
    except Exception as e:
        error_data = {}
        if isinstance(e, httpx.HTTPStatusError):
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {"detail": str(e)}
        else:
            error_data = {"detail": str(e)}

        detail = error_data.get("detail", str(e))
        say(f"Sorry, I couldn't do that: {detail}")


def _handle_query(token: str, sql: str, say):
    """Execute a SQL query against MariaDB through the gateway."""
    result = _call_gateway_sync(token, "mariadb", "query", {"query": sql})

    if result.get("error"):
        say(f"Query failed: {result['error']}")
        return

    data = result.get("result", [])
    if not data:
        say("Query returned no results.")
        return

    # Format results as a simple table
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            lines = [" | ".join(headers)]
            lines.append("-" * len(lines[0]))
            for row in data[:20]:  # Limit display to 20 rows
                lines.append(" | ".join(str(row.get(h, "")) for h in headers))
            say(f"```\n{chr(10).join(lines)}\n```")
        else:
            say(f"```\n{json.dumps(data, indent=2)}\n```")
    else:
        say(f"```\n{json.dumps(data, indent=2)}\n```")


def _handle_remember(token: str, content: str, say):
    """Store a memory through the gateway."""
    result = _call_gateway_sync(token, "memory", "store", {"content": content})
    if result.get("error"):
        say(f"Couldn't store that: {result['error']}")
    else:
        say("Stored in memory.")


def _handle_recall(token: str, query: str, say):
    """Search memories through the gateway."""
    if not query.strip():
        query = "recent context"

    result = _call_gateway_sync(token, "memory", "search", {"query": query})
    if result.get("error"):
        say(f"Memory search failed: {result['error']}")
        return

    memories = result.get("result", [])
    if not memories:
        say("No relevant memories found.")
        return

    lines = ["Here's what I remember:"]
    for i, mem in enumerate(memories, 1):
        content = mem.get("content", "")
        similarity = mem.get("similarity", 0)
        lines.append(f"{i}. {content[:200]} (relevance: {similarity:.2f})")

    say("\n".join(lines))


def _handle_help(say):
    """Show available commands."""
    say(
        "*Available commands:*\n"
        "• `query <SQL>` — Run a SQL query against the database\n"
        "• `remember <text>` — Store something in memory\n"
        "• `recall [topic]` — Search your memories\n"
        "• `help` — Show this message\n"
        "• Or just chat — I'll remember what you say"
    )


# ---------------------------------------------------------------------------
# App mention handler
# ---------------------------------------------------------------------------

@app.event("app_mention")
def handle_mention(event, say):
    """Handle @mentions of the bot."""
    text = event.get("text", "")
    # Strip the bot mention from the text
    # Mentions look like <@U12345> rest of message
    parts = text.split(">", 1)
    if len(parts) > 1:
        text = parts[1].strip()

    # Reuse the message handler logic
    handle_message(
        {"user": event.get("user", ""), "text": text},
        say,
        None,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not SLACK_BOT_TOKEN:
        print("Error: SLACK_BOT_TOKEN is not set")
        print("Set it in your .env file or environment")
        return

    if SLACK_APP_TOKEN:
        # Socket mode (recommended for development)
        print("Starting Slack bot in socket mode...")
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    else:
        # HTTP mode (for production with Slack Events API)
        print("Starting Slack bot in HTTP mode on port 3000...")
        app.start(port=3000)


if __name__ == "__main__":
    main()
