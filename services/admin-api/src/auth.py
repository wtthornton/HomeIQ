"""
Legacy compatibility shim for admin-api authentication imports.

The hardened authentication logic now lives in ``shared.auth`` so it can be
reused by multiple services. This module simply re-exports the shared
``AuthManager`` under the historical ``src.auth`` namespace used throughout
the admin-api codebase and tests.
"""

from shared.auth import AuthManager as SharedAuthManager
from shared.auth import User

__all__ = ["AuthManager", "User"]


class AuthManager(SharedAuthManager):
    """
    Backwards-compatible alias for :class:`shared.auth.AuthManager`.

    The ``enable_auth`` constructor argument is retained for legacy callers,
    but disabling authentication is no longer supported. Passing
    ``enable_auth=False`` raises a ``ValueError`` unless ``allow_anonymous`` is
    explicitly set (used only by unit tests).
    """

    def __init__(self, api_key, enable_auth: bool = True, **kwargs):
        if enable_auth is False and not kwargs.get("allow_anonymous"):
            raise ValueError(
                "Authentication cannot be disabled. Remove enable_auth=False."
            )

        super().__init__(api_key=api_key, **kwargs)

