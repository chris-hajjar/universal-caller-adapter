"""
Gateway API — the single entry point for all AI clients.

One FastAPI server that:
  1. Validates JWTs from Okta
  2. Reads the user's permission manifest
  3. Routes MCP tool calls to allowed servers only
  4. Fires background tasks to sync conversation memory
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_current_user
from .mcp_router import MCPRouter, create_router
from .memory import sync_memory
from .models import MCPToolCall, MCPToolInfo, MCPToolResult, UserContext
from .permissions import check_mcp_call_permissions

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

router: MCPRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router
    router = create_router()
    logger.info("Gateway started — MCP servers registered: %s", router.server_names)
    yield
    if router:
        await router.close()
    logger.info("Gateway shutdown")


app = FastAPI(
    title="Agentic Platform Gateway",
    description=(
        "Multi-tenant MCP gateway with Okta auth, per-user permissions, "
        "and invisible memory sync."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit admin UI and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health & info
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "servers": router.server_names if router else []}


@app.get("/whoami")
async def whoami(user: UserContext = Depends(get_current_user)):
    """Show the resolved identity and permissions for the current user."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.manifest.role,
        "is_owner": user.is_owner,
        "mcp_servers": {
            name: {
                "enabled": perm.enabled,
                "scope": perm.scope.value,
                "tables": perm.tables,
            }
            for name, perm in user.manifest.mcp_servers.items()
        },
    }


# ---------------------------------------------------------------------------
# MCP tool listing
# ---------------------------------------------------------------------------

@app.get("/mcp/tools")
async def list_tools(
    user: UserContext = Depends(get_current_user),
) -> list[MCPToolInfo]:
    """List all MCP tools the current user has access to."""
    assert router is not None
    return await router.list_tools(user)


# ---------------------------------------------------------------------------
# MCP tool calling — the core endpoint
# ---------------------------------------------------------------------------

@app.post("/mcp/call")
async def call_tool(
    call: MCPToolCall,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
) -> MCPToolResult:
    """
    Call an MCP tool through the gateway.

    The gateway:
    1. Validates the user's JWT (via dependency)
    2. Checks permissions for the target server + tool
    3. Forwards the call to the backend MCP server
    4. Fires a background task to sync the exchange to memory
    """
    # Permission check first — before touching the router
    check_mcp_call_permissions(
        user, call.server_name, call.tool_name, call.arguments
    )

    assert router is not None

    # Route the call (permissions already enforced above)
    result = await router.call_tool(user, call)

    # Fire-and-forget memory sync
    content = (
        f"Tool call: {call.server_name}.{call.tool_name}\n"
        f"Arguments: {call.arguments}\n"
        f"Result: {result.result}"
    )
    background_tasks.add_task(sync_memory, user.user_id, content)

    return result


# ---------------------------------------------------------------------------
# Batch tool calls (convenience for multi-step agent workflows)
# ---------------------------------------------------------------------------

@app.post("/mcp/call/batch")
async def call_tools_batch(
    calls: list[MCPToolCall],
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
) -> list[MCPToolResult]:
    """Call multiple MCP tools in sequence, enforcing permissions on each."""
    # Check all permissions up front before routing
    for call in calls:
        check_mcp_call_permissions(
            user, call.server_name, call.tool_name, call.arguments
        )

    assert router is not None

    results: list[MCPToolResult] = []
    memory_parts: list[str] = []

    for call in calls:
        result = await router.call_tool(user, call)
        results.append(result)
        memory_parts.append(
            f"{call.server_name}.{call.tool_name}: {result.result}"
        )

    # Sync the full batch as one memory
    background_tasks.add_task(
        sync_memory, user.user_id, "\n".join(memory_parts)
    )

    return results


# ---------------------------------------------------------------------------
# Admin endpoints (owner only)
# ---------------------------------------------------------------------------

@app.get("/admin/users")
async def list_users(user: UserContext = Depends(get_current_user)):
    """List all managed users and their permissions. Owner only."""
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access required")

    # In production, this fetches from Okta's user directory.
    # For the POC, return the hardcoded test users.
    from .auth import _get_dev_manifest

    users = ["chris@company.com", "user_a@company.com", "user_b@company.com"]
    return [
        {
            "email": email,
            "manifest": _get_dev_manifest(email).model_dump(),
        }
        for email in users
    ]


@app.put("/admin/users/{email}/permissions")
async def update_user_permissions(
    email: str,
    manifest: dict,
    user: UserContext = Depends(get_current_user),
):
    """
    Update a user's permission manifest. Owner only.

    In production, writes to Okta user attributes. Gateway enforces
    on the next request — no restart needed.
    """
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access required")

    okta_domain = os.getenv("OKTA_DOMAIN")
    okta_token = os.getenv("OKTA_API_TOKEN")

    if okta_domain and okta_token:
        # Write to Okta user profile
        import httpx
        import json

        async with httpx.AsyncClient() as client:
            # Find user by email
            search_resp = await client.get(
                f"https://{okta_domain}/api/v1/users?search=profile.email eq \"{email}\"",
                headers={"Authorization": f"SSWS {okta_token}"},
            )
            users = search_resp.json()
            if not users:
                raise HTTPException(status_code=404, detail="User not found in Okta")

            okta_user_id = users[0]["id"]

            # Update profile attribute
            resp = await client.post(
                f"https://{okta_domain}/api/v1/users/{okta_user_id}",
                headers={
                    "Authorization": f"SSWS {okta_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "profile": {
                        "mcp_permissions": json.dumps(manifest),
                    }
                },
            )
            resp.raise_for_status()

        return {"status": "updated", "target": email, "backend": "okta"}

    # Dev mode — log the change (won't persist across restarts)
    logger.info(f"Permission update for {email}: {manifest}")
    return {"status": "updated", "target": email, "backend": "local_dev"}
