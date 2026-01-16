"""Slack request signature authentication adapter."""
import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request

from src.models import Principal, AuthMethod, AUTH_STRENGTH_WEAK
from .base import AuthAdapter


class SlackAdapter(AuthAdapter):
    """
    Authenticates Slack requests via signature verification.

    Slack signs requests with a shared secret. We verify:
    - X-Slack-Request-Timestamp (prevent replay)
    - X-Slack-Signature (HMAC-SHA256)

    Auth strength is 1 (weak) because:
    - No user-level authentication (just app-level)
    - Shared secret model
    - Limited user identity verification

    For POC: Simulates signature verification.
    """

    def __init__(self, signing_secret: str = "slack-signing-secret", user_mapping: dict = None):
        """
        Args:
            signing_secret: Slack app signing secret
            user_mapping: Maps Slack user IDs to internal principals
        """
        self.signing_secret = signing_secret
        self.user_mapping = user_mapping or {
            "U01ABC123": {
                "principal_id": "slack_user_charlie",
                "tenant_id": "acme_corp",
                "entitlements": {"rag:read"}  # Limited permissions for Slack
            },
            "U02DEF456": {
                "principal_id": "slack_user_diana",
                "tenant_id": "acme_corp",
                "entitlements": {"rag:read"}
            }
        }

    async def can_handle(self, request: Request) -> bool:
        """Check if request has Slack signature headers."""
        return (
            "x-slack-signature" in request.headers and
            "x-slack-request-timestamp" in request.headers
        )

    async def authenticate(self, request: Request) -> Optional[Principal]:
        """Authenticate via Slack signature."""
        signature = request.headers.get("x-slack-signature")
        timestamp = request.headers.get("x-slack-request-timestamp")

        if not signature or not timestamp:
            return None

        # Verify timestamp (prevent replay attacks)
        try:
            request_time = int(timestamp)
            if abs(time.time() - request_time) > 60 * 5:  # 5 minute window
                return None
        except ValueError:
            return None

        # In a real implementation, we would:
        # 1. Read request body
        # 2. Compute HMAC-SHA256(signing_secret, f"v0:{timestamp}:{body}")
        # 3. Compare with signature

        # For POC: extract Slack user ID from body/headers (simplified)
        # In reality, this comes from the request body
        slack_user_id = request.headers.get("x-slack-user-id")

        if not slack_user_id:
            return None

        user_data = self.user_mapping.get(slack_user_id)
        if not user_data:
            # Unknown Slack user - create limited anonymous principal
            return Principal(
                principal_id=f"slack_unknown_{slack_user_id}",
                auth_method=AuthMethod.SLACK,
                auth_strength=AUTH_STRENGTH_WEAK,
                entitlements=set()
            )

        return Principal(
            principal_id=user_data["principal_id"],
            tenant_id=user_data.get("tenant_id"),
            auth_method=AuthMethod.SLACK,
            auth_strength=AUTH_STRENGTH_WEAK,  # Always weak (1) for Slack
            entitlements=set(user_data.get("entitlements", []))
        )
