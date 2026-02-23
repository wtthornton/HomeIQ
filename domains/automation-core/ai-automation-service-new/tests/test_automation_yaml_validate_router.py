"""
Phase 4.1: Tests for unified automation YAML validation endpoint

Epic: HomeIQ Automation Platform Improvements
Tests POST /api/v1/automations/validate - valid YAML, invalid YAML, response shape.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

VALID_YAML = """id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""

INVALID_YAML = """alias: Broken
trigger: []
action: []
# Missing required id, invalid structure
"""


@pytest.fixture
def mock_yaml_validation_client():
    """Mock YAML validation client that returns predictable results."""
    client = AsyncMock()
    return client


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedValidateEndpoint:
    """Tests for POST /api/v1/automations/validate."""

    async def test_validate_valid_yaml_returns_200(
        self, client: AsyncClient, auth_headers: dict, mock_yaml_validation_client
    ):
        """Valid YAML returns 200 with valid=True."""
        mock_yaml_validation_client.validate_yaml = AsyncMock(
            return_value={
                "valid": True,
                "errors": [],
                "warnings": [],
                "score": 95.0,
                "fixed_yaml": None,
                "fixes_applied": [],
            }
        )

        from src.api.dependencies import get_yaml_validation_client
        from src.main import app

        app.dependency_overrides[get_yaml_validation_client] = lambda: mock_yaml_validation_client

        try:
            response = await client.post(
                "/api/v1/automations/validate",
                json={
                    "yaml_content": VALID_YAML,
                    "normalize": True,
                    "validate_entities": False,
                    "validate_services": False,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["errors"] == []
            assert data["score"] == 95.0
        finally:
            app.dependency_overrides.pop(get_yaml_validation_client, None)

    async def test_validate_invalid_yaml_returns_errors(
        self, client: AsyncClient, auth_headers: dict, mock_yaml_validation_client
    ):
        """Invalid YAML returns valid=False with errors."""
        mock_yaml_validation_client.validate_yaml = AsyncMock(
            return_value={
                "valid": False,
                "errors": ["Missing required field: id or alias"],
                "warnings": [],
                "score": 0.0,
                "fixed_yaml": None,
                "fixes_applied": [],
            }
        )

        from src.api.dependencies import get_yaml_validation_client
        from src.main import app

        app.dependency_overrides[get_yaml_validation_client] = lambda: mock_yaml_validation_client

        try:
            response = await client.post(
                "/api/v1/automations/validate",
                json={
                    "yaml_content": INVALID_YAML,
                    "normalize": True,
                    "validate_entities": False,
                    "validate_services": False,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert len(data["errors"]) > 0
            assert "entity_validation" in data
            assert "service_validation" in data
        finally:
            app.dependency_overrides.pop(get_yaml_validation_client, None)

    async def test_validate_response_includes_entity_and_service_validation(
        self, client: AsyncClient, auth_headers: dict, mock_yaml_validation_client
    ):
        """Response includes entity_validation and service_validation subsections."""
        mock_yaml_validation_client.validate_yaml = AsyncMock(
            return_value={
                "valid": True,
                "errors": [],
                "warnings": [],
                "score": 90.0,
                "fixed_yaml": None,
                "fixes_applied": [],
            }
        )

        from src.api.dependencies import get_yaml_validation_client
        from src.main import app

        app.dependency_overrides[get_yaml_validation_client] = lambda: mock_yaml_validation_client

        try:
            response = await client.post(
                "/api/v1/automations/validate",
                json={
                    "yaml_content": VALID_YAML,
                    "normalize": True,
                    "validate_entities": True,
                    "validate_services": True,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "entity_validation" in data
            assert "performed" in data["entity_validation"]
            assert "passed" in data["entity_validation"]
            assert "errors" in data["entity_validation"]
            assert "service_validation" in data
            assert "performed" in data["service_validation"]
            assert "passed" in data["service_validation"]
        finally:
            app.dependency_overrides.pop(get_yaml_validation_client, None)
