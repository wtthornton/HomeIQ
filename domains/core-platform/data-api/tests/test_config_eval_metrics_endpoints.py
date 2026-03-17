"""
Tests for config + evaluation + metrics endpoints — Epic 80, Story 80.10b

Covers 16 scenarios:

config_endpoints:
1.  ConfigItem — validates fields
2.  ConfigUpdate — validates fields
3.  ConfigValidation — validates fields
4.  _validate_type — string type
5.  _validate_type — integer type
6.  _validate_type — boolean type
7.  _validate_type — unknown type returns True
8.  _validate_rules — min/max validation
9.  _validate_rules — string length validation
10. _validate_rules — pattern validation
11. _validate_rules — enum validation

evaluation_endpoints:
12. AgentSummary — default values
13. HealthResponse — validates fields
14. AlertResponse — validates fields
15. HistoryResponse — validates fields

metrics_endpoints:
16. ServiceMetrics — validates fields
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# config_endpoints tests
# ===========================================================================


class TestConfigModels:
    """ConfigEndpoints response models."""

    def test_config_item(self):
        from src.config_endpoints import ConfigItem

        item = ConfigItem(
            key="log_level",
            value="INFO",
            description="Logging level",
            type="string",
            required=True,
            default="INFO",
        )
        assert item.key == "log_level"
        assert item.required is True

    def test_config_update(self):
        from src.config_endpoints import ConfigUpdate

        u = ConfigUpdate(key="log_level", value="DEBUG", reason="debugging")
        assert u.key == "log_level"
        assert u.reason == "debugging"

    def test_config_validation(self):
        from src.config_endpoints import ConfigValidation

        v = ConfigValidation(is_valid=True)
        assert v.errors == []
        assert v.warnings == []

        v2 = ConfigValidation(is_valid=False, errors=["bad key"])
        assert not v2.is_valid
        assert len(v2.errors) == 1


class TestConfigValidateType:
    """ConfigEndpoints._validate_type()."""

    def _get_endpoints(self):
        from src.config_endpoints import ConfigEndpoints
        return ConfigEndpoints()

    def test_string_type(self):
        ep = self._get_endpoints()
        assert ep._validate_type("hello", "string") is True
        assert ep._validate_type(123, "string") is False

    def test_integer_type(self):
        ep = self._get_endpoints()
        assert ep._validate_type(42, "integer") is True
        assert ep._validate_type("42", "integer") is False

    def test_boolean_type(self):
        ep = self._get_endpoints()
        assert ep._validate_type(True, "boolean") is True
        assert ep._validate_type(1, "boolean") is False

    def test_unknown_type_returns_true(self):
        ep = self._get_endpoints()
        assert ep._validate_type("anything", "custom_type") is True


class TestConfigValidateRules:
    """ConfigEndpoints._validate_rules()."""

    def _get_endpoints(self):
        from src.config_endpoints import ConfigEndpoints
        return ConfigEndpoints()

    def test_min_max(self):
        ep = self._get_endpoints()
        result = ep._validate_rules(5, {"min": 0, "max": 10})
        assert result["errors"] == []

        result = ep._validate_rules(-1, {"min": 0, "max": 10})
        assert len(result["errors"]) == 1
        assert "below minimum" in result["errors"][0]

        result = ep._validate_rules(11, {"min": 0, "max": 10})
        assert len(result["errors"]) == 1
        assert "above maximum" in result["errors"][0]

    def test_string_length(self):
        ep = self._get_endpoints()
        result = ep._validate_rules("ab", {"min_length": 3})
        assert len(result["errors"]) == 1
        assert "below minimum" in result["errors"][0]

        result = ep._validate_rules("abcdef", {"max_length": 3})
        assert len(result["errors"]) == 1
        assert "above maximum" in result["errors"][0]

    def test_pattern(self):
        ep = self._get_endpoints()
        result = ep._validate_rules("abc123", {"pattern": r"^[a-z]+$"})
        assert len(result["errors"]) == 1
        assert "does not match" in result["errors"][0]

        result = ep._validate_rules("abc", {"pattern": r"^[a-z]+$"})
        assert result["errors"] == []

    def test_enum(self):
        ep = self._get_endpoints()
        result = ep._validate_rules("INFO", {"enum": ["INFO", "DEBUG", "ERROR"]})
        assert result["errors"] == []

        result = ep._validate_rules("TRACE", {"enum": ["INFO", "DEBUG", "ERROR"]})
        assert len(result["errors"]) == 1
        assert "not in allowed values" in result["errors"][0]


# ===========================================================================
# evaluation_endpoints tests
# ===========================================================================


class TestEvaluationModels:
    """Evaluation endpoint response models."""

    def test_agent_summary_defaults(self):
        from src.evaluation_endpoints import AgentSummary

        s = AgentSummary(agent_name="test-agent")
        assert s.sessions_evaluated == 0
        assert s.total_evaluations == 0
        assert s.alerts_triggered == 0
        assert s.aggregate_scores == {}

    def test_health_response(self):
        from src.evaluation_endpoints import HealthResponse

        r = HealthResponse(
            status="operational",
            registered_agents=["agent-a", "agent-b"],
            batch_size=10,
            timestamp=datetime.now(UTC).isoformat(),
        )
        assert r.status == "operational"
        assert len(r.registered_agents) == 2

    def test_alert_response(self):
        from src.evaluation_endpoints import AlertResponse

        a = AlertResponse(
            alert_id="alert-001",
            agent_name="test-agent",
            evaluator_name="outcome",
            level="L1",
            metric="accuracy",
            threshold=0.8,
            actual_score=0.65,
            priority="high",
            status="active",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        assert a.alert_id == "alert-001"
        assert a.actual_score == 0.65
        assert a.acknowledged_by is None

    def test_history_response(self):
        from src.evaluation_endpoints import HistoryResponse

        h = HistoryResponse(
            agent_name="test-agent",
            scores=[{"evaluator": "outcome", "score": 0.9}],
            total=1,
            page=1,
            page_size=50,
        )
        assert h.total == 1
        assert h.scores[0]["score"] == 0.9


# ===========================================================================
# metrics_endpoints tests
# ===========================================================================


class TestMetricsModels:
    """Metrics endpoint response models."""

    def test_service_metrics(self):
        from src.metrics_endpoints import ServiceMetrics

        m = ServiceMetrics(
            service="data-api",
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=3600.0,
            counters={"requests": 100},
            gauges={"memory_mb": 256.0},
            timers={"request_time": {"avg": 0.05, "max": 0.5}},
            system={"cpu_percent": 12.5},
        )
        assert m.service == "data-api"
        assert m.counters["requests"] == 100
        assert m.uptime_seconds == 3600.0
