"""
Okta Management API client — reads/writes user profile attributes.

Used by:
  - Permission engine (read manifest on every request)
  - Admin UI (write manifest when owner changes permissions)
"""

import os
import json
import logging

import httpx

logger = logging.getLogger(__name__)

OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")
OKTA_API_TOKEN = os.getenv("OKTA_API_TOKEN", "")

# Custom Okta user profile attribute that stores the permission manifest
MANIFEST_ATTRIBUTE = "agentic_manifest"


class OktaClient:
    """Thin wrapper around Okta Management API for user/manifest operations."""

    def __init__(self):
        self.base_url = f"https://{OKTA_DOMAIN}/api/v1"
        self.headers = {
            "Authorization": f"SSWS {OKTA_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def list_users(self) -> list[dict]:
        """List all users in the Okta org."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/users",
                headers=self.headers,
                params={"limit": 100},
            )
            resp.raise_for_status()
            users = resp.json()

        return [
            {
                "id": u["id"],
                "email": u["profile"].get("email", ""),
                "name": f"{u['profile'].get('firstName', '')} {u['profile'].get('lastName', '')}".strip(),
                "status": u.get("status", ""),
            }
            for u in users
        ]

    async def get_user_by_email(self, email: str) -> dict | None:
        """Find a user by email."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/users",
                headers=self.headers,
                params={"search": f'profile.email eq "{email}"'},
            )
            resp.raise_for_status()
            users = resp.json()

        if users:
            return users[0]
        return None

    async def get_user_manifest(self, user_id: str) -> dict:
        """Read the permission manifest from a user's Okta profile."""
        user = await self.get_user_by_email(user_id)
        if not user:
            logger.warning("User %s not found in Okta", user_id)
            return {"user_id": user_id, "role": "none", "mcp_servers": {}}

        manifest_json = user.get("profile", {}).get(MANIFEST_ATTRIBUTE, "{}")
        try:
            if isinstance(manifest_json, str):
                return json.loads(manifest_json)
            return manifest_json
        except json.JSONDecodeError:
            logger.error("Invalid manifest JSON for user %s", user_id)
            return {"user_id": user_id, "role": "none", "mcp_servers": {}}

    async def set_user_manifest(self, user_id: str, manifest: dict):
        """Write the permission manifest to a user's Okta profile."""
        user = await self.get_user_by_email(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found in Okta")

        okta_user_id = user["id"]
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/users/{okta_user_id}",
                headers=self.headers,
                json={
                    "profile": {
                        MANIFEST_ATTRIBUTE: json.dumps(manifest),
                    }
                },
            )
            resp.raise_for_status()

        logger.info("Manifest updated for user %s in Okta", user_id)
