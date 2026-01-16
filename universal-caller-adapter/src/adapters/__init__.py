"""Authentication adapters - normalize different entry points to Principal."""
from .base import AuthAdapter
from .cookie import CookieAdapter
from .oauth import OAuthAdapter
from .slack import SlackAdapter

__all__ = ["AuthAdapter", "CookieAdapter", "OAuthAdapter", "SlackAdapter"]
