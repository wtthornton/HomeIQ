"""
Tests for Epic 69: Agent Eval — Adaptive Model Routing & Feedback Loop.

Covers: ComplexityClassifier, ModelRouter, EvalAlertService,
CostTracker, RegressionInvestigator.
"""

import time

# ---------------------------------------------------------------------------
# Story 69.1: Request Complexity Classifier
# ---------------------------------------------------------------------------


class TestComplexityClassifier:
    """Tests for request complexity classification."""

    def test_simple_query_is_low(self):
        """Short simple query classifies as low."""
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        result = c.classify("Is the kitchen light on?")
        assert result.level == ComplexityLevel.LOW
        assert result.score < 0.30

    def test_complex_multi_entity_is_high(self):
        """Long multi-entity, multi-step request classifies as high.

        HIGH needs a weighted score >= 0.55. Maxing entity_count (>=3
        entities) and tool_hint (>=2 multi-step keywords) only reaches
        0.41, so a first-turn request must also clear the 200-character
        length threshold to be classified HIGH.
        """
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        msg = (
            "Create an automation that turns on light.kitchen, light.bedroom, "
            "and light.living_room when sensor.motion_front is triggered, "
            "and then also set climate.hallway to 22 degrees, and after that "
            "close cover.garage and lock lock.front_door once everyone has left"
        )
        assert len(msg) > 200
        result = c.classify(msg)
        assert result.level == ComplexityLevel.HIGH
        assert result.factors["token_count"] == 1.0
        assert result.factors["entity_count"] == 1.0
        assert result.factors["tool_hint"] == 0.8

    def test_multi_entity_under_length_threshold_is_medium(self):
        """The same request shape, but under 200 chars, stops at medium.

        Entity and tool-hint signals alone cap the score at 0.535, just
        under the 0.55 HIGH threshold.
        """
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        msg = (
            "Create an automation that turns on light.kitchen, light.bedroom, "
            "and light.living_room when sensor.motion_front is triggered, "
            "and then also set climate.hallway to 22 degrees"
        )
        assert len(msg) < 200
        result = c.classify(msg)
        assert result.level == ComplexityLevel.MEDIUM
        assert result.factors["entity_count"] == 1.0
        assert result.factors["tool_hint"] == 0.8

    def test_medium_complexity(self):
        """Several explicit entities plus one multi-step hint is medium."""
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        result = c.classify(
            "Set the brightness on light.kitchen and light.dining to 40 percent "
            "and then turn off switch.porch when the sun goes down",
            conversation_depth=2,
        )
        assert result.level == ComplexityLevel.MEDIUM

    def test_natural_language_device_names_are_not_entities(self):
        """Only `domain.entity_id` tokens count toward entity_count.

        A short single-device request phrased in natural language carries
        no entity signal, so it stays LOW and routes to the cheap model
        even a few turns into a conversation.
        """
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        result = c.classify(
            "Turn on the kitchen light and set brightness to 50%",
            conversation_depth=3,
        )
        assert result.factors["entity_count"] == 0.0
        assert result.level == ComplexityLevel.LOW

    def test_deep_conversation_increases_complexity(self):
        """Deep conversation history increases complexity score."""
        from src.services.eval_routing.complexity_classifier import ComplexityClassifier

        c = ComplexityClassifier()
        shallow = c.classify("Hello", conversation_depth=0)
        deep = c.classify("Hello", conversation_depth=10)
        assert deep.score > shallow.score

    def test_prior_tool_calls_increase_complexity(self):
        """Prior tool calls increase complexity score."""
        from src.services.eval_routing.complexity_classifier import ComplexityClassifier

        c = ComplexityClassifier()
        no_tools = c.classify("Hello", previous_tool_calls=0)
        many_tools = c.classify("Hello", previous_tool_calls=6)
        assert many_tools.score > no_tools.score

    def test_entity_ids_counted(self):
        """Provided entity_ids are used for entity count."""
        from src.services.eval_routing.complexity_classifier import ComplexityClassifier

        c = ComplexityClassifier()
        result = c.classify(
            "Control these",
            entity_ids=["light.a", "light.b", "light.c", "light.d"],
        )
        assert result.factors["entity_count"] == 1.0

    def test_multi_tool_keywords(self):
        """Multi-tool keywords detected."""
        from src.services.eval_routing.complexity_classifier import ComplexityClassifier

        c = ComplexityClassifier()
        result = c.classify("First turn on the light, and then set the thermostat")
        assert result.factors["tool_hint"] > 0.0

    def test_empty_message_is_low(self):
        """Empty message is low complexity."""
        from src.services.eval_routing.complexity_classifier import (
            ComplexityClassifier,
            ComplexityLevel,
        )

        c = ComplexityClassifier()
        result = c.classify("")
        assert result.level == ComplexityLevel.LOW


# ---------------------------------------------------------------------------
# Story 69.2: Adaptive Model Router
# ---------------------------------------------------------------------------


