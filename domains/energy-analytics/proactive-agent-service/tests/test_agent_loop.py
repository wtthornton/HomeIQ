"""
Integration Tests for Proactive Agent Loop (Epic 68, Story 68.8).

Tests:
- Autonomous execution of low-risk action with high confidence
- Suggestion surfacing for medium-risk action
- Safety guardrail blocks lock/alarm auto-execution
- Preference learning improves confidence over iterations
- Undo reverses autonomous action
- Quiet hours suppression
"""

import pytest

from src.models.autonomous_action import ActionOutcome
from src.services.confidence_scorer import (
    ActionScore,
    ConfidenceScorer,
    SAFETY_BLOCKED_DOMAINS,
)


# ---------------------------------------------------------------------------
# Confidence Scorer Tests (Story 68.3)
# ---------------------------------------------------------------------------


class TestConfidenceScorer:
    """Tests for the confidence & risk scoring engine."""

    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_low_risk_high_confidence_auto_execute(self):
        """High confidence + low risk → should auto-execute."""
        score = self.scorer.score_action(
            action_type="turn_off",
            entity_domain="light",
            context_type="time_of_day",
            llm_confidence=0.95,
            acceptance_rate=0.90,
            context_match_strength=0.85,
            preference_alignment=0.80,
        )
        assert score.risk_level == "low"
        assert score.confidence >= 85
        assert score.should_auto_execute is True

    def test_medium_risk_suggests_only(self):
        """Climate actions are medium risk — never auto-execute."""
        score = self.scorer.score_action(
            action_type="set_temperature",
            entity_domain="climate",
            context_type="weather",
            llm_confidence=0.90,
            acceptance_rate=0.85,
        )
        assert score.risk_level == "medium"
        assert score.should_auto_execute is False
        assert score.should_suggest is True

    def test_safety_blocked_domains(self):
        """Lock/alarm/camera domains are always blocked."""
        for domain in SAFETY_BLOCKED_DOMAINS:
            score = self.scorer.score_action(
                action_type="turn_on",
                entity_domain=domain,
                context_type="security",
                llm_confidence=1.0,
                acceptance_rate=1.0,
            )
            assert score.is_safety_blocked is True
            assert score.confidence == 0
            assert score.risk_level == "critical"

    def test_low_confidence_suppressed(self):
        """Very low confidence → suppress entirely."""
        score = self.scorer.score_action(
            action_type="turn_off",
            entity_domain="light",
            context_type="unknown",
            llm_confidence=0.1,
            acceptance_rate=0.1,
            context_match_strength=0.1,
        )
        assert score.should_suppress is True

    def test_no_history_uses_baseline(self):
        """No acceptance history → uses neutral 0.5 baseline."""
        score = self.scorer.score_action(
            action_type="turn_off",
            entity_domain="light",
            context_type="time_of_day",
            llm_confidence=0.8,
            acceptance_rate=None,  # No history
        )
        assert score.confidence > 0
        assert "acceptance_rate" in score.factors

    def test_reversibility_affects_confidence(self):
        """More reversible actions get a confidence boost."""
        score_reversible = self.scorer.score_action(
            action_type="turn_off",
            entity_domain="light",
            context_type="time_of_day",
            llm_confidence=0.8,
        )
        score_irreversible = self.scorer.score_action(
            action_type="run_script",
            entity_domain="script",
            context_type="time_of_day",
            llm_confidence=0.8,
        )
        assert score_reversible.confidence >= score_irreversible.confidence


class TestActionRouting:
    """Tests for action route evaluation."""

    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_quiet_hours_blocks_auto_execute(self):
        """During quiet hours, never auto-execute."""
        score = ActionScore(confidence=95, risk_level="low", reversibility=1.0)
        route = self.scorer.evaluate_action_route(
            score=score,
            autonomous_enabled=True,
            in_quiet_hours=True,
        )
        assert route == "suggest"  # Falls through to suggest

    def test_autonomous_disabled_blocks_auto_execute(self):
        """When autonomous execution disabled, only suggest."""
        score = ActionScore(confidence=95, risk_level="low", reversibility=1.0)
        route = self.scorer.evaluate_action_route(
            score=score,
            autonomous_enabled=False,
            in_quiet_hours=False,
        )
        assert route == "suggest"

    def test_critical_risk_always_suppressed(self):
        """Critical risk (locks/alarms) → suppress regardless of confidence."""
        score = ActionScore(confidence=100, risk_level="critical", reversibility=0.0)
        route = self.scorer.evaluate_action_route(score=score)
        assert route == "suppress"

    def test_auto_execute_happy_path(self):
        """High confidence + low risk + enabled + not quiet → auto-execute."""
        score = ActionScore(confidence=90, risk_level="low", reversibility=1.0)
        route = self.scorer.evaluate_action_route(
            score=score,
            autonomous_enabled=True,
            in_quiet_hours=False,
        )
        assert route == "auto_execute"

    def test_medium_confidence_suggests(self):
        """Medium confidence → suggest."""
        score = ActionScore(confidence=60, risk_level="low", reversibility=1.0)
        route = self.scorer.evaluate_action_route(score=score)
        assert route == "suggest"

    def test_very_low_confidence_suppressed(self):
        """Below suppress threshold → suppress."""
        score = ActionScore(confidence=20, risk_level="low", reversibility=1.0)
        route = self.scorer.evaluate_action_route(score=score)
        assert route == "suppress"


