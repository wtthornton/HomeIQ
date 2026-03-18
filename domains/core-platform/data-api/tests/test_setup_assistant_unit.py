"""Unit tests for SetupAssistantService — Story 85.3

Tests setup guide generation and issue detection fallback paths.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.setup_assistant import (
    SetupAssistantService,
    get_setup_assistant,
)


class TestGenerateSetupGuide:
    """Test generate_setup_guide — especially the fallback path."""

    def setup_method(self):
        self.svc = SetupAssistantService()

    def test_fallback_returns_generic_guide(self):
        """When SetupGuideGenerator import fails, returns fallback guide."""
        # The default sys.path won't have the generator, so fallback triggers
        result = self.svc.generate_setup_guide(
            device_id="d1",
            device_name="Kitchen Light",
            device_type="light",
            integration="hue",
        )
        assert result["device_id"] == "d1"
        assert result["device_name"] == "Kitchen Light"
        assert len(result["steps"]) >= 1
        assert result["estimated_time_minutes"] == 10

    def test_fallback_step_contains_device_name(self):
        result = self.svc.generate_setup_guide(
            "d1", "My Device", "sensor", "zwave"
        )
        assert "My Device" in result["steps"][0]["description"]

    def test_with_setup_url_passed_through(self):
        """setup_instructions_url is passed to generator (or ignored in fallback)."""
        result = self.svc.generate_setup_guide(
            "d1", "Light", "light", "hue",
            setup_instructions_url="https://example.com"
        )
        assert result["device_id"] == "d1"


class TestDetectSetupIssues:

    def setup_method(self):
        self.svc = SetupAssistantService()

    @pytest.mark.asyncio
    async def test_no_ha_config_returns_empty(self):
        self.svc.ha_url = None
        self.svc.ha_token = None
        result = await self.svc.detect_setup_issues("d1", "Light", ["light.kitchen"])
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_detects_no_entities(self):
        """When IssueDetector import fails and entity list is empty, detect issue."""
        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        result = await self.svc.detect_setup_issues("d1", "Light", [])
        assert len(result) == 1
        assert result[0]["type"] == "no_entities"
        assert result[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_fallback_no_issues_when_entities_exist(self):
        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        result = await self.svc.detect_setup_issues("d1", "Light", ["light.kitchen"])
        assert result == []


class TestSingleton:

    def test_returns_same_instance(self):
        import src.services.setup_assistant as mod
        mod._setup_assistant = None
        assert get_setup_assistant() is get_setup_assistant()
