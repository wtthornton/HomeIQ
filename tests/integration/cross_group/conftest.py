"""Shared fixtures for cross-group integration tests."""

import os

import pytest


@pytest.fixture
def data_api_url():
    return os.environ.get("DATA_API_URL", "http://localhost:8006")


@pytest.fixture
def admin_api_url():
    return os.environ.get("ADMIN_API_URL", "http://localhost:8004")


@pytest.fixture
def postgres_url():
    return os.environ.get(
        "POSTGRES_URL",
        "postgresql+asyncpg://homeiq:homeiq_test@localhost:5432/homeiq_test",
    )
