"""
Tests for E3.S5-S7: Agent-Specific Evaluation Configurations
- Proactive Agent (E3.S5)
- AI Automation Service (E3.S6)
- AI Core Service (E3.S7)
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


def _config_path(filename: str):
    from pathlib import Path

    return (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "homeiq_patterns"
        / "evaluation"
        / "configs"
        / filename
    )


# ---------------------------------------------------------------------------
# Proactive Agent Config (E3.S5)
# ---------------------------------------------------------------------------


class TestProactiveAgentConfig:
    """Test that the Proactive Agent config loads and validates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("proactive_agent.yaml"))

    def test_config_loads(self, config):
        assert config.agent_name == "proactive-agent"
        assert config.model == "gpt-4o-mini"

    def test_has_tools(self, config):
        assert len(config.tools) == 5
        tool_names = {t.name for t in config.tools}
        assert "fetch_context" in tool_names
        assert "analyze_context" in tool_names
        assert "generate_prompt" in tool_names
        assert "create_suggestion" in tool_names
        assert "send_to_ha_agent" in tool_names

    def test_fetch_context_tool(self, config):
        tool = config.get_tool("fetch_context")
        assert tool is not None
        param_names = {p.name for p in tool.parameters}
        assert "context_types" in param_names

    def test_create_suggestion_tool(self, config):
        tool = config.get_tool("create_suggestion")
        assert tool is not None
        assert "prompt" in tool.required_params
        assert "context_type" in tool.required_params
        assert "quality_score" in tool.required_params

    def test_has_path_rules(self, config):
        assert len(config.paths) >= 2
        path_names = {p.name for p in config.paths}
        assert "context_before_suggestion" in path_names
        assert "suggestion_before_send" in path_names

    def test_context_before_suggestion_path(self, config):
        path = next(p for p in config.paths if p.name == "context_before_suggestion")
        assert path.sequence == [
            "fetch_context",
            "analyze_context",
            "generate_prompt",
            "create_suggestion",
        ]

    def test_has_system_prompt_rules(self, config):
        assert len(config.system_prompt_rules) >= 4
        rule_names = {r.name for r in config.system_prompt_rules}
        assert "suggestion_relevance" in rule_names
        assert "device_validation" in rule_names
        assert "no_hardcoded_times" in rule_names

    def test_device_validation_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "device_validation"
        )
        assert rule.check_type == "llm_judge"
        assert rule.severity == "critical"

    def test_no_hardcoded_times_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "no_hardcoded_times"
        )
        assert rule.check_type == "response_check"
        assert rule.pattern  # Has regex pattern

    def test_has_quality_rubrics(self, config):
        assert "correctness" in config.quality_rubrics
        assert "helpfulness" in config.quality_rubrics
        assert "response_relevance" in config.quality_rubrics

    def test_has_safety_rubrics(self, config):
        assert "harmfulness" in config.safety_rubrics

    def test_has_thresholds(self, config):
        assert config.thresholds["goal_success_rate"] == 0.80
        assert config.thresholds["device_validation"] == 0.95
        assert config.thresholds["harmfulness"] == 1.00

    def test_has_parameter_rules(self, config):
        assert len(config.parameter_rules) >= 2
        tools_with_rules = {r.tool for r in config.parameter_rules}
        assert "create_suggestion" in tools_with_rules

    def test_has_priority_matrix(self, config):
        assert len(config.priority_matrix) >= 4
        priorities = {p.priority for p in config.priority_matrix}
        assert "P0" in priorities


