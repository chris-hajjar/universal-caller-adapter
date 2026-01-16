"""
Demo script for Universal Caller Adapter POC

Demonstrates:
1. Different auth methods (Cookie, OAuth, Slack, Anonymous)
2. All resolving to the same Principal structure
3. Authorization working consistently across entry points
4. Slack blocked from sensitive tools due to weak auth
"""
import jwt
import httpx
import asyncio
from datetime import datetime, timedelta


BASE_URL = "http://localhost:8000"
JWT_SECRET = "demo-secret-key"


def create_jwt(principal_id: str, role: str, tenant_id: str = None) -> str:
    """Create a demo JWT token."""
    payload = {
        "sub": principal_id,
        "role": role,
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def demo():
    """Run the complete demo."""
    async with httpx.AsyncClient() as client:
        print("=" * 80)
        print("UNIVERSAL CALLER ADAPTER POC - DEMO")
        print("=" * 80)
        print()

        # Demo 1: Cookie Authentication
        print("📍 DEMO 1: Cookie Authentication (Platform)")
        print("-" * 80)
        cookies = {"session_id": "sess_alice_123"}
        response = await client.get(f"{BASE_URL}/whoami", cookies=cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Demo 2: OAuth Authentication
        print("📍 DEMO 2: OAuth/JWT Authentication")
        print("-" * 80)
        token = create_jwt("user_bob", "admin", "acme_corp")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{BASE_URL}/whoami", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Demo 3: Slack Authentication
        print("📍 DEMO 3: Slack Authentication")
        print("-" * 80)
        slack_headers = {
            "x-slack-signature": "v0=abc123",
            "x-slack-request-timestamp": str(int(datetime.utcnow().timestamp())),
            "x-slack-user-id": "U01ABC123"
        }
        response = await client.get(f"{BASE_URL}/whoami", headers=slack_headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Demo 4: Anonymous (no auth)
        print("📍 DEMO 4: Anonymous (No Authentication)")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/whoami")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        print("=" * 80)
        print("AUTHORIZATION DEMOS - Same Tool, Different Auth Methods")
        print("=" * 80)
        print()

        # Demo 5: RAG Search via Cookie (SUCCESS)
        print("📍 DEMO 5: RAG Search via Cookie (SHOULD SUCCEED)")
        print("-" * 80)
        cookies = {"session_id": "sess_alice_123"}
        response = await client.post(
            f"{BASE_URL}/tools/rag-search",
            json={"query": "What is the capital of France?"},
            cookies=cookies
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Demo 6: RAG Search via OAuth (SUCCESS)
        print("📍 DEMO 6: RAG Search via OAuth (SHOULD SUCCEED)")
        print("-" * 80)
        token = create_jwt("user_carol", "user", "acme_corp")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{BASE_URL}/tools/rag-search",
            json={"query": "What is the capital of France?"},
            headers=headers
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Demo 7: RAG Search via Slack (SUCCESS - weak auth is OK)
        print("📍 DEMO 7: RAG Search via Slack (SHOULD SUCCEED - weak auth OK)")
        print("-" * 80)
        slack_headers = {
            "x-slack-signature": "v0=abc123",
            "x-slack-request-timestamp": str(int(datetime.utcnow().timestamp())),
            "x-slack-user-id": "U01ABC123"
        }
        response = await client.post(
            f"{BASE_URL}/tools/rag-search",
            json={"query": "What is the capital of France?"},
            headers=slack_headers
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        print("=" * 80)
        print("SENSITIVE TOOL DEMOS - Strong Auth Required")
        print("=" * 80)
        print()

        # Demo 8: Diagnostics via Cookie (SUCCESS)
        print("📍 DEMO 8: Diagnostics via Cookie (SHOULD SUCCEED)")
        print("-" * 80)
        cookies = {"session_id": "sess_alice_123"}
        response = await client.post(
            f"{BASE_URL}/tools/diagnostics",
            cookies=cookies
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.json()}")
        print()

        # Demo 9: Diagnostics via OAuth (SUCCESS)
        print("📍 DEMO 9: Diagnostics via OAuth (SHOULD SUCCEED)")
        print("-" * 80)
        token = create_jwt("user_dave", "admin", "acme_corp")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{BASE_URL}/tools/diagnostics",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.json()}")
        print()

        # Demo 10: Diagnostics via Slack (FAIL - weak auth not allowed)
        print("📍 DEMO 10: Diagnostics via Slack (SHOULD FAIL - weak auth)")
        print("-" * 80)
        slack_headers = {
            "x-slack-signature": "v0=abc123",
            "x-slack-request-timestamp": str(int(datetime.utcnow().timestamp())),
            "x-slack-user-id": "U01ABC123"
        }
        response = await client.post(
            f"{BASE_URL}/tools/diagnostics",
            headers=slack_headers
        )
        print(f"Status: {response.status_code}")
        print(f"Error (expected): {response.json()}")
        print()

        # Demo 11: Missing entitlements
        print("📍 DEMO 11: Missing Entitlements (SHOULD FAIL)")
        print("-" * 80)
        cookies = {"session_id": "sess_bob_456"}  # Bob only has rag:read
        response = await client.post(
            f"{BASE_URL}/tools/diagnostics",
            cookies=cookies
        )
        print(f"Status: {response.status_code}")
        print(f"Error (expected): {response.json()}")
        print()

        print("=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print()
        print("Key Takeaways:")
        print("✓ All entry points normalize to the same Principal structure")
        print("✓ Authorization is centralized and consistent")
        print("✓ Tools are auth-agnostic")
        print("✓ Slack blocked from sensitive tools due to weak auth")
        print("✓ Architecture is clear and extensible")


if __name__ == "__main__":
    print()
    print("Starting demo...")
    print("Make sure the server is running: python main.py")
    print()
    input("Press Enter when server is ready...")
    print()

    asyncio.run(demo())
