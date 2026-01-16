"""Diagnostics tool - demonstrates sensitive tool with strict auth requirements."""
from typing import Dict, Any
import platform
import sys

from src.models import Principal


async def diagnostics(principal: Principal) -> Dict[str, Any]:
    """
    System diagnostics - sensitive operation.

    This tool requires:
    - diag:read entitlement
    - STRONG authentication (enforced by authorizer, not here)

    Like all tools, this is auth-agnostic and trusts that
    authorization already happened.

    Args:
        principal: The authenticated caller (for logging/audit)

    Returns:
        System diagnostic information
    """
    return {
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": sys.version,
            "architecture": platform.machine()
        },
        "principal": {
            "principal_id": principal.principal_id,
            "tenant_id": principal.tenant_id,
            "auth_method": principal.auth_method.value,
            "auth_strength": principal.auth_strength.value,
            "entitlements": list(principal.entitlements)
        },
        "warning": "This is sensitive diagnostic data - requires strong auth"
    }
