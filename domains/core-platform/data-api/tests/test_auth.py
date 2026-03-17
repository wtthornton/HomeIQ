"""
Tests for AuthManager in src/auth.py

Covers all 17 scenarios:
1.  AuthManager initialization (enabled/disabled)
2.  get_current_user — auth disabled returns default user
3.  get_current_user — missing credentials raises 401
4.  get_current_user — invalid API key raises 401
5.  get_current_user — valid API key returns user and updates last_login
6.  _validate_api_key — timing-safe comparison via secrets.compare_digest
7.  _validate_api_key — no API key configured returns False
8.  generate_api_key — returns URL-safe token of correct length
9.  create_session — returns token and stores session
10. validate_session — valid session returns user
11. validate_session — expired session returns None and cleans up
12. validate_session — unknown token returns None
13. revoke_session — removes session
14. cleanup_expired_sessions — removes only expired sessions
15. get_session_statistics — returns correct counts
16. configure_auth — updates settings
17. configure_session_timeout — positive value works, zero/negative raises ValueError
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.auth import AuthManager, User

# ---------------------------------------------------------------------------
# Override the autouse fresh_db fixture from conftest.py.
# AuthManager has no database dependency — we provide a no-op replacement so
# these unit tests run without a live PostgreSQL connection.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():  # noqa: F811  (intentional override of conftest fixture)
    """No-op override: auth tests have no database dependency."""
    yield

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_KEY = "test-api-key-12345"


def _make_manager(api_key: str | None = _TEST_KEY, enable_auth: bool = True) -> AuthManager:
    """Return a fresh AuthManager for each test."""
    return AuthManager(api_key=api_key, enable_auth=enable_auth)


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _make_user(username: str = "testuser") -> User:
    return User(
        username=username,
        permissions=["read"],
        created_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# 1. Initialization
# ---------------------------------------------------------------------------


class TestAuthManagerInit:
    """AuthManager initialization behaviour."""

    @pytest.mark.unit
    def test_init_with_auth_enabled(self):
        mgr = AuthManager(api_key=_TEST_KEY, enable_auth=True)
        assert mgr.api_key == _TEST_KEY
        assert mgr.enable_auth is True

    @pytest.mark.unit
    def test_init_with_auth_disabled(self):
        mgr = AuthManager(api_key=None, enable_auth=False)
        assert mgr.api_key is None
        assert mgr.enable_auth is False

    @pytest.mark.unit
    def test_init_default_user_has_admin_permissions(self):
        mgr = _make_manager()
        assert "admin" in mgr.default_user.permissions
        assert mgr.default_user.username == "admin"

    @pytest.mark.unit
    def test_init_sessions_empty(self):
        mgr = _make_manager()
        assert mgr.sessions == {}

    @pytest.mark.unit
    def test_init_default_session_timeout(self):
        mgr = _make_manager()
        assert mgr.session_timeout == 3600


# ---------------------------------------------------------------------------
# 2. get_current_user — auth disabled
# ---------------------------------------------------------------------------


class TestGetCurrentUserAuthDisabled:
    """When auth is disabled, get_current_user always returns the default user."""

    @pytest.mark.unit
    async def test_returns_default_user_when_disabled(self):
        mgr = _make_manager(enable_auth=False)
        user = await mgr.get_current_user(credentials=None)
        assert user.username == "admin"

    @pytest.mark.unit
    async def test_ignores_credentials_when_disabled(self):
        mgr = _make_manager(enable_auth=False)
        creds = _make_credentials("any-token-at-all")
        user = await mgr.get_current_user(credentials=creds)
        assert user.username == "admin"


# ---------------------------------------------------------------------------
# 3. get_current_user — missing credentials
# ---------------------------------------------------------------------------


class TestGetCurrentUserMissingCredentials:
    @pytest.mark.unit
    async def test_raises_401_when_no_credentials(self):
        mgr = _make_manager(enable_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            await mgr.get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 4. get_current_user — invalid API key
# ---------------------------------------------------------------------------


class TestGetCurrentUserInvalidApiKey:
    @pytest.mark.unit
    async def test_raises_401_on_wrong_key(self):
        mgr = _make_manager(api_key=_TEST_KEY, enable_auth=True)
        creds = _make_credentials("wrong-key")
        with pytest.raises(HTTPException) as exc_info:
            await mgr.get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.unit
    async def test_raises_401_when_no_api_key_configured(self):
        mgr = _make_manager(api_key=None, enable_auth=True)
        creds = _make_credentials("any-key")
        with pytest.raises(HTTPException) as exc_info:
            await mgr.get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 5. get_current_user — valid API key
# ---------------------------------------------------------------------------


class TestGetCurrentUserValidApiKey:
    @pytest.mark.unit
    async def test_returns_user_on_valid_key(self):
        mgr = _make_manager(api_key=_TEST_KEY, enable_auth=True)
        creds = _make_credentials(_TEST_KEY)
        user = await mgr.get_current_user(credentials=creds)
        assert user.username == "admin"

    @pytest.mark.unit
    async def test_updates_last_login_on_valid_key(self):
        mgr = _make_manager(api_key=_TEST_KEY, enable_auth=True)
        assert mgr.default_user.last_login is None
        creds = _make_credentials(_TEST_KEY)
        before = datetime.now()
        await mgr.get_current_user(credentials=creds)
        after = datetime.now()
        assert mgr.default_user.last_login is not None
        assert before <= mgr.default_user.last_login <= after


# ---------------------------------------------------------------------------
# 6. _validate_api_key — timing-safe comparison
# ---------------------------------------------------------------------------


class TestValidateApiKeyTimingSafe:
    @pytest.mark.unit
    def test_uses_secrets_compare_digest(self):
        """_validate_api_key must delegate to secrets.compare_digest."""
        mgr = _make_manager(api_key=_TEST_KEY)
        with patch("src.auth.secrets.compare_digest", wraps=secrets.compare_digest) as spy:
            mgr._validate_api_key(_TEST_KEY)
            spy.assert_called_once_with(_TEST_KEY, _TEST_KEY)

    @pytest.mark.unit
    def test_valid_key_returns_true(self):
        mgr = _make_manager(api_key=_TEST_KEY)
        assert mgr._validate_api_key(_TEST_KEY) is True

    @pytest.mark.unit
    def test_invalid_key_returns_false(self):
        mgr = _make_manager(api_key=_TEST_KEY)
        assert mgr._validate_api_key("not-the-right-key") is False


# ---------------------------------------------------------------------------
# 7. _validate_api_key — no key configured
# ---------------------------------------------------------------------------


class TestValidateApiKeyNoKeyConfigured:
    @pytest.mark.unit
    def test_returns_false_when_no_key(self):
        mgr = _make_manager(api_key=None)
        assert mgr._validate_api_key("anything") is False

    @pytest.mark.unit
    def test_returns_false_for_empty_string_key(self):
        mgr = _make_manager(api_key="")
        # Empty string is falsy, same branch as None
        assert mgr._validate_api_key("anything") is False


# ---------------------------------------------------------------------------
# 8. generate_api_key
# ---------------------------------------------------------------------------


class TestGenerateApiKey:
    @pytest.mark.unit
    def test_returns_string(self):
        mgr = _make_manager()
        key = mgr.generate_api_key()
        assert isinstance(key, str)

    @pytest.mark.unit
    def test_correct_minimum_length(self):
        """token_urlsafe(32) produces at least 43 URL-safe base64 chars."""
        mgr = _make_manager()
        key = mgr.generate_api_key()
        assert len(key) >= 43

    @pytest.mark.unit
    def test_url_safe_characters_only(self):
        """URL-safe base64 uses A-Z a-z 0-9 - _."""
        mgr = _make_manager()
        key = mgr.generate_api_key()
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        assert all(c in allowed for c in key)

    @pytest.mark.unit
    def test_keys_are_unique(self):
        mgr = _make_manager()
        keys = {mgr.generate_api_key() for _ in range(20)}
        assert len(keys) == 20


# ---------------------------------------------------------------------------
# 9. create_session
# ---------------------------------------------------------------------------


class TestCreateSession:
    @pytest.mark.unit
    def test_returns_string_token(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.unit
    def test_token_stored_in_sessions(self):
        mgr = _make_manager()
        user = _make_user()
        token = mgr.create_session(user)
        assert token in mgr.sessions

    @pytest.mark.unit
    def test_session_contains_user(self):
        mgr = _make_manager()
        user = _make_user("alice")
        token = mgr.create_session(user)
        assert mgr.sessions[token]["user"].username == "alice"

    @pytest.mark.unit
    def test_session_has_expiry(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        session = mgr.sessions[token]
        assert "expires_at" in session
        assert isinstance(session["expires_at"], datetime)

    @pytest.mark.unit
    def test_session_expiry_matches_timeout(self):
        mgr = _make_manager()
        mgr.session_timeout = 120
        before = datetime.now()
        token = mgr.create_session(_make_user())
        after = datetime.now()
        expires_at = mgr.sessions[token]["expires_at"]
        assert before + timedelta(seconds=120) <= expires_at <= after + timedelta(seconds=120)

    @pytest.mark.unit
    def test_multiple_sessions_are_independent(self):
        mgr = _make_manager()
        t1 = mgr.create_session(_make_user("user1"))
        t2 = mgr.create_session(_make_user("user2"))
        assert t1 != t2
        assert len(mgr.sessions) == 2


# ---------------------------------------------------------------------------
# 10. validate_session — valid
# ---------------------------------------------------------------------------


class TestValidateSessionValid:
    @pytest.mark.unit
    def test_returns_user_for_valid_token(self):
        mgr = _make_manager()
        user = _make_user("bob")
        token = mgr.create_session(user)
        result = mgr.validate_session(token)
        assert result is not None
        assert result.username == "bob"

    @pytest.mark.unit
    def test_session_not_removed_after_valid_read(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        mgr.validate_session(token)
        assert token in mgr.sessions


# ---------------------------------------------------------------------------
# 11. validate_session — expired
# ---------------------------------------------------------------------------


class TestValidateSessionExpired:
    @pytest.mark.unit
    def test_expired_session_returns_none(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        # Wind the clock back so the session appears expired
        mgr.sessions[token]["expires_at"] = datetime.now() - timedelta(seconds=1)
        result = mgr.validate_session(token)
        assert result is None

    @pytest.mark.unit
    def test_expired_session_is_cleaned_up(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        mgr.sessions[token]["expires_at"] = datetime.now() - timedelta(seconds=1)
        mgr.validate_session(token)
        assert token not in mgr.sessions


# ---------------------------------------------------------------------------
# 12. validate_session — unknown token
# ---------------------------------------------------------------------------


class TestValidateSessionUnknown:
    @pytest.mark.unit
    def test_unknown_token_returns_none(self):
        mgr = _make_manager()
        assert mgr.validate_session("completely-unknown-token") is None

    @pytest.mark.unit
    def test_empty_sessions_returns_none(self):
        mgr = _make_manager()
        assert mgr.validate_session("x") is None


# ---------------------------------------------------------------------------
# 13. revoke_session
# ---------------------------------------------------------------------------


class TestRevokeSession:
    @pytest.mark.unit
    def test_revoke_removes_session(self):
        mgr = _make_manager()
        token = mgr.create_session(_make_user())
        assert token in mgr.sessions
        mgr.revoke_session(token)
        assert token not in mgr.sessions

    @pytest.mark.unit
    def test_revoke_nonexistent_token_is_safe(self):
        """Revoking an unknown token must not raise."""
        mgr = _make_manager()
        mgr.revoke_session("ghost-token")  # should not raise

    @pytest.mark.unit
    def test_revoke_only_removes_target_session(self):
        mgr = _make_manager()
        t1 = mgr.create_session(_make_user("u1"))
        t2 = mgr.create_session(_make_user("u2"))
        mgr.revoke_session(t1)
        assert t1 not in mgr.sessions
        assert t2 in mgr.sessions


# ---------------------------------------------------------------------------
# 14. cleanup_expired_sessions
# ---------------------------------------------------------------------------


class TestCleanupExpiredSessions:
    @pytest.mark.unit
    def test_removes_only_expired_sessions(self):
        mgr = _make_manager()
        live_token = mgr.create_session(_make_user("live"))
        dead_token = mgr.create_session(_make_user("dead"))

        # Expire the dead session
        mgr.sessions[dead_token]["expires_at"] = datetime.now() - timedelta(seconds=10)

        mgr.cleanup_expired_sessions()

        assert live_token in mgr.sessions
        assert dead_token not in mgr.sessions

    @pytest.mark.unit
    def test_cleanup_with_no_sessions_is_safe(self):
        mgr = _make_manager()
        mgr.cleanup_expired_sessions()  # should not raise

    @pytest.mark.unit
    def test_cleanup_removes_all_expired(self):
        mgr = _make_manager()
        tokens = [mgr.create_session(_make_user(f"u{i}")) for i in range(5)]
        # Expire all of them
        for t in tokens:
            mgr.sessions[t]["expires_at"] = datetime.now() - timedelta(seconds=1)

        mgr.cleanup_expired_sessions()
        assert len(mgr.sessions) == 0

    @pytest.mark.unit
    def test_cleanup_keeps_active_when_all_alive(self):
        mgr = _make_manager()
        for i in range(3):
            mgr.create_session(_make_user(f"u{i}"))

        mgr.cleanup_expired_sessions()
        assert len(mgr.sessions) == 3


# ---------------------------------------------------------------------------
# 15. get_session_statistics
# ---------------------------------------------------------------------------


class TestGetSessionStatistics:
    @pytest.mark.unit
    def test_empty_stats(self):
        mgr = _make_manager()
        stats = mgr.get_session_statistics()
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["expired_sessions"] == 0

    @pytest.mark.unit
    def test_counts_active_and_expired(self):
        mgr = _make_manager()
        live = mgr.create_session(_make_user("live"))
        dead = mgr.create_session(_make_user("dead"))
        mgr.sessions[dead]["expires_at"] = datetime.now() - timedelta(seconds=5)

        stats = mgr.get_session_statistics()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["expired_sessions"] == 1

    @pytest.mark.unit
    def test_includes_session_timeout(self):
        mgr = _make_manager()
        mgr.session_timeout = 900
        stats = mgr.get_session_statistics()
        assert stats["session_timeout"] == 900

    @pytest.mark.unit
    def test_includes_auth_enabled_flag(self):
        mgr = _make_manager(enable_auth=False)
        stats = mgr.get_session_statistics()
        assert stats["authentication_enabled"] is False

        mgr2 = _make_manager(enable_auth=True)
        assert mgr2.get_session_statistics()["authentication_enabled"] is True

    @pytest.mark.unit
    def test_live_token_not_counted_as_expired(self):
        # Regression guard: a token expiring exactly now may be borderline
        mgr = _make_manager()
        mgr.create_session(_make_user())
        stats = mgr.get_session_statistics()
        assert stats["expired_sessions"] == 0


# ---------------------------------------------------------------------------
# 16. configure_auth
# ---------------------------------------------------------------------------


class TestConfigureAuth:
    @pytest.mark.unit
    def test_updates_api_key(self):
        mgr = _make_manager(api_key=_TEST_KEY)
        mgr.configure_auth(api_key="new-key", enable_auth=True)
        assert mgr.api_key == "new-key"

    @pytest.mark.unit
    def test_updates_enable_auth_flag(self):
        mgr = _make_manager(enable_auth=True)
        mgr.configure_auth(api_key=_TEST_KEY, enable_auth=False)
        assert mgr.enable_auth is False

    @pytest.mark.unit
    def test_can_set_api_key_to_none(self):
        mgr = _make_manager(api_key=_TEST_KEY)
        mgr.configure_auth(api_key=None, enable_auth=True)
        assert mgr.api_key is None

    @pytest.mark.unit
    async def test_new_key_takes_effect_immediately(self):
        """After configure_auth, the new key should authenticate successfully."""
        mgr = _make_manager(api_key=_TEST_KEY)
        new_key = "brand-new-key"
        mgr.configure_auth(api_key=new_key, enable_auth=True)
        creds = _make_credentials(new_key)
        user = await mgr.get_current_user(credentials=creds)
        assert user.username == "admin"


# ---------------------------------------------------------------------------
# 17. configure_session_timeout
# ---------------------------------------------------------------------------


class TestConfigureSessionTimeout:
    @pytest.mark.unit
    def test_positive_value_is_accepted(self):
        mgr = _make_manager()
        mgr.configure_session_timeout(7200)
        assert mgr.session_timeout == 7200

    @pytest.mark.unit
    def test_value_of_one_is_accepted(self):
        mgr = _make_manager()
        mgr.configure_session_timeout(1)
        assert mgr.session_timeout == 1

    @pytest.mark.unit
    def test_zero_raises_value_error(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="positive"):
            mgr.configure_session_timeout(0)

    @pytest.mark.unit
    def test_negative_raises_value_error(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="positive"):
            mgr.configure_session_timeout(-1)

    @pytest.mark.unit
    def test_large_negative_raises_value_error(self):
        mgr = _make_manager()
        with pytest.raises(ValueError):
            mgr.configure_session_timeout(-99999)

    @pytest.mark.unit
    def test_new_timeout_applies_to_subsequent_sessions(self):
        """Sessions created after configure_session_timeout use the new value."""
        mgr = _make_manager()
        mgr.configure_session_timeout(120)
        before = datetime.now()
        token = mgr.create_session(_make_user())
        after = datetime.now()
        expires_at = mgr.sessions[token]["expires_at"]
        assert before + timedelta(seconds=120) <= expires_at <= after + timedelta(seconds=121)
