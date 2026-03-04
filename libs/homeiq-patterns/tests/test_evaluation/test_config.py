"""
Tests for E1.S6: AgentEvalConfig YAML Schema & Loader
"""

import pytest
from homeiq_patterns.evaluation.config import (
    AgentEvalConfig,
    ConfigLoader,
    ParamDef,
    ParamRule,
    PathRule,
    PromptRule,
    ToolDef,
)

# ---------------------------------------------------------------------------
# Tests: AgentEvalConfig model
# ---------------------------------------------------------------------------


class TestAgentEvalConfig:
    def test_create_minimal(self):
        config = AgentEvalConfig(agent_name="test")
        assert config.agent_name == "test"
        assert config.tools == []
        assert config.thresholds == {}

    def test_create_full(self):
        config = AgentEvalConfig(
            agent_name="ha-ai-agent",
            model="gpt-4o",
            tools=[
                ToolDef(
                    name="call_service",
                    parameters=[
                        ParamDef(name="entity_id", type="string", required=True),
                    ],
                    required_params=["entity_id"],
                )
            ],
            paths=[
                PathRule(
                    name="search_then_act",
                    sequence=["search", "call_service"],
                    exceptions=["Direct entity reference"],
                )
            ],
            parameter_rules=[
                ParamRule(tool="call_service", param="entity_id", extraction_type="exact")
            ],
            system_prompt_rules=[
                PromptRule(
                    name="confirm_before_action",
                    check_type="path_validation",
                    severity="critical",
                )
            ],
            quality_rubrics=["correctness", "faithfulness"],
            thresholds={"correctness": 0.85, "faithfulness": 0.90},
        )
        assert len(config.tools) == 1
        assert config.tools[0].name == "call_service"
        assert len(config.paths) == 1
        assert config.thresholds["correctness"] == 0.85

    def test_get_tool_found(self):
        config = AgentEvalConfig(
            tools=[ToolDef(name="search"), ToolDef(name="book")]
        )
        assert config.get_tool("search") is not None
        assert config.get_tool("search").name == "search"

    def test_get_tool_not_found(self):
        config = AgentEvalConfig(tools=[ToolDef(name="search")])
        assert config.get_tool("nonexistent") is None

    def test_get_path_rules_for_tool(self):
        config = AgentEvalConfig(
            paths=[
                PathRule(name="flow1", sequence=["search", "book"]),
                PathRule(name="flow2", sequence=["list", "cancel"]),
            ]
        )
        rules = config.get_path_rules_for_tool("search")
        assert len(rules) == 1
        assert rules[0].name == "flow1"

    def test_get_param_rules_for_tool(self):
        config = AgentEvalConfig(
            parameter_rules=[
                ParamRule(tool="book", param="room_id"),
                ParamRule(tool="book", param="date"),
                ParamRule(tool="search", param="query"),
            ]
        )
        rules = config.get_param_rules_for_tool("book")
        assert len(rules) == 2


# ---------------------------------------------------------------------------
# Tests: ToolDef & ParamDef
# ---------------------------------------------------------------------------


class TestToolDef:
    def test_with_parameters(self):
        tool = ToolDef(
            name="book_room",
            description="Book a room",
            parameters=[
                ParamDef(name="room_id", type="integer", required=True),
                ParamDef(
                    name="date",
                    type="string",
                    format="YYYY-MM-DD",
                    required=True,
                ),
                ParamDef(
                    name="capacity",
                    type="integer",
                    min_value=1,
                    max_value=100,
                ),
            ],
            required_params=["room_id", "date"],
        )
        assert len(tool.parameters) == 3
        assert tool.parameters[2].min_value == 1


# ---------------------------------------------------------------------------
# Tests: ConfigLoader from YAML string
# ---------------------------------------------------------------------------


class TestConfigLoaderString:
    def test_load_minimal(self):
        yaml_str = "agent_name: test-agent\nmodel: gpt-4o\n"
        config = ConfigLoader.load_string(yaml_str)
        assert config.agent_name == "test-agent"
        assert config.model == "gpt-4o"

    def test_load_with_tools(self):
        yaml_str = """
agent_name: test
tools:
  - name: search
    description: Search for items
    parameters:
      - name: query
        type: string
        required: true
    required_params: [query]
"""
        config = ConfigLoader.load_string(yaml_str)
        assert len(config.tools) == 1
        assert config.tools[0].name == "search"
        assert len(config.tools[0].parameters) == 1

    def test_load_with_thresholds(self):
        yaml_str = """
agent_name: test
thresholds:
  correctness: 0.85
  faithfulness: 0.90
"""
        config = ConfigLoader.load_string(yaml_str)
        assert config.thresholds["correctness"] == 0.85
        assert config.thresholds["faithfulness"] == 0.90

    def test_load_with_paths(self):
        yaml_str = """
agent_name: test
paths:
  - name: booking_flow
    sequence: [search, preview, book]
    exceptions: ["Direct ID provided"]
"""
        config = ConfigLoader.load_string(yaml_str)
        assert len(config.paths) == 1
        assert config.paths[0].sequence == ["search", "preview", "book"]

    def test_load_with_system_prompt_rules(self):
        yaml_str = """
agent_name: test
system_prompt_rules:
  - name: no_headings
    check_type: response_check
    severity: warning
    pattern: "^#{1,3}\\\\s"
"""
        config = ConfigLoader.load_string(yaml_str)
        assert len(config.system_prompt_rules) == 1
        assert config.system_prompt_rules[0].check_type == "response_check"

    def test_invalid_yaml_type(self):
        with pytest.raises(ValueError, match="YAML mapping"):
            ConfigLoader.load_string("- item1\n- item2\n")


# ---------------------------------------------------------------------------
# Tests: ConfigLoader from file
# ---------------------------------------------------------------------------


class TestConfigLoaderFile:
    def test_load_example_config(self):
        from pathlib import Path

        # test_evaluation/ -> tests/ -> homeiq-patterns/ -> src/homeiq_patterns/evaluation/configs/
        config_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "homeiq_patterns"
            / "evaluation"
            / "configs"
            / "example_agent.yaml"
        )
        config = ConfigLoader.load(config_path)
        assert config.agent_name == "example-agent"
        assert len(config.tools) == 2
        assert len(config.paths) == 1
        assert len(config.quality_rubrics) >= 3
        assert config.thresholds.get("correctness") == 0.85

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("/nonexistent/path.yaml")
