"""
Okta JWT validation and user context resolution.

Validates JWTs issued by Okta, extracts user identity, and loads
the permission manifest from Okta user profile attributes.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import MCPServerPermission, MCPServerScope, PermissionManifest, UserContext

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")  # e.g. "dev-12345.okta.com"
OKTA_AUDIENCE = os.getenv("OKTA_AUDIENCE", "api://default")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID", "")

# Owner email — gateway skips permission checks for this user
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "chris@company.com")

# Cache for JWKS keys
_jwks_cache: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# JWKS fetching
# ---------------------------------------------------------------------------

async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache JWKS from Okta."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"https://{OKTA_DOMAIN}/oauth2/default/v1/keys"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


def _clear_jwks_cache() -> None:
    """Clear JWKS cache — useful for key rotation."""
    global _jwks_cache
    _jwks_cache = None


# ---------------------------------------------------------------------------
# JWT validation
# ---------------------------------------------------------------------------

async def _validate_jwt(token: str) -> dict[str, Any]:
    """
    Validate a JWT against Okta's JWKS and return the decoded claims.

    In production this performs full JWKS validation. When OKTA_DOMAIN is
    not set (local development), falls back to accepting unverified tokens
    with a warning.
    """
    if not OKTA_DOMAIN:
        # Local dev mode — decode without verification
        logger.warning("OKTA_DOMAIN not set — skipping JWT verification (dev mode)")
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError:
            # Treat the token as a simple user identifier for local dev
            claims = {"sub": token, "email": token}
        return claims

    jwks = await _get_jwks()

    # Find the signing key
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    rsa_key: dict[str, str] = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise HTTPException(status_code=401, detail="Unable to find signing key")

    try:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=OKTA_AUDIENCE,
            issuer=f"https://{OKTA_DOMAIN}/oauth2/default",
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

async def _load_manifest_from_okta(user_id: str, email: str) -> PermissionManifest:
    """
    Load the permission manifest from Okta user profile attributes.

    In production, calls the Okta Users API to read the user's profile
    attribute `mcp_permissions`. When OKTA_DOMAIN is not set, falls back
    to the hardcoded test manifests.
    """
    if OKTA_DOMAIN and os.getenv("OKTA_API_TOKEN"):
        return await _fetch_okta_manifest(user_id, email)

    # Fall back to hardcoded test manifests for local dev
    return _get_dev_manifest(email)


async def _fetch_okta_manifest(user_id: str, email: str) -> PermissionManifest:
    """Fetch manifest from Okta user profile attributes."""
    api_token = os.getenv("OKTA_API_TOKEN", "")
    url = f"https://{OKTA_DOMAIN}/api/v1/users/{user_id}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"SSWS {api_token}"},
        )
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch Okta profile for {user_id}, using defaults")
            return _get_dev_manifest(email)

        profile = resp.json().get("profile", {})
        raw = profile.get("mcp_permissions")
        if raw:
            data = json.loads(raw) if isinstance(raw, str) else raw
            return PermissionManifest(**data)

    return _get_dev_manifest(email)


def _get_dev_manifest(email: str) -> PermissionManifest:
    """
    Hardcoded manifests for the three POC test users.

    Chris (owner) — full access, gateway skips checks
    User A — invoices, orders, products (read only) + memory + slack
    User B — invoices only (read only) + memory, no slack
    """
    manifests: dict[str, PermissionManifest] = {
        OWNER_EMAIL: PermissionManifest(
            user_id=OWNER_EMAIL,
            role="owner",
            mcp_servers={
                "mariadb": MCPServerPermission(
                    enabled=True,
                    scope=MCPServerScope.READ_WRITE,
                    tables=["invoices", "orders", "users", "products", "reports"],
                ),
                "memory": MCPServerPermission(enabled=True),
                "slack": MCPServerPermission(enabled=True),
                "reports": MCPServerPermission(enabled=True),
            },
        ),
        "user_a@company.com": PermissionManifest(
            user_id="user_a@company.com",
            role="standard",
            mcp_servers={
                "mariadb": MCPServerPermission(
                    enabled=True,
                    scope=MCPServerScope.READ_ONLY,
                    tables=["invoices", "orders", "products"],
                ),
                "memory": MCPServerPermission(enabled=True, scope=MCPServerScope.READ_WRITE),
                "slack": MCPServerPermission(enabled=True),
                "reports": MCPServerPermission(enabled=False),
            },
        ),
        "user_b@company.com": PermissionManifest(
            user_id="user_b@company.com",
            role="limited",
            mcp_servers={
                "mariadb": MCPServerPermission(
                    enabled=True,
                    scope=MCPServerScope.READ_ONLY,
                    tables=["invoices"],
                ),
                "memory": MCPServerPermission(enabled=True, scope=MCPServerScope.READ_WRITE),
                "slack": MCPServerPermission(enabled=False),
                "reports": MCPServerPermission(enabled=False),
            },
        ),
    }
    return manifests.get(
        email,
        PermissionManifest(user_id=email, role="limited", mcp_servers={}),
    )


# ---------------------------------------------------------------------------
# FastAPI dependency — resolves the current user
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> UserContext:
    """
    FastAPI dependency that validates the JWT and returns a UserContext.

    Usage:
        @app.post("/mcp/call")
        async def call_tool(user: UserContext = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    claims = await _validate_jwt(credentials.credentials)

    user_id = claims.get("sub", claims.get("uid", "unknown"))
    email = claims.get("email", user_id)

    manifest = await _load_manifest_from_okta(user_id, email)

    return UserContext(
        user_id=user_id,
        email=email,
        tenant_id=claims.get("tenant_id", "default"),
        manifest=manifest,
    )
