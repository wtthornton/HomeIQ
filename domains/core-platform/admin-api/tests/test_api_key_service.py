"""Tests for API key management service."""

import os
from dataclasses import fields
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api_key_service import APIKeyInfo, APIKeyService, APIKeyStatus


# ---------------------------------------------------------------------------
# APIKeyStatus enum
# ---------------------------------------------------------------------------

class TestAPIKeyStatus:
    """Tests for APIKeyStatus enum values."""

    def test_configured_value(self):
        """CONFIGURED enum member has expected string value."""
        assert APIKeyStatus.CONFIGURED.value == "configured"

    def test_invalid_value(self):
        """INVALID enum member has expected string value."""
        assert APIKeyStatus.INVALID.value == "invalid"

    def test_required_value(self):
        """REQUIRED enum member has expected string value."""
        assert APIKeyStatus.REQUIRED.value == "required"

    def test_disabled_value(self):
        """DISABLED enum member has expected string value."""
        assert APIKeyStatus.DISABLED.value == "disabled"

    def test_testing_value(self):
        """TESTING enum member has expected string value."""
        assert APIKeyStatus.TESTING.value == "testing"

    def test_all_five_members_present(self):
        """Enum exposes exactly the expected five members."""
        names = {m.name for m in APIKeyStatus}
        assert names == {"CONFIGURED", "INVALID", "REQUIRED", "DISABLED", "TESTING"}


# ---------------------------------------------------------------------------
# APIKeyInfo dataclass
# ---------------------------------------------------------------------------

class TestAPIKeyInfo:
    """Tests for APIKeyInfo dataclass structure."""

    def test_required_fields_exist(self):
        """Dataclass exposes all mandatory fields."""
        field_names = {f.name for f in fields(APIKeyInfo)}
        assert {"service", "key_name", "status", "masked_key", "is_required", "description"}.issubset(field_names)

    def test_validation_url_optional(self):
        """validation_url field has a default of None."""
        info = APIKeyInfo(
            service="weather",
            key_name="WEATHER_API_KEY",
            status=APIKeyStatus.CONFIGURED,
            masked_key="abcd...wxyz",
            is_required=True,
            description="OpenWeatherMap API Key",
        )
        assert info.validation_url is None

    def test_full_construction(self):
        """All fields are stored correctly when explicitly supplied."""
        info = APIKeyInfo(
            service="weather",
            key_name="WEATHER_API_KEY",
            status=APIKeyStatus.CONFIGURED,
            masked_key="abcd...wxyz",
            is_required=True,
            description="OpenWeatherMap API Key",
            validation_url="https://example.com/validate",
        )
        assert info.service == "weather"
        assert info.key_name == "WEATHER_API_KEY"
        assert info.status == APIKeyStatus.CONFIGURED
        assert info.masked_key == "abcd...wxyz"
        assert info.is_required is True
        assert info.description == "OpenWeatherMap API Key"
        assert info.validation_url == "https://example.com/validate"


# ---------------------------------------------------------------------------
# APIKeyService initialisation
# ---------------------------------------------------------------------------

