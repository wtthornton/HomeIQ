"""
Tests for Story 3.1: TemplateAppropriatenessEvaluator (L2 Path)

Verifies deterministic keyword-based intent-to-template matching
and LLM fallback for unrecognised intents.
"""

import pytest

from homeiq_patterns.evaluation.evaluators.l2_template_match import (
    TemplateAppropriatenessEvaluator,
)
from homeiq_patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvalScope,
    SessionTrace,
    UserMessage,
)


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        self.call_count += 1
        return self._response


def _make_session(prompt: str = "", template_id: str = "") -> SessionTrace:
    metadata: dict = {}
    if template_id:
        metadata["template_id"] = template_id
    return SessionTrace(
        agent_name="test",
        user_messages=[UserMessage(content=prompt)] if prompt else [],
        metadata=metadata,
    )


# =====================================================================
# Deterministic keyword matching
# =====================================================================


class TestKeywordMatching:
    @pytest.mark.asyncio
    async def test_turn_on_matches_room_entry(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("turn on the office lights", "room_entry_light_on")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Match"

    @pytest.mark.asyncio
    async def test_turn_on_matches_state_based(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("turn on the office lights", "state_based_automation")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Match"

    @pytest.mark.asyncio
    async def test_turn_on_wrong_template(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("turn on the office lights", "scheduled_task")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Mismatch"
        assert "scheduled_task" in result.explanation

    @pytest.mark.asyncio
    async def test_temperature_keyword(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "set the thermostat to 72 degrees", "temperature_control"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Match"

    @pytest.mark.asyncio
    async def test_scene_keyword(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "make it look like a party in the office", "scene_activation"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_leave_keyword(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "when I leave home turn off everything", "state_based_automation"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_every_not_matched_in_everything(self):
        """'every' should NOT match inside 'everything' — word boundary."""
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "when I leave home turn off everything", "scheduled_task"
        )
        result = await evaluator.evaluate(session)
        # "leave" matches before "every" could, and scheduled_task is wrong
        assert result.score == 0.0
        assert result.label == "Mismatch"

    @pytest.mark.asyncio
    async def test_entry_not_matched_in_sentry(self):
        """'entry' should NOT match inside 'sentry' — word boundary."""
        evaluator = TemplateAppropriatenessEvaluator()
        # "sentry" contains "entry" as substring but not as a word.
        # "notify" is a standalone word matching the notify group.
        session = _make_session(
            "notify me about sentry errors", "notification_on_event"
        )
        result = await evaluator.evaluate(session)
        # "notify" matches the notify group, not "entry" from "sentry"
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_schedule_keyword(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("every hour flash the lights", "scheduled_task")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_first_keyword_group_wins(self):
        """'turn off all lights at midnight' — 'at midnight' matches the 'time'
        group (checked before 'turn off'), so time_based_light_on is valid."""
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "turn off all lights at midnight", "time_based_light_on"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_turn_off_without_time(self):
        """Pure 'turn off' without time keywords matches the turn-off group."""
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session(
            "turn off the bedroom lights", "state_based_automation"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("TURN ON the office lights", "room_entry_light_on")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0


# =====================================================================
# Missing / empty inputs
# =====================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_missing_template_id(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on the lights")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Missing"

    @pytest.mark.asyncio
    async def test_empty_template_id(self):
        evaluator = TemplateAppropriatenessEvaluator()
        session = _make_session("turn on the lights", "")
        # Empty string is falsy, so treated as missing
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Missing"


# =====================================================================
# LLM fallback
# =====================================================================


class TestLLMFallback:
    @pytest.mark.asyncio
    async def test_fallback_yes(self):
        provider = MockProvider(
            '{"label": "Yes", "explanation": "Template matches intent."}'
        )
        evaluator = TemplateAppropriatenessEvaluator(
            llm_judge=LLMJudge(provider=provider)
        )
        # Prompt that matches no keyword group (no substring overlaps)
        session = _make_session(
            "lock the front door when it rains", "custom_automation"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_partial(self):
        provider = MockProvider(
            '{"label": "Partial", "explanation": "Somewhat appropriate."}'
        )
        evaluator = TemplateAppropriatenessEvaluator(
            llm_judge=LLMJudge(provider=provider)
        )
        session = _make_session(
            "lock the front door when it rains", "notification_on_event"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_fallback_no(self):
        provider = MockProvider(
            '{"label": "No", "explanation": "Wrong template."}'
        )
        evaluator = TemplateAppropriatenessEvaluator(
            llm_judge=LLMJudge(provider=provider)
        )
        session = _make_session(
            "lock the front door when it rains", "notification_on_event"
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_empty_prompt_triggers_fallback(self):
        provider = MockProvider(
            '{"label": "Yes", "explanation": "OK."}'
        )
        evaluator = TemplateAppropriatenessEvaluator(
            llm_judge=LLMJudge(provider=provider)
        )
        session = _make_session("", "room_entry_light_on")
        result = await evaluator.evaluate(session)
        # Empty prompt matches no keywords -> LLM fallback
        assert provider.call_count == 1


# =====================================================================
# Evaluator properties
# =====================================================================


class TestEvaluatorProperties:
    def test_name(self):
        evaluator = TemplateAppropriatenessEvaluator()
        assert evaluator.name == "template_appropriateness"

    def test_level(self):
        evaluator = TemplateAppropriatenessEvaluator()
        assert evaluator.level == EvalLevel.PATH

    def test_scope(self):
        evaluator = TemplateAppropriatenessEvaluator()
        assert evaluator.scope == EvalScope.SESSION
