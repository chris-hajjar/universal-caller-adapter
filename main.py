"""
Universal Caller Adapter - POC

Demonstrates unified authentication/authorization across multiple entry points.
"""
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from src.models import Principal, AUTH_STRENGTH_WEAK, AUTH_STRENGTH_STRONG
from src.adapters import CookieAdapter, OAuthAdapter, SlackAdapter
from src.auth import Authorizer, ToolPolicy, AuthorizationError
from src.middleware import AuthMiddleware
from src.tools import rag_search, diagnostics


# Request/Response models
class RagSearchRequest(BaseModel):
    query: str


class ToolResponse(BaseModel):
    success: bool
    data: dict = None
    error: str = None
    principal_info: dict = None


# Initialize FastAPI app
app = FastAPI(
    title="Universal Caller Adapter POC",
    description="Demonstrates unified auth across Cookie, OAuth, and Slack entry points",
    version="1.0.0"
)


# Initialize authorizer with tool policies
authorizer = Authorizer()

# Configure policies
authorizer.register_policy(ToolPolicy(
    tool_name="rag_search",
    required_entitlements={"rag:read"},
    min_auth_strength=AUTH_STRENGTH_WEAK,  # Slack can access this (strength >= 1)
    description="Search over RAG knowledge base"
))

authorizer.register_policy(ToolPolicy(
    tool_name="diagnostics",
    required_entitlements={"diag:read"},
    min_auth_strength=AUTH_STRENGTH_STRONG,  # Requires strong auth (strength >= 2, blocks Slack)
    description="System diagnostics - sensitive operation"
))


# Initialize authentication adapters
cookie_adapter = CookieAdapter()
oauth_adapter = OAuthAdapter()
slack_adapter = SlackAdapter()

# Add auth middleware (order matters - first match wins)
app.add_middleware(
    AuthMiddleware,
    adapters=[cookie_adapter, oauth_adapter, slack_adapter]
)


# Helper to get principal from request
def get_principal(request: Request) -> Principal:
    """Extract principal from request state (set by middleware)."""
    return request.state.principal


# Helper to format principal info
def format_principal_info(principal: Principal) -> dict:
    """Format principal for response."""
    return {
        "principal_id": principal.principal_id,
        "tenant_id": principal.tenant_id,
        "auth_method": principal.auth_method.value,
        "auth_strength": principal.auth_strength.value,
        "entitlements": list(principal.entitlements),
        "is_authenticated": principal.is_authenticated
    }


# Endpoints
@app.get("/")
async def root():
    """API information."""
    return {
        "service": "Universal Caller Adapter POC",
        "version": "1.0.0",
        "endpoints": {
            "/whoami": "Show current principal",
            "/tools/rag-search": "Search RAG knowledge base (requires rag:read, auth strength >= 1)",
            "/tools/diagnostics": "System diagnostics (requires diag:read + auth strength >= 2)"
        }
    }


@app.get("/whoami")
async def whoami(request: Request):
    """
    Show the resolved principal for the current request.

    This demonstrates that all entry points normalize to the same Principal structure.
    """
    principal = get_principal(request)

    return {
        "message": "You are authenticated as:",
        "principal": format_principal_info(principal),
        "note": "All entry points (cookie, OAuth, Slack) resolve to this same structure"
    }


@app.post("/tools/rag-search", response_model=ToolResponse)
async def invoke_rag_search(request: Request, body: RagSearchRequest):
    """
    Invoke RAG search tool.

    Authorization:
    - Requires: rag:read entitlement
    - Min auth strength: 1 (weak - Slack can access)
    """
    principal = get_principal(request)

    try:
        # Centralized authorization (happens here, not in tool)
        authorizer.authorize(principal, "rag_search")

        # Tool invocation (auth-agnostic)
        result = await rag_search(principal, body.query)

        return ToolResponse(
            success=True,
            data=result,
            principal_info=format_principal_info(principal)
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Authorization failed",
                "message": str(e),
                "reason": e.reason,
                "principal": format_principal_info(principal)
            }
        )


@app.post("/tools/diagnostics", response_model=ToolResponse)
async def invoke_diagnostics(request: Request):
    """
    Invoke system diagnostics tool.

    Authorization:
    - Requires: diag:read entitlement
    - Min auth strength: 2 (strong - blocks Slack)
    """
    principal = get_principal(request)

    try:
        # Centralized authorization
        authorizer.authorize(principal, "diagnostics")

        # Tool invocation
        result = await diagnostics(principal)

        return ToolResponse(
            success=True,
            data=result,
            principal_info=format_principal_info(principal)
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Authorization failed",
                "message": str(e),
                "reason": e.reason,
                "principal": format_principal_info(principal)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
