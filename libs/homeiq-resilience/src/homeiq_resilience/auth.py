"""Cross-group service-to-service Bearer token authentication.

Provides a reusable FastAPI dependency that validates ``Authorization: Bearer <token>``
headers against a pre-shared secret configured via environment variable.  Services
opt in by adding the dependency to their route definitions::

    from homeiq_resilience import require_service_auth

    @app.get("/api/v1/data", dependencies=[Depends(require_service_auth)])
    async def get_data():
        ...

The expected token is read from the ``SERVICE_AUTH_TOKEN`` environment variable
(configurable via the *env_var* parameter).  When the env var is **not set**,
authentication is **disabled** so that local development and tests work without
extra configuration.
"""

from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Reusable scheme instance — extracts the Bearer token from the header.
_bearer_scheme = HTTPBearer(auto_error=False)


class ServiceAuthValidator:
    """Callable FastAPI dependency that validates Bearer tokens.

    Parameters
    ----------
    env_var:
        Name of the environment variable holding the expected token.
        Defaults to ``SERVICE_AUTH_TOKEN``.
    """

    def __init__(self, env_var: str = "SERVICE_AUTH_TOKEN") -> None:
        self._env_var = env_var

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = None,
    ) -> str | None:
        """Validate the Bearer token from the request.

        Returns
        -------
        str or None
            The validated token string, or ``None`` when auth is disabled.

        Raises
        ------
        HTTPException (401)
            If a token is required but missing or invalid.
        """
        expected_token = os.getenv(self._env_var)

        # Auth disabled — allow all requests (local dev / testing).
        if not expected_token:
            return None

        # Extract credentials via the HTTPBearer scheme.
        if credentials is None:
            credentials = await _bearer_scheme(request)

        if credentials is None:
            logger.warning(
                "Missing Authorization header on %s %s",
                request.method,
                request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if credentials.credentials != expected_token:
            logger.warning(
                "Invalid service token on %s %s (source=%s)",
                request.method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return credentials.credentials


# Default instance — most services can use this directly.
require_service_auth = ServiceAuthValidator()
