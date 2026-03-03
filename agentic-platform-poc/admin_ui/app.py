"""
Admin UI — Streamlit dashboard for managing MCP permissions.

Single page with three sections:
  1. User List — all users, their roles, enabled MCPs
  2. MCP Permission Grid — toggle access per user per server
  3. Live Manifest Preview — raw JSON, updates in real time

Owner-only access.
"""

import os
import json
import logging

import streamlit as st
import httpx

logger = logging.getLogger(__name__)

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "chris@company.com")

# Dev mode token for the owner
OWNER_TOKEN = f"dev:{OWNER_EMAIL}"

# Available MCP servers and their configurable options
MCP_SERVERS = {
    "mariadb": {
        "label": "MariaDB",
        "has_tables": True,
        "tables": ["invoices", "orders", "users", "products", "reports"],
        "has_scope": True,
        "scopes": ["read_only", "read_write"],
    },
    "memory": {
        "label": "Memory MCP",
        "has_tables": False,
        "has_scope": True,
        "scopes": ["personal_only"],
    },
    "slack_mcp": {
        "label": "Slack MCP",
        "has_tables": False,
        "has_scope": False,
    },
    "reports": {
        "label": "Reports MCP",
        "has_tables": False,
        "has_scope": False,
    },
}


def _gateway_headers() -> dict:
    return {"Authorization": f"Bearer {OWNER_TOKEN}"}


def _fetch_users() -> list[dict]:
    """Fetch all users from the gateway."""
    try:
        resp = httpx.get(f"{GATEWAY_URL}/admin/users", headers=_gateway_headers(), timeout=10.0)
        if resp.status_code == 200:
            return resp.json().get("users", [])
    except httpx.ConnectError:
        st.error("Cannot connect to gateway. Is it running?")
    return []


def _fetch_manifest(user_email: str) -> dict:
    """Fetch a user's permission manifest."""
    try:
        resp = httpx.get(
            f"{GATEWAY_URL}/admin/manifest/{user_email}",
            headers=_gateway_headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
    except httpx.ConnectError:
        st.error("Cannot connect to gateway.")
    return {"user_id": user_email, "role": "none", "mcp_servers": {}}


def _save_manifest(user_email: str, manifest: dict):
    """Save a user's permission manifest via the gateway."""
    try:
        resp = httpx.put(
            f"{GATEWAY_URL}/admin/manifest/{user_email}",
            json=manifest,
            headers=_gateway_headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            st.success(f"Manifest saved for {user_email}")
        else:
            st.error(f"Failed to save: {resp.text}")
    except httpx.ConnectError:
        st.error("Cannot connect to gateway.")


def main():
    st.set_page_config(page_title="Agentic Platform Admin", layout="wide")
    st.title("Agentic Platform — Admin UI")
    st.caption("Manage MCP server permissions per user. Changes take effect immediately.")

    # -----------------------------------------------------------------------
    # Section 1 — User List
    # -----------------------------------------------------------------------
    st.header("Users")

    users = _fetch_users()
    if not users:
        st.info(
            "No users loaded. In dev mode, users come from local manifests. "
            "Make sure the gateway is running."
        )
        # Dev mode fallback: show hardcoded test users
        users = [
            {"email": "chris@company.com", "name": "Chris (Owner)"},
            {"email": "user_a@company.com", "name": "User A"},
            {"email": "user_b@company.com", "name": "User B"},
        ]

    user_emails = [u["email"] for u in users]
    user_names = {u["email"]: u.get("name", u["email"]) for u in users}

    selected_email = st.selectbox(
        "Select a user to manage",
        user_emails,
        format_func=lambda e: f"{user_names.get(e, e)} ({e})",
    )

    if not selected_email:
        return

    # -----------------------------------------------------------------------
    # Section 2 — MCP Permission Grid
    # -----------------------------------------------------------------------
    st.header(f"MCP Permissions — {user_names.get(selected_email, selected_email)}")

    manifest = _fetch_manifest(selected_email)
    servers = manifest.get("mcp_servers", {})
    role = manifest.get("role", "none")

    if role == "owner":
        st.info("This user is an **owner** — all permissions are implicit. No restrictions applied.")
        st.json(manifest)
        return

    st.markdown("---")

    updated_servers = {}

    for server_key, server_config in MCP_SERVERS.items():
        current = servers.get(server_key, {})

        col1, col2 = st.columns([1, 3])

        with col1:
            enabled = st.checkbox(
                f"**{server_config['label']}**",
                value=current.get("enabled", False),
                key=f"enable_{selected_email}_{server_key}",
            )

        server_entry = {"enabled": enabled}

        with col2:
            if enabled:
                # Scope selector
                if server_config.get("has_scope"):
                    current_scope = current.get("scope", server_config["scopes"][0])
                    scope_idx = (
                        server_config["scopes"].index(current_scope)
                        if current_scope in server_config["scopes"]
                        else 0
                    )
                    scope = st.radio(
                        "Scope",
                        server_config["scopes"],
                        index=scope_idx,
                        key=f"scope_{selected_email}_{server_key}",
                        horizontal=True,
                    )
                    server_entry["scope"] = scope

                # Table checklist (MariaDB)
                if server_config.get("has_tables"):
                    current_tables = current.get("tables", [])
                    st.markdown("**Tables:**")
                    selected_tables = []
                    cols = st.columns(len(server_config["tables"]))
                    for i, table in enumerate(server_config["tables"]):
                        with cols[i]:
                            if st.checkbox(
                                table,
                                value=table in current_tables,
                                key=f"table_{selected_email}_{server_key}_{table}",
                            ):
                                selected_tables.append(table)
                    server_entry["tables"] = selected_tables
            else:
                st.caption("Disabled")

        updated_servers[server_key] = server_entry
        st.markdown("---")

    # -----------------------------------------------------------------------
    # Save button
    # -----------------------------------------------------------------------
    if st.button("Save Permissions", type="primary"):
        updated_manifest = {
            "user_id": selected_email,
            "role": role,
            "mcp_servers": updated_servers,
        }
        _save_manifest(selected_email, updated_manifest)
        st.rerun()

    # -----------------------------------------------------------------------
    # Section 3 — Live Manifest Preview
    # -----------------------------------------------------------------------
    st.header("Live Manifest Preview")
    st.caption("This is the JSON that will be written to Okta when you save.")

    preview_manifest = {
        "user_id": selected_email,
        "role": role,
        "mcp_servers": updated_servers,
    }
    st.json(preview_manifest)


if __name__ == "__main__":
    main()
