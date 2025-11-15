"""
Shared authentication manager for secured HomeIQ services.

Implements API-key enforcement, optional JWT support, and basic session
tracking that can be reused across admin-api, data-api, and other FastAPI
services. Authentication can no longer be disabled through configuration.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class User(BaseModel):
    """Simple authenticated user representation."""

    username: str
    permissions: List[str] = []
    created_at: datetime
    last_login: Optional[datetime] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class AuthManager:
    """Authentication manager providing API key + JWT validation."""

    def __init__(
        self,
        api_key: Optional[str],
        *,
        allow_anonymous: bool = False,
        users: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the authentication manager.

        Args:
            api_key: Static API key that must be presented as Bearer token.
            allow_anonymous: Intended for unit tests only; skips API key enforcement.
            users: Optional list of user definitions (dicts) for JWT/password auth.
        """

        if not api_key and not allow_anonymous:
            raise ValueError(
                "API key is required – authentication cannot be disabled in production"
            )

        self.api_key = api_key
        self.allow_anonymous = allow_anonymous

        self.security = HTTPBearer(auto_error=False)
        self.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

        self.secret_key = os.getenv("ADMIN_API_JWT_SECRET") or secrets.token_urlsafe(32)
        self.algorithm = os.getenv("ADMIN_API_JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ADMIN_API_JWT_TTL", "30"))

        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = 3600  # seconds

        # The pseudo-user returned when API key authentication succeeds
        self.api_key_user = User(
            username="api-key",
            permissions=["admin"],
            created_at=datetime.now(),
        )

        # Configurable user store for JWT/password auth
        self.users_db: Dict[str, Dict[str, Any]] = {}
        self._load_users(users)

        logger.info(
            "Authentication manager initialized (anonymous=%s)", self.allow_anonymous
        )

    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        ),
    ):
        """
        FastAPI dependency that enforces authentication.

        Supports either JWT bearer tokens (preferred) or the static API key.
        """

        if credentials is None or not credentials.credentials:
            if self.allow_anonymous:
                return self.api_key_user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials.strip()
        user = self.verify_token(token)
        if user:
            user["last_login"] = datetime.utcnow()
            return user

        if self._validate_api_key(token):
            self.api_key_user.last_login = datetime.utcnow()
            return self.api_key_user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _validate_api_key(self, presented_key: str) -> bool:
        """Constant-time API key comparison."""
        if not self.api_key:
            logger.warning("API key validation requested but no key is configured")
            return False
        return secrets.compare_digest(presented_key, self.api_key)

    def validate_api_key(self, api_key: Optional[str]) -> bool:
        """Public helper for validating API key strings."""
        if not api_key:
            return False
        return self._validate_api_key(api_key)

    def generate_api_key(self) -> str:
        """Generate a new API key value."""
        return secrets.token_urlsafe(32)

    # ----------------------------------------------------------------------
    # Password / JWT helpers
    # ----------------------------------------------------------------------

    def register_user(
        self,
        username: str,
        password: str,
        *,
        permissions: Optional[List[str]] = None,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        """Register a new user (mainly for tests or setup scripts)."""
        self.users_db[username] = {
            "username": username,
            "hashed_password": self.get_password_hash(password),
            "full_name": full_name,
            "email": email,
            "disabled": disabled,
            "permissions": permissions or ["admin"],
        }

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a stored hash."""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except ValueError:
            logger.warning("Password verification failed due to invalid hash")
            return False

    def get_password_hash(self, password: str) -> str:
        """Return a PBKDF2-SHA256 hash for the provided password."""
        return self.pwd_context.hash(password)

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch a user definition."""
        return self.users_db.get(username)

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user using username/password credentials."""
        user = self.get_user(username)
        if not user or user.get("disabled"):
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a signed JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": True, "verify_exp": True},
            )
        except JWTError as exc:
            logger.warning("Failed to decode JWT: %s", exc)
            return None

        username: Optional[str] = payload.get("sub")
        if not username:
            return None

        user = self.get_user(username)
        if not user or user.get("disabled"):
            return None

        return {
            "username": user["username"],
            "permissions": user.get("permissions", []),
            "full_name": user.get("full_name"),
            "email": user.get("email"),
            "last_login": datetime.utcnow(),
        }

    # ----------------------------------------------------------------------
    # Session helpers retained for backwards compatibility
    # ----------------------------------------------------------------------

    def create_session(self, user: User) -> str:
        """Create a short-lived opaque session token."""
        session_token = secrets.token_urlsafe(32)
        self.sessions[session_token] = {
            "user": user,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=self.session_timeout),
        }
        logger.debug("Created session for user %s", user.username)
        return session_token

    def validate_session(self, session_token: str) -> Optional[User]:
        """Validate a stored session token."""
        session = self.sessions.get(session_token)
        if not session:
            return None
        if datetime.now() > session["expires_at"]:
            del self.sessions[session_token]
            return None
        return session["user"]

    def revoke_session(self, session_token: str) -> None:
        """Revoke an existing session token."""
        if session_token in self.sessions:
            del self.sessions[session_token]
            logger.debug("Revoked session %s", session_token)

    def cleanup_expired_sessions(self) -> None:
        """Remove expired session entries."""
        now = datetime.now()
        expired = [
            token for token, session in self.sessions.items() if now > session["expires_at"]
        ]
        for token in expired:
            del self.sessions[token]
        if expired:
            logger.debug("Cleaned up %s expired sessions", len(expired))

    def get_session_statistics(self) -> Dict[str, Any]:
        """Return diagnostic information about session usage."""
        now = datetime.now()
        active = sum(1 for session in self.sessions.values() if now <= session["expires_at"])
        expired = len(self.sessions) - active
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active,
            "expired_sessions": expired,
            "session_timeout": self.session_timeout,
            "authentication_enforced": not self.allow_anonymous,
        }

    def configure_auth(self, api_key: Optional[str], enable_auth: Optional[bool] = None):
        """
        Legacy helper retained for backward compatibility.

        Disabling authentication is not supported; requests to do so are ignored.
        """

        if enable_auth is False and not self.allow_anonymous:
            logger.warning(
                "Ignoring request to disable authentication – this toggle is deprecated"
            )
        self.api_key = api_key

    def configure_session_timeout(self, timeout: int):
        """Update the session timeout duration."""
        if timeout <= 0:
            raise ValueError("Session timeout must be positive")
        self.session_timeout = timeout
        logger.info("Updated session timeout to %s seconds", timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_users(self, provided_users: Optional[List[Dict[str, Any]]]) -> None:
        """Populate the user store from provided config or environment variables."""
        definitions = provided_users or self._load_users_from_env()
        for entry in definitions:
            username = entry.get("username")
            if not username:
                logger.warning("Skipping user definition without username: %s", entry)
                continue

            password_hash = entry.get("password_hash")
            password_plain = entry.get("password")

            if password_hash:
                hashed = password_hash
            elif password_plain:
                hashed = self.get_password_hash(password_plain)
            else:
                logger.warning("Skipping user %s – no password supplied", username)
                continue

            self.users_db[username] = {
                "username": username,
                "hashed_password": hashed,
                "full_name": entry.get("full_name"),
                "email": entry.get("email"),
                "permissions": entry.get("permissions", ["admin"]),
                "disabled": entry.get("disabled", False),
            }

    def _load_users_from_env(self) -> List[Dict[str, Any]]:
        """Load user definitions from ADMIN_API_USERS_* environment variables."""
        users_json = os.getenv("ADMIN_API_USERS_JSON")
        if users_json:
            try:
                data = json.loads(users_json)
                if isinstance(data, list):
                    return data
                logger.warning("ADMIN_API_USERS_JSON must be a JSON list")
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse ADMIN_API_USERS_JSON: %s", exc)

        users_file = os.getenv("ADMIN_API_USERS_FILE")
        if users_file:
            path = Path(users_file)
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    logger.error("Failed to read ADMIN_API_USERS_FILE: %s", exc)

        return []

