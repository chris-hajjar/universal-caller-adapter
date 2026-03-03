#!/usr/bin/env python3
"""
Claude Desktop config swap script.

Swaps the Claude Desktop MCP configuration to route through the gateway
as a specific test user.

Usage:
    python scripts/swap_claude_config.py chris    # Owner
    python scripts/swap_claude_config.py user_a   # Limited user A
    python scripts/swap_claude_config.py user_b   # Limited user B
"""

import json
import os
import platform
import shutil
import sys
from pathlib import Path

# Claude Desktop config locations by OS
CONFIG_PATHS = {
    "Darwin": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    "Windows": Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
    "Linux": Path.home() / ".config" / "claude" / "claude_desktop_config.json",
}

# User profiles
USERS = {
    "chris": {
        "email": "chris@company.com",
        "name": "Chris (Owner)",
    },
    "user_a": {
        "email": "user_a@company.com",
        "name": "User A (Limited)",
    },
    "user_b": {
        "email": "user_b@company.com",
        "name": "User B (Limited)",
    },
}

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")


def get_config_path() -> Path:
    system = platform.system()
    path = CONFIG_PATHS.get(system)
    if not path:
        print(f"Unsupported OS: {system}")
        sys.exit(1)
    return path


def build_config(user_key: str) -> dict:
    """Build a Claude Desktop config that routes MCP through the gateway."""
    user = USERS[user_key]
    token = f"dev:{user['email']}"

    return {
        "mcpServers": {
            "agentic-gateway-mariadb": {
                "command": "npx",
                "args": [
                    "-y",
                    "mcp-remote",
                    f"{GATEWAY_URL}/mcp/mariadb",
                    "--header",
                    f"Authorization: Bearer {token}",
                ],
            },
            "agentic-gateway-memory": {
                "command": "npx",
                "args": [
                    "-y",
                    "mcp-remote",
                    f"{GATEWAY_URL}/mcp/memory",
                    "--header",
                    f"Authorization: Bearer {token}",
                ],
            },
        },
    }


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in USERS:
        print(f"Usage: python {sys.argv[0]} <{'|'.join(USERS.keys())}>")
        print("\nAvailable users:")
        for key, user in USERS.items():
            print(f"  {key:10s} → {user['name']} ({user['email']})")
        sys.exit(1)

    user_key = sys.argv[1]
    user = USERS[user_key]
    config_path = get_config_path()

    # Backup existing config
    if config_path.exists():
        backup = config_path.with_suffix(".json.backup")
        shutil.copy2(config_path, backup)
        print(f"Backed up existing config to {backup}")

    # Write new config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = build_config(user_key)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nClaude Desktop config updated for: {user['name']}")
    print(f"  Email:  {user['email']}")
    print(f"  Config: {config_path}")
    print(f"\nRestart Claude Desktop to apply changes.")


if __name__ == "__main__":
    main()