class TestProactiveAgentRegistration:
    """Test Proactive Agent registers and evaluates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("proactive_agent.yaml"))

    def test_registers_in_registry(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        assert "proactive-agent" in registry.registered_agents

    def test_evaluators_cover_all_levels(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        evaluators = registry.get_evaluators("proactive-agent")
        levels = {e.level for e in evaluators}
        assert EvalLevel.OUTCOME in levels
        assert EvalLevel.PATH in levels
        assert EvalLevel.QUALITY in levels
        assert EvalLevel.SAFETY in levels

    @pytest.mark.asyncio
    async def test_evaluate_session(self, config):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="proactive-agent",
            user_messages=[UserMessage(content="Generate suggestions")],
            agent_responses=[
                AgentResponse(content="Found 2 weather-based suggestions")
            ],
            tool_calls=[
                ToolCall(
                    tool_name="fetch_context",
                    parameters={"context_types": ["weather"]},
                    result={"weather": {"temp": 85}},
                    sequence_index=0,
                ),
                ToolCall(
                    tool_name="analyze_context",
                    parameters={"context_data": {}},
                    result={"insights": ["high_temp"]},
                    sequence_index=1,
                ),
                ToolCall(
                    tool_name="generate_prompt",
                    parameters={"analysis_result": {}, "device_inventory": []},
                    result={"prompt": "Pre-cool your home"},
                    sequence_index=2,
                ),
                ToolCall(
                    tool_name="create_suggestion",
                    parameters={
                        "prompt": "Pre-cool your home",
                        "context_type": "weather",
                        "quality_score": 0.85,
                    },
                    result={"suggestion_id": "abc123"},
                    sequence_index=3,
                ),
            ],
        )
        report = await registry.evaluate(session)
        assert report.agent_name == "proactive-agent"
        assert len(report.results) > 0


# ---------------------------------------------------------------------------
# AI Automation Service Config (E3.S6)
# ---------------------------------------------------------------------------


class TestAIAutomationServiceConfig:
    """Test that the AI Automation Service config loads and validates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("ai_automation_service.yaml"))

    def test_config_loads(self, config):
        assert config.agent_name == "ai-automation-service"
        assert config.model == "gpt-4o-mini"

    def test_has_tools(self, config):
        assert len(config.tools) >= 7
        tool_names = {t.name for t in config.tools}
        assert "create_plan" in tool_names
        assert "validate_plan" in tool_names
        assert "compile_yaml" in tool_names
        assert "deploy_automation" in tool_names
        assert "verify_deployment" in tool_names
        assert "rollback_automation" in tool_names
        assert "validate_yaml" in tool_names

    def test_create_plan_tool(self, config):
        tool = config.get_tool("create_plan")
        assert tool is not None
        assert "user_text" in tool.required_params

    def test_deploy_tool(self, config):
        tool = config.get_tool("deploy_automation")
        assert tool is not None
        assert "compiled_id" in tool.required_params
        assert "approved_by" in tool.required_params

    def test_has_path_rules(self, config):
        assert len(config.paths) >= 3
        path_names = {p.name for p in config.paths}
        assert "validate_before_deploy" in path_names
        assert "verify_after_deploy" in path_names

    def test_full_pipeline_path(self, config):
        path = next(
            p for p in config.paths if p.name == "plan_validate_compile_deploy"
        )
        assert path.sequence == [
            "create_plan",
            "validate_plan",
            "compile_yaml",
            "deploy_automation",
            "verify_deployment",
        ]

    def test_has_system_prompt_rules(self, config):
        assert len(config.system_prompt_rules) >= 4
        rule_names = {r.name for r in config.system_prompt_rules}
        assert "validation_before_deploy" in rule_names
        assert "post_deploy_verification" in rule_names
        assert "no_direct_yaml_from_llm" in rule_names
        assert "yaml_safety_check" in rule_names

    def test_validation_before_deploy_rule(self, config):
        rule = next(
            r
            for r in config.system_prompt_rules
            if r.name == "validation_before_deploy"
        )
        assert rule.check_type == "path_validation"
        assert rule.severity == "critical"

    def test_yaml_safety_check_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "yaml_safety_check"
        )
        assert rule.check_type == "response_check"
        assert rule.severity == "critical"
        assert rule.pattern  # Has regex pattern

    def test_has_thresholds(self, config):
        assert config.thresholds["goal_success_rate"] == 0.90
        assert config.thresholds["validation_before_deploy"] == 1.00
        assert config.thresholds["yaml_safety_check"] == 1.00
        assert config.thresholds["harmfulness"] == 1.00

    def test_has_quality_rubrics(self, config):
        assert "correctness" in config.quality_rubrics
        assert "instruction_following" in config.quality_rubrics

    def test_has_parameter_rules(self, config):
        assert len(config.parameter_rules) >= 3
        tools_with_rules = {r.tool for r in config.parameter_rules}
        assert "rollback_automation" in tools_with_rules

    def test_has_priority_matrix(self, config):
        assert len(config.priority_matrix) >= 5
        priorities = {p.priority for p in config.priority_matrix}
        assert "P0" in priorities


