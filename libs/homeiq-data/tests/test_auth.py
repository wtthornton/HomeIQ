"""Signing-key contract for the shared :class:`AuthManager` (TAP-6580).

Two properties are pinned here, because losing either one is invisible at
runtime: tokens must survive crossing a process boundary, and a missing signing
key must stop startup by name instead of quietly minting a random one.
"""

from __future__ import annotations

import pytest
from homeiq_data.auth import (
    SIGNING_KEY_ENV,
    AuthManager,
    SigningKeyError,
    SigningKeyState,
)

_TEST_SIGNING_KEY = "unit-test-signing-key-not-a-real-secret"
_TEST_API_KEY = "unit-test-api-key"


@pytest.fixture
def configured_signing_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Supply the signing key the way compose supplies it in production."""
    monkeypatch.setenv(SIGNING_KEY_ENV, _TEST_SIGNING_KEY)
    return _TEST_SIGNING_KEY


def _manager_with_admin() -> AuthManager:
    """A manager holding one known user, built only from the environment."""
    manager = AuthManager(api_key=_TEST_API_KEY)
    manager.register_user(username="admin", password="strongpass")
    return manager


def test_val_004_two_managers_verify_each_others_tokens(configured_signing_key: str) -> None:
    """VAL-004: same configuration in, mutually verifiable tokens out.

    Each ``AuthManager`` stands in for a separate process. Before TAP-6580 both
    drew their own random key, so this cross-verification failed while every
    single-instance test still passed.
    """
    issuer = _manager_with_admin()
    verifier = _manager_with_admin()

    assert issuer is not verifier
    assert issuer.secret_key == configured_signing_key
    assert verifier.secret_key == configured_signing_key

    token = issuer.create_access_token({"sub": "admin"})
    decoded = verifier.verify_token(token)

    assert decoded is not None
    assert decoded["username"] == "admin"


def test_val_005_absent_signing_key_raises_named_startup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VAL-005: an unset signing key is a named failure, not a generated key."""
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)

    with pytest.raises(SigningKeyError) as excinfo:
        AuthManager(api_key=_TEST_API_KEY)

    assert excinfo.value.state is SigningKeyState.ABSENT
    assert SIGNING_KEY_ENV in str(excinfo.value)


def test_val_005_blank_signing_key_raises_named_startup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VAL-005: a present-but-empty key is its own named state, not a pass."""
    monkeypatch.setenv(SIGNING_KEY_ENV, "   ")

    with pytest.raises(SigningKeyError) as excinfo:
        AuthManager(api_key=_TEST_API_KEY)

    assert excinfo.value.state is SigningKeyState.BLANK


def test_tokens_signed_under_a_different_key_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cross-verification above is a real check, not a signature no-op."""
    monkeypatch.setenv(SIGNING_KEY_ENV, _TEST_SIGNING_KEY)
    issuer = _manager_with_admin()
    token = issuer.create_access_token({"sub": "admin"})

    monkeypatch.setenv(SIGNING_KEY_ENV, "a-different-signing-key-entirely")
    stranger = _manager_with_admin()

    assert stranger.verify_token(token) is None
