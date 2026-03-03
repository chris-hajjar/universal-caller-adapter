"""
Agentic Platform Gateway — Single FastAPI entry point.

Routes all AI client requests through:
  1. Okta JWT validation
  2. Permission manifest enforcement
  3. MCP server routing
  4. Async memory sync (BackgroundTasks)
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from gateway.auth import get_current_user, UserToken
from gateway.permissions import PermissionEngine, load_manifest_for_user
from gateway.mcp_router import MCPRouter
from gateway.memory import MemoryMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp_router = MCPRouter()
memory_middleware = MemoryMiddleware()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup, clean up on shutdown."""
    logger.info("Gateway starting up")
    await mcp_router.initialize()
    await memory_middleware.initialize()
    yield
    logger.info("Gateway shutting down")
    await mcp_router.shutdown()
    await memory_middleware.shutdown()


app = FastAPI(
    title="Agentic Platform Gateway",
    description="Multi-tenant gateway for AI client → MCP server routing with permissions and memory",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentic-platform-gateway"}


# ---------------------------------------------------------------------------
# MCP Proxy — the main entry point for all AI clients
# ---------------------------------------------------------------------------

@app.post("/mcp/{server_name}/{action}")
async def mcp_proxy(
    server_name: str,
    action: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: UserToken = Depends(get_current_user),
):
    """
    Proxy a request to an MCP server after enforcing permissions.

    Path: /mcp/<server_name>/<action>
    Example: POST /mcp/mariadb/query  body={"sql": "SELECT * FROM invoices"}
    """
    body = await request.json()

    # --- Permission check ---
    manifest = await load_manifest_for_user(user.user_id)
    engine = PermissionEngine(manifest)

    if not engine.is_owner():
        if not engine.can_access_server(server_name):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {server_name} is not enabled for {user.user_id}",
            )
        # For mariadb, enforce table-level and scope checks
        if server_name == "mariadb":
            engine.enforce_mariadb(action, body)

    # --- Route to MCP server ---
    result = await mcp_router.route(server_name, action, body, user)

    # --- Async memory sync (fire and forget) ---
    background_tasks.add_task(
        memory_middleware.sync_exchange,
        user_id=user.user_id,
        server_name=server_name,
        action=action,
        request_body=body,
        response_body=result,
    )

    return {"status": "ok", "server": server_name, "action": action, "result": result}


# ---------------------------------------------------------------------------
# Memory search — direct endpoint for retrieving memories
# ---------------------------------------------------------------------------

@app.post("/memory/search")
async def memory_search(
    request: Request,
    user: UserToken = Depends(get_current_user),
):
    """Search user's conversation memory by semantic similarity."""
    body = await request.json()
    query = body.get("query", "")
    limit = body.get("limit", 5)

    manifest = await load_manifest_for_user(user.user_id)
    engine = PermissionEngine(manifest)

    if not engine.is_owner() and not engine.can_access_server("memory"):
        raise HTTPException(status_code=403, detail="Memory access not enabled")

    results = await memory_middleware.search(
        user_id=user.user_id,
        query=query,
        limit=limit,
    )
    return {"status": "ok", "results": results}


# ---------------------------------------------------------------------------
# Manifest introspection (owner only)
# ---------------------------------------------------------------------------

@app.get("/admin/manifest/{target_user_id}")
async def get_manifest(
    target_user_id: str,
    user: UserToken = Depends(get_current_user),
):
    """Owner-only: read a user's permission manifest."""
    owner_manifest = await load_manifest_for_user(user.user_id)
    if not PermissionEngine(owner_manifest).is_owner():
        raise HTTPException(status_code=403, detail="Owner access required")

    manifest = await load_manifest_for_user(target_user_id)
    return manifest


@app.put("/admin/manifest/{target_user_id}")
async def update_manifest(
    target_user_id: str,
    request: Request,
    user: UserToken = Depends(get_current_user),
):
    """Owner-only: update a user's permission manifest in Okta."""
    owner_manifest = await load_manifest_for_user(user.user_id)
    if not PermissionEngine(owner_manifest).is_owner():
        raise HTTPException(status_code=403, detail="Owner access required")

    body = await request.json()

    from gateway.okta_client import OktaClient
    okta = OktaClient()
    await okta.set_user_manifest(target_user_id, body)

    return {"status": "ok", "user_id": target_user_id, "manifest": body}


@app.get("/admin/users")
async def list_users(
    user: UserToken = Depends(get_current_user),
):
    """Owner-only: list all managed users."""
    owner_manifest = await load_manifest_for_user(user.user_id)
    if not PermissionEngine(owner_manifest).is_owner():
        raise HTTPException(status_code=403, detail="Owner access required")

    from gateway.okta_client import OktaClient
    okta = OktaClient()
    users = await okta.list_users()
    return {"status": "ok", "users": users}