class TestAPIKeyServiceInit:
    """Tests for APIKeyService.__init__ defaults."""

    def test_config_file_default(self):
        """config_file defaults to /app/infrastructure/.env.production."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADMIN_API_ALLOW_SECRET_WRITES", None)
            svc = APIKeyService()
        assert svc.config_file == "/app/infrastructure/.env.production"

    def test_config_dir_default(self):
        """config_dir defaults to /app/infrastructure."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADMIN_API_ALLOW_SECRET_WRITES", None)
            svc = APIKeyService()
        assert svc.config_dir == "/app/infrastructure"

    def test_allow_secret_writes_false_by_default(self):
        """allow_secret_writes is False when env var is absent."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADMIN_API_ALLOW_SECRET_WRITES", None)
            svc = APIKeyService()
        assert svc.allow_secret_writes is False

    def test_allow_secret_writes_true_when_env_set(self):
        """allow_secret_writes is True when ADMIN_API_ALLOW_SECRET_WRITES=true."""
        with patch.dict(os.environ, {"ADMIN_API_ALLOW_SECRET_WRITES": "true"}):
            svc = APIKeyService()
        assert svc.allow_secret_writes is True

    def test_allow_secret_writes_case_insensitive(self):
        """allow_secret_writes handles upper-case TRUE."""
        with patch.dict(os.environ, {"ADMIN_API_ALLOW_SECRET_WRITES": "TRUE"}):
            svc = APIKeyService()
        assert svc.allow_secret_writes is True

    def test_api_key_config_contains_expected_services(self):
        """api_key_config is pre-populated with the six known services."""
        svc = APIKeyService()
        expected = {"weather", "carbon-intensity", "electricity-pricing", "air-quality", "calendar", "smart-meter"}
        assert set(svc.api_key_config.keys()) == expected


# ---------------------------------------------------------------------------
# get_api_keys
# ---------------------------------------------------------------------------

class TestGetApiKeys:
    """Tests for APIKeyService.get_api_keys."""

    async def test_returns_list_of_api_key_info(self):
        """Returns one APIKeyInfo per configured service."""
        svc = APIKeyService()
        # Patch all env-var lookups to return None (no keys set)
        with patch("src.api_key_service.os.getenv", return_value=None):
            result = await svc.get_api_keys()
        assert isinstance(result, list)
        assert len(result) == len(svc.api_key_config)
        assert all(isinstance(item, APIKeyInfo) for item in result)

    async def test_required_service_no_key_returns_required_status(self):
        """Required services with no key set show REQUIRED status."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            result = await svc.get_api_keys()
        required_services = {s for s, cfg in svc.api_key_config.items() if cfg["required"]}
        result_map = {info.service: info for info in result}
        for service in required_services:
            assert result_map[service].status == APIKeyStatus.REQUIRED, (
                f"{service} should be REQUIRED but got {result_map[service].status}"
            )

    async def test_optional_service_no_key_returns_disabled_status(self):
        """Optional services with no key set show DISABLED status."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            result = await svc.get_api_keys()
        optional_services = {s for s, cfg in svc.api_key_config.items() if not cfg["required"]}
        result_map = {info.service: info for info in result}
        for service in optional_services:
            assert result_map[service].status == APIKeyStatus.DISABLED, (
                f"{service} should be DISABLED but got {result_map[service].status}"
            )

    async def test_key_set_with_no_validation_url_returns_configured(self):
        """A key that is set for a service with no validation_url → CONFIGURED."""
        svc = APIKeyService()
        # 'smart-meter' has no validation_url
        def fake_getenv(key, *args):
            if key == "METER_API_TOKEN":
                return "sometoken123"
            return None

        with patch("src.api_key_service.os.getenv", side_effect=fake_getenv):
            result = await svc.get_api_keys()

        result_map = {info.service: info for info in result}
        assert result_map["smart-meter"].status == APIKeyStatus.CONFIGURED

    async def test_key_set_with_validation_url_valid_returns_configured(self):
        """A key that passes _test_api_key → CONFIGURED."""
        svc = APIKeyService()

        def fake_getenv(key, *args):
            if key == "WEATHER_API_KEY":
                return "a" * 32
            return None

        with patch("src.api_key_service.os.getenv", side_effect=fake_getenv):
            with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=True)):
                result = await svc.get_api_keys()

        result_map = {info.service: info for info in result}
        assert result_map["weather"].status == APIKeyStatus.CONFIGURED

    async def test_key_set_with_validation_url_invalid_returns_invalid(self):
        """A key that fails _test_api_key → INVALID."""
        svc = APIKeyService()

        def fake_getenv(key, *args):
            if key == "WEATHER_API_KEY":
                return "a" * 32
            return None

        with patch("src.api_key_service.os.getenv", side_effect=fake_getenv):
            with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=False)):
                result = await svc.get_api_keys()

        result_map = {info.service: info for info in result}
        assert result_map["weather"].status == APIKeyStatus.INVALID

    async def test_masked_key_present_when_key_set(self):
        """masked_key field is populated (not 'Not configured') when a key exists."""
        svc = APIKeyService()

        def fake_getenv(key, *args):
            if key == "METER_API_TOKEN":
                return "mytesttoken99"
            return None

        with patch("src.api_key_service.os.getenv", side_effect=fake_getenv):
            result = await svc.get_api_keys()

        result_map = {info.service: info for info in result}
        assert result_map["smart-meter"].masked_key != "Not configured"

    async def test_masked_key_not_configured_when_key_absent(self):
        """masked_key is 'Not configured' when no key is set."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            result = await svc.get_api_keys()
        for info in result:
            assert info.masked_key == "Not configured"


