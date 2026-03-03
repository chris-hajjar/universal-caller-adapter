"""
Okta JWT validation and user token extraction.
"""

import os
import logging
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Okta configuration from env
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")  # e.g. dev-12345.okta.com
OKTA_AUDIENCE = os.getenv("OKTA_AUDIENCE", "api://default")
OKTA_ISSUER = os.getenv("OKTA_ISSUER", "")  # e.g. https://dev-12345.okta.com/oauth2/default

# Cache for JWKS keys
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch Okta JWKS (JSON Web Key Set) with caching."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"https://{OKTA_DOMAIN}/oauth2/default/v1/keys"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _find_rsa_key(token: str, jwks: dict) -> dict | None:
    """Match the token's kid to a key in the JWKS."""
    unverified_header = jwt.get_unverified_header(token)
    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return key
    return None


@dataclass
class UserToken:
    """Decoded user identity from JWT."""
    user_id: str  # email or sub
    email: str
    name: str
    raw_claims: dict


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserToken:
    """
    Validate the Okta JWT and return a UserToken.

    In development mode (GATEWAY_DEV_MODE=true), accepts a simple
    bearer token of the form "dev:<user_email>" for testing without Okta.
    """
    token = credentials.credentials

    # --- Dev mode: skip JWT validation ---
    if os.getenv("GATEWAY_DEV_MODE", "").lower() == "true":
        if token.startswith("dev:"):
            email = token[4:]
            return UserToken(
                user_id=email,
                email=email,
                name=email.split("@")[0],
                raw_claims={"sub": email, "email": email},
            )

    # --- Production: full Okta JWT validation ---
    try:
        jwks = await _get_jwks()
        rsa_key = _find_rsa_key(token, jwks)
        if rsa_key is None:
            raise HTTPException(status_code=401, detail="Unable to find matching signing key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=OKTA_AUDIENCE,
            issuer=OKTA_ISSUER,
        )

        email = payload.get("email", payload.get("sub", "unknown"))
        name = payload.get("name", email.split("@")[0])

        return UserToken(
            user_id=email,
            email=email,
            name=name,
            raw_claims=payload,
        )
    except JWTError as e:
        logger.error("JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except httpx.HTTPError as e:
        logger.error("Failed to fetch JWKS: %s", e)
        raise HTTPException(status_code=503, detail="Auth service unavailable")
