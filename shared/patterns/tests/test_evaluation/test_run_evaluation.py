"""
Tests for E3.S8: Baseline Evaluation Run & Report

Tests the SyntheticSessionGenerator and run_evaluation runner.
"""

import json
import tempfile
from pathlib import Path

import pytest

from shared.patterns.evaluation.config import ConfigLoader
from shared.patterns.evaluation.models import (
    AgentResponse,
    BatchReport,
    EvalLevel,
    SessionTrace,
    ToolCall,
    UserMessage,
)
from shared.patterns.evaluation.run_evaluation import (
    BaselineMockProvider,
    _compute_threshold_adjustments,
    _render_baseline_markdown,
    run_evaluation,
)
from shared.patterns.evaluation.session_generator import SyntheticSessionGenerator


def _config_path(filename: str):
    return (
        Path(__file__).resolve().parent.parent.parent
        / "evaluation"
        / "configs"
        / filename
    )


# ---------------------------------------------------------------------------
# SyntheticSessionGenerator tests
# ---------------------------------------------------------------------------


class TestSyntheticSessionGenerator:
    """Test synthetic session generation from agent configs."""

    @pytest.fixture
    def ha_config(self):
        return ConfigLoader.load(_config_path("ha_ai_agent.yaml"))

    @pytest.fixture
    def proactive_config(self):
        return ConfigLoader.load(_config_path("proactive_agent.yaml"))

    @pytest.fixture
    def automation_config(self):
        return ConfigLoader.load(_config_path("ai_automation_service.yaml"))

    @pytest.fixture
    def core_config(self):
        return ConfigLoader.load(_config_path("ai_core_service.yaml"))

    def test_generates_correct_count(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        sessions = gen.generate(count=5)
        assert len(sessions) == 5

    def test_generates_different_counts(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        assert len(gen.generate(count=3)) == 3
        assert len(gen.generate(count=10)) == 10
        assert len(gen.generate(count=1)) == 1

    def test_deterministic_with_seed(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        s1 = gen.generate(count=5, seed=42)
        s2 = gen.generate(count=5, seed=42)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.session_id == b.session_id
            assert a.agent_name == b.agent_name

    def test_different_seeds_produce_different_sessions(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        s1 = gen.generate(count=5, seed=42)
        s2 = gen.generate(count=5, seed=99)
        ids1 = {s.session_id for s in s1}
        ids2 = {s.session_id for s in s2}
        assert ids1 != ids2

    def test_sessions_have_correct_agent_name(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        for session in gen.generate(count=5):
            assert session.agent_name == "ha-ai-agent"

    def test_sessions_have_user_messages(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        for session in gen.generate(count=5):
            assert len(session.user_messages) >= 1
            assert session.user_messages[0].content

    def test_sessions_have_agent_responses(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        for session in gen.generate(count=5):
            assert len(session.agent_responses) >= 1
            assert session.agent_responses[0].content

    def test_sessions_have_tool_calls(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        for session in gen.generate(count=5):
            assert len(session.tool_calls) >= 1

    def test_happy_path_follows_path_rules(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        sessions = gen.generate(count=1, seed=42)
        session = sessions[0]  # First session is always happy_path
        tool_names = [tc.tool_name for tc in session.tool_calls]
        # Should follow the preview_before_execute path
        expected = ha_config.paths[0].sequence
        assert tool_names == expected

    def test_error_session_has_metadata(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        sessions = gen.generate(count=6, seed=42)
        # 6th session (index 5) is error_session
        error_session = sessions[5]
        assert error_session.metadata.get("error") is True

    def test_proactive_agent_sessions(self, proactive_config):
        gen = SyntheticSessionGenerator(proactive_config)
        sessions = gen.generate(count=5)
        assert all(s.agent_name == "proactive-agent" for s in sessions)
        # First session should follow context_before_suggestion path
        first = sessions[0]
        tool_names = [tc.tool_name for tc in first.tool_calls]
        expected = proactive_config.paths[0].sequence
        assert tool_names == expected

    def test_automation_service_sessions(self, automation_config):
        gen = SyntheticSessionGenerator(automation_config)
        sessions = gen.generate(count=5)
        assert all(s.agent_name == "ai-automation-service" for s in sessions)

    def test_core_service_sessions(self, core_config):
        gen = SyntheticSessionGenerator(core_config)
        sessions = gen.generate(count=5)
        assert all(s.agent_name == "ai-core-service" for s in sessions)

    def test_tool_calls_have_parameters(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        sessions = gen.generate(count=1, seed=42)
        for tc in sessions[0].tool_calls:
            assert isinstance(tc.parameters, dict)
            assert tc.latency_ms is not None

    def test_tool_calls_have_results(self, ha_config):
        gen = SyntheticSessionGenerator(ha_config)
        sessions = gen.generate(count=1, seed=42)
        for tc in sessions[0].tool_calls:
            assert tc.result is not None


# ---------------------------------------------------------------------------
# BaselineMockProvider tests
# ---------------------------------------------------------------------------


class TestBaselineMockProvider:
    """Test the deterministic mock LLM provider."""

    @pytest.mark.asyncio
    async def test_safety_returns_no(self):
        provider = BaselineMockProvider()
        resp = await provider.complete("Is this response harmful?")
        data = json.loads(resp)
        assert data["label"] == "No"

    @pytest.mark.asyncio
    async def test_goal_success_returns_varied(self):
        provider = BaselineMockProvider(seed=42)
        labels = set()
        for i in range(20):
            resp = await provider.complete(f"Was the goal successfully achieved? Case {i}")
            data = json.loads(resp)
            labels.add(data["label"])
        # Should produce at least 2 different labels
        assert len(labels) >= 2

    @pytest.mark.asyncio
    async def test_deterministic_with_seed(self):
        p1 = BaselineMockProvider(seed=42)
        p2 = BaselineMockProvider(seed=42)
        for i in range(5):
            r1 = await p1.complete(f"test prompt {i}")
            r2 = await p2.complete(f"test prompt {i}")
            assert r1 == r2


# ---------------------------------------------------------------------------
# Run evaluation tests
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    """Test the run_evaluation function."""

    @pytest.mark.asyncio
    async def test_single_agent_evaluation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports = await run_evaluation(
                agent_names=["ha-ai-agent"],
                sessions_source="synthetic",
                session_count=3,
                output_format="markdown",
                output_dir=Path(tmpdir),
                seed=42,
            )
            assert "ha-ai-agent" in reports
            report = reports["ha-ai-agent"]
            assert report.sessions_evaluated == 3
            assert report.total_evaluations > 0

    @pytest.mark.asyncio
    async def test_all_agents_evaluation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports = await run_evaluation(
                agent_names=["all"],
                sessions_source="synthetic",
                session_count=2,
                output_format="markdown",
                output_dir=Path(tmpdir),
                seed=42,
            )
            assert len(reports) == 4
            assert "ha-ai-agent" in reports
            assert "proactive-agent" in reports
            assert "ai-automation-service" in reports
            assert "ai-core-service" in reports

    @pytest.mark.asyncio
    async def test_markdown_report_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            await run_evaluation(
                agent_names=["ha-ai-agent"],
                sessions_source="synthetic",
                session_count=2,
                output_format="markdown",
                output_dir=Path(tmpdir),
            )
            md_files = list(Path(tmpdir).glob("*.md"))
            assert len(md_files) == 1
            content = md_files[0].read_text()
            assert "# Baseline Evaluation Report" in content
            assert "ha-ai-agent" in content

    @pytest.mark.asyncio
    async def test_json_report_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            await run_evaluation(
                agent_names=["ha-ai-agent"],
                sessions_source="synthetic",
                session_count=2,
                output_format="json",
                output_dir=Path(tmpdir),
            )
            json_files = list(Path(tmpdir).glob("*.json"))
            assert len(json_files) == 1
            data = json.loads(json_files[0].read_text())
            assert data["agent_name"] == "ha-ai-agent"

    @pytest.mark.asyncio
    async def test_json_session_file_loading(self):
        """Test loading sessions from a JSON file."""
        # Create a JSON file with a session
        session = SessionTrace(
            agent_name="ha-ai-agent",
            user_messages=[UserMessage(content="Test")],
            agent_responses=[AgentResponse(content="Response")],
            tool_calls=[
                ToolCall(
                    tool_name="preview_automation_from_prompt",
                    parameters={"user_prompt": "test", "automation_yaml": "alias: test", "alias": "test"},
                    result={"preview_id": "p1"},
                )
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "sessions.json"
            session_file.write_text(json.dumps([session.to_dict()], default=str))
            reports = await run_evaluation(
                agent_names=["ha-ai-agent"],
                sessions_source=str(session_file),
                session_count=10,
                output_dir=Path(tmpdir),
            )
            assert "ha-ai-agent" in reports
            assert reports["ha-ai-agent"].sessions_evaluated == 1

    @pytest.mark.asyncio
    async def test_reports_have_aggregate_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports = await run_evaluation(
                agent_names=["ha-ai-agent"],
                sessions_source="synthetic",
                session_count=3,
                output_dir=Path(tmpdir),
            )
            report = reports["ha-ai-agent"]
            assert len(report.aggregate_scores) > 0

    @pytest.mark.asyncio
    async def test_unknown_agent_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports = await run_evaluation(
                agent_names=["nonexistent-agent"],
                sessions_source="synthetic",
                output_dir=Path(tmpdir),
            )
            assert len(reports) == 0


# ---------------------------------------------------------------------------
# Report rendering tests
# ---------------------------------------------------------------------------


class TestReportRendering:
    """Test baseline report markdown rendering."""

    def test_render_baseline_markdown_has_sections(self):
        config = ConfigLoader.load(_config_path("ha_ai_agent.yaml"))
        report = BatchReport(
            agent_name="ha-ai-agent",
            sessions_evaluated=3,
            total_evaluations=30,
            aggregate_scores={"goal_success_rate": 0.75, "correctness": 0.90},
        )
        md = _render_baseline_markdown(report, config)
        assert "# Baseline Evaluation Report" in md
        assert "Agent Configuration Summary" in md
        assert "Top 3 Lowest-Scoring Evaluators" in md
        assert "Recommended Threshold Adjustments" in md

    def test_compute_threshold_adjustments(self):
        config = ConfigLoader.load(_config_path("ha_ai_agent.yaml"))
        report = BatchReport(
            agent_name="ha-ai-agent",
            aggregate_scores={
                "goal_success_rate": 0.70,  # Below 0.85 threshold
                "correctness": 0.95,  # Above 0.90 threshold
            },
        )
        adjustments = _compute_threshold_adjustments(report, config)
        assert len(adjustments) >= 1
        goal_adj = next(a for a in adjustments if a["metric"] == "goal_success_rate")
        assert goal_adj["current"] == 0.85
        assert goal_adj["baseline"] == 0.70
        assert goal_adj["recommended"] < goal_adj["current"]
