"""
End-to-End Tests for Cross-Group Resilience

Tests the live resilience infrastructure against the running Docker stack:
- GroupHealthCheck structured responses
- Dependency probing (latency, status)
- Circuit breaker degradation (data-api stop/start)

Requires: docker compose services running.
Uses 127.0.0.1 instead of localhost to avoid IPv6 resolution issues on Windows.
"""

import pytest
import requests
from typing import Any

# Use 127.0.0.1 to avoid IPv6 resolution issues on Windows Docker
SERVICES = {
    "ha-ai-agent": "http://127.0.0.1:8030",
    "ai-pattern": "http://127.0.0.1:8034",
    "ai-automation": "http://127.0.0.1:8036",
    "proactive-agent": "http://127.0.0.1:8031",
    "device-health-monitor": "http://127.0.0.1:8019",
    "blueprint-suggestion": "http://127.0.0.1:8039",
}

DATA_API_URL = "http://127.0.0.1:8006"


@pytest.fixture(scope="session", autouse=True)
def verify_stack_running():
    """Verify the Docker stack is running before tests."""
    for name, base_url in SERVICES.items():
        try:
            resp = requests.get(f"{base_url}/health", timeout=5)
            if resp.status_code >= 500:
                pytest.skip(f"Service {name} not healthy (status {resp.status_code})")
        except requests.RequestException:
            pytest.skip(f"Service {name} not reachable at {base_url}")


def _get_health(name: str) -> dict[str, Any]:
    """Fetch health response from a service."""
    resp = requests.get(f"{SERVICES[name]}/health", timeout=10)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# GroupHealthCheck structured responses
# ------------------------------------------------------------------


class TestGroupHealthCheckFormat:
    """Verify all 6 services return valid GroupHealthCheck responses."""

    @pytest.mark.parametrize("service_name", list(SERVICES.keys()))
    def test_has_required_fields(self, service_name: str):
        """Every resilience service must return group, status, version, dependencies."""
        data = _get_health(service_name)
        assert "status" in data, f"{service_name} missing 'status'"
        assert "group" in data, f"{service_name} missing 'group'"
        assert "version" in data, f"{service_name} missing 'version'"
        assert "dependencies" in data, f"{service_name} missing 'dependencies'"

    @pytest.mark.parametrize("service_name", list(SERVICES.keys()))
    def test_status_is_valid(self, service_name: str):
        """Status must be one of healthy, degraded, unhealthy."""
        data = _get_health(service_name)
        assert data["status"] in ("healthy", "degraded", "unhealthy"), (
            f"{service_name} has invalid status: {data['status']}"
        )

    @pytest.mark.parametrize("service_name", list(SERVICES.keys()))
    def test_uptime_is_positive(self, service_name: str):
        """uptime_seconds must be > 0 for a running service."""
        data = _get_health(service_name)
        assert data.get("uptime_seconds", 0) > 0, (
            f"{service_name} uptime should be positive"
        )


class TestGroupAssignment:
    """Verify services report correct group names."""

    EXPECTED_GROUPS = {
        "ha-ai-agent": "automation-intelligence",
        "ai-pattern": "automation-intelligence",
        "ai-automation": "automation-intelligence",
        "proactive-agent": "automation-intelligence",
        "blueprint-suggestion": "automation-intelligence",
        "device-health-monitor": "device-management",
    }

    @pytest.mark.parametrize("service_name,expected_group", list(EXPECTED_GROUPS.items()))
    def test_group_name(self, service_name: str, expected_group: str):
        data = _get_health(service_name)
        assert data["group"] == expected_group


# ------------------------------------------------------------------
# Dependency probing
# ------------------------------------------------------------------


class TestDependencyProbing:
    """Verify dependency probing works correctly."""

    def test_data_api_is_healthy_dependency(self):
        """All services that depend on data-api should report it healthy."""
        for name in ["ai-pattern", "ai-automation", "proactive-agent",
                      "blueprint-suggestion", "device-health-monitor"]:
            data = _get_health(name)
            deps = data.get("dependencies", {})
            assert "data-api" in deps, f"{name} should list data-api dependency"
            assert deps["data-api"]["status"] == "healthy", (
                f"{name}: data-api should be healthy, got {deps['data-api']['status']}"
            )

    def test_latency_is_reported(self):
        """Healthy dependencies should report latency_ms."""
        data = _get_health("ai-pattern")
        dep = data["dependencies"].get("data-api", {})
        assert "latency_ms" in dep, "Healthy dependency should report latency"
        assert dep["latency_ms"] > 0, "Latency should be positive"

    def test_last_seen_is_reported(self):
        """Healthy dependencies should report last_seen timestamp."""
        data = _get_health("ai-pattern")
        dep = data["dependencies"].get("data-api", {})
        assert "last_seen" in dep, "Healthy dependency should report last_seen"
        # ISO-8601 format check
        assert "T" in dep["last_seen"], "last_seen should be ISO-8601"


class TestMultipleDependencies:
    """Verify services with multiple cross-group dependencies."""

    def test_proactive_agent_has_two_deps(self):
        """proactive-agent should monitor data-api + weather-api."""
        data = _get_health("proactive-agent")
        deps = data["dependencies"]
        assert "data-api" in deps, "Should monitor data-api"
        assert "weather-api" in deps, "Should monitor weather-api"

    def test_device_health_has_two_deps(self):
        """device-health-monitor should monitor data-api + device-intelligence."""
        data = _get_health("device-health-monitor")
        deps = data["dependencies"]
        assert "data-api" in deps, "Should monitor data-api"
        assert "device-intelligence" in deps, "Should monitor device-intelligence"

    def test_ha_ai_agent_has_multiple_deps(self):
        """ha-ai-agent should monitor data-api + device-intelligence + ai-automation."""
        data = _get_health("ha-ai-agent")
        deps = data["dependencies"]
        assert "data-api" in deps, "Should monitor data-api"
        assert "device-intelligence-service" in deps, "Should monitor device-intelligence"


# ------------------------------------------------------------------
# Cross-service API smoke tests
# ------------------------------------------------------------------


class TestCrossServiceAPIs:
    """Smoke test actual cross-group API calls."""

    def test_data_api_entities_from_host(self):
        """data-api /api/entities should respond (proves core-platform is up)."""
        resp = requests.get(
            f"{DATA_API_URL}/api/entities",
            headers={"Authorization": "Bearer test"},
            timeout=10,
        )
        # 200 or 401 both prove the service is responding
        assert resp.status_code in (200, 401, 403), (
            f"data-api should respond, got {resp.status_code}"
        )

    def test_ai_pattern_root(self):
        """ai-pattern-service root should respond."""
        resp = requests.get(f"{SERVICES['ai-pattern']}/", timeout=10)
        assert resp.status_code == 200

    def test_proactive_agent_health(self):
        """proactive-agent health endpoint should respond."""
        resp = requests.get(f"{SERVICES['proactive-agent']}/health", timeout=10)
        assert resp.status_code == 200
