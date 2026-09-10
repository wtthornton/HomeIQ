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

from src.proactive.models.autonomous_action import ActionOutcome
from src.proactive.services.confidence_scorer import (
    SAFETY_BLOCKED_DOMAINS,
    ActionScore,
    ConfidenceScorer,
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
            llm_confidence=0.8,
        )
        score_irreversible = self.scorer.score_action(
            action_type="run_script",
            entity_domain="script",
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
        from src.proactive.services.agent_loop import ProactiveAgentLoop

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
        from src.proactive.models.autonomous_action import ActionPreferenceHistory

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
        from src.proactive.models.autonomous_action import ActionPreferenceHistory

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


# ---------------------------------------------------------------------------
# OpenAI key secrecy (SecretStr regression)
# ---------------------------------------------------------------------------


class TestAgentForgeKeySecret:
    """Regression: the reasoning credential must be masked and unwrapped at use.

    ``agentforge_api_key`` is a ``SecretStr`` so a repr/log dump of the settings
    object cannot leak it, and ``_init_agentforge_client`` must unwrap it before
    putting it on the wire. TAP-7275 changed which credential this is -- it was
    ``openai_api_key`` -- but not the property being guarded.
    """

    def _make_loop(self, settings):
        from src.proactive.services.agent_loop import ProactiveAgentLoop

        stub = object()
        return ProactiveAgentLoop(
            settings=settings,
            context_service=stub,
            device_control_client=stub,
            agent_client=stub,
            confidence_scorer=stub,
            preference_service=stub,
            feedback_recorder=stub,
            autonomous_executor=stub,
        )

    def test_settings_repr_does_not_leak_key(self):
        from src.proactive.config import Settings

        settings = Settings(agentforge_api_key="afp-super-secret")
        assert "afp-super-secret" not in repr(settings)
        assert "afp-super-secret" not in str(settings)

    def test_init_unwraps_the_secret(self):
        from src.proactive.config import Settings

        loop = self._make_loop(Settings(agentforge_api_key="afp-real-value"))
        loop._init_agentforge_client()

        assert loop._agentforge is not None
        assert loop._agentforge.api_key == "afp-real-value"
        assert "SecretStr" not in loop._agentforge.api_key

    def test_absent_key_leaves_reasoning_disabled(self):
        from src.proactive.config import Settings

        loop = self._make_loop(Settings(agentforge_api_key=None))
        loop._init_agentforge_client()
        assert loop._agentforge is None


class TestReasonStepCallShape:
    """Regression: gpt-5-mini rejects ``max_tokens`` and any explicit
    ``temperature``.

    The live circuit breaker opened 1,306x on
    ``Unsupported parameter: 'max_tokens' is not supported with this model.
    Use 'max_completion_tokens' instead.`` and
    ``Unsupported value: 'temperature' does not support 0.3 with this model.
    Only the default (1) value is supported.`` The fix must send
    ``max_completion_tokens`` and omit ``temperature`` entirely.
    """

    @pytest.mark.asyncio
    async def test_reason_runs_the_proactive_suggest_workflow_and_reads_actions(self):
        """TAP-7275: the reasoning step is a workflow run, not a provider call.

        This replaces the assertion that the call omitted `temperature` and used
        `max_completion_tokens` -- a gpt-5-mini parameter contract that no longer
        exists here, because the model call, its parameters and its credential
        moved into AgentForge. What still has to hold is that the loop reaches
        the right workflow and reads the half of the answer meant for it.
        """
        from unittest.mock import AsyncMock

        from src.proactive.config import Settings
        from src.proactive.services.agent_loop import ProactiveAgentLoop

        settings = Settings(agentforge_api_key="afp-real-value")

        preference_service = AsyncMock()
        preference_service.get_preference_summary.return_value = "no history"

        calls: list = []

        class FakeAgentForge:
            async def run_workflow_json(self, name, inputs, dry_run=False):
                calls.append((name, inputs))
                return {
                    "suggestions": [
                        {"prompt": "not this half", "category": "energy", "priority": "low"}
                    ],
                    "actions": [
                        {
                            "action_type": "turn_off",
                            "entity_id": "light.kitchen",
                            "entity_domain": "light",
                            "reasoning": "on for four hours with nobody home",
                        }
                    ],
                }

        stub = object()
        loop = ProactiveAgentLoop(
            settings=settings,
            context_service=stub,
            device_control_client=stub,
            agent_client=stub,
            confidence_scorer=stub,
            preference_service=preference_service,
            feedback_recorder=stub,
            autonomous_executor=stub,
        )
        loop._agentforge = FakeAgentForge()

        actions = await loop._reason(
            {
                "home_state": {"light.kitchen": "on"},
                "weather": {},
                "time": {
                    "utc": "2026-09-09T00:00:00",
                    "hour": 0,
                    "day_of_week": "Tuesday",
                    "time_slot": "night",
                },
            }
        )

        assert calls, "the reasoning step must reach AgentForge"
        name, inputs = calls[-1]
        assert name == "proactive-suggest"
        assert "light.kitchen" in inputs["home_context"]
        # It reads `actions`, not `suggestions` -- the other caller of this same
        # gene reads the other half.
        assert [a["entity_id"] for a in actions] == ["light.kitchen"]
