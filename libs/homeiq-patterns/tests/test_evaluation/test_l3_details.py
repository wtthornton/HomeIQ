"""
Tests for E2.S4: L3 ToolParameterAccuracy Evaluator
"""

import pytest

from homeiq_patterns.evaluation.config import (
    AgentEvalConfig,
    ParamDef,
    ParamRule,
    ToolDef,
)
from homeiq_patterns.evaluation.evaluators.l3_details import (
    ToolParameterAccuracyEvaluator,
)
from homeiq_patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvalScope,
    SessionTrace,
    ToolCall,
    UserMessage,
)


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, prompt: str) -> str:
        return self._response


def _make_config(**kwargs) -> AgentEvalConfig:
    defaults = dict(
        agent_name="test-agent",
        tools=[
            ToolDef(
                name="book_room",
                description="Book a room",
                parameters=[
                    ParamDef(name="room_id", type="integer", required=True),
                    ParamDef(
                        name="start_time",
                        type="string",
                        required=True,
                        format="HH:MM",
                    ),
                    ParamDef(
                        name="end_time",
                        type="string",
                        required=True,
                        format="HH:MM",
                    ),
                    ParamDef(
                        name="date",
                        type="string",
                        required=True,
                        format="YYYY-MM-DD",
                    ),
                    ParamDef(
                        name="capacity",
                        type="integer",
                        required=False,
                        min_value=1,
                        max_value=100,
                    ),
                ],
                required_params=["room_id", "start_time", "end_time", "date"],
            ),
        ],
        parameter_rules=[
            ParamRule(
                tool="book_room",
                param="start_time",
                extraction_type="fuzzy",
                format="HH:MM",
            ),
            ParamRule(
                tool="book_room",
                param="room_id",
                extraction_type="exact",
                valid_values=[1, 2, 3, 4, 5],
            ),
        ],
    )
    defaults.update(kwargs)
    return AgentEvalConfig(**defaults)


class TestToolParameterAccuracy:
    @pytest.mark.asyncio
    async def test_all_params_correct(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 3,
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "2026-03-15",
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"
        assert result.level == EvalLevel.DETAILS

    @pytest.mark.asyncio
    async def test_missing_required_param(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 3,
                        "start_time": "14:00",
                        # Missing end_time and date
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "missing required" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_invalid_time_format(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 3,
                        "start_time": "2:00 PM",  # Wrong format
                        "end_time": "15:00",
                        "date": "2026-03-15",
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "HH:MM" in result.explanation

    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 3,
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "03/15/2026",  # Wrong format
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0

    @pytest.mark.asyncio
    async def test_invalid_enum_value(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 99,  # Not in valid_values [1-5]
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "2026-03-15",
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "not in" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_value_below_min(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 1,
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "2026-03-15",
                        "capacity": 0,  # Below min_value=1
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "below min" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_value_above_max(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 1,
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "2026-03-15",
                        "capacity": 200,  # Above max_value=100
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "above max" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_invalid_time_values(self):
        """Hour 25 should fail even if format looks like HH:MM."""
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": 1,
                        "start_time": "25:00",  # Invalid hour
                        "end_time": "15:00",
                        "date": "2026-03-15",
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
        assert "invalid time" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_no_tool_calls(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_unknown_tool_skipped(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="unknown_tool",
                    parameters={"foo": "bar"},
                )
            ],
        )
        result = await evaluator.evaluate(session)
        # Unknown tool with no config — falls through to LLM
        # With mock returning empty, we get a result
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_fallback_no_config(self):
        """When no param rules/tools defined, uses LLM judge."""
        config = _make_config(tools=[], parameter_rules=[])
        provider = MockProvider('{"label": "Yes", "explanation": "Params OK."}')
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Book room 5 at 2pm")],
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={"room_id": 5, "start_time": "14:00"},
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_evaluator_properties(self):
        evaluator = ToolParameterAccuracyEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        assert evaluator.name == "tool_parameter_accuracy"
        assert evaluator.level == EvalLevel.DETAILS
        assert evaluator.scope == EvalScope.TOOL_CALL

    @pytest.mark.asyncio
    async def test_wrong_type_string_for_integer(self):
        config = _make_config()
        evaluator = ToolParameterAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(
                    tool_name="book_room",
                    parameters={
                        "room_id": "five",  # String instead of integer
                        "start_time": "14:00",
                        "end_time": "15:00",
                        "date": "2026-03-15",
                    },
                )
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score < 1.0
