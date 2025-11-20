"""
Contract Models for AI Automation Service
Pydantic v2 models with strict schema enforcement (extra="forbid")
"""

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AutomationMode(str, Enum):
    """Automation execution mode"""
    SINGLE = "single"
    RESTART = "restart"
    QUEUED = "queued"
    PARALLEL = "parallel"


class MaxExceeded(str, Enum):
    """Behavior when max triggers exceeded"""
    SILENT = "silent"
    WARNING = "warning"
    ERROR = "error"


class AutomationMetadata(BaseModel):
    """Metadata for LLM-generated automation"""
    schema_version: str = Field(default="1.0.0", pattern=r"^1\.0\.0$")
    provider_id: str = Field(..., description="LLM provider identifier (e.g., 'openai', 'anthropic')")
    model_id: str = Field(..., description="Model identifier (e.g., 'gpt-4o-mini', 'claude-3-sonnet')")
    prompt_pack_id: str | None = Field(None, description="Prompt pack identifier for traceability")

    class Config:
        extra = "forbid"
        frozen = True


class Trigger(BaseModel):
    """Automation trigger"""
    platform: Literal[
        "state", "time", "time_pattern", "numeric_state", "sun",
        "event", "mqtt", "webhook", "zone", "geo_location", "device"
    ] = Field(..., description="Trigger platform")
    entity_id: str | list[str] | None = None
    to: str | list[str] | None = None
    from_: str | list[str] | None = Field(None, alias="from")
    for_: str | dict[str, Any] | None = Field(None, alias="for")
    at: str | None = None
    hours: str | int | None = None
    minutes: str | int | None = None
    seconds: str | int | None = None
    event_type: str | None = None
    event_data: dict[str, Any] | None = None
    topic: str | None = None
    payload: str | None = None
    above: float | None = None
    below: float | None = None
    value_template: str | None = None
    offset: str | None = None
    event: Literal["sunrise", "sunset"] | None = None
    device_id: str | None = None
    domain: str | None = None
    type: str | None = None
    subtype: str | None = None

    class Config:
        extra = "forbid"
        populate_by_name = True


class Condition(BaseModel):
    """Automation condition"""
    condition: Literal[
        "state", "numeric_state", "time", "sun", "template",
        "zone", "and", "or", "not", "device"
    ] = Field(..., description="Condition type")
    entity_id: str | list[str] | None = None
    state: str | list[str] | None = None
    above: float | None = None
    below: float | None = None
    after: str | None = None
    before: str | None = None
    after_offset: str | None = None
    before_offset: str | None = None
    value_template: str | None = None
    zone: str | None = None
    conditions: list["Condition"] | None = None
    device_id: str | None = None
    domain: str | None = None
    type: str | None = None
    subtype: str | None = None

    class Config:
        extra = "forbid"


# Forward reference resolution
Condition.model_rebuild()


class Action(BaseModel):
    """Automation action"""
    service: str = Field(..., pattern=r"^[a-z_]+\.[a-z_]+$", description="Service in format domain.service")
    entity_id: str | list[str] | None = None
    target: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    service_data: dict[str, Any] | None = None
    delay: str | dict[str, Any] | None = None
    wait_template: str | None = None
    wait_for_trigger: list["Trigger"] | None = Field(None, description="Wait for specified triggers before continuing")
    timeout: str | dict[str, Any] | None = Field(None, description="Timeout for wait_for_trigger (e.g., '00:05:00' or {minutes: 5})")
    continue_on_timeout: bool | None = Field(None, description="Continue sequence if wait_for_trigger times out")
    repeat: dict[str, Any] | None = None
    choose: list[Any] | None = None
    if_: list[Condition] | None = Field(None, alias="if")
    parallel: list[Any] | None = None
    sequence: list[Any] | None = None
    stop: Literal["all", "first"] | None = None
    error: Literal["continue", "stop"] | None = None

    class Config:
        extra = "forbid"
        populate_by_name = True


# Forward reference resolution
Action.model_rebuild()


class AutomationPlan(BaseModel):
    """
    Complete automation plan with strict schema enforcement.
    
    This is the contract that all LLM outputs must conform to.
    Rejects any extra fields or invalid structures.
    """
    schema_version: str = Field(default="1.0.0", pattern=r"^1\.0\.0$")
    name: str = Field(..., min_length=1, max_length=200, description="Automation name/alias")
    triggers: list[Trigger] = Field(..., min_length=1, description="List of triggers")
    conditions: list[Condition] = Field(default_factory=list, description="Optional conditions")
    actions: list[Action] = Field(..., min_length=1, description="List of actions")
    description: str | None = Field(None, max_length=500, description="Human-readable description")
    mode: AutomationMode = Field(default=AutomationMode.SINGLE, description="Automation mode")
    max_exceeded: MaxExceeded | None = None

    # Metadata fields (not part of HA automation, but required for traceability)
    metadata: AutomationMetadata | None = None

    class Config:
        extra = "forbid"

    @field_validator("triggers", mode="before")
    @classmethod
    def validate_triggers(cls, v):
        if not isinstance(v, list):
            raise ValueError("triggers must be a list")
        if len(v) == 0:
            raise ValueError("triggers must have at least one item")
        return v

    @field_validator("actions", mode="before")
    @classmethod
    def validate_actions(cls, v):
        if not isinstance(v, list):
            raise ValueError("actions must be a list")
        if len(v) == 0:
            raise ValueError("actions must have at least one item")
        return v

    def to_yaml(self) -> str:
        """
        Convert automation plan to Home Assistant YAML format.
        
        Returns:
            YAML string ready for Home Assistant
        """
        import yaml

        # Build HA automation dict (exclude metadata)
        ha_automation = {
            "alias": self.name,
            "description": self.description,
            "trigger": [t.model_dump(exclude_none=True, by_alias=True) for t in self.triggers],
            "action": [a.model_dump(exclude_none=True, by_alias=True) for a in self.actions],
            "mode": self.mode.value,
        }

        if self.conditions:
            ha_automation["condition"] = [c.model_dump(exclude_none=True) for c in self.conditions]

        if self.max_exceeded:
            ha_automation["max_exceeded"] = self.max_exceeded.value

        return yaml.dump(ha_automation, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_json(cls, json_str: str, metadata: AutomationMetadata | None = None) -> "AutomationPlan":
        """
        Parse JSON string into AutomationPlan with strict validation.
        
        Args:
            json_str: JSON string from LLM
            metadata: Optional metadata to attach
            
        Returns:
            Validated AutomationPlan
            
        Raises:
            ValidationError: If JSON doesn't conform to schema
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Attach metadata if provided
        if metadata:
            data["metadata"] = metadata.model_dump()

        return cls.model_validate(data)

