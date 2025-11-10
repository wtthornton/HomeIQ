"""
Authentication Manager for Admin API
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import calendar
import secrets

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model"""
    username: str
    permissions: list[str] = []
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthManager:
    """Authentication manager for Admin API"""
    
    def __init__(self, api_key: Optional[str] = None, enable_auth: bool = True):
        """
        Initialize authentication manager
        
        Args:
            api_key: API key for authentication
            enable_auth: Whether to enable authentication
        """
        self.api_key = api_key
        self.enable_auth = enable_auth
        self.secret_key = secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        
        # Security scheme
        self.security = HTTPBearer(auto_error=False)
        
        # Default user
        self.default_user = User(
            username="admin",
            permissions=["read", "write", "admin"],
            created_at=datetime.now()
        )
        
        # Session management
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = 3600  # 1 hour

        # Demo users (would normally be stored securely)
        hashed_admin = self.pwd_context.hash("adminpass")
        self.users_db: Dict[str, Dict[str, Any]] = {
            "admin": {
                "username": "admin",
                "full_name": "Admin User",
                "email": "admin@example.com",
                "hashed_password": hashed_admin,
                "disabled": False,
            }
        }
        
        logger.info(f"Authentication manager initialized (enabled: {enable_auth})")
    
    def get_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
        """
        Get current authenticated user
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User object
            
        Raises:
            HTTPException: If authentication fails
        """
        if isinstance(credentials, str):
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        if not self.enable_auth:
            return None

        if not credentials:
            return None
        # First, attempt to treat credentials as JWT token
        token_user = self.verify_token(credentials.credentials)
        if token_user:
            self.default_user.last_login = datetime.now()
            return token_user

        # Fallback to API key validation
        if self._validate_api_key(credentials.credentials):
            self.default_user.last_login = datetime.now()
            return self.default_user

        return None
    
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

    def validate_api_key(self, api_key: Optional[str]) -> bool:
        """Public wrapper to validate provided API key values."""
        if not self.enable_auth:
            return True
        if not api_key:
            return False
        return self._validate_api_key(api_key)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except ValueError:
            logger.warning("Password verification failed due to invalid hash")
            return False

    def get_password_hash(self, password: str) -> str:
        """Generate a password hash using the configured context."""
        return self.pwd_context.hash(password)

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user record from the in-memory database."""
        return self.users_db.get(username)

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password credentials."""
        user = self.get_user(username)
        if not user:
            return None
        if user.get("disabled"):
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a signed JWT access token."""
        to_encode = data.copy()
        expires_delta = expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        now_utc = datetime.utcnow()
        expire_utc = now_utc + expires_delta
        offset_seconds = int(round((datetime.utcnow() - datetime.now()).total_seconds()))
        exp_epoch = calendar.timegm(expire_utc.timetuple()) + offset_seconds
        to_encode.update({"exp": exp_epoch})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return the associated user if valid."""
        if not token:
            return None
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
        except JWTError as exc:
            logger.warning("Failed to decode JWT: %s", exc)
            return None

        exp_value = payload.get("exp")
        if exp_value:
            exp_dt: Optional[datetime] = None
            if isinstance(exp_value, datetime):
                exp_dt = exp_value
            elif isinstance(exp_value, (int, float)):
                offset_seconds = int(round((datetime.utcnow() - datetime.now()).total_seconds()))
                exp_dt = datetime.utcfromtimestamp(exp_value - offset_seconds)
            elif isinstance(exp_value, str) and exp_value.isdigit():
                offset_seconds = int(round((datetime.utcnow() - datetime.now()).total_seconds()))
                exp_dt = datetime.utcfromtimestamp(int(exp_value) - offset_seconds)
            if exp_dt and datetime.utcnow() > exp_dt:
                return None

        username: Optional[str] = payload.get("sub")
        if not username:
            return None
        return self.get_user(username)
    
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
    
    def validate_session(self, session_token: str) -> Optional[User]:
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
    
    def get_session_statistics(self) -> Dict[str, Any]:
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
    
    def configure_auth(self, api_key: Optional[str], enable_auth: bool):
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
