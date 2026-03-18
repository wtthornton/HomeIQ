"""Unit tests for api_key_service.py — Story 85.10

Tests APIKeyService pure logic: masking, format validation, status checks.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api_key_service import APIKeyInfo, APIKeyService, APIKeyStatus


class TestAPIKeyStatus:

    def test_enum_values(self):
        assert APIKeyStatus.CONFIGURED.value == "configured"
        assert APIKeyStatus.INVALID.value == "invalid"
        assert APIKeyStatus.REQUIRED.value == "required"
        assert APIKeyStatus.DISABLED.value == "disabled"
        assert APIKeyStatus.TESTING.value == "testing"


class TestAPIKeyInfo:

    def test_defaults(self):
        info = APIKeyInfo(
            service="weather",
            key_name="WEATHER_API_KEY",
            status=APIKeyStatus.CONFIGURED,
            masked_key="abc1...xyz9",
            is_required=True,
            description="Weather API",
        )
        assert info.validation_url is None

    def test_with_validation_url(self):
        info = APIKeyInfo(
            service="weather",
            key_name="WEATHER_API_KEY",
            status=APIKeyStatus.CONFIGURED,
            masked_key="abc1...xyz9",
            is_required=True,
            description="Weather API",
            validation_url="https://api.example.com",
        )
        assert info.validation_url == "https://api.example.com"


class TestMaskApiKey:

    def setup_method(self):
        self.svc = APIKeyService()

    def test_none_key(self):
        assert self.svc._mask_api_key(None) == "Not configured"

    def test_empty_key(self):
        assert self.svc._mask_api_key("") == "Not configured"

    def test_short_key(self):
        assert self.svc._mask_api_key("abc") == "***"

    def test_exactly_4_chars(self):
        assert self.svc._mask_api_key("abcd") == "****"

    def test_normal_key(self):
        result = self.svc._mask_api_key("abcdefghijklmnop")
        assert result.startswith("abcd")
        assert result.endswith("mnop")
        assert "..." in result


class TestValidateKeyFormat:

    def setup_method(self):
        self.svc = APIKeyService()

    def test_empty_key(self):
        assert self.svc._validate_key_format("weather", "") is False

    def test_whitespace_only(self):
        assert self.svc._validate_key_format("weather", "   ") is False

    def test_weather_key_too_short(self):
        assert self.svc._validate_key_format("weather", "short") is False

    def test_weather_key_valid(self):
        assert self.svc._validate_key_format("weather", "a" * 32) is True

    def test_carbon_intensity_key_valid(self):
        assert self.svc._validate_key_format("carbon-intensity", "a" * 10) is True

    def test_carbon_intensity_key_too_short(self):
        assert self.svc._validate_key_format("carbon-intensity", "ab") is False

    def test_air_quality_key_valid(self):
        assert self.svc._validate_key_format("air-quality", "12345") is True

    def test_generic_service_valid(self):
        assert self.svc._validate_key_format("calendar", "12345") is True

    def test_generic_service_too_short(self):
        assert self.svc._validate_key_format("calendar", "abc") is False


class TestGetApiKeyStatus:

    def setup_method(self):
        self.svc = APIKeyService()

    def test_unknown_service(self):
        assert self.svc.get_api_key_status("unknown") == APIKeyStatus.DISABLED

    def test_required_service_not_configured(self, monkeypatch):
        monkeypatch.delenv("WEATHER_API_KEY", raising=False)
        assert self.svc.get_api_key_status("weather") == APIKeyStatus.REQUIRED

    def test_optional_service_not_configured(self, monkeypatch):
        monkeypatch.delenv("PRICING_API_KEY", raising=False)
        assert self.svc.get_api_key_status("electricity-pricing") == APIKeyStatus.DISABLED

    def test_service_configured(self, monkeypatch):
        monkeypatch.setenv("WEATHER_API_KEY", "test-key-12345")
        assert self.svc.get_api_key_status("weather") == APIKeyStatus.CONFIGURED


class TestAPIKeyServiceInit:

    def test_has_config(self):
        svc = APIKeyService()
        assert "weather" in svc.api_key_config
        assert "carbon-intensity" in svc.api_key_config
        assert "air-quality" in svc.api_key_config
        assert len(svc.api_key_config) >= 6

    def test_weather_config(self):
        svc = APIKeyService()
        cfg = svc.api_key_config["weather"]
        assert cfg["env_var"] == "WEATHER_API_KEY"
        assert cfg["required"] is True
        assert cfg["validation_url"] is not None


class TestTestApiKey:

    @pytest.mark.asyncio
    async def test_unknown_service(self):
        svc = APIKeyService()
        ok, msg = await svc.test_api_key("unknown_svc", "key")
        assert ok is False
        assert "Unknown" in msg

    @pytest.mark.asyncio
    async def test_no_validation_url(self):
        svc = APIKeyService()
        ok, msg = await svc.test_api_key("electricity-pricing", "key")
        assert ok is True
        assert "No validation" in msg

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        svc = APIKeyService()
        svc._test_api_key = AsyncMock(side_effect=Exception("network error"))
        ok, msg = await svc.test_api_key("weather", "key")
        assert ok is False


class TestUpdateApiKey:

    @pytest.mark.asyncio
    async def test_unknown_service(self):
        svc = APIKeyService()
        ok, msg = await svc.update_api_key("unknown_svc", "key")
        assert ok is False

    @pytest.mark.asyncio
    async def test_invalid_format(self):
        svc = APIKeyService()
        ok, msg = await svc.update_api_key("weather", "")
        assert ok is False
        assert "format" in msg.lower()