# ---------------------------------------------------------------------------
# update_api_key
# ---------------------------------------------------------------------------

class TestUpdateApiKey:
    """Tests for APIKeyService.update_api_key."""

    async def test_unknown_service_returns_false(self):
        """Unknown service name returns (False, message)."""
        svc = APIKeyService()
        success, msg = await svc.update_api_key("nonexistent-service", "somekey")
        assert success is False
        assert "nonexistent-service" in msg

    async def test_invalid_key_format_returns_false(self):
        """Key that fails format validation returns (False, message)."""
        svc = APIKeyService()
        # Weather keys must be >= 20 chars; pass a short one
        success, msg = await svc.update_api_key("weather", "short")
        assert success is False
        assert "weather" in msg

    async def test_valid_key_no_validation_url_returns_true(self):
        """Valid key for service with no validation URL returns (True, message)."""
        svc = APIKeyService()
        with patch.object(svc, "_update_config_file", new=AsyncMock()):
            success, msg = await svc.update_api_key("smart-meter", "validtoken12345")
        assert success is True
        assert "smart-meter" in msg

    async def test_valid_key_validation_passes_returns_true(self):
        """Valid key that passes _test_api_key returns (True, message)."""
        svc = APIKeyService()
        good_key = "a" * 32
        with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=True)):
            with patch.object(svc, "_update_config_file", new=AsyncMock()):
                success, msg = await svc.update_api_key("weather", good_key)
        assert success is True

    async def test_valid_key_validation_fails_returns_false(self):
        """Valid key that fails _test_api_key returns (False, message)."""
        svc = APIKeyService()
        good_key = "a" * 32
        with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=False)):
            success, msg = await svc.update_api_key("weather", good_key)
        assert success is False
        assert "validation failed" in msg.lower()

    async def test_exception_returns_false_with_error_message(self):
        """Unexpected exception inside update_api_key returns (False, error detail)."""
        svc = APIKeyService()
        with patch.object(svc, "_update_config_file", new=AsyncMock(side_effect=RuntimeError("disk full"))):
            success, msg = await svc.update_api_key("smart-meter", "validtoken12345")
        assert success is False
        assert "disk full" in msg


# ---------------------------------------------------------------------------
# test_api_key (public)
# ---------------------------------------------------------------------------

class TestTestApiKey:
    """Tests for APIKeyService.test_api_key."""

    async def test_unknown_service_returns_false(self):
        """Unknown service name returns (False, message)."""
        svc = APIKeyService()
        success, msg = await svc.test_api_key("no-such-service", "somekey")
        assert success is False
        assert "no-such-service" in msg

    async def test_no_validation_url_returns_true(self):
        """Service with no validation_url returns (True, message) without network call."""
        svc = APIKeyService()
        # 'calendar' has validation_url=None
        success, msg = await svc.test_api_key("calendar", "anykey12345")
        assert success is True
        assert "calendar" in msg

    async def test_validation_url_success_returns_true(self):
        """Valid key confirmed by _test_api_key returns (True, message)."""
        svc = APIKeyService()
        with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=True)):
            success, msg = await svc.test_api_key("weather", "a" * 32)
        assert success is True

    async def test_validation_url_failure_returns_false(self):
        """Key rejected by _test_api_key returns (False, message)."""
        svc = APIKeyService()
        with patch.object(svc, "_test_api_key", new=AsyncMock(return_value=False)):
            success, msg = await svc.test_api_key("weather", "a" * 32)
        assert success is False


# ---------------------------------------------------------------------------
# get_api_key_status
# ---------------------------------------------------------------------------

