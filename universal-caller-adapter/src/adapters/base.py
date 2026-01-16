"""Base authentication adapter interface."""
from abc import ABC, abstractmethod
from typing import Optional
from fastapi import Request

from src.models import Principal


class AuthAdapter(ABC):
    """
    Base interface for authentication adapters.

    Each adapter is responsible for:
    1. Detecting if a request matches its auth method
    2. Extracting and validating credentials
    3. Resolving to a Principal

    Adapters should NOT perform authorization - only authentication.
    """

    @abstractmethod
    async def can_handle(self, request: Request) -> bool:
        """
        Check if this adapter can handle the given request.

        Returns:
            True if this adapter recognizes the auth method in the request
        """
        pass

    @abstractmethod
    async def authenticate(self, request: Request) -> Optional[Principal]:
        """
        Authenticate the request and resolve to a Principal.

        Returns:
            Principal if authentication succeeds, None if it fails
        """
        pass
