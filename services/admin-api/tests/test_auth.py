"""
Tests for authentication module
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import os

from src.auth import AuthManager


class TestAuthManager:
    """Test AuthManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.auth_manager = AuthManager(
            api_key="test-api-key",
            enable_auth=True
        )
    
    def test_init(self):
        """Test AuthManager initialization"""
        assert self.auth_manager.api_key == "test-api-key"
        assert self.auth_manager.enable_auth is True
        assert self.auth_manager.secret_key is not None
        assert self.auth_manager.algorithm == "HS256"
        assert self.auth_manager.access_token_expire_minutes == 30
        assert self.auth_manager.pwd_context is not None
        assert "admin" in self.auth_manager.users_db
    
    def test_init_without_auth(self):
        """Test AuthManager initialization without auth"""
        auth_manager = AuthManager(
            api_key="test-api-key",
            enable_auth=False
        )
        
        assert auth_manager.enable_auth is False
    
    def test_verify_password(self):
        """Test password verification"""
        # Test correct password
        assert self.auth_manager.verify_password("adminpass", self.auth_manager.users_db["admin"]["hashed_password"]) is True
        
        # Test incorrect password
        assert self.auth_manager.verify_password("wrongpass", self.auth_manager.users_db["admin"]["hashed_password"]) is False
    
    def test_get_user(self):
        """Test getting user"""
        # Test existing user
        user = self.auth_manager.get_user("admin")
        assert user is not None
        assert user["username"] == "admin"
        assert user["full_name"] == "Admin User"
        assert user["email"] == "admin@example.com"
        assert user["disabled"] is False
        
        # Test non-existing user
        user = self.auth_manager.get_user("nonexistent")
        assert user is None
    
    def test_authenticate_user(self):
        """Test user authentication"""
        # Test correct credentials
        user = self.auth_manager.authenticate_user("admin", "adminpass")
        assert user is not None
        assert user["username"] == "admin"
        
        # Test incorrect username
        user = self.auth_manager.authenticate_user("wronguser", "adminpass")
        assert user is None
        
        # Test incorrect password
        user = self.auth_manager.authenticate_user("admin", "wrongpass")
        assert user is None
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "admin"}
        token = self.auth_manager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiry(self):
        """Test access token creation with custom expiry"""
        data = {"sub": "admin"}
        expires_delta = timedelta(minutes=60)
        token = self.auth_manager.create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self):
        """Test token verification"""
        # Create token
        data = {"sub": "admin"}
        token = self.auth_manager.create_access_token(data)
        
        # Verify token
        user = self.auth_manager.verify_token(token)
        assert user is not None
        assert user["username"] == "admin"
    
    def test_verify_invalid_token(self):
        """Test invalid token verification"""
        # Test invalid token
        user = self.auth_manager.verify_token("invalid-token")
        assert user is None
        
        # Test empty token
        user = self.auth_manager.verify_token("")
        assert user is None
        
        # Test None token
        user = self.auth_manager.verify_token(None)
        assert user is None
    
    def test_verify_expired_token(self):
        """Test expired token verification"""
        # Create expired token
        data = {"sub": "admin"}
        expired_delta = timedelta(minutes=-1)  # Negative delta for expired token
        token = self.auth_manager.create_access_token(data, expired_delta)
        
        # Verify expired token
        user = self.auth_manager.verify_token(token)
        assert user is None
    
    def test_verify_token_wrong_user(self):
        """Test token verification with wrong user"""
        # Create token for non-existing user
        data = {"sub": "nonexistent"}
        token = self.auth_manager.create_access_token(data)
        
        # Verify token
        user = self.auth_manager.verify_token(token)
        assert user is None
    
    def test_verify_token_no_subject(self):
        """Test token verification without subject"""
        # Create token without subject
        data = {"other": "value"}
        token = self.auth_manager.create_access_token(data)
        
        # Verify token
        user = self.auth_manager.verify_token(token)
        assert user is None
    
    def test_get_current_user(self):
        """Test get_current_user dependency"""
        # Create token
        data = {"sub": "admin"}
        token = self.auth_manager.create_access_token(data)
        
        # Mock FastAPI dependency
        from fastapi import Depends
        from fastapi.security import HTTPBearer
        
        # Test with valid token
        user = self.auth_manager.get_current_user(token)
        assert user is not None
        assert user["username"] == "admin"
    
    def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token"""
        # Test with invalid token
        user = self.auth_manager.get_current_user("invalid-token")
        assert user is None
    
    def test_get_current_user_none_token(self):
        """Test get_current_user with None token"""
        # Test with None token
        user = self.auth_manager.get_current_user(None)
        assert user is None
    
    def test_auth_disabled(self):
        """Test behavior when auth is disabled"""
        auth_manager = AuthManager(
            api_key="test-api-key",
            enable_auth=False
        )
        
        # Should return None for any token
        user = auth_manager.get_current_user("any-token")
        assert user is None
        
        # Should return None for None token
        user = auth_manager.get_current_user(None)
        assert user is None
    
    def test_api_key_validation(self):
        """Test API key validation"""
        # Test with correct API key
        assert self.auth_manager.validate_api_key("test-api-key") is True
        
        # Test with incorrect API key
        assert self.auth_manager.validate_api_key("wrong-key") is False
        
        # Test with None API key
        assert self.auth_manager.validate_api_key(None) is False
    
    def test_api_key_validation_disabled(self):
        """Test API key validation when auth is disabled"""
        auth_manager = AuthManager(
            api_key="test-api-key",
            enable_auth=False
        )
        
        # Should always return True when auth is disabled
        assert auth_manager.validate_api_key("any-key") is True
        assert auth_manager.validate_api_key("wrong-key") is True
        assert auth_manager.validate_api_key(None) is True
    
    def test_user_disabled(self):
        """Test authentication with disabled user"""
        # Create disabled user
        self.auth_manager.users_db["disabled_user"] = {
            "username": "disabled_user",
            "hashed_password": self.auth_manager.pwd_context.hash("password"),
            "full_name": "Disabled User",
            "email": "disabled@example.com",
            "disabled": True
        }
        
        # Test authentication with disabled user
        user = self.auth_manager.authenticate_user("disabled_user", "password")
        assert user is None
    
    def test_token_expiry(self):
        """Test token expiry calculation"""
        # Test default expiry
        data = {"sub": "admin"}
        token = self.auth_manager.create_access_token(data)
        
        # Decode token to check expiry
        import jwt
        payload = jwt.decode(token, self.auth_manager.secret_key, algorithms=[self.auth_manager.algorithm])
        
        # Check that expiry is approximately 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + timedelta(minutes=30)
        
        # Allow 1 minute tolerance
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 60
    
    def test_token_expiry_custom(self):
        """Test custom token expiry"""
        # Test custom expiry
        data = {"sub": "admin"}
        expires_delta = timedelta(minutes=60)
        token = self.auth_manager.create_access_token(data, expires_delta)
        
        # Decode token to check expiry
        import jwt
        payload = jwt.decode(token, self.auth_manager.secret_key, algorithms=[self.auth_manager.algorithm])
        
        # Check that expiry is approximately 60 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + timedelta(minutes=60)
        
        # Allow 1 minute tolerance
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 60
    
    def test_password_hashing(self):
        """Test password hashing"""
        # Test that passwords are hashed
        password = "testpassword"
        hashed = self.auth_manager.pwd_context.hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        
        # Test that hashed password can be verified
        assert self.auth_manager.pwd_context.verify(password, hashed) is True
        assert self.auth_manager.pwd_context.verify("wrongpassword", hashed) is False
    
    def test_multiple_users(self):
        """Test multiple users"""
        # Add another user
        self.auth_manager.users_db["user2"] = {
            "username": "user2",
            "hashed_password": self.auth_manager.pwd_context.hash("password2"),
            "full_name": "User 2",
            "email": "user2@example.com",
            "disabled": False
        }
        
        # Test authentication for both users
        user1 = self.auth_manager.authenticate_user("admin", "adminpass")
        user2 = self.auth_manager.authenticate_user("user2", "password2")
        
        assert user1 is not None
        assert user2 is not None
        assert user1["username"] == "admin"
        assert user2["username"] == "user2"
        
        # Test cross-authentication (should fail)
        user1_wrong = self.auth_manager.authenticate_user("admin", "password2")
        user2_wrong = self.auth_manager.authenticate_user("user2", "adminpass")
        
        assert user1_wrong is None
        assert user2_wrong is None
