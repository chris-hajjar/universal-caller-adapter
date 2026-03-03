#!/usr/bin/env python3
"""
Quick integration test for the gateway.

Tests all three users against the gateway to verify permission enforcement.
Run the gateway first: uvicorn gateway.main:app --port 8000

Usage:
    python scripts/test_gateway.py
"""

import httpx
import json
import sys

GATEWAY_URL = "http://localhost:8000"


def test(description: str, method: str, path: str, token: str, body: dict | None = None, expect_status: int = 200):
    """Run a single test case."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GATEWAY_URL}{path}"

    if method == "GET":
        resp = httpx.get(url, headers=headers, timeout=10.0)
    else:
        resp = httpx.post(url, json=body or {}, headers=headers, timeout=10.0)

    status_icon = "PASS" if resp.status_code == expect_status else "FAIL"
    print(f"  [{status_icon}] {description}")
    print(f"         Status: {resp.status_code} (expected {expect_status})")
    if resp.status_code != expect_status:
        print(f"         Body: {resp.text[:200]}")
    return resp.status_code == expect_status


def main():
    print("=" * 60)
    print("Agentic Platform Gateway — Integration Tests")
    print("=" * 60)

    # Health check
    print("\n--- Health Check ---")
    try:
        resp = httpx.get(f"{GATEWAY_URL}/health", timeout=5.0)
        if resp.status_code != 200:
            print(f"Gateway not healthy: {resp.status_code}")
            sys.exit(1)
        print("  [PASS] Gateway is running")
    except httpx.ConnectError:
        print("  [FAIL] Cannot connect to gateway. Is it running?")
        sys.exit(1)

    passed = 0
    failed = 0

    # --- Chris (Owner) — full access ---
    print("\n--- Chris (Owner) ---")
    token_chris = "dev:chris@company.com"

    tests = [
        ("Query all tables (invoices)", "POST", "/mcp/mariadb/query",
         token_chris, {"sql": "SELECT * FROM invoices LIMIT 5"}, 200),
        ("Query all tables (reports)", "POST", "/mcp/mariadb/query",
         token_chris, {"sql": "SELECT * FROM reports LIMIT 5"}, 200),
        ("Query all tables (users)", "POST", "/mcp/mariadb/query",
         token_chris, {"sql": "SELECT * FROM users LIMIT 5"}, 200),
        ("Write access", "POST", "/mcp/mariadb/query",
         token_chris, {"sql": "INSERT INTO users (email, name) VALUES ('test@test.com', 'Test')"}, 200),
        ("Admin: list users", "GET", "/admin/users", token_chris, None, 200),
    ]

    for t in tests:
        if test(*t):
            passed += 1
        else:
            failed += 1

    # --- User A — invoices, orders, products (read only) ---
    print("\n--- User A (Limited) ---")
    token_a = "dev:user_a@company.com"

    tests = [
        ("Query invoices (allowed)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "SELECT * FROM invoices LIMIT 5"}, 200),
        ("Query orders (allowed)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "SELECT * FROM orders LIMIT 5"}, 200),
        ("Query products (allowed)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "SELECT * FROM products LIMIT 5"}, 200),
        ("Query reports (DENIED)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "SELECT * FROM reports LIMIT 5"}, 403),
        ("Query users (DENIED)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "SELECT * FROM users LIMIT 5"}, 403),
        ("Write access (DENIED)", "POST", "/mcp/mariadb/query",
         token_a, {"sql": "INSERT INTO invoices (amount) VALUES (100)"}, 403),
        ("Admin: list users (DENIED)", "GET", "/admin/users", token_a, None, 403),
    ]

    for t in tests:
        if test(*t):
            passed += 1
        else:
            failed += 1

    # --- User B — invoices only (read only), no Slack ---
    print("\n--- User B (Limited) ---")
    token_b = "dev:user_b@company.com"

    tests = [
        ("Query invoices (allowed)", "POST", "/mcp/mariadb/query",
         token_b, {"sql": "SELECT * FROM invoices LIMIT 5"}, 200),
        ("Query orders (DENIED)", "POST", "/mcp/mariadb/query",
         token_b, {"sql": "SELECT * FROM orders LIMIT 5"}, 403),
        ("Query products (DENIED)", "POST", "/mcp/mariadb/query",
         token_b, {"sql": "SELECT * FROM products LIMIT 5"}, 403),
        ("Slack MCP (DENIED)", "POST", "/mcp/slack/send",
         token_b, {"message": "hello"}, 403),
        ("Memory search (allowed)", "POST", "/memory/search",
         token_b, {"query": "test"}, 200),
    ]

    for t in tests:
        if test(*t):
            passed += 1
        else:
            failed += 1

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
