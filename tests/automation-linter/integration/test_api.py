"""
Integration tests for FastAPI endpoints.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services" / "automation-linter" / "src"))

from main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "engine_version" in data
        assert "ruleset_version" in data


class TestRulesEndpoint:
    """Test rules listing endpoint."""

    def test_list_rules(self, client):
        """Test listing all rules."""
        response = client.get("/rules")
        assert response.status_code == 200
        data = response.json()
        assert "ruleset_version" in data
        assert "rules" in data
        assert len(data["rules"]) >= 15


class TestLintEndpoint:
    """Test lint endpoint."""

    def test_lint_valid_automation(self, client):
        """Test linting valid automation."""
        request_data = {
            "yaml": """
alias: "Test"
id: "test_001"
description: "Test automation"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        }
        response = client.post("/lint", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["automations_detected"] == 1
        assert "findings" in data
        assert "summary" in data

    def test_lint_invalid_automation(self, client):
        """Test linting invalid automation."""
        request_data = {
            "yaml": """
alias: "Test"
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        }
        response = client.post("/lint", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["errors_count"] > 0
        assert any(f["rule_id"] == "SCHEMA001" for f in data["findings"])

    def test_lint_oversized_request(self, client):
        """Test request size limit."""
        large_yaml = "a" * 1_000_000  # 1MB
        request_data = {"yaml": large_yaml}
        response = client.post("/lint", json=request_data)
        assert response.status_code == 413


class TestFixEndpoint:
    """Test fix endpoint."""

    def test_fix_automation(self, client):
        """Test auto-fix functionality."""
        request_data = {
            "yaml": """
alias: "Test"
id: "test_001"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
""",
            "fix_mode": "safe"
        }
        response = client.post("/fix", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "fixed_yaml" in data or data["applied_fixes"] == []
        assert "findings" in data

    def test_fix_mode_none(self, client):
        """Test fix with mode=none."""
        request_data = {
            "yaml": """
alias: "Test"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
""",
            "fix_mode": "none"
        }
        response = client.post("/fix", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["fixed_yaml"] is None
        assert len(data["applied_fixes"]) == 0
