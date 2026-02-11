"""
Tests for E2.S1: L1 GoalSuccessRate Evaluator
"""

import pytest

from shared.patterns.evaluation.evaluators.l1_outcome import GoalSuccessRateEvaluator
from shared.patterns.evaluation.llm_judge import JudgeRubric, LLMJudge, LLMProvider
from shared.patterns.evaluation.models import (
    AgentResponse,
    EvalLevel,
    SessionTrace,
    ToolCall,
    UserMessage,
)


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, prompt: str) -> str:
        return self._response


@pytest.fixture
def judge_yes():
    provider = MockProvider('{"label": "Yes", "explanation": "Goal achieved."}')
    return LLMJudge(provider=provider)


@pytest.fixture
def judge_partial():
    provider = MockProvider('{"label": "Partial", "explanation": "Partially done."}')
    return LLMJudge(provider=provider)


@pytest.fixture
def judge_no():
    provider = MockProvider('{"label": "No", "explanation": "Goal not met."}')
    return LLMJudge(provider=provider)


class TestGoalSuccessRate:
    @pytest.mark.asyncio
    async def test_successful_goal(self, judge_yes):
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on the lights")],
            agent_responses=[AgentResponse(content="I've turned on the lights.")],
            tool_calls=[
                ToolCall(tool_name="call_service", parameters={"entity_id": "light.living"}, result={"success": True})
            ],
        )
        evaluator = GoalSuccessRateEvaluator(llm_judge=judge_yes)
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"
        assert result.level == EvalLevel.OUTCOME

    @pytest.mark.asyncio
    async def test_partial_goal(self, judge_partial):
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on all lights")],
            agent_responses=[AgentResponse(content="I turned on 2 of 3 lights.")],
        )
        evaluator = GoalSuccessRateEvaluator(llm_judge=judge_partial)
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_failed_goal(self, judge_no):
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Book a room")],
            agent_responses=[AgentResponse(content="I cannot find any rooms.")],
        )
        evaluator = GoalSuccessRateEvaluator(llm_judge=judge_no)
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "No"
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_error_session_metadata(self):
        session = SessionTrace(
            agent_name="test",
            metadata={"error": "Connection timeout"},
        )
        evaluator = GoalSuccessRateEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "No"
        assert "error" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_error_session_tool_error(self):
        session = SessionTrace(
            agent_name="test",
            tool_calls=[ToolCall(tool_name="api_call", result={"error": "500 Internal Server Error"})],
        )
        evaluator = GoalSuccessRateEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        result = await evaluator.evaluate(session)
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_goal_pattern_match(self):
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="I've successfully turned on the lights.")],
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            goal_patterns=["successfully"],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert "pattern matched" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_goal_pattern_no_match_falls_through(self, judge_no):
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Do something")],
            agent_responses=[AgentResponse(content="I tried but failed.")],
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=judge_no,
            goal_patterns=["successfully"],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0  # Fell through to LLM judge

    @pytest.mark.asyncio
    async def test_evaluator_name_and_level(self):
        evaluator = GoalSuccessRateEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "goal_success_rate"
        assert evaluator.level == EvalLevel.OUTCOME
