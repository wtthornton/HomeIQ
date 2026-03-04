"""
Tests for E4.S1: Evaluation Scheduler Service

Tests the EvaluationScheduler, SessionSource protocol,
frequency-based scheduling, and manual triggers.
"""

import time
from pathlib import Path

import pytest
from homeiq_patterns.evaluation.config import ConfigLoader
from homeiq_patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
    AgentResponse,
    SessionTrace,
    ToolCall,
    UserMessage,
)
from homeiq_patterns.evaluation.registry import EvaluationRegistry
from homeiq_patterns.evaluation.scheduler import (
    EvaluationScheduler,
    InMemorySessionSource,
    _is_due,
)


class MockProvider(LLMProvider):
    async def complete(self, _prompt: str) -> str:
        return '{"label": "Yes", "explanation": "OK."}'


def _config_path(filename: str):
    return (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "homeiq_patterns"
        / "evaluation"
        / "configs"
        / filename
    )


def _make_session(agent_name: str) -> SessionTrace:
    """Create a minimal valid session for testing."""
    return SessionTrace(
        agent_name=agent_name,
        user_messages=[UserMessage(content="Test request")],
        agent_responses=[AgentResponse(content="Test response")],
        tool_calls=[
            ToolCall(
                tool_name="preview_automation_from_prompt"
                if agent_name == "ha-ai-agent"
                else "fetch_context",
                parameters={"user_prompt": "test"},
                result={"status": "ok"},
                sequence_index=0,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Frequency helper tests
# ---------------------------------------------------------------------------


class TestFrequencyChecks:
    """Test the _is_due frequency calculation."""

    def test_every_session_always_due(self):
        assert _is_due(last_run=time.time(), frequency="every_session", now=time.time())

    def test_never_run_is_due(self):
        assert _is_due(last_run=None, frequency="daily", now=time.time())

    def test_hourly_not_due_within_hour(self):
        now = time.time()
        assert not _is_due(last_run=now - 1800, frequency="hourly", now=now)

    def test_hourly_due_after_hour(self):
        now = time.time()
        assert _is_due(last_run=now - 3700, frequency="hourly", now=now)

    def test_daily_not_due_within_day(self):
        now = time.time()
        assert not _is_due(last_run=now - 43200, frequency="daily", now=now)

    def test_daily_due_after_day(self):
        now = time.time()
        assert _is_due(last_run=now - 90000, frequency="daily", now=now)

    def test_weekly_due_after_week(self):
        now = time.time()
        assert _is_due(last_run=now - 700000, frequency="weekly", now=now)

    def test_monthly_due_after_month(self):
        now = time.time()
        assert _is_due(last_run=now - 3000000, frequency="monthly", now=now)

    def test_unknown_frequency_treated_as_due(self):
        assert _is_due(last_run=time.time(), frequency="unknown_freq", now=time.time())


# ---------------------------------------------------------------------------
# InMemorySessionSource tests
# ---------------------------------------------------------------------------


class TestInMemorySessionSource:
    """Test the in-memory session source."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_sessions(self):
        source = InMemorySessionSource()
        result = await source.get_recent("test-agent", 10)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_matching_agent_sessions(self):
        source = InMemorySessionSource()
        source.add(_make_session("agent-a"))
        source.add(_make_session("agent-b"))
        source.add(_make_session("agent-a"))
        result = await source.get_recent("agent-a", 10)
        assert len(result) == 2
        assert all(s.agent_name == "agent-a" for s in result)

    @pytest.mark.asyncio
    async def test_respects_count_limit(self):
        source = InMemorySessionSource()
        source.add_many([_make_session("agent-a") for _ in range(10)])
        result = await source.get_recent("agent-a", 3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_add_many(self):
        source = InMemorySessionSource()
        sessions = [_make_session("test") for _ in range(5)]
        source.add_many(sessions)
        result = await source.get_recent("test", 10)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# EvaluationScheduler tests
# ---------------------------------------------------------------------------


class TestEvaluationScheduler:
    """Test the evaluation scheduler."""

    @pytest.fixture
    def ha_config(self):
        return ConfigLoader.load(_config_path("ha_ai_agent.yaml"))

    @pytest.fixture
    def registry(self):
        judge = LLMJudge(provider=MockProvider())
        return EvaluationRegistry(llm_judge=judge)

    def test_register_agent(self, registry, ha_config):
        source = InMemorySessionSource()
        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)
        assert "ha-ai-agent" in scheduler.registered_agents

    def test_batch_size_default(self, registry):
        scheduler = EvaluationScheduler(registry=registry)
        assert scheduler.batch_size == 20

    def test_batch_size_configurable(self, registry):
        scheduler = EvaluationScheduler(registry=registry, batch_size=10)
        assert scheduler.batch_size == 10

    def test_batch_size_minimum(self, registry):
        scheduler = EvaluationScheduler(registry=registry)
        scheduler.batch_size = -5
        assert scheduler.batch_size == 1

    @pytest.mark.asyncio
    async def test_check_and_run_with_sessions(self, registry, ha_config):
        source = InMemorySessionSource()
        source.add_many([_make_session("ha-ai-agent") for _ in range(3)])

        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        reports = await scheduler.check_and_run()
        assert "ha-ai-agent" in reports
        assert reports["ha-ai-agent"].sessions_evaluated == 3

    @pytest.mark.asyncio
    async def test_check_and_run_empty_sessions(self, registry, ha_config):
        source = InMemorySessionSource()  # No sessions
        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        reports = await scheduler.check_and_run()
        assert "ha-ai-agent" in reports
        assert reports["ha-ai-agent"].sessions_evaluated == 0

    @pytest.mark.asyncio
    async def test_manual_trigger(self, registry, ha_config):
        source = InMemorySessionSource()
        source.add_many([_make_session("ha-ai-agent") for _ in range(2)])

        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        report = await scheduler.run_agent("ha-ai-agent")
        assert report is not None
        assert report.sessions_evaluated == 2

    @pytest.mark.asyncio
    async def test_manual_trigger_unknown_agent(self, registry):
        scheduler = EvaluationScheduler(registry=registry)
        report = await scheduler.run_agent("nonexistent")
        assert report is None

    @pytest.mark.asyncio
    async def test_get_due_evaluations(self, registry, ha_config):
        source = InMemorySessionSource()
        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        due = await scheduler.get_due_evaluations()
        assert len(due) > 0
        assert all("agent" in d and "priority" in d and "metrics" in d for d in due)

    @pytest.mark.asyncio
    async def test_frequency_respected(self, registry, ha_config):
        source = InMemorySessionSource()
        source.add_many([_make_session("ha-ai-agent") for _ in range(2)])

        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        # First run — should evaluate
        reports1 = await scheduler.check_and_run()
        assert "ha-ai-agent" in reports1

        # Immediate second run — hourly metrics should NOT be due again
        # (but every_session ones will be)
        reports2 = await scheduler.check_and_run()
        assert "ha-ai-agent" in reports2  # every_session still due

    def test_get_last_run_before_and_after(self, registry, ha_config):
        source = InMemorySessionSource()
        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        # Before any run
        assert scheduler.get_last_run("ha-ai-agent", "P0") is None

    @pytest.mark.asyncio
    async def test_last_run_updated_after_check(self, registry, ha_config):
        source = InMemorySessionSource()
        source.add(_make_session("ha-ai-agent"))

        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(ha_config, session_source=source)

        await scheduler.check_and_run()
        # P0 has every_session frequency — should have a last run now
        last = scheduler.get_last_run("ha-ai-agent", "P0")
        assert last is not None

    @pytest.mark.asyncio
    async def test_batch_size_limits_sessions(self, registry, ha_config):
        source = InMemorySessionSource()
        source.add_many([_make_session("ha-ai-agent") for _ in range(50)])

        scheduler = EvaluationScheduler(registry=registry, batch_size=5)
        scheduler.register_agent(ha_config, session_source=source)

        reports = await scheduler.check_and_run()
        assert reports["ha-ai-agent"].sessions_evaluated == 5
