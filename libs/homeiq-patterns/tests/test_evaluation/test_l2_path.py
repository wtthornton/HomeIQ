"""
Tests for E2.S2-S3: L2 Path Evaluators (ToolSelectionAccuracy, ToolSequenceValidator)
"""

import pytest
from homeiq_patterns.evaluation.config import AgentEvalConfig, PathRule, ToolDef
from homeiq_patterns.evaluation.evaluators.l2_path import (
    ToolSelectionAccuracyEvaluator,
    ToolSequenceValidatorEvaluator,
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

    async def complete(self, _prompt: str) -> str:
        return self._response


def _make_config(**kwargs) -> AgentEvalConfig:
    defaults = dict(
        agent_name="test-agent",
        tools=[
            ToolDef(name="search_rooms", description="Search rooms"),
            ToolDef(name="book_room", description="Book a room"),
            ToolDef(name="cancel_booking", description="Cancel booking"),
        ],
        paths=[
            PathRule(
                name="standard_booking",
                description="Search before booking",
                sequence=["search_rooms", "book_room"],
                exceptions=["User provides exact room ID directly"],
            ),
        ],
    )
    defaults.update(kwargs)
    return AgentEvalConfig(**defaults)


# =====================================================================
# ToolSelectionAccuracyEvaluator
# =====================================================================


class TestToolSelectionAccuracy:
    @pytest.mark.asyncio
    async def test_all_tools_known(self):
        config = _make_config()
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms", sequence_index=0),
                ToolCall(tool_name="book_room", sequence_index=1),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"
        assert result.level == EvalLevel.PATH

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        config = _make_config()
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms", sequence_index=0),
                ToolCall(tool_name="unknown_tool", sequence_index=1),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "No"
        assert "unknown_tool" in result.explanation

    @pytest.mark.asyncio
    async def test_all_unknown_tools(self):
        config = _make_config()
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="bad_tool_1"),
                ToolCall(tool_name="bad_tool_2"),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_no_tool_calls(self):
        config = _make_config()
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"

    @pytest.mark.asyncio
    async def test_no_tools_in_config_uses_llm(self):
        config = _make_config(tools=[])
        provider = MockProvider('{"label": "Yes", "explanation": "Correct tool."}')
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Do something")],
            tool_calls=[ToolCall(tool_name="any_tool")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"

    @pytest.mark.asyncio
    async def test_evaluator_properties(self):
        evaluator = ToolSelectionAccuracyEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        assert evaluator.name == "tool_selection_accuracy"
        assert evaluator.level == EvalLevel.PATH
        assert evaluator.scope == EvalScope.SESSION

    @pytest.mark.asyncio
    async def test_mixed_known_unknown(self):
        config = _make_config()
        evaluator = ToolSelectionAccuracyEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms"),
                ToolCall(tool_name="book_room"),
                ToolCall(tool_name="unknown_tool"),
            ],
        )
        result = await evaluator.evaluate(session)
        assert abs(result.score - 2.0 / 3.0) < 0.01
        assert result.label == "No"


# =====================================================================
# ToolSequenceValidatorEvaluator
# =====================================================================


class TestToolSequenceValidator:
    @pytest.mark.asyncio
    async def test_correct_sequence(self):
        config = _make_config()
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms", sequence_index=0),
                ToolCall(tool_name="book_room", sequence_index=1),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Correct Sequence"

    @pytest.mark.asyncio
    async def test_correct_sequence_with_extra_tools(self):
        """Extra tools between expected steps should still pass."""
        config = _make_config()
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms", sequence_index=0),
                ToolCall(tool_name="cancel_booking", sequence_index=1),
                ToolCall(tool_name="book_room", sequence_index=2),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_wrong_order(self):
        config = _make_config()
        # Exception check returns "No" — exception does NOT apply
        provider = MockProvider('{"label": "No", "explanation": "No exception."}')
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="book_room", sequence_index=0),
                ToolCall(tool_name="search_rooms", sequence_index=1),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Wrong Sequence"

    @pytest.mark.asyncio
    async def test_missing_tool_in_sequence(self):
        config = _make_config()
        provider = MockProvider('{"label": "No", "explanation": "N/A"}')
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="book_room", sequence_index=0),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert "violated" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_exception_applies(self):
        config = _make_config()
        # Exception check returns "Yes" — exception applies
        provider = MockProvider('{"label": "Yes", "explanation": "User gave room ID."}')
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Book room 42 directly")],
            tool_calls=[
                ToolCall(tool_name="book_room", parameters={"room_id": 42}),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_no_path_rules(self):
        config = _make_config(paths=[])
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[ToolCall(tool_name="anything")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_no_tool_calls_with_required_paths(self):
        config = _make_config()
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert "no tool calls" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_multiple_path_rules(self):
        config = _make_config(
            paths=[
                PathRule(
                    name="search_then_book",
                    sequence=["search_rooms", "book_room"],
                ),
                PathRule(
                    name="book_then_cancel",
                    sequence=["book_room", "cancel_booking"],
                ),
            ]
        )
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        # Satisfies first rule but not second
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="search_rooms", sequence_index=0),
                ToolCall(tool_name="book_room", sequence_index=1),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "Wrong Sequence"

    @pytest.mark.asyncio
    async def test_evaluator_properties(self):
        evaluator = ToolSequenceValidatorEvaluator(
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        assert evaluator.name == "tool_sequence_validator"
        assert evaluator.level == EvalLevel.PATH
        assert evaluator.scope == EvalScope.SESSION

    @pytest.mark.asyncio
    async def test_empty_sequence_rule_passes(self):
        config = _make_config(
            paths=[
                PathRule(name="empty_rule", sequence=[]),
            ]
        )
        evaluator = ToolSequenceValidatorEvaluator(
            config=config,
            llm_judge=LLMJudge(provider=MockProvider()),
        )
        session = SessionTrace(
            agent_name="test",
            tool_calls=[ToolCall(tool_name="anything")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
