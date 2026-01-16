"""
Authentication middleware - the entry point that coordinates adapters.

This middleware:
1. Tries each adapter in order
2. Resolves to a Principal (or anonymous if all fail)
3. Attaches Principal to request state
4. Never blocks requests - always produces a Principal
"""
from typing import List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.models import Principal
from src.adapters import AuthAdapter


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that normalizes all entry points to a Principal.

    Key behavior:
    - Tries adapters in order (first match wins)
    - Falls back to anonymous Principal if no adapter succeeds
    - Never rejects requests at this layer (authorization happens later)
    - Attaches Principal to request.state for downstream use
    """

    def __init__(self, app, adapters: List[AuthAdapter]):
        """
        Args:
            app: FastAPI application
            adapters: List of auth adapters (order matters - first match wins)
        """
        super().__init__(app)
        self.adapters = adapters

    async def dispatch(self, request: Request, call_next):
        """
        Resolve request to a Principal and attach to request state.
        """
        principal = await self._resolve_principal(request)

        # Attach to request state for downstream handlers
        request.state.principal = principal

        # Continue processing
        response = await call_next(request)
        return response

    async def _resolve_principal(self, request: Request) -> Principal:
        """
        Try each adapter in order to resolve a Principal.

        Returns:
            Principal (authenticated or anonymous)
        """
        for adapter in self.adapters:
            try:
                # Check if adapter can handle this request
                if not await adapter.can_handle(request):
                    continue

                # Try to authenticate
                principal = await adapter.authenticate(request)
                if principal:
                    return principal

            except Exception as e:
                # Log error but continue trying other adapters
                # In production, you'd use proper logging
                print(f"Adapter {adapter.__class__.__name__} failed: {e}")
                continue

        # No adapter succeeded - return anonymous principal
        return Principal.anonymous()
