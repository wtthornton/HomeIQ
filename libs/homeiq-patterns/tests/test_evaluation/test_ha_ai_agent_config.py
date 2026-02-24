"""
Tests for E3.S1: HA AI Agent — Tool & Path Configuration
"""

import pytest

from homeiq_patterns.evaluation.config import ConfigLoader
from homeiq_patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
    AgentResponse,
    EvalLevel,
    SessionTrace,
    ToolCall,
    UserMessage,
)
from homeiq_patterns.evaluation.registry import EvaluationRegistry


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, prompt: str) -> str:
        return self._response


class TestHAAIAgentConfig:
    """Test that the HA AI Agent config loads and validates correctly."""

    @pytest.fixture
    def config(self):
        from pathlib import Path

        config_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "homeiq_patterns"
            / "evaluation"
            / "configs"
            / "ha_ai_agent.yaml"
        )
        return ConfigLoader.load(config_path)

    def test_config_loads(self, config):
        assert config.agent_name == "ha-ai-agent"
        assert config.model == "gpt-4o"

    def test_has_three_tools(self, config):
        assert len(config.tools) == 3
        tool_names = {t.name for t in config.tools}
        assert "preview_automation_from_prompt" in tool_names
        assert "create_automation_from_prompt" in tool_names
        assert "suggest_automation_enhancements" in tool_names

    def test_preview_tool_params(self, config):
        tool = config.get_tool("preview_automation_from_prompt")
        assert tool is not None
        assert len(tool.required_params) == 3
        assert "user_prompt" in tool.required_params
        assert "automation_yaml" in tool.required_params
        assert "alias" in tool.required_params

    def test_create_tool_params(self, config):
        tool = config.get_tool("create_automation_from_prompt")
        assert tool is not None
        assert "user_prompt" in tool.required_params
        assert "automation_yaml" in tool.required_params

    def test_suggest_tool_params(self, config):
        tool = config.get_tool("suggest_automation_enhancements")
        assert tool is not None
        assert "original_prompt" in tool.required_params

    def test_has_path_rules(self, config):
        assert len(config.paths) >= 1
        path_names = {p.name for p in config.paths}
        assert "preview_before_execute" in path_names

    def test_preview_before_execute_path(self, config):
        path = next(p for p in config.paths if p.name == "preview_before_execute")
        assert path.sequence == [
            "preview_automation_from_prompt",
            "create_automation_from_prompt",
        ]
        assert len(path.exceptions) >= 1

    def test_has_system_prompt_rules(self, config):
        assert len(config.system_prompt_rules) >= 5
        rule_names = {r.name for r in config.system_prompt_rules}
        assert "preview_before_execute" in rule_names
        assert "no_markdown_headings" in rule_names
        assert "no_hallucinated_entities" in rule_names
        assert "error_handling_compliance" in rule_names
        assert "context_injection_complete" in rule_names

    def test_preview_rule_is_path_validation(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "preview_before_execute"
        )
        assert rule.check_type == "path_validation"
        assert rule.severity == "critical"

    def test_no_markdown_rule_is_response_check(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "no_markdown_headings"
        )
        assert rule.check_type == "response_check"
        assert rule.pattern  # Should have a regex pattern

    def test_has_quality_rubrics(self, config):
        assert "correctness" in config.quality_rubrics
        assert "faithfulness" in config.quality_rubrics
        assert "helpfulness" in config.quality_rubrics
        assert "instruction_following" in config.quality_rubrics

    def test_has_safety_rubrics(self, config):
        assert "harmfulness" in config.safety_rubrics
        assert "stereotyping" in config.safety_rubrics
        assert "refusal" in config.safety_rubrics

    def test_has_thresholds(self, config):
        assert config.thresholds["goal_success_rate"] == 0.85
        assert config.thresholds["correctness"] == 0.90
        assert config.thresholds["harmfulness"] == 1.00
        assert config.thresholds["preview_before_execute"] == 0.95

    def test_has_priority_matrix(self, config):
        assert len(config.priority_matrix) >= 4
        priorities = {p.priority for p in config.priority_matrix}
        assert "P0" in priorities
        assert "P1" in priorities

    def test_parameter_rules(self, config):
        assert len(config.parameter_rules) >= 5
        tools_with_rules = {r.tool for r in config.parameter_rules}
        assert "preview_automation_from_prompt" in tools_with_rules
        assert "create_automation_from_prompt" in tools_with_rules
        assert "suggest_automation_enhancements" in tools_with_rules

    # --- E3.S2: New system prompt rules ---

    def test_error_handling_compliance_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "error_handling_compliance"
        )
        assert rule.check_type == "llm_judge"
        assert rule.severity == "critical"
        assert rule.labels == ["Pass", "Fail"]

    def test_context_injection_complete_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "context_injection_complete"
        )
        assert rule.check_type == "path_validation"
        assert rule.severity == "warning"
        assert "preview_automation_from_prompt" in rule.tool_sequence

    # --- E3.S3: Extended thresholds ---

    def test_has_extended_thresholds(self, config):
        assert config.thresholds["error_handling_compliance"] == 0.90
        assert config.thresholds["context_injection_complete"] == 0.85

    def test_has_alias_param_rules(self, config):
        alias_rules = [
            r for r in config.parameter_rules
            if r.param == "alias"
        ]
        assert len(alias_rules) >= 1