class TestAIAutomationServiceRegistration:
    """Test AI Automation Service registers and evaluates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("ai_automation_service.yaml"))

    def test_registers_in_registry(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        assert "ai-automation-service" in registry.registered_agents

    def test_evaluators_cover_key_levels(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        evaluators = registry.get_evaluators("ai-automation-service")
        levels = {e.level for e in evaluators}
        assert EvalLevel.OUTCOME in levels
        assert EvalLevel.PATH in levels
        assert EvalLevel.QUALITY in levels
        assert EvalLevel.SAFETY in levels

    @pytest.mark.asyncio
    async def test_evaluate_session(self, config):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="ai-automation-service",
            user_messages=[UserMessage(content="Deploy automation")],
            agent_responses=[AgentResponse(content="Automation deployed.")],
            tool_calls=[
                ToolCall(
                    tool_name="create_plan",
                    parameters={"user_text": "Turn on lights at sunset"},
                    result={"plan_id": "p1", "template_id": "t1"},
                    sequence_index=0,
                ),
                ToolCall(
                    tool_name="validate_plan",
                    parameters={"plan_id": "p1", "template_id": "t1",
                                "template_version": "1.0", "parameters": {}},
                    result={"valid": True},
                    sequence_index=1,
                ),
                ToolCall(
                    tool_name="compile_yaml",
                    parameters={"plan_id": "p1", "template_id": "t1",
                                "template_version": "1.0", "parameters": {}},
                    result={"compiled_id": "c1", "yaml": "alias: test"},
                    sequence_index=2,
                ),
                ToolCall(
                    tool_name="deploy_automation",
                    parameters={"compiled_id": "c1", "approved_by": "user"},
                    result={"deployment_id": "d1", "status": "deployed"},
                    sequence_index=3,
                ),
                ToolCall(
                    tool_name="verify_deployment",
                    parameters={"deployment_id": "d1"},
                    result={"success": True, "state": "on"},
                    sequence_index=4,
                ),
            ],
        )
        report = await registry.evaluate(session)
        assert report.agent_name == "ai-automation-service"
        assert len(report.results) > 0


# ---------------------------------------------------------------------------
# AI Core Service Config (E3.S7)
# ---------------------------------------------------------------------------


class TestAICoreServiceConfig:
    """Test that the AI Core Service config loads and validates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("ai_core_service.yaml"))

    def test_config_loads(self, config):
        assert config.agent_name == "ai-core-service"
        assert config.model == "gpt-4o-mini"

    def test_has_tools(self, config):
        assert len(config.tools) == 5
        tool_names = {t.name for t in config.tools}
        assert "generate_embeddings" in tool_names
        assert "classify_pattern" in tool_names
        assert "cluster_data" in tool_names
        assert "detect_anomalies" in tool_names
        assert "generate_suggestions" in tool_names

    def test_generate_embeddings_tool(self, config):
        tool = config.get_tool("generate_embeddings")
        assert tool is not None
        assert "texts" in tool.required_params

    def test_generate_suggestions_tool(self, config):
        tool = config.get_tool("generate_suggestions")
        assert tool is not None
        assert "context" in tool.required_params
        assert "suggestion_type" in tool.required_params

    def test_has_path_rules(self, config):
        assert len(config.paths) >= 2
        path_names = {p.name for p in config.paths}
        assert "embed_before_cluster" in path_names
        assert "embed_before_anomaly" in path_names

    def test_embed_before_cluster_path(self, config):
        path = next(p for p in config.paths if p.name == "embed_before_cluster")
        assert path.sequence == ["generate_embeddings", "cluster_data"]

    def test_has_system_prompt_rules(self, config):
        assert len(config.system_prompt_rules) >= 3
        rule_names = {r.name for r in config.system_prompt_rules}
        assert "context_sanitization" in rule_names
        assert "graceful_degradation" in rule_names

    def test_context_sanitization_rule(self, config):
        rule = next(
            r for r in config.system_prompt_rules if r.name == "context_sanitization"
        )
        assert rule.check_type == "llm_judge"
        assert rule.severity == "critical"

    def test_has_quality_rubrics(self, config):
        assert "correctness" in config.quality_rubrics
        assert "helpfulness" in config.quality_rubrics
        assert "response_relevance" in config.quality_rubrics

    def test_has_safety_rubrics(self, config):
        assert "harmfulness" in config.safety_rubrics

    def test_has_thresholds(self, config):
        assert config.thresholds["context_sanitization"] == 1.00
        assert config.thresholds["harmfulness"] == 1.00
        assert config.thresholds["goal_success_rate"] == 0.85

    def test_has_parameter_rules(self, config):
        assert len(config.parameter_rules) >= 2
        tools_with_rules = {r.tool for r in config.parameter_rules}
        assert "generate_suggestions" in tools_with_rules

    def test_has_priority_matrix(self, config):
        assert len(config.priority_matrix) >= 4
        priorities = {p.priority for p in config.priority_matrix}
        assert "P0" in priorities


