"""
Integration tests for the automation generation endpoint.

Endpoint: POST /api/v1/synergies/{synergy_id}/generate-automation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.config import settings
from src.database import get_db
from src.main import app
import httpx


@pytest.mark.integration
class TestGenerateAutomationEndpoint:
    """Integration tests for POST /api/v1/synergies/{synergy_id}/generate-automation."""

    @pytest.fixture
    async def api_client(self, test_db: AsyncSession):
        # Override DB dependency
        def override_get_db():
            return test_db
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                yield ac
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_automation_success(
        self,
        api_client: httpx.AsyncClient,
        test_db: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test successful automation generation from synergy."""
        # Arrange: insert a synergy row
        synergy_id = "syn-int-001"
        await test_db.execute(
            text(
                """
                INSERT INTO synergy_opportunities (
                    synergy_id, synergy_type, device_ids, opportunity_metadata,
                    impact_score, complexity, confidence, area, context_breakdown
                ) VALUES (
                    :sid, :stype, :devices, :meta,
                    :impact, :complexity, :confidence, :area, :ctx
                )
                """
            ),
            {
                "sid": synergy_id,
                "stype": "device_pair",
                "devices": "binary_sensor.motion_office,light.office_lamp",
                "meta": '{"trigger_entity":"binary_sensor.motion_office","action_entity":"light.office_lamp"}',
                "impact": 0.7,
                "complexity": "low",
                "confidence": 0.8,
                "area": "office",
                "ctx": '{"energy": {"saver": true}}',
            },
        )
        await test_db.commit()

        # Mock HA configuration
        monkeypatch.setattr(settings, "ha_url", "http://localhost:8123", raising=False)
        monkeypatch.setattr(settings, "ha_token", "test_token", raising=False)

        # Mock external dependencies: YAMLTransformer, BlueprintPatternLibrary, and httpx client
        # Note: httpx is imported inside the function, so we patch it at the httpx module level
        with patch("src.services.automation_generator.YAMLTransformer") as MockTransformer, \
             patch("src.services.automation_generator.BlueprintPatternLibrary") as MockBlueprint, \
             patch("httpx.AsyncClient") as MockClient:
            
            # Mock YAMLTransformer
            mock_transformer = MagicMock()
            mock_transformer.transform_to_yaml = AsyncMock(
                return_value=(
                    "alias: Test Automation\n"
                    "trigger:\n"
                    "  - platform: state\n"
                    "    entity_id: binary_sensor.motion_office\n"
                    "action:\n"
                    "  - service: light.turn_on\n"
                    "    entity_id: light.office_lamp\n"
                )
            )
            MockTransformer.return_value = mock_transformer
            
            # Mock BlueprintPatternLibrary
            mock_blueprint = MagicMock()
            mock_blueprint.find_matching_blueprint.return_value = None
            MockBlueprint.return_value = mock_blueprint
            
            # Mock httpx.AsyncClient for HA API calls
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"entity_id": f"automation.synergy_{synergy_id}"}
            mock_response.raise_for_status.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            
            # Mock GET endpoints used by validator (must be async)
            async def mock_get(url, *args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status.return_value = None
                # Services list
                if "/api/services" in url:
                    resp.json.return_value = {
                        "light": {"turn_on": {}, "turn_off": {}},
                        "automation": {"create": {}},
                        "binary_sensor": {},
                    }
                    return resp
                # Entity state check
                if "/api/states/" in url:
                    entity_id = url.split("/api/states/")[-1]
                    resp.json.return_value = {"entity_id": entity_id, "state": "on"}
                    return resp
                # Default
                resp.json.return_value = {}
                return resp
            mock_client_instance.get = AsyncMock(side_effect=mock_get)
            
            # Async context manager setup
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            resp = await api_client.post(f"/api/v1/synergies/{synergy_id}/generate-automation")

        # Assert
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}, body: {resp.text}"
        body = resp.json()
        assert body.get("success") is True
        assert "data" in body
        assert body["data"].get("automation_id") == f"automation.synergy_{synergy_id}"
        assert body["message"].startswith("Automation ")

    @pytest.mark.asyncio
    async def test_generate_automation_missing_synergy_404(
        self,
        api_client: httpx.AsyncClient,
        test_db: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Arrange: ensure HA config is present
        monkeypatch.setattr(settings, "ha_url", "http://localhost:8123", raising=False)
        monkeypatch.setattr(settings, "ha_token", "test_token", raising=False)

        # Act
        resp = await api_client.post("/api/v1/synergies/does-not-exist/generate-automation")

        # Assert
        assert resp.status_code == 404
        assert "not found" in resp.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_generate_automation_missing_ha_config_400(
        self,
        api_client: httpx.AsyncClient,
        test_db: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Arrange: insert a synergy row
        synergy_id = "syn-int-002"
        await test_db.execute(
            text(
                """
                INSERT INTO synergy_opportunities (
                    synergy_id, synergy_type, device_ids, opportunity_metadata,
                    impact_score, complexity, confidence, area
                ) VALUES (
                    :sid, :stype, :devices, :meta,
                    :impact, :complexity, :confidence, :area
                )
                """
            ),
            {
                "sid": synergy_id,
                "stype": "device_pair",
                "devices": "binary_sensor.motion_living,light.living_room",
                "meta": '{"trigger_entity":"binary_sensor.motion_living","action_entity":"light.living_room"}',
                "impact": 0.6,
                "complexity": "low",
                "confidence": 0.75,
                "area": "living_room",
            },
        )
        await test_db.commit()

        # Ensure HA config is missing
        monkeypatch.setattr(settings, "ha_url", None, raising=False)
        monkeypatch.setattr(settings, "ha_token", None, raising=False)

        # Act
        resp = await api_client.post(f"/api/v1/synergies/{synergy_id}/generate-automation")

        # Assert
        assert resp.status_code in (400, 503)
        assert "home assistant" in resp.json().get("detail", "").lower()