class TestHAAIAgentRegistration:
    """Test that the HA AI Agent config registers correctly in the registry."""

    @pytest.fixture
    def config(self):
        from pathlib import Path

        config_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "homeiq_patterns"
            / "evaluation"
            / "configs"
            / "ha_ai_agent.yaml"
        )
        return ConfigLoader.load(config_path)

    def test_registers_in_registry(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        assert "ha-ai-agent" in registry.registered_agents

    def test_evaluator_count(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        evaluators = registry.get_evaluators("ha-ai-agent")
        # L1 (1) + L2 (2) + L3 (1) + L4 quality (7 rubrics) +
        # L4 system prompt rules (7) + L5 safety (3) = 21
        assert len(evaluators) >= 17

    def test_evaluators_cover_all_levels(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        evaluators = registry.get_evaluators("ha-ai-agent")
        levels = {e.level for e in evaluators}
        assert EvalLevel.OUTCOME in levels
        assert EvalLevel.PATH in levels
        assert EvalLevel.DETAILS in levels
        assert EvalLevel.QUALITY in levels
        assert EvalLevel.SAFETY in levels

    @pytest.mark.asyncio
    async def test_evaluate_session(self, config):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="ha-ai-agent",
            user_messages=[
                UserMessage(content="Make office lights blink red every 15 minutes")
            ],
            agent_responses=[
                AgentResponse(content="Here's a preview of your automation...")
            ],
            tool_calls=[
                ToolCall(
                    tool_name="preview_automation_from_prompt",
                    parameters={
                        "user_prompt": "Make office lights blink red",
                        "automation_yaml": "alias: test\ntrigger: []\naction: []",
                        "alias": "Office lights blink red",
                    },
                    result={"success": True, "preview": {}},
                    sequence_index=0,
                ),
                ToolCall(
                    tool_name="create_automation_from_prompt",
                    parameters={
                        "user_prompt": "Make office lights blink red",
                        "automation_yaml": "alias: test\ntrigger: []\naction: []",
                        "alias": "Office lights blink red",
                    },
                    result={"success": True, "automation_id": "automation.test"},
                    sequence_index=1,
                ),
            ],
        )
        report = await registry.evaluate(session)
        assert report.agent_name == "ha-ai-agent"
        assert len(report.results) > 0
        # All evaluators should have run
        evaluator_names = {r.evaluator_name for r in report.results}
        assert "goal_success_rate" in evaluator_names
        assert "tool_selection_accuracy" in evaluator_names
        assert "preview_before_execute" in evaluator_names
