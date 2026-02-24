"""
Tests for E2.S1: L1 GoalSuccessRate Evaluator
"""

import pytest

from homeiq_patterns.evaluation.evaluators.l1_outcome import GoalSuccessRateEvaluator
from homeiq_patterns.evaluation.llm_judge import JudgeRubric, LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
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


class TestMetadataSuccessSignals:
    """Tests for metadata_success_signals deterministic pre-screening."""

    @pytest.mark.asyncio
    async def test_preview_success_yaml_valid(self):
        """Preview mode with pipeline_success + yaml_valid → Yes (1.0)."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on the office lights")],
            agent_responses=[AgentResponse(content="Selected template: room_entry_light_on")],
            metadata={
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": True,
                "pipeline_score": 99,
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"
        assert "preview mode" in result.explanation

    @pytest.mark.asyncio
    async def test_preview_success_yaml_invalid(self):
        """Preview mode with pipeline_success but yaml_valid=False → Partial."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="set thermostat to 72")],
            agent_responses=[AgentResponse(content="Plan created but YAML invalid")],
            metadata={
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": False,
                "pipeline_score": 60,
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_preview_low_score_falls_through(self, judge_no):
        """Preview pipeline_success=True but score < 50 and yaml_valid=False → LLM."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="do something weird")],
            agent_responses=[AgentResponse(content="Hmm...")],
            metadata={
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": False,
                "pipeline_score": 30,
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=judge_no,
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        # Falls through to LLM judge
        assert result.score == 0.0
        assert result.label == "No"

    @pytest.mark.asyncio
    async def test_deploy_success(self):
        """Deploy mode with deployment_audit.status=success → Yes (1.0)."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Automation deployed")],
            metadata={
                "execution_mode": "deploy",
                "deployment_audit": {"status": "success"},
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"
        assert "deployment_audit" in result.explanation

    @pytest.mark.asyncio
    async def test_deploy_failure(self):
        """Deploy mode with deployment_audit.status=failed → Partial (0.5)."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Deployment failed")],
            metadata={
                "execution_mode": "deploy",
                "deployment_audit": {"status": "failed"},
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_no_metadata_falls_through(self, judge_yes):
        """No metadata → falls through to LLM judge."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done!")],
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=judge_yes,
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"

    @pytest.mark.asyncio
    async def test_error_session_overrides_metadata(self):
        """Error detection takes priority over metadata signals."""
        session = SessionTrace(
            agent_name="test",
            metadata={
                "error": "Pipeline crashed",
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": True,
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "No"

    @pytest.mark.asyncio
    async def test_metadata_disabled_uses_llm(self, judge_partial):
        """metadata_success_signals=False → always uses LLM."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done!")],
            metadata={
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": True,
                "pipeline_score": 99,
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=judge_partial,
            metadata_success_signals=False,
        )
        result = await evaluator.evaluate(session)
        # LLM judge used, not metadata
        assert result.score == 0.5
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_leave_home_preview_deterministic(self):
        """The 'leave home' scenario is deterministic with metadata signals."""
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="when I leave home turn off everything")],
            agent_responses=[AgentResponse(
                content="Selected template: state_based_automation (confidence: 0.90)\n"
                        "Pipeline score: 97/100"
            )],
            metadata={
                "execution_mode": "preview",
                "pipeline_success": True,
                "yaml_valid": True,
                "pipeline_score": 97,
                "unresolved_placeholders": ["{{presence_sensor_entity}}"],
            },
        )
        evaluator = GoalSuccessRateEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
            metadata_success_signals=True,
        )
        # Run twice — must be deterministic
        result1 = await evaluator.evaluate(session)
        result2 = await evaluator.evaluate(session)
        assert result1.score == 1.0
        assert result1.label == "Yes"
        assert result1.score == result2.score
        assert result1.label == result2.label
