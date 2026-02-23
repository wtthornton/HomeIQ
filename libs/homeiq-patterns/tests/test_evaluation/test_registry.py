"""
Tests for E1.S7: EvaluationRegistry + Pipeline
"""

import pytest

from shared.patterns.evaluation.config import (
    AgentEvalConfig,
    ParamDef,
    ParamRule,
    PathRule,
    ToolDef,
)
from shared.patterns.evaluation.evaluators.l1_outcome import GoalSuccessRateEvaluator
from shared.patterns.evaluation.evaluators.l2_path import (
    ToolSelectionAccuracyEvaluator,
    ToolSequenceValidatorEvaluator,
)
from shared.patterns.evaluation.evaluators.l2_template_match import (
    TemplateAppropriatenessEvaluator,
)
from shared.patterns.evaluation.evaluators.l3_details import ToolParameterAccuracyEvaluator
from shared.patterns.evaluation.evaluators.l3_entity_resolution import (
    EntityResolutionEvaluator,
)
from shared.patterns.evaluation.evaluators.l3_yaml_completeness import (
    YAMLCompletenessEvaluator,
)
from shared.patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from shared.patterns.evaluation.models import (
    AgentResponse,
    EvalLevel,
    SessionTrace,
    ToolCall,
    UserMessage,
)
from shared.patterns.evaluation.registry import EvaluationRegistry


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, prompt: str) -> str:
        return self._response


def _make_full_config() -> AgentEvalConfig:
    return AgentEvalConfig(
        agent_name="test-agent",
        model="gpt-4o",
        tools=[
            ToolDef(
                name="search_rooms",
                description="Search for rooms",
                parameters=[
                    ParamDef(name="date", type="string", format="YYYY-MM-DD"),
                ],
                required_params=["date"],
            ),
            ToolDef(
                name="book_room",
                description="Book a room",
                parameters=[
                    ParamDef(name="room_id", type="integer", required=True),
                    ParamDef(name="start_time", type="string", format="HH:MM"),
                ],
                required_params=["room_id", "start_time"],
            ),
        ],
        paths=[
            PathRule(
                name="standard_booking",
                sequence=["search_rooms", "book_room"],
            ),
        ],
        parameter_rules=[
            ParamRule(tool="book_room", param="room_id", extraction_type="exact"),
        ],
        quality_rubrics=["correctness", "faithfulness", "coherence"],
        safety_rubrics=["harmfulness", "stereotyping", "refusal"],
        thresholds={
            "goal_success_rate": 0.80,
            "correctness": 0.85,
            "harmfulness": 1.00,
        },
    )


def _make_session() -> SessionTrace:
    return SessionTrace(
        agent_name="test-agent",
        user_messages=[UserMessage(content="Search for rooms tomorrow and book room 3 at 2pm")],
        agent_responses=[AgentResponse(content="I found rooms and booked room 3 at 14:00.")],
        tool_calls=[
            ToolCall(
                tool_name="search_rooms",
                parameters={"date": "2026-03-15"},
                result={"rooms": [{"id": 3, "name": "Room 3"}]},
                sequence_index=0,
            ),
            ToolCall(
                tool_name="book_room",
                parameters={"room_id": 3, "start_time": "14:00"},
                result={"success": True},
                sequence_index=1,
            ),
        ],
    )


