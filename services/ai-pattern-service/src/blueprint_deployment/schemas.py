"""
Pydantic schemas for Blueprint Deployment (Phase 3)
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class DeploymentRequest(BaseModel):
    """Request to deploy a blueprint as an automation."""
    
    blueprint_id: str = Field(..., description="Blueprint ID from the index")
    automation_name: str = Field(..., description="Name for the created automation")
    description: str | None = Field(None, description="Optional description")
    input_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Input values for the blueprint (entity IDs, etc.)"
    )
    use_auto_fill: bool = Field(
        default=True,
        description="Whether to use auto-fill for missing inputs"
    )
    enabled: bool = Field(default=True, description="Whether to enable the automation")
    mode: str = Field(
        default="single",
        description="Automation mode: single, restart, queued, parallel"
    )
    max_runs: int | None = Field(None, description="Max concurrent runs (for queued/parallel)")


class AutomationFromBlueprint(BaseModel):
    """Generated automation configuration from a blueprint."""
    
    alias: str = Field(..., description="Automation name/alias")
    description: str | None = Field(None, description="Automation description")
    use_blueprint: dict[str, Any] = Field(
        ...,
        description="Blueprint reference with path and inputs"
    )
    mode: str = Field(default="single", description="Execution mode")
    max: int | None = Field(None, description="Max concurrent executions")


class BlueprintImportResult(BaseModel):
    """Result of importing a blueprint into Home Assistant."""
    
    success: bool
    blueprint_path: str | None = Field(None, description="HA blueprint path (e.g., homeassistant/motion_light)")
    error: str | None = None
    already_exists: bool = False


class DeploymentResult(BaseModel):
    """Result of deploying a blueprint as an automation."""
    
    success: bool
    automation_id: str | None = Field(None, description="Created automation entity ID")
    automation_yaml: str | None = Field(None, description="Generated YAML configuration")
    blueprint_path: str | None = Field(None, description="Blueprint path used")
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    
    # Deployment metadata
    deployed_at: datetime | None = None
    input_values_used: dict[str, Any] = Field(default_factory=dict)
    auto_filled_inputs: list[str] = Field(default_factory=list)


class BlueprintDeploymentPreview(BaseModel):
    """Preview of what a blueprint deployment would look like."""
    
    automation_yaml: str
    automation_config: dict[str, Any]
    input_mapping: dict[str, Any]
    auto_fill_suggestions: dict[str, Any]
    missing_required_inputs: list[str]
    warnings: list[str] = Field(default_factory=list)
