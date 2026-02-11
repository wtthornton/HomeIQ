"""
Tests for E1.S1: SessionTrace Data Model (shared/patterns/evaluation/models.py)
"""

import json
from datetime import datetime, timezone

import pytest

from shared.patterns.evaluation.models import (
    AgentResponse,
    Alert,
    BatchReport,
    EvalLevel,
    EvalScope,
    EvaluationReport,
    EvaluationResult,
    LevelSummary,
    MetricResult,
    SessionTrace,
    SummaryMatrix,
    ToolCall,
    UserMessage,
)


# ---------------------------------------------------------------------------
# UserMessage
# ---------------------------------------------------------------------------


class TestUserMessage:
    def test_create_minimal(self):
        msg = UserMessage(content="hello")
        assert msg.content == "hello"
        assert msg.turn_index == 0
        assert isinstance(msg.timestamp, datetime)

    def test_create_with_all_fields(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        msg = UserMessage(content="test", timestamp=ts, turn_index=3)
        assert msg.timestamp == ts
        assert msg.turn_index == 3


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------


class TestToolCall:
    def test_create_minimal(self):
        tc = ToolCall(tool_name="search")
        assert tc.tool_name == "search"
        assert tc.parameters == {}
        assert tc.result is None
        assert tc.sequence_index == 0

    def test_create_with_params_and_result(self):
        tc = ToolCall(
            tool_name="book_room",
            parameters={"room_id": 42, "date": "2026-01-15"},
            result={"status": "ok"},
            sequence_index=2,
            turn_index=1,
            latency_ms=150.5,
        )
        assert tc.parameters["room_id"] == 42
        assert tc.result["status"] == "ok"
        assert tc.latency_ms == 150.5


# ---------------------------------------------------------------------------
# AgentResponse
# ---------------------------------------------------------------------------


class TestAgentResponse:
    def test_create_minimal(self):
        resp = AgentResponse(content="I found 3 options.")
        assert resp.content == "I found 3 options."
        assert resp.tool_calls_in_turn == []

    def test_with_embedded_tool_calls(self):
        tc = ToolCall(tool_name="search", parameters={"q": "room"})
        resp = AgentResponse(content="Here are results", tool_calls_in_turn=[tc])
        assert len(resp.tool_calls_in_turn) == 1
        assert resp.tool_calls_in_turn[0].tool_name == "search"


# ---------------------------------------------------------------------------
# SessionTrace
# ---------------------------------------------------------------------------


class TestSessionTrace:
    def test_create_default(self):
        trace = SessionTrace()
        assert trace.session_id  # auto-generated UUID
        assert trace.agent_name == ""
        assert trace.user_messages == []
        assert trace.agent_responses == []
        assert trace.tool_calls == []
        assert trace.metadata == {}

    def test_create_with_all_fields(self):
        trace = SessionTrace(
            agent_name="ha-ai-agent",
            model="gpt-4o",
            temperature=0.7,
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done!")],
            tool_calls=[ToolCall(tool_name="call_service", parameters={"entity_id": "light.living"})],
            metadata={"source": "api"},
        )
        assert trace.agent_name == "ha-ai-agent"
        assert trace.model == "gpt-4o"
        assert trace.temperature == 0.7
        assert len(trace.user_messages) == 1
        assert len(trace.tool_calls) == 1

    def test_to_dict_serialization(self):
        trace = SessionTrace(agent_name="test-agent")
        d = trace.to_dict()
        assert isinstance(d, dict)
        assert d["agent_name"] == "test-agent"
        # Should be JSON-serializable
        json.dumps(d)

    def test_from_dict_deserialization(self):
        original = SessionTrace(
            agent_name="test-agent",
            model="gpt-4o",
            user_messages=[UserMessage(content="hi")],
            tool_calls=[ToolCall(tool_name="search", parameters={"q": "room"})],
        )
        d = original.to_dict()
        restored = SessionTrace.from_dict(d)
        assert restored.agent_name == original.agent_name
        assert restored.model == original.model
        assert len(restored.user_messages) == 1
        assert restored.user_messages[0].content == "hi"
        assert len(restored.tool_calls) == 1

    def test_round_trip_serialization(self):
        trace = SessionTrace(
            agent_name="roundtrip",
            user_messages=[
                UserMessage(content="msg1", turn_index=0),
                UserMessage(content="msg2", turn_index=1),
            ],
            agent_responses=[
                AgentResponse(content="resp1", turn_index=0),
            ],
            tool_calls=[
                ToolCall(tool_name="tool1", parameters={"a": 1}, result="ok"),
                ToolCall(tool_name="tool2", sequence_index=1),
            ],
            metadata={"key": "value"},
        )
        restored = SessionTrace.from_dict(trace.to_dict())
        assert restored.agent_name == "roundtrip"
        assert len(restored.user_messages) == 2
        assert len(restored.tool_calls) == 2
        assert restored.metadata["key"] == "value"

    def test_unique_session_ids(self):
        t1 = SessionTrace()
        t2 = SessionTrace()
        assert t1.session_id != t2.session_id


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_eval_level_values(self):
        assert EvalLevel.OUTCOME == "L1_OUTCOME"
        assert EvalLevel.PATH == "L2_PATH"
        assert EvalLevel.DETAILS == "L3_DETAILS"
        assert EvalLevel.QUALITY == "L4_QUALITY"
        assert EvalLevel.SAFETY == "L5_SAFETY"

    def test_eval_scope_values(self):
        assert EvalScope.SESSION == "session"
        assert EvalScope.TOOL_CALL == "tool_call"
        assert EvalScope.RESPONSE == "response"

    def test_eval_level_iteration(self):
        levels = list(EvalLevel)
        assert len(levels) == 5


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------


class TestEvaluationResult:
    def test_create(self):
        result = EvaluationResult(
            evaluator_name="goal_success",
            level=EvalLevel.OUTCOME,
            score=1.0,
            label="Yes",
            explanation="Goal achieved",
            passed=True,
        )
        assert result.score == 1.0
        assert result.passed is True

    def test_score_validation_bounds(self):
        with pytest.raises(Exception):
            EvaluationResult(
                evaluator_name="test",
                level=EvalLevel.OUTCOME,
                score=1.5,  # out of range
            )

    def test_score_zero_valid(self):
        result = EvaluationResult(
            evaluator_name="test", level=EvalLevel.SAFETY, score=0.0
        )
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# SummaryMatrix / MetricResult / LevelSummary
# ---------------------------------------------------------------------------


class TestSummaryMatrix:
    def test_empty_matrix(self):
        matrix = SummaryMatrix()
        assert matrix.levels == {}

    def test_populated_matrix(self):
        matrix = SummaryMatrix(
            levels={
                EvalLevel.OUTCOME: LevelSummary(
                    metrics={
                        "goal_success_rate": MetricResult(
                            score=0.85, label="Yes", evaluations_count=10, passed=True
                        )
                    }
                ),
                EvalLevel.SAFETY: LevelSummary(
                    metrics={
                        "harmfulness": MetricResult(
                            score=1.0, label="Not Harmful", evaluations_count=10, passed=True
                        )
                    }
                ),
            }
        )
        assert len(matrix.levels) == 2
        assert matrix.levels[EvalLevel.OUTCOME].metrics["goal_success_rate"].score == 0.85


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


class TestAlert:
    def test_create(self):
        alert = Alert(
            level=EvalLevel.QUALITY,
            metric="correctness",
            threshold=0.8,
            actual=0.65,
            priority="critical",
        )
        assert alert.actual < alert.threshold


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


class TestEvaluationReport:
    def _make_report(self) -> EvaluationReport:
        return EvaluationReport(
            session_id="sess-1",
            agent_name="test-agent",
            results=[
                EvaluationResult(
                    evaluator_name="goal_success",
                    level=EvalLevel.OUTCOME,
                    score=1.0,
                    label="Yes",
                    passed=True,
                )
            ],
            summary_matrix=SummaryMatrix(
                levels={
                    EvalLevel.OUTCOME: LevelSummary(
                        metrics={
                            "goal_success": MetricResult(
                                score=1.0, label="Yes", evaluations_count=1, passed=True
                            )
                        }
                    )
                }
            ),
        )

    def test_to_dict(self):
        report = self._make_report()
        d = report.to_dict()
        assert d["session_id"] == "sess-1"
        json.dumps(d)  # must be JSON-serializable

    def test_to_markdown(self):
        report = self._make_report()
        md = report.to_markdown()
        assert "test-agent" in md
        assert "goal_success" in md
        assert "PASS" in md


# ---------------------------------------------------------------------------
# BatchReport
# ---------------------------------------------------------------------------


class TestBatchReport:
    def test_to_markdown_with_alerts(self):
        report = BatchReport(
            agent_name="test-agent",
            sessions_evaluated=5,
            total_evaluations=25,
            aggregate_scores={"correctness": 0.72, "faithfulness": 0.90},
            alerts=[
                Alert(
                    level=EvalLevel.QUALITY,
                    metric="correctness",
                    threshold=0.80,
                    actual=0.72,
                    priority="warning",
                )
            ],
        )
        md = report.to_markdown()
        assert "test-agent" in md
        assert "correctness" in md
        assert "WARNING" in md
