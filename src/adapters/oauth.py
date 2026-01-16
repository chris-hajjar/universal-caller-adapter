"""OAuth/OIDC JWT authentication adapter."""
import jwt
from typing import Optional
from fastapi import Request

from src.models import Principal, AuthMethod, AUTH_STRENGTH_STRONG
from .base import AuthAdapter


class OAuthAdapter(AuthAdapter):
    """
    Authenticates via OAuth 2.0 / OIDC JWT access tokens.

    In a real system, this would:
    - Fetch JWKS from identity provider
    - Verify JWT signature
    - Validate claims (exp, iss, aud)
    - Map claims to entitlements

    For POC: Uses a simplified JWT verification with symmetric key.
    """

    def __init__(self, jwt_secret: str = "demo-secret-key", entitlement_mapping: dict = None):
        """
        Args:
            jwt_secret: Secret key for JWT validation (use JWKS in production)
            entitlement_mapping: Maps user roles/scopes to entitlements
        """
        self.jwt_secret = jwt_secret
        self.entitlement_mapping = entitlement_mapping or {
            "admin": {"rag:read", "rag:write", "diag:read", "diag:write"},
            "user": {"rag:read", "rag:write"},
            "readonly": {"rag:read"}
        }

    async def can_handle(self, request: Request) -> bool:
        """Check if request has Bearer token."""
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Bearer ")

    async def authenticate(self, request: Request) -> Optional[Principal]:
        """Authenticate via JWT token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")

        try:
            # Verify and decode JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )

            # Extract claims
            principal_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            role = payload.get("role", "user")

            if not principal_id:
                return None

            # Map role to entitlements
            entitlements = self.entitlement_mapping.get(role, set())

            return Principal(
                principal_id=principal_id,
                tenant_id=tenant_id,
                auth_method=AuthMethod.OAUTH,
                auth_strength=AUTH_STRENGTH_STRONG,
                entitlements=set(entitlements)
            )

        except jwt.InvalidTokenError:
            return None
