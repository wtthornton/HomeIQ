"""
Tests for the hardened shared AuthManager implementation.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.auth import AuthManager


@pytest.fixture
def auth_manager():
    manager = AuthManager(api_key="test-api-key")
    manager.register_user(
        username="admin",
        password="strongpass",
        full_name="Admin User",
        email="admin@example.com",
    )
    return manager


def test_register_and_get_user(auth_manager):
    user = auth_manager.get_user("admin")
    assert user is not None
    assert user["full_name"] == "Admin User"
    assert auth_manager.get_user("missing") is None


def test_authenticate_user(auth_manager):
    assert auth_manager.authenticate_user("admin", "strongpass") is not None
    assert auth_manager.authenticate_user("admin", "wrong") is None
    assert auth_manager.authenticate_user("missing", "strongpass") is None


def test_password_hashing(auth_manager):
    hashed = auth_manager.get_password_hash("hello-world")
    assert hashed != "hello-world"
    assert auth_manager.verify_password("hello-world", hashed) is True
    assert auth_manager.verify_password("other", hashed) is False


def test_create_and_verify_token(auth_manager):
    token = auth_manager.create_access_token({"sub": "admin"})
    decoded = auth_manager.verify_token(token)
    assert decoded is not None
    assert decoded["username"] == "admin"


def test_expired_token(auth_manager):
    token = auth_manager.create_access_token({"sub": "admin"}, timedelta(minutes=-1))
    assert auth_manager.verify_token(token) is None


def test_validate_api_key(auth_manager):
    assert auth_manager.validate_api_key("test-api-key") is True
    assert auth_manager.validate_api_key("wrong") is False
    assert auth_manager.validate_api_key(None) is False


@pytest.mark.asyncio
async def test_get_current_user_with_api_key(auth_manager):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-api-key")
    user = await auth_manager.get_current_user(credentials)
    assert user.username == "api-key"


@pytest.mark.asyncio
async def test_get_current_user_with_jwt(auth_manager):
    token = auth_manager.create_access_token({"sub": "admin"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await auth_manager.get_current_user(credentials)
    assert user["username"] == "admin"


@pytest.mark.asyncio
async def test_get_current_user_invalid(auth_manager):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
    with pytest.raises(HTTPException):
        await auth_manager.get_current_user(credentials)


def test_create_access_token_custom_expiry(auth_manager):
    token = auth_manager.create_access_token({"sub": "admin"}, timedelta(minutes=60))
    payload = auth_manager.verify_token(token)
    assert payload is not None
    # decoded payload includes datetime last_login; ensure structure
    assert payload["username"] == "admin"
