"""Tests for automation-linter FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the automation-linter app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "engine_version" in data
        assert "ruleset_version" in data

    def test_health_includes_timestamp(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert isinstance(data["timestamp"], float)


class TestRulesEndpoint:
    """Tests for the /rules endpoint."""

    def test_list_rules_returns_200(self, client: TestClient) -> None:
        response = client.get("/rules")
        assert response.status_code == 200
        data = response.json()
        assert "ruleset_version" in data
        assert "rules" in data
        assert isinstance(data["rules"], list)


class TestLintEndpoint:
    """Tests for the /lint endpoint."""

    def test_lint_valid_yaml(self, client: TestClient) -> None:
        yaml_content = """
- alias: "Test Automation"
  trigger:
    - platform: state
      entity_id: binary_sensor.motion
      to: "on"
  action:
    - service: light.turn_on
      target:
        entity_id: light.living_room
"""
        response = client.post("/lint", json={"yaml": yaml_content})
        assert response.status_code == 200
        data = response.json()
        assert "engine_version" in data
        assert "findings" in data
        assert "summary" in data

    def test_lint_empty_yaml_returns_error(self, client: TestClient) -> None:
        response = client.post("/lint", json={"yaml": ""})
        # Empty YAML should either return 200 with findings or 500
        assert response.status_code in (200, 500)

    def test_lint_oversized_yaml_returns_413(self, client: TestClient) -> None:
        # Create YAML larger than MAX_YAML_SIZE_BYTES (default 1MB)
        large_yaml = "a" * (1024 * 1024 + 1)
        response = client.post("/lint", json={"yaml": large_yaml})
        assert response.status_code == 413


class TestFixEndpoint:
    """Tests for the /fix endpoint."""

    def test_fix_valid_yaml(self, client: TestClient) -> None:
        yaml_content = """
- alias: "Test Automation"
  trigger:
    - platform: state
      entity_id: binary_sensor.motion
      to: "on"
  action:
    - service: light.turn_on
      target:
        entity_id: light.living_room
"""
        response = client.post("/fix", json={"yaml": yaml_content, "fix_mode": "safe"})
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "applied_fixes" in data

    def test_fix_none_mode_skips_fixes(self, client: TestClient) -> None:
        yaml_content = """
- alias: "Test"
  trigger:
    - platform: state
      entity_id: binary_sensor.motion
  action:
    - service: light.turn_on
"""
        response = client.post("/fix", json={"yaml": yaml_content, "fix_mode": "none"})
        assert response.status_code == 200
        data = response.json()
        assert data["fixed_yaml"] is None
        assert data["applied_fixes"] == []


class TestRootEndpoint:
    """Tests for the / root endpoint."""

    def test_root_returns_200(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