class TestEvaluationRegistry:
    def test_register_agent(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()

        registry.register_agent(config)
        assert "test-agent" in registry.registered_agents

    def test_register_multiple_agents(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)

        config1 = AgentEvalConfig(agent_name="agent-1")
        config2 = AgentEvalConfig(agent_name="agent-2")

        registry.register_agent(config1)
        registry.register_agent(config2)

        assert len(registry.registered_agents) == 2
        assert "agent-1" in registry.registered_agents
        assert "agent-2" in registry.registered_agents

    def test_get_evaluators(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()

        registry.register_agent(config)
        evaluators = registry.get_evaluators("test-agent")

        # Should have: L1 (goal), L2 (selection + sequence + template_match),
        # L3 (params + yaml_completeness + entity_resolution),
        # L4 (correctness + faithfulness + coherence), L5 (harm + stereo + refusal)
        assert len(evaluators) == 13

    def test_get_evaluators_unknown_agent(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        with pytest.raises(KeyError, match="not registered"):
            registry.get_evaluators("unknown")

    def test_evaluator_types(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()
        registry.register_agent(config)
        evaluators = registry.get_evaluators("test-agent")

        evaluator_types = {type(e) for e in evaluators}
        assert GoalSuccessRateEvaluator in evaluator_types
        assert ToolSelectionAccuracyEvaluator in evaluator_types
        assert ToolSequenceValidatorEvaluator in evaluator_types
        assert TemplateAppropriatenessEvaluator in evaluator_types
        assert ToolParameterAccuracyEvaluator in evaluator_types
        assert YAMLCompletenessEvaluator in evaluator_types
        assert EntityResolutionEvaluator in evaluator_types

    def test_minimal_config_has_goal_and_deterministic_l3(self):
        """A config with no tools/paths/rubrics gets L1 + always-on L3 evaluators."""
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = AgentEvalConfig(agent_name="minimal")
        registry.register_agent(config)

        evaluators = registry.get_evaluators("minimal")
        # L1 (goal) + L3 (yaml_completeness + entity_resolution)
        assert len(evaluators) == 3
        names = {e.name for e in evaluators}
        assert "goal_success_rate" in names
        assert "yaml_completeness" in names
        assert "entity_resolution" in names

    def test_tools_only_gets_l2_l3(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = AgentEvalConfig(
            agent_name="tools-only",
            tools=[ToolDef(name="search")],
        )
        registry.register_agent(config)

        evaluators = registry.get_evaluators("tools-only")
        names = {e.name for e in evaluators}
        assert "goal_success_rate" in names
        assert "tool_selection_accuracy" in names
        assert "tool_parameter_accuracy" in names

    @pytest.mark.asyncio
    async def test_evaluate_session(self):
        provider = MockProvider('{"label": "Yes", "explanation": "All good."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()
        registry.register_agent(config)

        session = _make_session()
        report = await registry.evaluate(session)

        assert report.session_id == session.session_id
        assert report.agent_name == "test-agent"
        assert len(report.results) > 0

    @pytest.mark.asyncio
    async def test_evaluate_unknown_agent(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)

        session = SessionTrace(agent_name="unknown")
        with pytest.raises(KeyError, match="not registered"):
            await registry.evaluate(session)

    @pytest.mark.asyncio
    async def test_evaluate_batch(self):
        provider = MockProvider('{"label": "Yes", "explanation": "All good."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()
        registry.register_agent(config)

        sessions = [_make_session(), _make_session()]
        batch = await registry.evaluate_batch(sessions)

        assert batch.sessions_evaluated == 2
        assert len(batch.reports) == 2

    @pytest.mark.asyncio
    async def test_evaluate_batch_empty(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        batch = await registry.evaluate_batch([])
        assert batch.sessions_evaluated == 0

    @pytest.mark.asyncio
    async def test_evaluate_report_has_results_per_level(self):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = _make_full_config()
        registry.register_agent(config)

        session = _make_session()
        report = await registry.evaluate(session)

        # Check that results span multiple levels
        levels_seen = {r.level for r in report.results}
        assert EvalLevel.OUTCOME in levels_seen
        assert EvalLevel.PATH in levels_seen
        assert EvalLevel.DETAILS in levels_seen
        assert EvalLevel.QUALITY in levels_seen
        assert EvalLevel.SAFETY in levels_seen

    def test_unknown_quality_rubric_skipped(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        config = AgentEvalConfig(
            agent_name="test",
            quality_rubrics=["correctness", "unknown_rubric"],
        )
        registry.register_agent(config)
        evaluators = registry.get_evaluators("test")
        names = {e.name for e in evaluators}
        assert "correctness" in names
        # unknown_rubric should be skipped with a warning
        assert "unknown_rubric" not in names


# =====================================================================
# Enhancement A: Preview-mode evaluator skipping
# =====================================================================


class TestPreviewModeSkipping:
    """Deploy-dependent evaluators should be skipped in preview mode."""

    @staticmethod
    def _make_config_with_deploy_rules() -> AgentEvalConfig:
        """Config that includes system_prompt_rules with deploy-dependent names."""
        from shared.patterns.evaluation.config import PromptRule

        return AgentEvalConfig(
            agent_name="test-agent",
            tools=[
                ToolDef(name="create_plan"),
                ToolDef(name="validate_plan"),
                ToolDef(name="compile_yaml"),
            ],
            paths=[
                PathRule(
                    name="preview_path",
                    sequence=["create_plan", "validate_plan", "compile_yaml"],
                ),
            ],
            quality_rubrics=["correctness"],
            system_prompt_rules=[
                PromptRule(
                    name="validation_before_deploy",
                    description="Validate before deploying",
                    check_type="path_validation",
                    tool_sequence=["validate_plan"],
                ),
                PromptRule(
                    name="post_deploy_verification",
                    description="Verify after deploy",
                    check_type="path_validation",
                    tool_sequence=["verify_deployment"],
                ),
                PromptRule(
                    name="audit_trail_complete",
                    description="Audit trail present",
                    check_type="llm_judge",
                ),
                PromptRule(
                    name="no_direct_yaml_from_llm",
                    description="No raw YAML in response",
                    check_type="llm_judge",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_preview_mode_skips_deploy_evaluators(self):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = self._make_config_with_deploy_rules()
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="test-agent",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done.")],
            tool_calls=[
                ToolCall(tool_name="create_plan", sequence_index=0),
                ToolCall(tool_name="validate_plan", sequence_index=1),
                ToolCall(tool_name="compile_yaml", sequence_index=2),
            ],
            metadata={"execution_mode": "preview"},
        )
        report = await registry.evaluate(session)
        result_names = {r.evaluator_name for r in report.results}

        # Deploy-dependent evaluators should be excluded
        assert "validation_before_deploy" not in result_names
        assert "post_deploy_verification" not in result_names
        assert "audit_trail_complete" not in result_names

        # Non-deploy evaluators should still run
        assert "no_direct_yaml_from_llm" in result_names
        assert "correctness" in result_names

    @pytest.mark.asyncio
    async def test_deploy_mode_includes_all_evaluators(self):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = self._make_config_with_deploy_rules()
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="test-agent",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done.")],
            tool_calls=[
                ToolCall(tool_name="create_plan", sequence_index=0),
                ToolCall(tool_name="validate_plan", sequence_index=1),
                ToolCall(tool_name="compile_yaml", sequence_index=2),
            ],
            metadata={"execution_mode": "deploy"},
        )
        report = await registry.evaluate(session)
        result_names = {r.evaluator_name for r in report.results}

        # All evaluators should run in deploy mode
        assert "validation_before_deploy" in result_names
        assert "post_deploy_verification" in result_names
        assert "audit_trail_complete" in result_names

    @pytest.mark.asyncio
    async def test_no_mode_includes_all_evaluators(self):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        config = self._make_config_with_deploy_rules()
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="test-agent",
            user_messages=[UserMessage(content="turn on lights")],
            agent_responses=[AgentResponse(content="Done.")],
            tool_calls=[
                ToolCall(tool_name="create_plan", sequence_index=0),
            ],
        )
        report = await registry.evaluate(session)
        result_names = {r.evaluator_name for r in report.results}

        # Without execution_mode, all evaluators should run
        assert "validation_before_deploy" in result_names
        assert "post_deploy_verification" in result_names
        assert "audit_trail_complete" in result_names
