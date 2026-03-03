"""Tests for the gateway API endpoints."""

import pytest
from fastapi.testclient import TestClient

from gateway.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_no_auth(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "servers" in data


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestAuth:
    def test_whoami_no_token(self):
        resp = client.get("/whoami")
        assert resp.status_code == 401

    def test_whoami_with_dev_token(self):
        """In dev mode, any token is accepted as a user identifier."""
        resp = client.get(
            "/whoami",
            headers={"Authorization": "Bearer user_a@company.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user_a@company.com"
        assert data["role"] == "standard"

    def test_whoami_owner(self):
        resp = client.get(
            "/whoami",
            headers={"Authorization": "Bearer chris@company.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_owner"] is True
        assert data["role"] == "owner"

    def test_whoami_user_b(self):
        resp = client.get(
            "/whoami",
            headers={"Authorization": "Bearer user_b@company.com"},
        )
        data = resp.json()
        assert data["role"] == "limited"
        # User B should not have slack enabled
        assert data["mcp_servers"]["slack"]["enabled"] is False


# ---------------------------------------------------------------------------
# MCP tool listing
# ---------------------------------------------------------------------------


class TestToolListing:
    def test_list_tools_requires_auth(self):
        resp = client.get("/mcp/tools")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# MCP tool calls — permission enforcement
# ---------------------------------------------------------------------------


class TestMCPCalls:
    def test_call_requires_auth(self):
        resp = client.post(
            "/mcp/call",
            json={
                "server_name": "mariadb",
                "tool_name": "query",
                "arguments": {"query": "SELECT 1"},
            },
        )
        assert resp.status_code == 401

    def test_user_b_blocked_from_slack(self):
        resp = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer user_b@company.com"},
            json={
                "server_name": "slack",
                "tool_name": "send_message",
                "arguments": {"text": "hello"},
            },
        )
        assert resp.status_code == 403

    def test_user_b_blocked_from_orders(self):
        resp = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer user_b@company.com"},
            json={
                "server_name": "mariadb",
                "tool_name": "query",
                "arguments": {"query": "SELECT * FROM orders"},
            },
        )
        assert resp.status_code == 403

    def test_user_a_blocked_from_reports_server(self):
        resp = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer user_a@company.com"},
            json={
                "server_name": "reports",
                "tool_name": "generate",
                "arguments": {},
            },
        )
        assert resp.status_code == 403

    def test_user_a_blocked_from_write(self):
        resp = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer user_a@company.com"},
            json={
                "server_name": "mariadb",
                "tool_name": "query",
                "arguments": {"query": "INSERT INTO invoices (amount) VALUES (100)"},
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


class TestAdmin:
    def test_admin_requires_owner(self):
        resp = client.get(
            "/admin/users",
            headers={"Authorization": "Bearer user_a@company.com"},
        )
        assert resp.status_code == 403

    def test_admin_owner_can_list_users(self):
        resp = client.get(
            "/admin/users",
            headers={"Authorization": "Bearer chris@company.com"},
        )
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 3
        emails = [u["email"] for u in users]
        assert "chris@company.com" in emails
        assert "user_a@company.com" in emails
        assert "user_b@company.com" in emails
