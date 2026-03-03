"""
Claude Desktop config swap script.

Generates and swaps the Claude Desktop MCP configuration to route
through the gateway as a specific user. Each user gets their own
config pointing to the gateway with their auth token.

Usage:
    python scripts/claude_config_swap.py user_a
    python scripts/claude_config_swap.py user_b
    python scripts/claude_config_swap.py owner
    python scripts/claude_config_swap.py --list
    python scripts/claude_config_swap.py --restore
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

# Test user configs
USER_CONFIGS = {
    "owner": {
        "email": "chris@company.com",
        "token": os.getenv("OWNER_TOKEN", "chris@company.com"),
        "description": "Owner — full access to all MCP servers",
    },
    "user_a": {
        "email": "user_a@company.com",
        "token": os.getenv("USER_A_TOKEN", "user_a@company.com"),
        "description": "Standard — invoices, orders, products (read-only) + memory + slack",
    },
    "user_b": {
        "email": "user_b@company.com",
        "token": os.getenv("USER_B_TOKEN", "user_b@company.com"),
        "description": "Limited — invoices only (read-only) + memory, no slack",
    },
}


def get_claude_config_path() -> Path:
    """Get the Claude Desktop config file path for the current OS."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_backup_path(config_path: Path) -> Path:
    """Get the backup path for the original config."""
    return config_path.with_suffix(".json.backup")


def generate_config(user_key: str) -> dict:
    """
    Generate a Claude Desktop MCP config that routes through the gateway.

    The MCP proxy server is a small Python script that:
    1. Speaks MCP protocol (stdio) to Claude Desktop
    2. Forwards all calls to the gateway REST API
    3. Includes the user's auth token in every request
    """
    user = USER_CONFIGS[user_key]

    return {
        "mcpServers": {
            "agentic-gateway": {
                "command": sys.executable,
                "args": [
                    os.path.join(os.path.dirname(__file__), "mcp_proxy.py"),
                ],
                "env": {
                    "GATEWAY_URL": GATEWAY_URL,
                    "AUTH_TOKEN": user["token"],
                },
            },
        },
    }


def swap_config(user_key: str) -> None:
    """Swap the Claude Desktop config to the specified user."""
    if user_key not in USER_CONFIGS:
        print(f"Unknown user: {user_key}")
        print(f"Available users: {', '.join(USER_CONFIGS.keys())}")
        sys.exit(1)

    config_path = get_claude_config_path()
    backup_path = get_backup_path(config_path)

    # Backup existing config if not already backed up
    if config_path.exists() and not backup_path.exists():
        shutil.copy2(config_path, backup_path)
        print(f"Backed up existing config to {backup_path}")

    # Generate and write new config
    config = generate_config(user_key)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))

    user = USER_CONFIGS[user_key]
    print(f"Config swapped to: {user['email']}")
    print(f"  {user['description']}")
    print(f"  Config: {config_path}")
    print()
    print("Restart Claude Desktop to apply the new config.")


def restore_config() -> None:
    """Restore the original Claude Desktop config from backup."""
    config_path = get_claude_config_path()
    backup_path = get_backup_path(config_path)

    if not backup_path.exists():
        print("No backup found — nothing to restore.")
        return

    shutil.copy2(backup_path, config_path)
    print(f"Restored config from {backup_path}")
    print("Restart Claude Desktop to apply.")


def list_users() -> None:
    """List available user configurations."""
    print("Available user configurations:\n")
    for key, user in USER_CONFIGS.items():
        print(f"  {key:10s}  {user['email']}")
        print(f"             {user['description']}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Swap Claude Desktop MCP config for different test users"
    )
    parser.add_argument(
        "user",
        nargs="?",
        help="User to swap to (owner, user_a, user_b)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available user configurations",
    )
    parser.add_argument(
        "--restore", "-r",
        action="store_true",
        help="Restore original config from backup",
    )
    parser.add_argument(
        "--show", "-s",
        action="store_true",
        help="Show the config that would be generated (don't write)",
    )

    args = parser.parse_args()

    if args.list:
        list_users()
    elif args.restore:
        restore_config()
    elif args.user:
        if args.show:
            config = generate_config(args.user)
            print(json.dumps(config, indent=2))
        else:
            swap_config(args.user)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
