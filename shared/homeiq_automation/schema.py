"""
HomeIQ JSON Automation Schema

Comprehensive Pydantic models for HomeIQ JSON Automation format.
Extends AutomationSpec with HomeIQ-specific metadata and context.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from shared.yaml_validation_service.schema import AutomationMode, MaxExceeded


class TimeConstraints(BaseModel):
    """Time-based constraints for automation execution."""
    after: str | None = Field(None, description="Earliest time (HH:MM:SS)")
    before: str | None = Field(None, description="Latest time (HH:MM:SS)")
    weekdays: list[int] | None = Field(None, description="Weekdays (0=Monday, 6=Sunday)")
    exclude_holidays: bool = Field(False, description="Exclude holidays")


class HomeIQMetadata(BaseModel):
    """HomeIQ-specific metadata for automations."""
    created_by: str = Field(default="ai-automation-service", description="Service that created this automation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    pattern_id: int | None = Field(None, description="Pattern ID that generated this automation")
    suggestion_id: int | None = Field(None, description="Suggestion ID this automation belongs to")
    confidence_score: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score (0-1)")
    safety_score: float | None = Field(None, ge=0.0, le=100.0, description="Safety score (0-100)")
    use_case: Literal["energy", "comfort", "security", "convenience"] = Field(
        description="Primary use case category"
    )
    complexity: Literal["low", "medium", "high"] = Field(description="Automation complexity level")


class PatternContext(BaseModel):
    """Context about the pattern that generated this automation."""
    pattern_type: str = Field(description="Pattern type (time_of_day, co_occurrence, anomaly, etc.)")
    pattern_id: int = Field(description="Pattern ID")
    pattern_metadata: dict[str, Any] = Field(default_factory=dict, description="Pattern-specific metadata")
    confidence: float = Field(ge=0.0, le=1.0, description="Pattern confidence (0-1)")
    occurrences: int = Field(ge=0, description="Number of pattern occurrences")


class DeviceContext(BaseModel):
    """Context about devices involved in the automation."""
    device_ids: list[str] = Field(default_factory=list, description="Device IDs involved")
    entity_ids: list[str] = Field(default_factory=list, description="Entity IDs involved")
    device_types: list[str] = Field(default_factory=list, description="Device types (light, sensor, etc.)")
    area_ids: list[str] | None = Field(None, description="Area IDs where devices are located")
    device_capabilities: dict[str, Any] | None = Field(
        None, description="Device capabilities (effects, modes, ranges, etc.)"
    )


class SafetyChecks(BaseModel):
    """Safety validation information."""
    requires_confirmation: bool = Field(default=False, description="Requires user confirmation before deployment")
    critical_devices: list[str] | None = Field(None, description="Critical device IDs (locks, security, etc.)")
    time_constraints: TimeConstraints | None = Field(None, description="Time-based safety constraints")
    safety_warnings: list[str] | None = Field(None, description="Safety warnings for this automation")


class EnergyImpact(BaseModel):
    """Energy consumption impact analysis."""
    estimated_power_w: float | None = Field(None, ge=0.0, description="Estimated power consumption in watts")
    estimated_daily_kwh: float | None = Field(None, ge=0.0, description="Estimated daily energy in kWh")
    peak_hours: list[int] | None = Field(None, description="Peak consumption hours (0-23)")


class HomeIQTrigger(BaseModel):
    """HomeIQ trigger specification (extends TriggerSpec with HomeIQ context)."""
    platform: str = Field(..., description="Trigger platform (e.g., 'state', 'time', 'time_pattern')")
    entity_id: str | list[str] | None = Field(None, description="Entity ID(s) for state triggers")
    to: str | None = Field(None, description="Target state for state triggers")
    from_state: str | None = Field(None, alias="from", description="Source state for state triggers")
    at: str | None = Field(None, description="Time for time triggers (HH:MM:SS)")
    minutes: str | int | None = Field(None, description="Minutes pattern for time_pattern triggers")
    hours: str | int | None = Field(None, description="Hours pattern for time_pattern triggers")
    days: str | int | None = Field(None, description="Days pattern for time_pattern triggers")
    # HomeIQ extensions
    device_id: str | None = Field(None, description="Device ID if trigger is device-specific")
    area_id: str | None = Field(None, description="Area ID if trigger is area-specific")
    # Additional trigger fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional trigger-specific fields")

    class Config:
        populate_by_name = True


class HomeIQCondition(BaseModel):
    """HomeIQ condition specification (extends ConditionSpec with HomeIQ context)."""
    condition: str = Field(..., description="Condition type (e.g., 'state', 'numeric_state', 'time')")
    entity_id: str | list[str] | None = Field(None, description="Entity ID(s) for state conditions")
    state: str | None = Field(None, description="State value for state conditions")
    above: float | None = Field(None, description="Above value for numeric_state conditions")
    below: float | None = Field(None, description="Below value for numeric_state conditions")
    # HomeIQ extensions
    device_id: str | None = Field(None, description="Device ID if condition is device-specific")
    area_id: str | None = Field(None, description="Area ID if condition is area-specific")
    # Additional condition fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional condition-specific fields")


class HomeIQAction(BaseModel):
    """HomeIQ action specification (extends ActionSpec with HomeIQ context)."""
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
    # HomeIQ extensions
    energy_impact_w: float | None = Field(None, ge=0.0, description="Estimated power consumption for this action")
    # Additional action fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional action-specific fields")


class HomeIQAutomation(BaseModel):
    """
    Comprehensive HomeIQ JSON Automation format.
    
    This is the primary format for HomeIQ automations, extending beyond
    Home Assistant YAML to include HomeIQ-specific metadata, patterns,
    device context, and integration capabilities.
    """
    # Core automation fields
    id: str | None = Field(None, description="Automation ID (optional, can be generated)")
    alias: str = Field(..., description="Automation alias/name")
    description: str | None = Field(None, description="Automation description")
    version: str = Field(default="1.0.0", description="HomeIQ JSON schema version")
    
    # HomeIQ-specific metadata
    homeiq_metadata: HomeIQMetadata = Field(..., description="HomeIQ metadata")
    pattern_context: PatternContext | None = Field(None, description="Pattern that generated this automation")
    device_context: DeviceContext = Field(..., description="Devices involved in automation")
    area_context: list[str] | None = Field(None, description="Areas involved in automation")
    
    # Automation structure (compatible with AutomationSpec)
    triggers: list[HomeIQTrigger] = Field(..., min_length=1, description="List of triggers")
    conditions: list[HomeIQCondition] | None = Field(None, description="List of conditions")
    actions: list[HomeIQAction] = Field(..., min_length=1, description="List of actions")
    mode: AutomationMode = Field(default=AutomationMode.SINGLE, description="Automation execution mode")
    initial_state: bool = Field(default=True, description="Initial state (required for 2025.10+)")
    max_exceeded: MaxExceeded | str | None = Field(None, description="Behavior when max_exceeded")
    
    # HomeIQ extensions
    safety_checks: SafetyChecks | None = Field(None, description="Safety validation information")
    energy_impact: EnergyImpact | None = Field(None, description="Energy consumption impact")
    dependencies: list[str] | None = Field(None, description="Other automation IDs this depends on")
    tags: list[str] | None = Field(None, description="Automation tags")
    
    # Additional fields for extensibility
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional automation-specific fields")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