class TestGetApiKeyStatus:
    """Tests for APIKeyService.get_api_key_status."""

    def test_unknown_service_returns_disabled(self):
        """Unknown service returns DISABLED."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            status = svc.get_api_key_status("totally-unknown")
        assert status == APIKeyStatus.DISABLED

    def test_required_service_no_key_returns_required(self):
        """Required service with no key returns REQUIRED."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            status = svc.get_api_key_status("weather")
        assert status == APIKeyStatus.REQUIRED

    def test_optional_service_no_key_returns_disabled(self):
        """Optional service with no key returns DISABLED."""
        svc = APIKeyService()
        with patch("src.api_key_service.os.getenv", return_value=None):
            status = svc.get_api_key_status("smart-meter")
        assert status == APIKeyStatus.DISABLED

    def test_any_service_with_key_returns_configured(self):
        """Any service that has a key set returns CONFIGURED (sync check, no network)."""
        svc = APIKeyService()

        def fake_getenv(key, *args):
            return "somevalue" if key == "WEATHER_API_KEY" else None

        with patch("src.api_key_service.os.getenv", side_effect=fake_getenv):
            status = svc.get_api_key_status("weather")
        assert status == APIKeyStatus.CONFIGURED


# ---------------------------------------------------------------------------
# _validate_key_format
# ---------------------------------------------------------------------------

class TestValidateKeyFormat:
    """Tests for APIKeyService._validate_key_format."""

    def test_empty_string_returns_false(self):
        """Empty string is always invalid."""
        svc = APIKeyService()
        assert svc._validate_key_format("weather", "") is False

    def test_whitespace_only_returns_false(self):
        """Whitespace-only string is invalid."""
        svc = APIKeyService()
        assert svc._validate_key_format("weather", "   ") is False

    def test_weather_key_too_short_returns_false(self):
        """Weather key shorter than 20 chars returns False."""
        svc = APIKeyService()
        assert svc._validate_key_format("weather", "short") is False

    def test_weather_key_exactly_minimum_length_returns_true(self):
        """Weather key of exactly 20 chars returns True."""
        svc = APIKeyService()
        assert svc._validate_key_format("weather", "a" * 20) is True

    def test_weather_key_long_returns_true(self):
        """Weather key well above minimum returns True."""
        svc = APIKeyService()
        assert svc._validate_key_format("weather", "a" * 32) is True

    def test_carbon_intensity_minimum_length_returns_true(self):
        """Carbon-intensity key of 10 chars returns True."""
        svc = APIKeyService()
        assert svc._validate_key_format("carbon-intensity", "a" * 10) is True

    def test_carbon_intensity_too_short_returns_false(self):
        """Carbon-intensity key shorter than 10 chars returns False."""
        svc = APIKeyService()
        assert svc._validate_key_format("carbon-intensity", "short") is False

    def test_generic_service_minimum_length_returns_true(self):
        """Generic service key of 5 chars returns True."""
        svc = APIKeyService()
        assert svc._validate_key_format("smart-meter", "12345") is True

    def test_generic_service_too_short_returns_false(self):
        """Generic service key shorter than 5 chars returns False."""
        svc = APIKeyService()
        assert svc._validate_key_format("smart-meter", "abc") is False


# ---------------------------------------------------------------------------
# _mask_api_key
# ---------------------------------------------------------------------------

class TestMaskApiKey:
    """Tests for APIKeyService._mask_api_key."""

    def test_empty_string_returns_not_configured(self):
        """Empty string returns the literal 'Not configured'."""
        svc = APIKeyService()
        assert svc._mask_api_key("") == "Not configured"

    def test_none_returns_not_configured(self):
        """None returns 'Not configured'."""
        svc = APIKeyService()
        assert svc._mask_api_key(None) == "Not configured"

    def test_short_key_fully_masked(self):
        """Key of 4 or fewer chars is fully replaced with asterisks."""
        svc = APIKeyService()
        assert svc._mask_api_key("abc") == "***"
        assert svc._mask_api_key("abcd") == "****"

    def test_normal_key_shows_first_and_last_four(self):
        """Key longer than 4 chars shows first 4, '...', last 4."""
        svc = APIKeyService()
        key = "abcdefgh12345678"
        result = svc._mask_api_key(key)
        assert result.startswith("abcd")
        assert result.endswith("5678")
        assert "..." in result

    def test_mask_hides_middle(self):
        """Middle characters are not visible in the masked output."""
        svc = APIKeyService()
        key = "FIRST_hidden_middle_LAST"
        result = svc._mask_api_key(key)
        assert result == f"{key[:4]}...{key[-4:]}"
        # The middle section must not appear in the masked string
        assert "hidden_middle" not in result


