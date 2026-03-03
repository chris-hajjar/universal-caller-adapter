"""
Admin UI — Streamlit dashboard for managing MCP permissions.

Single page, owner only. Three sections:
  1. User List — overview of all users and their MCP access
  2. MCP Permission Grid — toggle access per user per server
  3. Live Manifest Preview — real-time JSON of the permission manifest

Usage:
    streamlit run admin/app.py
"""

from __future__ import annotations

import json
import os

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
OWNER_TOKEN = os.getenv("OWNER_TOKEN", "chris@company.com")  # Dev mode token

# All MCP servers managed by the platform
MCP_SERVERS = ["mariadb", "memory", "slack", "reports"]

# MariaDB tables that can be individually toggled
MARIADB_TABLES = ["invoices", "orders", "users", "products", "reports"]

# ---------------------------------------------------------------------------
# Gateway API helpers
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {OWNER_TOKEN}"}


def fetch_users() -> list[dict]:
    """Fetch user list from the gateway."""
    try:
        resp = httpx.get(
            f"{GATEWAY_URL}/admin/users",
            headers=_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch users: {e}")
        return _fallback_users()


def update_permissions(email: str, manifest: dict) -> dict:
    """Push updated permissions to the gateway (→ Okta)."""
    try:
        resp = httpx.put(
            f"{GATEWAY_URL}/admin/users/{email}/permissions",
            headers=_headers(),
            json=manifest,
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to update permissions: {e}")
        return {"status": "error", "detail": str(e)}


def _fallback_users() -> list[dict]:
    """Fallback user data when gateway is unavailable."""
    return [
        {
            "email": "chris@company.com",
            "manifest": {
                "user_id": "chris@company.com",
                "role": "owner",
                "mcp_servers": {
                    "mariadb": {"enabled": True, "scope": "read_write", "tables": MARIADB_TABLES},
                    "memory": {"enabled": True, "scope": "read_write", "tables": None},
                    "slack": {"enabled": True, "scope": "read_write", "tables": None},
                    "reports": {"enabled": True, "scope": "read_write", "tables": None},
                },
            },
        },
        {
            "email": "user_a@company.com",
            "manifest": {
                "user_id": "user_a@company.com",
                "role": "standard",
                "mcp_servers": {
                    "mariadb": {"enabled": True, "scope": "read_only", "tables": ["invoices", "orders", "products"]},
                    "memory": {"enabled": True, "scope": "read_write", "tables": None},
                    "slack": {"enabled": True, "scope": "read_write", "tables": None},
                    "reports": {"enabled": False, "scope": "read_only", "tables": None},
                },
            },
        },
        {
            "email": "user_b@company.com",
            "manifest": {
                "user_id": "user_b@company.com",
                "role": "limited",
                "mcp_servers": {
                    "mariadb": {"enabled": True, "scope": "read_only", "tables": ["invoices"]},
                    "memory": {"enabled": True, "scope": "read_write", "tables": None},
                    "slack": {"enabled": False, "scope": "read_only", "tables": None},
                    "reports": {"enabled": False, "scope": "read_only", "tables": None},
                },
            },
        },
    ]


# ---------------------------------------------------------------------------
# Streamlit page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Agentic Platform Admin",
    page_icon="🔐",
    layout="wide",
)

st.title("Agentic Platform — Admin Dashboard")
st.caption("Manage MCP server permissions per user. Changes apply on the next gateway request.")

# Load users
users = fetch_users()

if not users:
    st.warning("No users found. Check the gateway connection.")
    st.stop()


# -----------------------------------------------------------------------
# Section 1: User List
# -----------------------------------------------------------------------

st.header("Users")

user_summary_data = []
for u in users:
    manifest = u["manifest"]
    servers = manifest.get("mcp_servers", {})
    enabled = [name for name, cfg in servers.items() if cfg.get("enabled")]
    user_summary_data.append({
        "Email": u["email"],
        "Role": manifest.get("role", "unknown"),
        "Enabled MCPs": ", ".join(enabled) if enabled else "none",
    })

st.dataframe(user_summary_data, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------
# Section 2: MCP Permission Grid
# -----------------------------------------------------------------------

st.header("MCP Permissions")

# User selector
user_emails = [u["email"] for u in users]
selected_email = st.selectbox("Select user", user_emails, index=1)

selected_user = next(u for u in users if u["email"] == selected_email)
manifest = selected_user["manifest"]
servers = manifest.get("mcp_servers", {})

# Initialize session state for this user's permissions
state_key = f"perms_{selected_email}"
if state_key not in st.session_state:
    st.session_state[state_key] = json.loads(json.dumps(servers))

current_perms = st.session_state[state_key]

st.subheader(f"Permissions for {selected_email}")

if manifest.get("role") == "owner":
    st.info("This user is the **owner** — all permission checks are bypassed by the gateway.")

# Permission grid
cols = st.columns(len(MCP_SERVERS))

for i, server_name in enumerate(MCP_SERVERS):
    with cols[i]:
        st.markdown(f"**{server_name.upper()}**")

        server_cfg = current_perms.get(server_name, {"enabled": False, "scope": "read_only", "tables": None})

        # Enable toggle
        enabled = st.checkbox(
            "Enabled",
            value=server_cfg.get("enabled", False),
            key=f"{state_key}_{server_name}_enabled",
            disabled=manifest.get("role") == "owner",
        )
        server_cfg["enabled"] = enabled

        if enabled:
            # Scope selector
            scope_options = ["read_only", "read_write"]
            current_scope = server_cfg.get("scope", "read_only")
            scope_idx = scope_options.index(current_scope) if current_scope in scope_options else 0
            scope = st.radio(
                "Scope",
                scope_options,
                index=scope_idx,
                key=f"{state_key}_{server_name}_scope",
                horizontal=True,
            )
            server_cfg["scope"] = scope

            # MariaDB-specific: table checklist
            if server_name == "mariadb":
                st.markdown("**Tables:**")
                allowed_tables = server_cfg.get("tables") or []
                selected_tables = []
                for table in MARIADB_TABLES:
                    checked = st.checkbox(
                        table,
                        value=table in allowed_tables,
                        key=f"{state_key}_{server_name}_table_{table}",
                    )
                    if checked:
                        selected_tables.append(table)
                server_cfg["tables"] = selected_tables

        current_perms[server_name] = server_cfg

st.session_state[state_key] = current_perms

# Save button
st.divider()
col_save, col_status = st.columns([1, 3])

with col_save:
    if st.button("Save Permissions", type="primary", use_container_width=True):
        updated_manifest = {
            "user_id": selected_email,
            "role": manifest.get("role", "limited"),
            "mcp_servers": current_perms,
        }
        result = update_permissions(selected_email, updated_manifest)
        if result.get("status") == "updated":
            st.success(f"Permissions saved for {selected_email}")
        else:
            st.error(f"Failed: {result}")

with col_status:
    st.caption("Changes are written to Okta immediately. The gateway enforces on the next request — no restart needed.")


# -----------------------------------------------------------------------
# Section 3: Live Manifest Preview
# -----------------------------------------------------------------------

st.header("Live Manifest Preview")
st.caption("This is the raw JSON that gets written to Okta for the selected user.")

live_manifest = {
    "user_id": selected_email,
    "role": manifest.get("role", "limited"),
    "mcp_servers": current_perms,
}

st.json(live_manifest)
