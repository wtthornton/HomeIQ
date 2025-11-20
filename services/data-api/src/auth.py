"""
Authentication Manager for Admin API
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model"""
    username: str
    permissions: list[str] = []
    created_at: datetime
    last_login: datetime | None = None


class AuthManager:
    """Authentication manager for Admin API"""

    def __init__(self, api_key: str | None = None, enable_auth: bool = True):
        """
        Initialize authentication manager
        
        Args:
            api_key: API key for authentication
            enable_auth: Whether to enable authentication
        """
        self.api_key = api_key
        self.enable_auth = enable_auth

        # Security scheme
        self.security = HTTPBearer(auto_error=False)

        # Default user
        self.default_user = User(
            username="admin",
            permissions=["read", "write", "admin"],
            created_at=datetime.now()
        )

        # Session management
        self.sessions: dict[str, dict[str, Any]] = {}
        self.session_timeout = 3600  # 1 hour

        logger.info(f"Authentication manager initialized (enabled: {enable_auth})")

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))):
        """
        Get current authenticated user
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User object
            
        Raises:
            HTTPException: If authentication fails
        """
        if not self.enable_auth:
            return self.default_user

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate API key
        if not self._validate_api_key(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login
        self.default_user.last_login = datetime.now()

        return self.default_user

    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self.api_key:
            logger.warning("No API key configured")
            return False

        return secrets.compare_digest(api_key, self.api_key)

    def generate_api_key(self) -> str:
        """
        Generate a new API key
        
        Returns:
            New API key
        """
        return secrets.token_urlsafe(32)

    def create_session(self, user: User) -> str:
        """
        Create a new session
        
        Args:
            user: User to create session for
            
        Returns:
            Session token
        """
        session_token = secrets.token_urlsafe(32)

        self.sessions[session_token] = {
            "user": user,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=self.session_timeout)
        }

        logger.debug(f"Created session for user {user.username}")
        return session_token

    def validate_session(self, session_token: str) -> User | None:
        """
        Validate session token
        
        Args:
            session_token: Session token to validate
            
        Returns:
            User if valid, None otherwise
        """
        if session_token not in self.sessions:
            return None

        session = self.sessions[session_token]

        # Check if session is expired
        if datetime.now() > session["expires_at"]:
            del self.sessions[session_token]
            return None

        return session["user"]

    def revoke_session(self, session_token: str):
        """
        Revoke a session
        
        Args:
            session_token: Session token to revoke
        """
        if session_token in self.sessions:
            del self.sessions[session_token]
            logger.debug(f"Revoked session {session_token}")

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []

        for session_token, session in self.sessions.items():
            if current_time > session["expires_at"]:
                expired_sessions.append(session_token)

        for session_token in expired_sessions:
            del self.sessions[session_token]

        if expired_sessions:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")

    def get_session_statistics(self) -> dict[str, Any]:
        """Get session statistics"""
        current_time = datetime.now()
        active_sessions = 0
        expired_sessions = 0

        for session in self.sessions.values():
            if current_time <= session["expires_at"]:
                active_sessions += 1
            else:
                expired_sessions += 1

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "session_timeout": self.session_timeout,
            "authentication_enabled": self.enable_auth
        }

    def configure_auth(self, api_key: str | None, enable_auth: bool):
        """
        Configure authentication settings
        
        Args:
            api_key: New API key
            enable_auth: Whether to enable authentication
        """
        self.api_key = api_key
        self.enable_auth = enable_auth
        logger.info(f"Updated authentication settings (enabled: {enable_auth})")

    def configure_session_timeout(self, timeout: int):
        """
        Configure session timeout
        
        Args:
            timeout: Session timeout in seconds
        """
        if timeout <= 0:
            raise ValueError("Session timeout must be positive")

        self.session_timeout = timeout
        logger.info(f"Updated session timeout to {timeout} seconds")
