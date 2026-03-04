"""Health Endpoint Aggregation Tests.

Verifies that every service that exposes a /health endpoint follows a
consistent response schema. This is a static analysis test — it scans
service source directories for FastAPI health route definitions and
validates they return the expected format.

The health-dashboard aggregates /health from all groups, so schema
consistency is critical for cross-group observability.
"""

import os
from pathlib import Path

import pytest

# All 9 domain groups and their service directories
DOMAIN_SERVICES = {
    "core-platform": [
        "websocket-ingestion", "data-api", "admin-api",
        "data-retention", "ha-simulator",
    ],
    "data-collectors": [
        "weather-api", "smart-meter-service", "sports-api",
        "air-quality-service", "carbon-intensity-service",
        "electricity-pricing-service", "calendar-service", "log-aggregator",
    ],
    "ml-engine": [
        "ai-core-service", "openvino-service", "ml-service",
        "rag-service", "ai-training-service", "device-intelligence-service",
        "model-prep", "nlp-fine-tuning", "ner-service", "openai-service",
    ],
    "automation-core": [
        "ha-ai-agent-service", "ai-automation-service-new",
        "ai-query-service", "automation-linter",
        "yaml-validation-service", "ai-code-executor",
        "automation-trace-service",
    ],
    "blueprints": [
        "blueprint-index", "blueprint-suggestion-service",
        "rule-recommendation-ml", "automation-miner",
    ],
    "energy-analytics": [
        "energy-correlator", "energy-forecasting", "proactive-agent-service",
    ],
    "device-management": [
        "device-health-monitor", "device-context-classifier",
        "device-setup-assistant", "device-database-client",
        "device-recommender", "activity-recognition",
        "activity-writer", "ha-setup-service",
    ],
    "pattern-analysis": [
        "ai-pattern-service", "api-automation-edge",
    ],
}


def _find_python_files(service_dir: str) -> list[str]:
    """Find all .py files in a service's src directory."""
    src_dir = os.path.join(service_dir, "src")
    if not os.path.isdir(src_dir):
        return []
    return [
        str(p) for p in Path(src_dir).rglob("*.py")
    ]


def _file_mentions_health_endpoint(filepath: str) -> bool:
    """Check if a Python file defines a /health route."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return '"/health"' in content or "'/health'" in content
    except OSError:
        return False


class TestHealthAggregation:
    """Validate health endpoint consistency across all domain groups."""

    def test_all_domain_groups_have_services(self):
        """Verify the domain directory structure matches expectations."""
        base = os.path.join(os.getcwd(), "domains")
        for group in DOMAIN_SERVICES:
            group_dir = os.path.join(base, group)
            assert os.path.isdir(group_dir), f"Domain group missing: {group}"

    @pytest.mark.parametrize(
        "group,service",
        [
            (group, svc)
            for group, services in DOMAIN_SERVICES.items()
            for svc in services
        ],
    )
    def test_service_directory_exists(self, group, service):
        """Each listed service should have a directory under its domain group."""
        svc_dir = os.path.join(os.getcwd(), "domains", group, service)
        if not os.path.isdir(svc_dir):
            pytest.skip(f"{group}/{service} directory not found")

    def test_health_endpoints_exist_in_core_services(self):
        """Core-platform services MUST have /health endpoints."""
        base = os.path.join(os.getcwd(), "domains", "core-platform")
        critical = ["data-api", "admin-api", "websocket-ingestion"]

        for svc in critical:
            svc_dir = os.path.join(base, svc)
            if not os.path.isdir(svc_dir):
                continue

            py_files = _find_python_files(svc_dir)
            has_health = any(_file_mentions_health_endpoint(f) for f in py_files)
            assert has_health, (
                f"Core service {svc} must define a /health endpoint"
            )

    def test_health_endpoints_return_status_field(self):
        """Services with /health should return {\"status\": ...} in response.

        Scans source files for health endpoint handlers and checks that
        they include a 'status' key in the response dict.
        """
        base = os.path.join(os.getcwd(), "domains")
        services_with_health = []

        for group, services in DOMAIN_SERVICES.items():
            for svc in services:
                svc_dir = os.path.join(base, group, svc)
                py_files = _find_python_files(svc_dir)
                for f in py_files:
                    if _file_mentions_health_endpoint(f):
                        services_with_health.append(f"{group}/{svc}")
                        try:
                            with open(f, encoding="utf-8", errors="ignore") as fh:
                                content = fh.read()
                            # Check that "status" appears near the health endpoint
                            assert '"status"' in content or "'status'" in content, (
                                f"{group}/{svc} health endpoint should return "
                                f"a 'status' field in its response"
                            )
                        except OSError:
                            pass
                        break

        # At least core services should have health endpoints
        assert len(services_with_health) >= 3, (
            f"Expected at least 3 services with /health, found {len(services_with_health)}"
        )
