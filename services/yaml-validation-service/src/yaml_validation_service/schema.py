"""
Canonical Automation Schema (AutomationSpec)

Epic 51, Story 51.1: Canonical Automation Schema & YAML Renderer

This module defines the canonical internal representation of Home Assistant automations
using Pydantic models. YAML is rendered FROM this schema, not the primary source of truth.

Supports all Home Assistant 2025.10+ features:
- Basic triggers and actions
- choose, repeat, parallel, sequence
- Conditions
- Error handling
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AutomationMode(str, Enum):
    """Automation execution mode."""
    SINGLE = "single"
    RESTART = "restart"
    QUEUED = "queued"
    PARALLEL = "parallel"


class MaxExceeded(str, Enum):
    """Behavior when max_exceeded is triggered."""
    SILENT = "silent"
    WARNING = "warning"
    ERROR = "error"


class TriggerSpec(BaseModel):
    """Trigger specification."""
    platform: str = Field(..., description="Trigger platform (e.g., 'state', 'time', 'time_pattern')")
    entity_id: str | list[str] | None = Field(None, description="Entity ID(s) for state triggers")
    to: str | None = Field(None, description="Target state for state triggers")
    from_state: str | None = Field(None, alias="from", description="Source state for state triggers")
    at: str | None = Field(None, description="Time for time triggers (HH:MM:SS)")
    minutes: str | int | None = Field(None, description="Minutes pattern for time_pattern triggers")
    hours: str | int | None = Field(None, description="Hours pattern for time_pattern triggers")
    days: str | int | None = Field(None, description="Days pattern for time_pattern triggers")
    # Additional trigger fields can be added as needed
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional trigger-specific fields")

    class Config:
        populate_by_name = True


class ConditionSpec(BaseModel):
    """Condition specification."""
    condition: str = Field(..., description="Condition type (e.g., 'state', 'numeric_state', 'time')")
    entity_id: str | list[str] | None = Field(None, description="Entity ID(s) for state conditions")
    state: str | None = Field(None, description="State value for state conditions")
    above: float | None = Field(None, description="Above value for numeric_state conditions")
    below: float | None = Field(None, description="Below value for numeric_state conditions")
    # Additional condition fields can be added as needed
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional condition-specific fields")


class ActionSpec(BaseModel):
    """Action specification."""
    service: str | None = Field(None, description="Service to call (e.g., 'light.turn_on')")
    scene: str | None = Field(None, description="Scene to activate")
    delay: str | None = Field(None, description="Delay duration (e.g., '00:00:05')")
    target: dict[str, Any] | None = Field(None, description="Target specification (entity_id, area_id, device_id)")
    data: dict[str, Any] = Field(default_factory=dict, description="Service data")
    # Advanced action types
    choose: list[dict[str, Any]] | None = Field(None, description="Choose action (list of conditions/sequences)")
    repeat: dict[str, Any] | None = Field(None, description="Repeat action")
    parallel: list[dict[str, Any]] | None = Field(None, description="Parallel actions")
    sequence: list[dict[str, Any]] | None = Field(None, description="Sequence actions")
    # Error handling
    error: str | None = Field(None, description="Error handling ('continue', 'stop', 'abort')")
    continue_on_error: bool | None = Field(None, description="Legacy error handling (deprecated, use 'error')")
    # Additional action fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional action-specific fields")

    @field_validator("service", "scene", "delay", mode="before")
    @classmethod
    def validate_action_type(cls, v, info):
        """Ensure at least one action type is specified."""
        if info.data.get("service") or info.data.get("scene") or info.data.get("delay"):
            return v
        # Allow advanced actions (choose, repeat, parallel, sequence)
        if info.data.get("choose") or info.data.get("repeat") or info.data.get("parallel") or info.data.get("sequence"):
            return v
        raise ValueError("Action must have at least one of: service, scene, delay, choose, repeat, parallel, or sequence")


class AutomationSpec(BaseModel):
    """
    Canonical automation specification.
    
    This is the internal representation of a Home Assistant automation.
    YAML is rendered FROM this schema, ensuring consistency and correctness.
    """
    id: str | None = Field(None, description="Automation ID (optional, can be generated)")
    alias: str = Field(..., description="Automation alias/name")
    description: str | None = Field(None, description="Automation description")
    initial_state: bool = Field(True, description="Initial state (required for 2025.10+)")
    mode: AutomationMode = Field(AutomationMode.SINGLE, description="Automation execution mode")
    trigger: list[TriggerSpec] = Field(..., description="List of triggers (singular 'trigger', not 'triggers')")
    condition: list[ConditionSpec] | None = Field(None, description="List of conditions")
    action: list[ActionSpec] = Field(..., description="List of actions (singular 'action', not 'actions')")
    max_exceeded: MaxExceeded | str | None = Field(None, description="Behavior when max_exceeded")
    tags: list[str] | None = Field(None, description="Automation tags")
    # Additional fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional automation-specific fields")

    class Config:
        use_enum_values = True

