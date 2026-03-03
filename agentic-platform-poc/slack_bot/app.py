"""
Slack Bot — routes messages through the Agentic Platform Gateway.

Uses Bolt for Python. Every message from a Slack user:
  1. Resolves the Slack user to their email (Okta identity)
  2. Sends the message through the gateway (with their token)
  3. Returns the gateway response in the Slack thread

This means Slack users get the same permissions and memory sync
as Claude Desktop users — the gateway is the single enforcement point.
"""

import os
import logging
import re

import httpx
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Slack tokens
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")

# Gateway URL
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

app = App(token=SLACK_BOT_TOKEN)

# Cache: slack_user_id → email
_user_email_cache: dict[str, str] = {}


def _get_user_email(client, user_id: str) -> str:
    """Resolve Slack user ID to email address."""
    if user_id in _user_email_cache:
        return _user_email_cache[user_id]

    resp = client.users_info(user=user_id)
    email = resp["user"]["profile"].get("email", "")
    if email:
        _user_email_cache[user_id] = email
    return email


def _parse_intent(text: str) -> tuple[str, str, dict]:
    """
    Parse a natural language message into an MCP server/action/body.

    Simple pattern matching for the POC:
      "query invoices" → mariadb/query {"sql": "SELECT * FROM invoices LIMIT 10"}
      "search memory for <topic>" → memory/search {"query": "<topic>"}
      "remember <text>" → memory/store {"content": "<text>"}

    In production, this would be an LLM call.
    """
    text_lower = text.strip().lower()

    # Memory search
    match = re.match(r"search memory (?:for )?(.+)", text_lower)
    if match:
        return "memory", "search", {"query": match.group(1)}

    # Memory store
    match = re.match(r"remember (.+)", text_lower)
    if match:
        return "memory", "store", {"content": match.group(1)}

    # Memory delete
    match = re.match(r"forget ([a-f0-9-]+)", text_lower)
    if match:
        return "memory", "delete", {"memory_id": match.group(1)}

    # SQL query - direct
    match = re.match(r"sql (.+)", text_lower, re.DOTALL)
    if match:
        return "mariadb", "query", {"sql": match.group(1)}

    # Table query shorthand
    match = re.match(r"query (\w+)", text_lower)
    if match:
        table = match.group(1)
        return "mariadb", "query", {"sql": f"SELECT * FROM {table} LIMIT 10"}

    # Default: treat as a query to mariadb
    return "mariadb", "query", {"sql": text}


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @bot mentions in channels."""
    user_id = event.get("user", "")
    text = event.get("text", "")
    thread_ts = event.get("ts", "")

    # Strip the bot mention from the text
    text = re.sub(r"<@\w+>\s*", "", text).strip()

    if not text:
        say("What would you like me to do?", thread_ts=thread_ts)
        return

    _process_message(client, say, user_id, text, thread_ts)


@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages to the bot."""
    # Skip bot messages to prevent loops
    if event.get("subtype") == "bot_message" or event.get("bot_id"):
        return

    user_id = event.get("user", "")
    text = event.get("text", "")
    thread_ts = event.get("ts", "")

    if not text:
        return

    _process_message(client, say, user_id, text, thread_ts)


def _process_message(client, say, user_id: str, text: str, thread_ts: str):
    """Route a message through the gateway and respond."""
    email = _get_user_email(client, user_id)
    if not email:
        say("I couldn't find your email address. Make sure your Slack profile has an email set.", thread_ts=thread_ts)
        return

    server_name, action, body = _parse_intent(text)

    # Use dev token for the gateway
    dev_mode = os.getenv("GATEWAY_DEV_MODE", "").lower() == "true"
    if dev_mode:
        token = f"dev:{email}"
    else:
        # In production, exchange Slack identity for an Okta token
        # For POC, we use dev mode
        token = f"dev:{email}"

    try:
        # Memory store/search/delete use dedicated endpoints, not the MCP proxy
        if server_name == "memory":
            url = f"{GATEWAY_URL}/memory/{action}"
        else:
            url = f"{GATEWAY_URL}/mcp/{server_name}/{action}"

        with httpx.Client(timeout=30.0) as http:
            resp = http.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code == 403:
            error = resp.json().get("detail", "Access denied")
            say(f"Permission denied: {error}", thread_ts=thread_ts)
            return

        if resp.status_code != 200:
            say(f"Gateway error ({resp.status_code}): {resp.text[:200]}", thread_ts=thread_ts)
            return

        result = resp.json()
        _format_and_respond(say, server_name, action, result, thread_ts)

    except httpx.ConnectError:
        say("Gateway is not reachable. Is it running?", thread_ts=thread_ts)
    except Exception as e:
        logger.exception("Error processing message")
        say(f"Something went wrong: {e}", thread_ts=thread_ts)


def _format_and_respond(say, server_name: str, action: str, result: dict, thread_ts: str):
    """Format the gateway response for Slack."""
    inner = result.get("result", result)

    if isinstance(inner, dict) and "error" in inner:
        say(f"Error from {server_name}: {inner['error']}", thread_ts=thread_ts)
        return

    # Pretty-print the result
    import json
    formatted = json.dumps(inner, indent=2, default=str)
    if len(formatted) > 3000:
        formatted = formatted[:3000] + "\n... (truncated)"

    say(f"*{server_name}/{action}*\n```{formatted}```", thread_ts=thread_ts)


def start():
    """Start the Slack bot in Socket Mode."""
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("Slack bot starting in Socket Mode")
    handler.start()


if __name__ == "__main__":
    start()