# ---------------------------------------------------------------------------
# _update_config_file
# ---------------------------------------------------------------------------

class TestUpdateConfigFile:
    """Tests for APIKeyService._update_config_file."""

    async def test_raises_permission_error_when_writes_disabled(self):
        """PermissionError is raised when allow_secret_writes is False."""
        svc = APIKeyService()
        svc.allow_secret_writes = False
        with pytest.raises(PermissionError):
            await svc._update_config_file("WEATHER_API_KEY", "newvalue")

    async def test_writes_new_key_when_file_does_not_exist(self, tmp_path):
        """Creates the config file and writes the variable when absent."""
        svc = APIKeyService()
        svc.allow_secret_writes = True
        svc.config_dir = str(tmp_path)
        await svc._update_config_file("WEATHER_API_KEY", "newvalue123")
        env_file = tmp_path / ".env.production"
        assert env_file.exists()
        content = env_file.read_text()
        assert "WEATHER_API_KEY=newvalue123" in content

    async def test_updates_existing_key_in_file(self, tmp_path):
        """Overwrites an existing variable line in the config file."""
        svc = APIKeyService()
        svc.allow_secret_writes = True
        svc.config_dir = str(tmp_path)
        env_file = tmp_path / ".env.production"
        env_file.write_text("OTHER_KEY=foo\nWEATHER_API_KEY=oldvalue\nANOTHER=bar\n")
        await svc._update_config_file("WEATHER_API_KEY", "updatedvalue")
        content = env_file.read_text()
        assert "WEATHER_API_KEY=updatedvalue" in content
        assert "oldvalue" not in content
        # Other keys should be preserved
        assert "OTHER_KEY=foo" in content

    async def test_appends_new_key_to_existing_file(self, tmp_path):
        """Appends a new variable when it does not yet exist in the file."""
        svc = APIKeyService()
        svc.allow_secret_writes = True
        svc.config_dir = str(tmp_path)
        env_file = tmp_path / ".env.production"
        env_file.write_text("EXISTING_KEY=value\n")
        await svc._update_config_file("NEW_KEY", "brandnew")
        content = env_file.read_text()
        assert "NEW_KEY=brandnew" in content
        assert "EXISTING_KEY=value" in content


# ---------------------------------------------------------------------------
# _test_api_key (internal) — network mocked via aiohttp.ClientSession
# ---------------------------------------------------------------------------

class TestInternalTestApiKey:
    """Tests for APIKeyService._test_api_key with mocked network layer."""

    async def test_returns_true_for_service_with_no_validation_url(self):
        """Service without a validation_url is assumed valid without a network call."""
        svc = APIKeyService()
        # Temporarily clear the validation_url for smart-meter (already None)
        result = await svc._test_api_key("smart-meter", "sometoken")
        assert result is True

    async def test_returns_true_on_200_with_expected_key_in_response(self):
        """HTTP 200 response containing the expected check field returns True."""
        svc = APIKeyService()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"cod": 200})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.api_key_service.aiohttp.ClientSession", return_value=mock_session):
            result = await svc._test_api_key("weather", "a" * 32)

        assert result is True

    async def test_returns_false_on_401_response(self):
        """HTTP 401 response means the key is invalid — returns False."""
        svc = APIKeyService()

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.api_key_service.aiohttp.ClientSession", return_value=mock_session):
            result = await svc._test_api_key("weather", "badkey" * 5)

        assert result is False

    async def test_returns_false_on_network_exception(self):
        """Network exception during request returns False without raising."""
        svc = APIKeyService()
        with patch("src.api_key_service.aiohttp.ClientSession", side_effect=Exception("connection refused")):
            result = await svc._test_api_key("weather", "a" * 32)
        assert result is False

    async def test_returns_false_when_response_missing_expected_key(self):
        """200 response whose JSON lacks the validation_response_check field returns False."""
        svc = APIKeyService()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"unexpected_field": "value"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.api_key_service.aiohttp.ClientSession", return_value=mock_session):
            result = await svc._test_api_key("weather", "a" * 32)

        assert result is False
