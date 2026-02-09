"""
Tests for Home Assistant API client.

Phase 4.1: HA client post-deploy verification (verification_warning when state is unavailable).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.clients.ha_client import HomeAssistantClient


def _mock_response(json_data: dict, status_code: int = 200):
    """Create a mock httpx response."""
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    response.status_code = status_code
    return response


@pytest.mark.unit
class TestHAClientPostDeployVerification:
    """Tests for post-deploy state verification and verification_warning."""

    @pytest.mark.asyncio
    async def test_deploy_automation_sets_verification_warning_when_state_unavailable(self):
        """Phase 4.1: deploy_automation sets verification_warning when get_state returns unavailable."""
        client = HomeAssistantClient(
            ha_url="http://localhost:8123",
            access_token="test-token",
        )

        # Mock httpx client: post (deploy) succeeds, get (state) returns unavailable
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(
            return_value=_mock_response({"id": "automation.test_123"})
        )
        mock_http.get = AsyncMock(
            return_value=_mock_response({
                "state": "unavailable",
                "attributes": {"last_triggered": None},
            })
        )
        client.client = mock_http

        result = await client.deploy_automation("""
id: automation.test_123
alias: Test
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.office
""")

        assert result["status"] == "deployed"
        assert result["automation_id"] == "automation.test_123"
        assert result["state"] == "unavailable"
        assert "verification_warning" in result
        assert "unavailable" in result["verification_warning"]

    @pytest.mark.asyncio
    async def test_deploy_automation_includes_last_triggered_when_available(self):
        """Phase 4.1: deploy_automation includes last_triggered in attributes when state is on."""
        client = HomeAssistantClient(
            ha_url="http://localhost:8123",
            access_token="test-token",
        )

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(
            return_value=_mock_response({"id": "automation.test_456"})
        )
        mock_http.get = AsyncMock(
            return_value=_mock_response({
                "state": "on",
                "attributes": {"last_triggered": "2026-02-09T12:00:00.000Z"},
            })
        )
        client.client = mock_http

        result = await client.deploy_automation("""
id: automation.test_456
alias: Test 2
trigger:
  - platform: time
    at: "08:00:00"
action:
  - service: light.turn_off
    target:
      entity_id: light.office
""")

        assert result["status"] == "deployed"
        assert result["state"] == "on"
        assert result["attributes"]["last_triggered"] == "2026-02-09T12:00:00.000Z"
        assert "verification_warning" not in result