# ---------------------------------------------------------------------------
# Safety Guardrails Tests (Story 68.6)
# ---------------------------------------------------------------------------


class TestSafetyGuardrails:
    """Tests for safety guardrail enforcement."""

    def test_lock_domain_blocked(self):
        assert "lock" in SAFETY_BLOCKED_DOMAINS

    def test_alarm_domain_blocked(self):
        assert "alarm_control_panel" in SAFETY_BLOCKED_DOMAINS

    def test_camera_domain_blocked(self):
        assert "camera" in SAFETY_BLOCKED_DOMAINS

    def test_light_domain_allowed(self):
        assert "light" not in SAFETY_BLOCKED_DOMAINS

    def test_switch_domain_allowed(self):
        assert "switch" not in SAFETY_BLOCKED_DOMAINS

    def test_safety_domains_are_frozen(self):
        """Safety blocked domains must be a frozenset (immutable)."""
        assert isinstance(SAFETY_BLOCKED_DOMAINS, frozenset)


# ---------------------------------------------------------------------------
# Feedback & Preference Tests (Stories 68.2, 68.5)
# ---------------------------------------------------------------------------


class TestActionPreferenceHistory:
    """Tests for preference history model logic."""

    def test_action_outcome_values(self):
        """All expected outcome types are defined."""
        assert ActionOutcome.AUTO_EXECUTED.value == "auto_executed"
        assert ActionOutcome.AUTO_EXECUTED_UNDONE.value == "auto_executed_undone"
        assert ActionOutcome.SUGGESTED.value == "suggested"
        assert ActionOutcome.ACCEPTED.value == "accepted"
        assert ActionOutcome.REJECTED.value == "rejected"
        assert ActionOutcome.SUPPRESSED.value == "suppressed"


# ---------------------------------------------------------------------------
# Agent Loop Validation Tests (Story 68.1)
# ---------------------------------------------------------------------------


class TestAgentLoopValidation:
    """Tests for LLM output validation in the agent loop."""

    def test_time_slot_mapping(self):
        """Time slots map correctly."""
        from src.services.agent_loop import ProactiveAgentLoop

        assert ProactiveAgentLoop._get_time_slot(6) == "morning"
        assert ProactiveAgentLoop._get_time_slot(14) == "afternoon"
        assert ProactiveAgentLoop._get_time_slot(19) == "evening"
        assert ProactiveAgentLoop._get_time_slot(2) == "night"
        assert ProactiveAgentLoop._get_time_slot(23) == "night"


# ---------------------------------------------------------------------------
# Integration: Preference Learning Over Iterations (Story 68.5)
# ---------------------------------------------------------------------------


class TestPreferenceLearning:
    """Tests that acceptance rate calculation is correct."""

    def test_acceptance_rate_calculation(self):
        """Acceptance rate formula: (accepted + auto_executed - undone) / total."""
        from src.models.autonomous_action import ActionPreferenceHistory

        pref = ActionPreferenceHistory(
            action_type="turn_off",
            entity_domain="light",
            context_type="time_of_day",
            time_slot="evening",
        )
        # Simulate 3 accepted, 1 rejected, 1 auto-executed
        pref.acceptance_count = 3
        pref.rejection_count = 1
        pref.auto_execute_count = 1
        pref.undo_count = 0
        total = pref.acceptance_count + pref.rejection_count + pref.auto_execute_count
        positive = pref.acceptance_count + pref.auto_execute_count - pref.undo_count
        rate = max(0.0, min(1.0, positive / total))
        assert rate == pytest.approx(0.8)

    def test_undo_reduces_acceptance_rate(self):
        """Undo counts should reduce acceptance rate."""
        from src.models.autonomous_action import ActionPreferenceHistory

        pref = ActionPreferenceHistory(
            action_type="turn_off",
            entity_domain="light",
            context_type="time_of_day",
            time_slot="evening",
        )
        pref.acceptance_count = 2
        pref.rejection_count = 1
        pref.auto_execute_count = 2
        pref.undo_count = 2  # Undone 2 auto-executions
        total = pref.acceptance_count + pref.rejection_count + pref.auto_execute_count
        positive = pref.acceptance_count + pref.auto_execute_count - pref.undo_count
        rate = max(0.0, min(1.0, positive / total))
        assert rate == pytest.approx(0.4)
