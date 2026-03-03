"""Pydantic models for the gateway."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Permission manifest models
# ---------------------------------------------------------------------------

class MCPServerScope(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class MCPServerPermission(BaseModel):
    """Permission config for a single MCP server for a single user."""
    enabled: bool = False
    scope: MCPServerScope = MCPServerScope.READ_ONLY
    tables: list[str] | None = None  # MariaDB-specific table allowlist


class PermissionManifest(BaseModel):
    """
    Source of truth for what a user can do.
    Stored as Okta user attributes, read by gateway on every request.
    """
    user_id: str
    role: str = "limited"  # "owner" | "standard" | "limited"
    mcp_servers: dict[str, MCPServerPermission] = Field(default_factory=dict)

    def is_owner(self) -> bool:
        return self.role == "owner"

    def server_enabled(self, server_name: str) -> bool:
        if self.is_owner():
            return True
        perm = self.mcp_servers.get(server_name)
        return perm is not None and perm.enabled

    def get_server_permission(self, server_name: str) -> MCPServerPermission | None:
        return self.mcp_servers.get(server_name)


# ---------------------------------------------------------------------------
# User context — resolved from JWT on every request
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    """Resolved identity + permissions for the current request."""
    user_id: str
    email: str
    tenant_id: str = "default"
    manifest: PermissionManifest

    @property
    def is_owner(self) -> bool:
        return self.manifest.is_owner()


# ---------------------------------------------------------------------------
# MCP protocol models
# ---------------------------------------------------------------------------

class MCPToolCall(BaseModel):
    """Incoming request to call an MCP tool."""
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    """Result from an MCP tool call."""
    server_name: str
    tool_name: str
    result: Any = None
    error: str | None = None


class MCPToolInfo(BaseModel):
    """Description of a single MCP tool."""
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPServerInfo(BaseModel):
    """Registration info for a backend MCP server."""
    name: str
    url: str
    description: str = ""


# ---------------------------------------------------------------------------
# Memory models
# ---------------------------------------------------------------------------

class MemoryRecord(BaseModel):
    """A single conversation memory stored in pgvector."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content: str
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Admin UI models
# ---------------------------------------------------------------------------

class UserSummary(BaseModel):
    """User summary for the admin UI."""
    user_id: str
    email: str
    role: str
    enabled_servers: list[str] = Field(default_factory=list)