class TestAICoreServiceRegistration:
    """Test AI Core Service registers and evaluates correctly."""

    @pytest.fixture
    def config(self):
        return ConfigLoader.load(_config_path("ai_core_service.yaml"))

    def test_registers_in_registry(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        assert "ai-core-service" in registry.registered_agents

    def test_evaluators_cover_key_levels(self, config):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)
        evaluators = registry.get_evaluators("ai-core-service")
        levels = {e.level for e in evaluators}
        assert EvalLevel.OUTCOME in levels
        assert EvalLevel.PATH in levels
        assert EvalLevel.QUALITY in levels
        assert EvalLevel.SAFETY in levels

    @pytest.mark.asyncio
    async def test_evaluate_session(self, config):
        provider = MockProvider('{"label": "Yes", "explanation": "OK."}')
        judge = LLMJudge(provider=provider)
        registry = EvaluationRegistry(llm_judge=judge)
        registry.register_agent(config)

        session = SessionTrace(
            agent_name="ai-core-service",
            user_messages=[UserMessage(content="Analyze patterns")],
            agent_responses=[AgentResponse(content="Found 3 patterns.")],
            tool_calls=[
                ToolCall(
                    tool_name="generate_embeddings",
                    parameters={"texts": ["light on", "light off"]},
                    result={"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
                    sequence_index=0,
                ),
                ToolCall(
                    tool_name="cluster_data",
                    parameters={"data": [[0.1, 0.2], [0.3, 0.4]]},
                    result={"labels": [0, 1], "n_clusters": 2},
                    sequence_index=1,
                ),
            ],
        )
        report = await registry.evaluate(session)
        assert report.agent_name == "ai-core-service"
        assert len(report.results) > 0


# ---------------------------------------------------------------------------
# Multi-agent registration test
# ---------------------------------------------------------------------------


class TestMultiAgentRegistration:
    """Test that all 4 agents can be registered in a single registry."""

    def test_register_all_agents(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)

        for filename in [
            "ha_ai_agent.yaml",
            "proactive_agent.yaml",
            "ai_automation_service.yaml",
            "ai_core_service.yaml",
        ]:
            config = ConfigLoader.load(_config_path(filename))
            registry.register_agent(config)

        assert len(registry.registered_agents) == 4
        assert "ha-ai-agent" in registry.registered_agents
        assert "proactive-agent" in registry.registered_agents
        assert "ai-automation-service" in registry.registered_agents
        assert "ai-core-service" in registry.registered_agents

    def test_each_agent_has_evaluators(self):
        judge = LLMJudge(provider=MockProvider())
        registry = EvaluationRegistry(llm_judge=judge)

        for filename in [
            "ha_ai_agent.yaml",
            "proactive_agent.yaml",
            "ai_automation_service.yaml",
            "ai_core_service.yaml",
        ]:
            config = ConfigLoader.load(_config_path(filename))
            registry.register_agent(config)

        for agent_name in registry.registered_agents:
            evaluators = registry.get_evaluators(agent_name)
            assert len(evaluators) >= 10, f"{agent_name} has too few evaluators"
