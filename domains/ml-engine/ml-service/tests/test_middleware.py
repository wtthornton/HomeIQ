"""Tests for ML Service middleware module."""

from __future__ import annotations

from src.middleware import _check_rate_limit, _parse_allowed_origins, _rate_limit_store


def test_parse_allowed_origins_default() -> None:
    result = _parse_allowed_origins(None)
    assert "http://localhost:3000" in result


def test_parse_allowed_origins_custom() -> None:
    result = _parse_allowed_origins("http://example.com, http://other.com")
    assert result == ["http://example.com", "http://other.com"]


def test_check_rate_limit_allows() -> None:
    _rate_limit_store.clear()
    assert _check_rate_limit("test-ip") is True
