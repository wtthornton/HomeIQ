"""
Tests for E2.S9: L5 Safety Evaluators (Harmfulness, Stereotyping, Refusal)
"""

import pytest

from shared.patterns.evaluation.evaluators.l5_safety import (
    HarmfulnessEvaluator,
    RefusalEvaluator,
    StereotypingEvaluator,
)
from shared.patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from shared.patterns.evaluation.models import (
    AgentResponse,
    EvalLevel,
    EvalScope,
    SessionTrace,
    UserMessage,
)


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, prompt: str) -> str:
        return self._response


# ---------------------------------------------------------------------------
# HarmfulnessEvaluator
# ---------------------------------------------------------------------------


class TestHarmfulnessEvaluator:
    @pytest.mark.asyncio
    async def test_safe_response(self):
        provider = MockProvider('{"label": "Not Harmful", "explanation": "Safe content."}')
        evaluator = HarmfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="Lights are on.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Not Harmful"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_harmful_response(self):
        provider = MockProvider('{"label": "Harmful", "explanation": "Contains dangerous info."}')
        evaluator = HarmfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            agent_responses=[AgentResponse(content="harmful content")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = HarmfulnessEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "harmfulness"
        assert evaluator.level == EvalLevel.SAFETY
        assert evaluator.scope == EvalScope.RESPONSE


# ---------------------------------------------------------------------------
# StereotypingEvaluator
# ---------------------------------------------------------------------------


class TestStereotypingEvaluator:
    @pytest.mark.asyncio
    async def test_no_stereotyping(self):
        provider = MockProvider('{"label": "Not Stereotyping", "explanation": "Fair content."}')
        evaluator = StereotypingEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            agent_responses=[AgentResponse(content="Here are the results.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_stereotyping_detected(self):
        provider = MockProvider('{"label": "Stereotyping", "explanation": "Biased language."}')
        evaluator = StereotypingEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = StereotypingEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "stereotyping"
        assert evaluator.level == EvalLevel.SAFETY


# ---------------------------------------------------------------------------
# RefusalEvaluator
# ---------------------------------------------------------------------------


class TestRefusalEvaluator:
    @pytest.mark.asyncio
    async def test_no_refusal(self):
        provider = MockProvider('{"label": "No", "explanation": "Agent helped normally."}')
        evaluator = RefusalEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="Done, lights are on.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "No"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_false_refusal(self):
        provider = MockProvider('{"label": "Yes", "explanation": "Refused valid request."}')
        evaluator = RefusalEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="I can't help with that.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Yes"
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = RefusalEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "refusal"
        assert evaluator.level == EvalLevel.SAFETY
