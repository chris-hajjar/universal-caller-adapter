"""Tests for the permission enforcement layer."""

import pytest

from gateway.models import (
    MCPServerPermission,
    MCPServerScope,
    PermissionManifest,
    UserContext,
)
from gateway.permissions import (
    PermissionDenied,
    check_mcp_call_permissions,
    enforce_server_access,
    enforce_sql_permissions,
    enforce_table_access,
    enforce_write_access,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(
    email: str = "test@company.com",
    role: str = "standard",
    servers: dict | None = None,
) -> UserContext:
    if servers is None:
        servers = {}
    return UserContext(
        user_id=email,
        email=email,
        manifest=PermissionManifest(
            user_id=email,
            role=role,
            mcp_servers={
                name: MCPServerPermission(**cfg) for name, cfg in servers.items()
            },
        ),
    )


OWNER = _make_user(
    email="chris@company.com",
    role="owner",
    servers={
        "mariadb": {"enabled": True, "scope": "read_write", "tables": None},
        "memory": {"enabled": True},
        "slack": {"enabled": True},
    },
)

USER_A = _make_user(
    email="user_a@company.com",
    role="standard",
    servers={
        "mariadb": {
            "enabled": True,
            "scope": "read_only",
            "tables": ["invoices", "orders", "products"],
        },
        "memory": {"enabled": True, "scope": "read_write"},
        "slack": {"enabled": True},
    },
)

USER_B = _make_user(
    email="user_b@company.com",
    role="limited",
    servers={
        "mariadb": {
            "enabled": True,
            "scope": "read_only",
            "tables": ["invoices"],
        },
        "memory": {"enabled": True, "scope": "read_write"},
        "slack": {"enabled": False},
    },
)


# ---------------------------------------------------------------------------
# Server access
# ---------------------------------------------------------------------------


class TestServerAccess:
    def test_owner_bypasses_all_checks(self):
        # Owner should access anything, even unregistered servers
        enforce_server_access(OWNER, "mariadb")
        enforce_server_access(OWNER, "nonexistent_server")

    def test_user_a_can_access_enabled_servers(self):
        enforce_server_access(USER_A, "mariadb")
        enforce_server_access(USER_A, "memory")
        enforce_server_access(USER_A, "slack")

    def test_user_a_cannot_access_disabled_servers(self):
        with pytest.raises(PermissionDenied):
            enforce_server_access(USER_A, "reports")

    def test_user_b_cannot_access_slack(self):
        with pytest.raises(PermissionDenied):
            enforce_server_access(USER_B, "slack")

    def test_user_b_can_access_mariadb(self):
        enforce_server_access(USER_B, "mariadb")

    def test_unknown_server_denied(self):
        with pytest.raises(PermissionDenied):
            enforce_server_access(USER_A, "unknown_server")


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------


class TestTableAccess:
    def test_owner_bypasses_table_checks(self):
        enforce_table_access(OWNER, "mariadb", "reports")
        enforce_table_access(OWNER, "mariadb", "secret_table")

    def test_user_a_can_access_allowed_tables(self):
        enforce_table_access(USER_A, "mariadb", "invoices")
        enforce_table_access(USER_A, "mariadb", "orders")
        enforce_table_access(USER_A, "mariadb", "products")

    def test_user_a_cannot_access_restricted_tables(self):
        with pytest.raises(PermissionDenied):
            enforce_table_access(USER_A, "mariadb", "users")
        with pytest.raises(PermissionDenied):
            enforce_table_access(USER_A, "mariadb", "reports")

    def test_user_b_can_only_access_invoices(self):
        enforce_table_access(USER_B, "mariadb", "invoices")
        with pytest.raises(PermissionDenied):
            enforce_table_access(USER_B, "mariadb", "orders")
        with pytest.raises(PermissionDenied):
            enforce_table_access(USER_B, "mariadb", "products")


# ---------------------------------------------------------------------------
# Write access
# ---------------------------------------------------------------------------


class TestWriteAccess:
    def test_owner_can_write(self):
        enforce_write_access(OWNER, "mariadb")

    def test_read_only_user_cannot_write(self):
        with pytest.raises(PermissionDenied):
            enforce_write_access(USER_A, "mariadb")
        with pytest.raises(PermissionDenied):
            enforce_write_access(USER_B, "mariadb")


# ---------------------------------------------------------------------------
# SQL enforcement
# ---------------------------------------------------------------------------


class TestSQLEnforcement:
    def test_owner_bypasses_sql_checks(self):
        enforce_sql_permissions(OWNER, "mariadb", "DELETE FROM users")

    def test_select_on_allowed_table(self):
        enforce_sql_permissions(USER_A, "mariadb", "SELECT * FROM invoices")
        enforce_sql_permissions(USER_A, "mariadb", "SELECT * FROM orders")

    def test_select_on_denied_table(self):
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(USER_A, "mariadb", "SELECT * FROM users")

    def test_write_blocked_for_read_only(self):
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(
                USER_A, "mariadb", "INSERT INTO invoices (amount) VALUES (100)"
            )
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(
                USER_A, "mariadb", "UPDATE invoices SET amount = 100"
            )
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(
                USER_A, "mariadb", "DELETE FROM invoices WHERE id = 1"
            )

    def test_user_b_blocked_from_orders(self):
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(
                USER_B, "mariadb", "SELECT * FROM orders"
            )

    def test_join_with_denied_table(self):
        with pytest.raises(PermissionDenied):
            enforce_sql_permissions(
                USER_B,
                "mariadb",
                "SELECT * FROM invoices JOIN orders ON invoices.order_id = orders.id",
            )


# ---------------------------------------------------------------------------
# Full MCP call check
# ---------------------------------------------------------------------------


class TestMCPCallPermissions:
    def test_allowed_query(self):
        check_mcp_call_permissions(
            USER_A, "mariadb", "query", {"query": "SELECT * FROM invoices"}
        )

    def test_denied_server(self):
        with pytest.raises(PermissionDenied):
            check_mcp_call_permissions(
                USER_B, "slack", "send_message", {"text": "hello"}
            )

    def test_denied_table_in_query(self):
        with pytest.raises(PermissionDenied):
            check_mcp_call_permissions(
                USER_B, "mariadb", "query", {"query": "SELECT * FROM orders"}
            )

    def test_memory_access_allowed(self):
        check_mcp_call_permissions(
            USER_A, "memory", "search", {"query": "test"}
        )

    def test_owner_full_access(self):
        check_mcp_call_permissions(
            OWNER, "mariadb", "query", {"query": "DROP TABLE users"}
        )
        check_mcp_call_permissions(
            OWNER, "reports", "generate", {}
        )
