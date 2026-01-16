"""Canonical caller model - the single source of truth for 'who is calling'."""
from enum import Enum
from typing import Optional, Set
from dataclasses import dataclass, field


class AuthMethod(str, Enum):
    """How the caller was authenticated."""
    COOKIE = "cookie"
    OAUTH = "oauth"
    SLACK = "slack"
    ANONYMOUS = "anonymous"


class AuthStrength(str, Enum):
    """Security level of the authentication."""
    STRONG = "strong"
    WEAK = "weak"
    ANONYMOUS = "anonymous"


@dataclass
class Principal:
    """
    Canonical representation of a caller.

    This is the normalized model that ALL authentication entry points
    must resolve to. Authorization decisions are made based on this
    structure alone.
    """
    principal_id: str
    tenant_id: Optional[str] = None
    auth_method: AuthMethod = AuthMethod.ANONYMOUS
    auth_strength: AuthStrength = AuthStrength.ANONYMOUS
    entitlements: Set[str] = field(default_factory=set)

    @property
    def is_authenticated(self) -> bool:
        """Check if this is an authenticated (non-anonymous) principal."""
        return self.auth_method != AuthMethod.ANONYMOUS

    @property
    def is_strong_auth(self) -> bool:
        """Check if this principal has strong authentication."""
        return self.auth_strength == AuthStrength.STRONG

    def has_entitlement(self, entitlement: str) -> bool:
        """Check if principal has a specific entitlement."""
        return entitlement in self.entitlements

    @classmethod
    def anonymous(cls) -> "Principal":
        """Create an anonymous principal for unauthenticated requests."""
        return cls(
            principal_id="anonymous",
            auth_method=AuthMethod.ANONYMOUS,
            auth_strength=AuthStrength.ANONYMOUS,
            entitlements=set()
        )
