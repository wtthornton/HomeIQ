"""
Template Schema Definitions

Pydantic models for template structure, parameter schemas, and compilation mappings.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SafetyClass(str, Enum):
    """Safety classification for templates."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ParameterType(str, Enum):
    """Parameter type definitions."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    TIME = "time"  # HH:MM format
    DURATION = "duration"  # HH:MM:SS format


class TemplateParameter(BaseModel):
    """Parameter schema definition for a template."""
    type: ParameterType
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if not provided")
    enum: list[Any] | None = Field(default=None, description="Allowed enum values")
    min: int | float | None = Field(default=None, description="Minimum value (for numeric types)")
    max: int | float | None = Field(default=None, description="Maximum value (for numeric types)")
    description: str | None = Field(default=None, description="Parameter description")
    format: str | None = Field(default=None, description="Format hint (e.g., 'HH:MM' for time)")
    properties: dict[str, "TemplateParameter"] | None = Field(
        default=None, description="Nested properties for object type"
    )
    items: "TemplateParameter" | None = Field(
        default=None, description="Item schema for array type"
    )


class RequiredCapabilities(BaseModel):
    """Required device capabilities for a template."""
    sensors: list[str] = Field(default_factory=list, description="Required sensor types")
    devices: list[str] = Field(default_factory=list, description="Required device types")
    services: list[str] = Field(default_factory=list, description="Required service domains")


class TemplateCompilationMapping(BaseModel):
    """Compilation mapping from template parameters to HA automation structure."""
    trigger: dict[str, Any] = Field(description="Trigger configuration with parameter placeholders")
    condition: dict[str, Any] | None = Field(default=None, description="Condition configuration")
    action: dict[str, Any] = Field(description="Action configuration with parameter placeholders")
    alias_template: str | None = Field(default=None, description="Alias template with placeholders")
    description_template: str | None = Field(default=None, description="Description template")


class Template(BaseModel):
    """Template definition for automation generation."""
    template_id: str = Field(description="Unique template identifier")
    version: int = Field(description="Template version number")
    description: str = Field(description="Template description and purpose")
    required_capabilities: RequiredCapabilities = Field(
        description="Required device/sensor capabilities"
    )
    parameter_schema: dict[str, TemplateParameter] = Field(
        description="Parameter schema definitions"
    )
    safety_class: SafetyClass = Field(description="Safety classification")
    forbidden_targets: list[str] = Field(
        default_factory=list, description="Forbidden device/entity patterns"
    )
    compilation_mapping: TemplateCompilationMapping = Field(
        description="Mapping from parameters to HA automation structure"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Example parameter sets"
    )


# Update forward references
TemplateParameter.model_rebuild()
Template.model_rebuild()
