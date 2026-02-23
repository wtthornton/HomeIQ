"""
Agent Evaluation Framework — Configuration Schema & Loader

Declarative YAML configuration for defining an agent's evaluation rules:
tools, paths, parameter rules, system prompt rules, quality rubrics,
and thresholds.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ParamDef(BaseModel):
    """Definition of a single tool parameter."""

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    valid_values: list[Any] = Field(default_factory=list)
    format: str = ""  # e.g. "YYYY-MM-DD", "HH:MM"
    min_value: float | None = None
    max_value: float | None = None


class ToolDef(BaseModel):
    """Definition of a tool available to the agent."""

    name: str
    description: str = ""
    parameters: list[ParamDef] = Field(default_factory=list)
    required_params: list[str] = Field(default_factory=list)


class PathRule(BaseModel):
    """Expected tool call sequence for a workflow."""

    name: str
    description: str = ""
    sequence: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)


class ParamRule(BaseModel):
    """Validation rule for a tool parameter."""

    tool: str
    param: str
    extraction_type: str = "exact"  # exact | fuzzy | entity_resolution
    valid_values: list[Any] = Field(default_factory=list)
    validation_fn: str = ""  # named validation function
    format: str = ""


class PromptRule(BaseModel):
    """System prompt compliance rule."""

    name: str
    description: str = ""
    check_type: str = "llm_judge"  # path_validation | response_check | llm_judge
    severity: str = "warning"  # critical | warning | info
    pattern: str = ""  # regex for response_check
    tool_sequence: list[str] = Field(default_factory=list)  # for path_validation
    labels: list[str] = Field(default_factory=list)  # custom labels


class PriorityEntry(BaseModel):
    """Priority matrix entry for evaluation scheduling."""

    priority: str = "P1"  # P0 | P1 | P2 | P3
    level: str = ""
    metric: str = ""
    frequency: str = "every_session"  # every_session | hourly | daily


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------


class AgentEvalConfig(BaseModel):
    """
    Declarative configuration for an agent's evaluation setup.

    Loaded from YAML and used by ``EvaluationRegistry`` to instantiate
    the correct evaluators.
    """

    agent_name: str = ""
    model: str = ""
    description: str = ""

    tools: list[ToolDef] = Field(default_factory=list)
    paths: list[PathRule] = Field(default_factory=list)
    parameter_rules: list[ParamRule] = Field(default_factory=list)
    system_prompt_rules: list[PromptRule] = Field(default_factory=list)
    system_prompt: str = ""  # full system prompt text for instruction-following eval

    quality_rubrics: list[str] = Field(default_factory=list)
    safety_rubrics: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    priority_matrix: list[PriorityEntry] = Field(default_factory=list)

    def get_tool(self, name: str) -> ToolDef | None:
        """Look up a tool definition by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_path_rules_for_tool(self, tool_name: str) -> list[PathRule]:
        """Find all path rules that include a given tool."""
        return [p for p in self.paths if tool_name in p.sequence]

    def get_param_rules_for_tool(self, tool_name: str) -> list[ParamRule]:
        """Find all parameter rules for a given tool."""
        return [r for r in self.parameter_rules if r.tool == tool_name]


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Loads and validates ``AgentEvalConfig`` from YAML files."""

    @staticmethod
    def load(path: str | Path) -> AgentEvalConfig:
        """Load an agent evaluation config from a YAML file."""
        import yaml  # lazy import

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)

        if not isinstance(data, dict):
            raise ValueError(f"Config must be a YAML mapping, got {type(data).__name__}")

        return AgentEvalConfig.model_validate(data)

    @staticmethod
    def load_string(yaml_string: str) -> AgentEvalConfig:
        """Load config from a YAML string (useful for testing)."""
        import yaml

        data = yaml.safe_load(yaml_string)
        if not isinstance(data, dict):
            raise ValueError(f"Config must be a YAML mapping, got {type(data).__name__}")
        return AgentEvalConfig.model_validate(data)
