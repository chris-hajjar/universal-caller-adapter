#!/usr/bin/env python3
"""
Simple Demo: Universal Caller Adapter
======================================

This demo shows how different authentication methods (cookies, OAuth tokens, Slack)
all get normalized into ONE unified model called a "Principal".

Think of it like this:
- You have multiple doors into your building (cookie login, OAuth, Slack bot)
- No matter which door you use, you get the same type of ID badge inside
- That ID badge (the Principal) is what determines what rooms you can access

This keeps your code simple - you don't need separate permission checks
for each type of login!
"""

import asyncio
import httpx
from typing import Dict, Any


# Color codes for pretty terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_step(step: str):
    """Print a step description"""
    print(f"{Colors.YELLOW}➤ {step}{Colors.END}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(label: str, value: str):
    """Print an info line"""
    print(f"  {Colors.BOLD}{label}:{Colors.END} {value}")


async def show_who_am_i(client: httpx.AsyncClient, headers: Dict[str, str], auth_method: str):
    """
    Show what Principal we become after authentication.

    This is the magic part - no matter how you logged in (cookie, OAuth, Slack),
    you get transformed into the same type of object: a Principal.
    """
    print_step(f"Checking who we are when using {auth_method}...")

    response = await client.get("http://localhost:8000/whoami", headers=headers)
    data = response.json()
    principal = data["principal"]  # Extract the nested principal object

    print_info("User ID", principal["principal_id"])
    print_info("Auth Method", principal["auth_method"])
    print_info("Auth Strength", principal["auth_strength"])
    print_info("Permissions", ", ".join(principal["entitlements"]))
    print()

    return principal


async def try_tool_access(
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    tool_name: str,
    endpoint: str,
    payload: Dict[str, Any],
    expected_result: str
):
    """
    Try to access a tool and explain what happens.

    This shows how authorization works consistently, regardless of how you logged in.
    """
    print_step(f"Trying to access: {tool_name}")
    print_info("Why this matters", expected_result)

    try:
        response = await client.post(
            f"http://localhost:8000{endpoint}",
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"Access granted! {tool_name} returned results.")
            return True
        else:
            error = response.json()
            print_error(f"Access denied: {error.get('detail', {}).get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return False
    finally:
        print()


async def main():
    """Run the simple demo"""

    print_section("UNIVERSAL CALLER ADAPTER - Simple Demo")

    print("""
This demo shows the key idea: No matter HOW you authenticate (cookie, OAuth, Slack),
you become the same type of object (a Principal) on the other side.

This means your tools don't need to know about cookies, tokens, or signatures.
They just check: "Does this Principal have permission?" Simple!

Let's see it in action...
    """)

    input(f"{Colors.BOLD}Press ENTER to start...{Colors.END}")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ================================================================
        # SCENARIO 1: Cookie Authentication (like a web login)
        # ================================================================
        print_section("SCENARIO 1: Cookie Authentication")

        print("""
Imagine you logged into a website with your username and password.
The website gave you a session cookie. Let's use that cookie to make requests.
        """)

        cookie_headers = {"Cookie": "session_id=sess_alice_123"}
        alice = await show_who_am_i(client, cookie_headers, "Cookie")

        print("Notice we became user 'user_alice' with STRONG authentication.")
        print("Alice has several permissions: rag:read, rag:write, diag:read")
        print()

        input(f"{Colors.BOLD}Press ENTER to continue...{Colors.END}")

        # Try accessing RAG search (should work - Alice has rag:read)
        await try_tool_access(
            client,
            cookie_headers,
            "RAG Search",
            "/tools/rag-search",
            {"query": "What is the universal adapter?"},
            "Alice has 'rag:read' permission, so this should work"
        )

        # Try accessing diagnostics (should work - Alice has diag:read AND strong auth)
        await try_tool_access(
            client,
            cookie_headers,
            "System Diagnostics",
            "/tools/diagnostics",
            {},
            "Alice has 'diag:read' AND strong authentication, so this should work"
        )

        input(f"{Colors.BOLD}Press ENTER for next scenario...{Colors.END}")

        # ================================================================
        # SCENARIO 2: OAuth Token (like an API token)
        # ================================================================
        print_section("SCENARIO 2: OAuth Token Authentication")

        print("""
Now imagine you're using an API token (OAuth) instead of a cookie.
This is common for mobile apps or third-party integrations.

Here's the cool part: Even though we're using a COMPLETELY DIFFERENT
authentication method, we still become a Principal on the other side!
        """)

        # Create a mock JWT token for demo (in real demo, this is a real JWT)
        # For this simple demo, we'll use a pre-generated token from the OAuth adapter
        import jwt
        token = jwt.encode(
            {"sub": "oauth_user_admin", "scope": "admin"},
            "demo-secret-key",
            algorithm="HS256"
        )

        oauth_headers = {"Authorization": f"Bearer {token}"}
        admin = await show_who_am_i(client, oauth_headers, "OAuth Token")

        print("Notice we became 'oauth_user_admin' with STRONG authentication.")
        print("This admin has MORE permissions: rag:read, rag:write, diag:read, diag:write")
        print()

        input(f"{Colors.BOLD}Press ENTER to continue...{Colors.END}")

        # Try accessing RAG search (should work - admin has rag:read)
        await try_tool_access(
            client,
            oauth_headers,
            "RAG Search",
            "/tools/rag-search",
            {"query": "How does OAuth work?"},
            "Admin has 'rag:read' permission, so this should work"
        )

        # Try accessing diagnostics (should work - admin has diag:read AND strong auth)
        await try_tool_access(
            client,
            oauth_headers,
            "System Diagnostics",
            "/tools/diagnostics",
            {},
            "Admin has 'diag:read' AND strong authentication, so this should work"
        )

        input(f"{Colors.BOLD}Press ENTER for next scenario...{Colors.END}")

        # ================================================================
        # SCENARIO 3: Slack Authentication (weaker auth)
        # ================================================================
        print_section("SCENARIO 3: Slack Bot Authentication")

        print("""
Now let's use Slack authentication. This is when a Slack bot calls your API.

Here's something important: Slack authentication is considered WEAKER because:
- It's just a shared secret between you and Slack
- It verifies the REQUEST came from Slack, but not which PERSON in Slack
- It's less secure than a proper login

Because of this, we give Slack users WEAKER permissions.
        """)

        slack_headers = {
            "x-slack-signature": "v0=mock_signature",
            "x-slack-request-timestamp": "1234567890",
            "Content-Type": "application/json"
        }

        # For this demo, we'll mock the Slack user
        # In the real system, this comes from the request body
        charlie = await show_who_am_i(client, slack_headers, "Slack Bot")

        print("Notice we became a Slack user with WEAK authentication.")
        print("Slack users only get 'rag:read' permission.")
        print()

        input(f"{Colors.BOLD}Press ENTER to continue...{Colors.END}")

        # Try accessing RAG search (should work - Slack user has rag:read, and RAG allows WEAK auth)
        await try_tool_access(
            client,
            slack_headers,
            "RAG Search",
            "/tools/rag-search",
            {"query": "What can Slack bots do?", "user_id": "U01ABC123"},
            "Slack user has 'rag:read' AND RAG Search allows WEAK auth, so this should work"
        )

        # Try accessing diagnostics (should FAIL - Slack is WEAK auth, but diagnostics requires STRONG)
        await try_tool_access(
            client,
            slack_headers,
            "System Diagnostics",
            "/tools/diagnostics",
            {},
            "Slack user has 'diag:read' BUT Slack is WEAK auth. Diagnostics requires STRONG auth, so this should FAIL"
        )

        print(f"{Colors.BOLD}☝️  This is the key security feature!{Colors.END}")
        print("Even though the Slack user has the right permission (diag:read),")
        print("they can't access sensitive diagnostics because Slack auth is WEAK.")
        print("This protects sensitive operations from less-secure auth methods.")
        print()

        input(f"{Colors.BOLD}Press ENTER for next scenario...{Colors.END}")

        # ================================================================
        # SCENARIO 4: Missing Permissions
        # ================================================================
        print_section("SCENARIO 4: User Without Permissions")

        print("""
Finally, let's see what happens when someone doesn't have the right permissions.
We'll use Bob's cookie - Bob only has 'rag:read' permission (no diagnostics access).
        """)

        bob_headers = {"Cookie": "session_id=sess_bob_456"}
        bob = await show_who_am_i(client, bob_headers, "Cookie (Bob)")

        print("Bob has STRONG authentication (cookie login), but LIMITED permissions.")
        print("Bob only has: rag:read")
        print()

        input(f"{Colors.BOLD}Press ENTER to continue...{Colors.END}")

        # Try accessing RAG search (should work - Bob has rag:read)
        await try_tool_access(
            client,
            bob_headers,
            "RAG Search",
            "/tools/rag-search",
            {"query": "What can Bob access?"},
            "Bob has 'rag:read' permission, so this should work"
        )

        # Try accessing diagnostics (should FAIL - Bob doesn't have diag:read)
        await try_tool_access(
            client,
            bob_headers,
            "System Diagnostics",
            "/tools/diagnostics",
            {},
            "Bob does NOT have 'diag:read' permission, so this should FAIL"
        )

        print(f"{Colors.BOLD}☝️  Another key security feature!{Colors.END}")
        print("Bob has STRONG authentication, but he still can't access diagnostics")
        print("because he doesn't have the 'diag:read' permission.")
        print("Both auth strength AND permissions must be satisfied.")
        print()

        input(f"{Colors.BOLD}Press ENTER for summary...{Colors.END}")

        # ================================================================
        # SUMMARY
        # ================================================================
        print_section("SUMMARY: Why This Matters")

        print(f"""
{Colors.BOLD}What we just saw:{Colors.END}

1. {Colors.GREEN}UNIFIED MODEL{Colors.END}
   - Cookie, OAuth, and Slack all become the same type of object: a Principal
   - Your tools don't need to know HOW someone authenticated
   - They just check: "Does this Principal have permission?"

2. {Colors.GREEN}AUTH STRENGTH LEVELS{Colors.END}
   - STRONG auth (Cookie, OAuth): Proper user login
   - WEAK auth (Slack): Less secure, shared-secret based
   - Sensitive operations can require STRONG auth only

3. {Colors.GREEN}PERMISSION CHECKING{Colors.END}
   - Each tool specifies what permissions it needs (e.g., 'rag:read')
   - Authorization happens in ONE place, consistently
   - No more scattered permission checks throughout your code!

4. {Colors.GREEN}SIMPLE TOOLS{Colors.END}
   - Tools don't implement authentication logic
   - Tools don't implement authorization logic
   - Tools just do their job and return results
   - All the security is handled BEFORE the tool runs

{Colors.BOLD}The Big Win:{Colors.END}
- Adding a new auth method? Just create one new adapter class.
- No need to update every tool in your system!
- Authorization rules stay consistent across ALL auth methods.
- Your code stays clean and easy to maintain.

{Colors.BOLD}This is the Universal Caller Adapter pattern!{Colors.END}
        """)


if __name__ == "__main__":
    print("\n" + Colors.BOLD + "=" * 80 + Colors.END)
    print(Colors.BOLD + "Starting Simple Demo - Make sure the server is running!".center(80) + Colors.END)
    print(Colors.BOLD + "(Tip: Use 'python run_demo.py' for automatic server management)".center(80) + Colors.END)
    print(Colors.BOLD + "=" * 80 + Colors.END + "\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}Error: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure the server is running on http://localhost:8000{Colors.END}")
