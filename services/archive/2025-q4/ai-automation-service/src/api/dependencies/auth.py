"""Authentication and authorization helpers for FastAPI routers."""

from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, Request, status

Role = Literal["user", "admin"]


@dataclass
class AuthContext:
    """Represents the authenticated caller."""

    role: Role
    token: str
    source: str = "header"


def get_auth_context(request: Request) -> AuthContext:
    """
    Retrieve the authentication context injected by AuthenticationMiddleware.
    """

    auth_context = getattr(request.state, "auth_context", None)

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return auth_context


def require_authenticated_user(auth_context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Dependency to ensure the caller is authenticated."""

    return auth_context


def require_admin_user(auth_context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Dependency to ensure the caller has admin privileges."""

    if auth_context.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return auth_context
