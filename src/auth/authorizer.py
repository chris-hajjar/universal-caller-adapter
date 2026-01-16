"""Centralized authorization - enforces permissions before tool execution."""
from dataclasses import dataclass
from typing import Set, Optional

from src.models import Principal, AUTH_STRENGTH_WEAK


class AuthorizationError(Exception):
    """Raised when a principal lacks required permissions."""

    def __init__(self, message: str, reason: str = None):
        super().__init__(message)
        self.reason = reason


@dataclass
class ToolPolicy:
    """
    Authorization policy for a tool.

    Defines what permissions and auth strength are required to invoke a tool.
    """
    tool_name: str
    required_entitlements: Set[str]
    min_auth_strength: int = AUTH_STRENGTH_WEAK
    description: str = ""


class Authorizer:
    """
    Centralized authorization layer.

    This is the single place where authorization decisions are made.
    Tools should NEVER perform their own authorization checks.

    Key principles:
    - Authorization happens BEFORE tool execution
    - Based solely on Principal and ToolPolicy
    - Tools remain auth-agnostic
    """

    def __init__(self, policies: dict[str, ToolPolicy] = None):
        """
        Args:
            policies: Map of tool_name -> ToolPolicy
        """
        self.policies = policies or {}

    def register_policy(self, policy: ToolPolicy):
        """Register a tool policy."""
        self.policies[policy.tool_name] = policy

    def authorize(self, principal: Principal, tool_name: str) -> None:
        """
        Authorize a principal to invoke a tool.

        Args:
            principal: The caller requesting access
            tool_name: The tool being invoked

        Raises:
            AuthorizationError: If authorization fails
        """
        policy = self.policies.get(tool_name)
        if not policy:
            # No policy defined = allow (fail open for demo)
            # In production, you might fail closed
            return

        # Check authentication strength
        if not self._check_auth_strength(principal, policy.min_auth_strength):
            raise AuthorizationError(
                f"Tool '{tool_name}' requires auth strength {policy.min_auth_strength}, "
                f"but caller has {principal.auth_strength}",
                reason="insufficient_auth_strength"
            )

        # Check entitlements
        missing = policy.required_entitlements - principal.entitlements
        if missing:
            raise AuthorizationError(
                f"Tool '{tool_name}' requires entitlements {policy.required_entitlements}, "
                f"but caller lacks: {missing}",
                reason="missing_entitlements"
            )

    def _check_auth_strength(self, principal: Principal, min_strength: int) -> bool:
        """Check if principal meets minimum auth strength requirement."""
        return principal.auth_strength >= min_strength

    def can_access(self, principal: Principal, tool_name: str) -> bool:
        """
        Check if principal can access a tool without raising an exception.

        Returns:
            True if authorized, False otherwise
        """
        try:
            self.authorize(principal, tool_name)
            return True
        except AuthorizationError:
            return False