class TestModelRouter:
    """Tests for the adaptive model router."""

    def test_high_complexity_uses_primary(self):
        """High complexity always routes to primary."""
        from src.services.eval_routing.complexity_classifier import ComplexityLevel
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        decision = router.route(
            "Create a complex automation with light.a, light.b, light.c and "
            "sensor.motion and then also configure climate.hall, and after "
            "that close cover.garage and lock lock.front_door whenever the "
            "house reports that nobody is home",
            conversation_id="test-1",
        )
        assert decision.complexity.level == ComplexityLevel.HIGH
        assert decision.chosen_model == "gpt-5.2-codex"
        assert decision.reason == "high_complexity"

    def test_low_complexity_uses_cheap(self):
        """Low complexity routes to cheap model."""
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        decision = router.route("Hello", conversation_id="test-2")
        assert decision.chosen_model == "gpt-4.1-mini"

    def test_eval_auto_upgrade(self):
        """Low eval scores auto-upgrade to primary model."""
        from src.services.eval_routing.complexity_classifier import ComplexityLevel
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        # Record poor eval scores for LOW category
        for _ in range(10):
            router.record_eval_score(ComplexityLevel.LOW, 55.0)

        decision = router.route("Hello", conversation_id="test-3")
        assert decision.chosen_model == "gpt-5.2-codex"
        assert decision.overridden is True
        assert "eval_auto_upgrade" in decision.reason

    def test_model_lock(self):
        """Locked model overrides all routing."""
        from src.services.eval_routing.model_router import ModelRouter, RoutingConfig

        config = RoutingConfig(locked_model="gpt-5.2-codex")
        router = ModelRouter(config=config)
        decision = router.route("Hello", conversation_id="test-4")
        assert decision.chosen_model == "gpt-5.2-codex"
        assert decision.reason == "model_locked"

    def test_agent_override(self):
        """Per-agent override takes precedence."""
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        router.set_agent_override("agent-1", "gpt-5.2-codex")
        decision = router.route("Hello", conversation_id="test-5", agent_id="agent-1")
        assert decision.chosen_model == "gpt-5.2-codex"
        assert decision.reason == "agent_override"

    def test_routing_disabled_uses_primary(self):
        """Disabled routing always uses primary."""
        from src.services.eval_routing.model_router import ModelRouter, RoutingConfig

        config = RoutingConfig(routing_enabled=False)
        router = ModelRouter(config=config)
        decision = router.route("Hello", conversation_id="test-6")
        assert decision.chosen_model == "gpt-5.2-codex"

    def test_routing_table(self):
        """Routing table includes all config."""
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        table = router.get_routing_table()
        assert "config" in table
        assert "category_scores" in table
        assert "low" in table["category_scores"]

    def test_decisions_recorded(self):
        """Routing decisions are recorded."""
        from src.services.eval_routing.model_router import ModelRouter

        router = ModelRouter()
        router.route("Hello", conversation_id="test-7")
        router.route("World", conversation_id="test-8")
        decisions = router.get_recent_decisions()
        assert len(decisions) == 2


# ---------------------------------------------------------------------------
# Story 69.4: Eval Degradation Alerting
# ---------------------------------------------------------------------------


class TestEvalAlerting:
    """Tests for eval degradation alerting."""

    def test_no_alert_with_few_samples(self):
        """No alerts fired with insufficient samples."""
        from src.services.eval_routing.eval_alerting import EvalAlertService

        svc = EvalAlertService()
        result = svc.record_score("agent-1", "accuracy", 50.0)
        assert result is None  # Not enough samples

    def test_floor_breach_alert(self):
        """Alert fires once when score drops below floor (50).

        The alert fires on the fifth sample (the minimum sample count);
        further samples inside the one-hour cooldown return None rather
        than re-firing for the same dimension.
        """
        from src.services.eval_routing.eval_alerting import EvalAlertService

        svc = EvalAlertService()
        # Record enough samples below floor
        results = [svc.record_score("agent-1", "accuracy", 40.0) for _ in range(6)]

        fired = [r for r in results if r is not None]
        assert len(fired) == 1
        assert fired[0].alert_type == "floor_breach"
        assert fired[0].agent_name == "agent-1"
        assert fired[0].current_score == 40.0
        # Samples 6+ are suppressed by the cooldown, not re-alerted.
        assert results[-1] is None

    def test_degradation_alert(self):
        """Alert fires when rolling 24h avg drops >10% from the 7d baseline.

        The baseline is the 7-day average, which includes the last 24
        hours, so a drop is only visible once there is older history to
        compare against. Backdating the good scores by two days is what
        makes the two windows differ.
        """
        from src.services.eval_routing.eval_alerting import EvalAlertService

        svc = EvalAlertService()
        # Build baseline of 80
        for _ in range(10):
            svc.record_score("agent-1", "quality", 80.0)

        # Age the baseline out of the 24h window so it is baseline-only.
        tracker = svc._trackers["agent-1:quality"]
        tracker.recent_scores = [(ts - 2 * 86400, score) for ts, score in tracker.recent_scores]

        # Simulate sudden drop
        for _ in range(6):
            svc.record_score("agent-1", "quality", 60.0)

        assert tracker.rolling_24h_avg == 60.0
        assert tracker.rolling_7d_avg > 60.0

        alerts = svc.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "degradation"
        assert alerts[0]["drop_pct"] > 10.0

    def test_acknowledge_alert(self):
        """Alert can be acknowledged."""
        from src.services.eval_routing.eval_alerting import EvalAlertService

        svc = EvalAlertService()
        for _ in range(6):
            svc.record_score("agent-1", "accuracy", 40.0)

        alerts = svc.get_alerts()
        assert len(alerts) > 0
        alert_id = alerts[-1]["alert_id"]
        assert svc.acknowledge_alert(alert_id) is True

        unacked = svc.get_alerts(unacknowledged_only=True)
        assert all(a["alert_id"] != alert_id for a in unacked)

    def test_tracker_status(self):
        """Tracker status returns dimension info."""
        from src.services.eval_routing.eval_alerting import EvalAlertService

        svc = EvalAlertService()
        svc.record_score("agent-1", "accuracy", 85.0)
        status = svc.get_tracker_status()
        assert "agent-1:accuracy" in status


