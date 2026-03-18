"""Unit tests for auth.py — Story 85.10

Tests AuthManager: API key validation, session management, and configuration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.auth import AuthManager, User


class TestUser:

    def test_user_defaults(self):
        u = User(username="admin", created_at=datetime.now())
        assert u.username == "admin"
        assert u.permissions == []
        assert u.last_login is None

    def test_user_with_permissions(self):
        u = User(
            username="admin",
            permissions=["read", "write"],
            created_at=datetime.now(),
        )
        assert "read" in u.permissions


class TestAuthManagerInit:

    def test_init_defaults(self):
        mgr = AuthManager(api_key="test-key")
        assert mgr.api_key == "test-key"
        assert mgr.enable_auth is True
        assert mgr.sessions == {}

    def test_init_auth_disabled(self):
        mgr = AuthManager(api_key=None, enable_auth=False)
        assert mgr.enable_auth is False

    def test_default_user(self):
        mgr = AuthManager(api_key="key")
        assert mgr.default_user.username == "admin"
        assert "admin" in mgr.default_user.permissions


class TestValidateApiKey:

    def test_valid_key(self):
        mgr = AuthManager(api_key="secret-key-123")
        assert mgr._validate_api_key("secret-key-123") is True

    def test_invalid_key(self):
        mgr = AuthManager(api_key="secret-key-123")
        assert mgr._validate_api_key("wrong-key") is False

    def test_no_api_key_configured(self):
        mgr = AuthManager(api_key=None)
        assert mgr._validate_api_key("any-key") is False


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_auth_disabled_returns_default_user(self):
        mgr = AuthManager(api_key="key", enable_auth=False)
        user = await mgr.get_current_user(None)
        assert user.username == "admin"

    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self):
        from fastapi import HTTPException
        mgr = AuthManager(api_key="key", enable_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            await mgr.get_current_user(None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self):
        from fastapi import HTTPException
        mgr = AuthManager(api_key="correct-key", enable_auth=True)
        creds = MagicMock()
        creds.credentials = "wrong-key"
        with pytest.raises(HTTPException) as exc_info:
            await mgr.get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_key_returns_user(self):
        mgr = AuthManager(api_key="correct-key", enable_auth=True)
        creds = MagicMock()
        creds.credentials = "correct-key"
        user = await mgr.get_current_user(creds)
        assert user.username == "admin"
        assert user.last_login is not None


class TestGenerateApiKey:

    def test_generates_unique_keys(self):
        mgr = AuthManager(api_key="key")
        k1 = mgr.generate_api_key()
        k2 = mgr.generate_api_key()
        assert k1 != k2
        assert len(k1) > 20


class TestSessionManagement:

    def test_create_session(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        token = mgr.create_session(user)
        assert token in mgr.sessions
        assert mgr.sessions[token]["user"] == user

    def test_validate_valid_session(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        token = mgr.create_session(user)
        result = mgr.validate_session(token)
        assert result == user

    def test_validate_invalid_session(self):
        mgr = AuthManager(api_key="key")
        assert mgr.validate_session("nonexistent") is None

    def test_validate_expired_session(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        token = mgr.create_session(user)
        # Force expiration
        mgr.sessions[token]["expires_at"] = datetime.now() - timedelta(seconds=1)
        assert mgr.validate_session(token) is None
        assert token not in mgr.sessions

    def test_revoke_session(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        token = mgr.create_session(user)
        mgr.revoke_session(token)
        assert token not in mgr.sessions

    def test_revoke_nonexistent_session(self):
        mgr = AuthManager(api_key="key")
        mgr.revoke_session("nonexistent")  # Should not raise

    def test_cleanup_expired_sessions(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        t1 = mgr.create_session(user)
        t2 = mgr.create_session(user)
        # Expire t1
        mgr.sessions[t1]["expires_at"] = datetime.now() - timedelta(seconds=1)
        mgr.cleanup_expired_sessions()
        assert t1 not in mgr.sessions
        assert t2 in mgr.sessions


class TestSessionStatistics:

    def test_empty_stats(self):
        mgr = AuthManager(api_key="key")
        stats = mgr.get_session_statistics()
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["authentication_enabled"] is True

    def test_stats_with_sessions(self):
        mgr = AuthManager(api_key="key")
        user = User(username="test", created_at=datetime.now())
        t1 = mgr.create_session(user)
        t2 = mgr.create_session(user)
        # Expire t2
        mgr.sessions[t2]["expires_at"] = datetime.now() - timedelta(seconds=1)
        stats = mgr.get_session_statistics()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["expired_sessions"] == 1


class TestConfigure:

    def test_configure_auth(self):
        mgr = AuthManager(api_key="old", enable_auth=True)
        mgr.configure_auth("new", False)
        assert mgr.api_key == "new"
        assert mgr.enable_auth is False

    def test_configure_session_timeout(self):
        mgr = AuthManager(api_key="key")
        mgr.configure_session_timeout(7200)
        assert mgr.session_timeout == 7200

    def test_configure_session_timeout_invalid(self):
        mgr = AuthManager(api_key="key")
        with pytest.raises(ValueError, match="positive"):
            mgr.configure_session_timeout(0)
