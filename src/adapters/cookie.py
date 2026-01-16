"""Platform cookie authentication adapter."""
from typing import Optional
from fastapi import Request

from src.models import Principal, AuthMethod, AUTH_STRENGTH_STRONG
from .base import AuthAdapter


class CookieAdapter(AuthAdapter):
    """
    Authenticates via platform session cookies.

    In a real system, this would:
    - Extract session cookie
    - Look up session in Redis/database
    - Validate session hasn't expired
    - Load user info and entitlements

    For POC: simulates session lookup with hardcoded data.
    """

    def __init__(self, session_store: dict = None):
        """
        Args:
            session_store: Mock session storage {session_id -> user_data}
        """
        self.session_store = session_store or {
            "sess_alice_123": {
                "principal_id": "user_alice",
                "tenant_id": "acme_corp",
                "entitlements": {"rag:read", "rag:write", "diag:read"}
            },
            "sess_bob_456": {
                "principal_id": "user_bob",
                "tenant_id": "acme_corp",
                "entitlements": {"rag:read"}
            }
        }

    async def can_handle(self, request: Request) -> bool:
        """Check if request has a session cookie."""
        return "session_id" in request.cookies

    async def authenticate(self, request: Request) -> Optional[Principal]:
        """Authenticate via session cookie."""
        session_id = request.cookies.get("session_id")
        if not session_id:
            return None

        # Simulate session lookup
        user_data = self.session_store.get(session_id)
        if not user_data:
            return None

        return Principal(
            principal_id=user_data["principal_id"],
            tenant_id=user_data.get("tenant_id"),
            auth_method=AuthMethod.COOKIE,
            auth_strength=AUTH_STRENGTH_STRONG,
            entitlements=set(user_data.get("entitlements", []))
        )