# ---------------------------------------------------------------------------
# Story 69.6: Cost Tracking
# ---------------------------------------------------------------------------


class TestCostTracker:
    """Tests for cost tracking and savings reporting."""

    def test_record_usage(self):
        """Usage recording returns estimated cost."""
        from src.services.eval_routing.cost_tracker import CostTracker

        tracker = CostTracker()
        cost = tracker.record_usage("gpt-4.1-mini", "agent-1", 1000, 500)
        assert cost > 0
        assert cost < 0.01  # Cheap model should be very cheap

    def test_savings_report(self):
        """Savings report compares actual vs baseline."""
        from src.services.eval_routing.cost_tracker import CostTracker

        tracker = CostTracker()
        # Some cheap, some expensive
        tracker.record_usage("gpt-4.1-mini", "agent-1", 1000, 500)
        tracker.record_usage("gpt-4.1-mini", "agent-1", 1000, 500)
        tracker.record_usage("gpt-5.2-codex", "agent-1", 1000, 500)

        report = tracker.get_savings_report()
        assert report["savings_usd"] > 0
        assert report["savings_pct"] > 0
        assert report["total_requests"] == 3

    def test_daily_summaries(self):
        """Daily summaries are tracked."""
        from src.services.eval_routing.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.record_usage("gpt-4.1-mini", "agent-1", 1000, 500)
        summaries = tracker.get_daily_summaries()
        assert len(summaries) == 1
        assert summaries[0]["request_count"] == 1

    def test_primary_model_costs_more(self):
        """Primary model costs more per request."""
        from src.services.eval_routing.cost_tracker import CostTracker

        tracker = CostTracker()
        cheap_cost = tracker.record_usage("gpt-4.1-mini", "a", 1000, 500)
        expensive_cost = tracker.record_usage("gpt-5.2-codex", "a", 1000, 500)
        assert expensive_cost > cheap_cost


# ---------------------------------------------------------------------------
# Story 69.5: Regression Investigator
# ---------------------------------------------------------------------------


class TestRegressionInvestigator:
    """Tests for automated regression investigation."""

    def test_investigate_generates_report(self):
        """Investigation produces a report."""
        from src.services.eval_routing.regression_investigator import (
            RegressionInvestigator,
            TraceRecord,
        )

        inv = RegressionInvestigator()
        now = time.time()

        for i in range(10):
            inv.record_trace(
                TraceRecord(
                    trace_id=f"trace-{i}",
                    timestamp=now - 3600 + i * 60,
                    score=50.0 + i * 2,
                    model="gpt-4.1-mini",
                    complexity_level="low",
                    entity_domains=["light"],
                    intent_category="control",
                )
            )

        report = inv.investigate(
            alert_id="alert-1",
            agent_name="agent-1",
            dimension="accuracy",
        )
        assert report.alert_id == "alert-1"
        assert len(report.lowest_traces) > 0
        assert report.summary  # Non-empty summary

    def test_common_patterns_detected(self):
        """Common patterns in failing traces are detected."""
        from src.services.eval_routing.regression_investigator import (
            RegressionInvestigator,
            TraceRecord,
        )

        inv = RegressionInvestigator()
        now = time.time()

        # All failures involve "light" domain
        for i in range(5):
            inv.record_trace(
                TraceRecord(
                    trace_id=f"fail-{i}",
                    timestamp=now - 1800 + i * 60,
                    score=40.0,
                    model="gpt-4.1-mini",
                    complexity_level="low",
                    entity_domains=["light"],
                    intent_category="control",
                    error_type="entity_not_found",
                )
            )

        report = inv.investigate("alert-2", "agent-1", "accuracy")
        pattern_names = [p["pattern"] for p in report.common_patterns]
        assert any("light" in p for p in pattern_names)

    def test_report_retrievable(self):
        """Generated report can be retrieved by alert ID."""
        from src.services.eval_routing.regression_investigator import (
            RegressionInvestigator,
        )

        inv = RegressionInvestigator()
        inv.investigate("alert-3", "agent-1", "accuracy")
        report = inv.get_report("alert-3")
        assert report is not None
        assert report["alert_id"] == "alert-3"
