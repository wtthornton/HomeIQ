"""
Contract Models for AI Automation Service
Pydantic v2 models with strict schema enforcement (extra="forbid")
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum
import json


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
    prompt_pack_id: Optional[str] = Field(None, description="Prompt pack identifier for traceability")
    
    class Config:
        extra = "forbid"
        frozen = True


class Trigger(BaseModel):
    """Automation trigger"""
    platform: Literal[
        "state", "time", "time_pattern", "numeric_state", "sun", 
        "event", "mqtt", "webhook", "zone", "geo_location", "device"
    ] = Field(..., description="Trigger platform")
    entity_id: Optional[Union[str, List[str]]] = None
    to: Optional[Union[str, List[str]]] = None
    from_: Optional[Union[str, List[str]]] = Field(None, alias="from")
    for_: Optional[Union[str, Dict[str, Any]]] = Field(None, alias="for")
    at: Optional[str] = None
    hours: Optional[Union[str, int]] = None
    minutes: Optional[Union[str, int]] = None
    seconds: Optional[Union[str, int]] = None
    event_type: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    topic: Optional[str] = None
    payload: Optional[str] = None
    above: Optional[float] = None
    below: Optional[float] = None
    value_template: Optional[str] = None
    offset: Optional[str] = None
    event: Optional[Literal["sunrise", "sunset"]] = None
    device_id: Optional[str] = None
    domain: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None
    
    class Config:
        extra = "forbid"
        populate_by_name = True


class Condition(BaseModel):
    """Automation condition"""
    condition: Literal[
        "state", "numeric_state", "time", "sun", "template", 
        "zone", "and", "or", "not", "device"
    ] = Field(..., description="Condition type")
    entity_id: Optional[Union[str, List[str]]] = None
    state: Optional[Union[str, List[str]]] = None
    above: Optional[float] = None
    below: Optional[float] = None
    after: Optional[str] = None
    before: Optional[str] = None
    after_offset: Optional[str] = None
    before_offset: Optional[str] = None
    value_template: Optional[str] = None
    zone: Optional[str] = None
    conditions: Optional[List["Condition"]] = None
    device_id: Optional[str] = None
    domain: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None
    
    class Config:
        extra = "forbid"


# Forward reference resolution
Condition.model_rebuild()


class Action(BaseModel):
    """Automation action"""
    service: str = Field(..., pattern=r"^[a-z_]+\.[a-z_]+$", description="Service in format domain.service")
    entity_id: Optional[Union[str, List[str]]] = None
    target: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    service_data: Optional[Dict[str, Any]] = None
    delay: Optional[Union[str, Dict[str, Any]]] = None
    wait_template: Optional[str] = None
    repeat: Optional[Dict[str, Any]] = None
    choose: Optional[List[Any]] = None
    if_: Optional[List[Condition]] = Field(None, alias="if")
    parallel: Optional[List[Any]] = None
    sequence: Optional[List[Any]] = None
    stop: Optional[Literal["all", "first"]] = None
    error: Optional[Literal["continue", "stop"]] = None
    
    class Config:
        extra = "forbid"
        populate_by_name = True


class AutomationPlan(BaseModel):
    """
    Complete automation plan with strict schema enforcement.
    
    This is the contract that all LLM outputs must conform to.
    Rejects any extra fields or invalid structures.
    """
    schema_version: str = Field(default="1.0.0", pattern=r"^1\.0\.0$")
    name: str = Field(..., min_length=1, max_length=200, description="Automation name/alias")
    triggers: List[Trigger] = Field(..., min_length=1, description="List of triggers")
    conditions: List[Condition] = Field(default_factory=list, description="Optional conditions")
    actions: List[Action] = Field(..., min_length=1, description="List of actions")
    description: Optional[str] = Field(None, max_length=500, description="Human-readable description")
    mode: AutomationMode = Field(default=AutomationMode.SINGLE, description="Automation mode")
    max_exceeded: Optional[MaxExceeded] = None
    
    # Metadata fields (not part of HA automation, but required for traceability)
    metadata: Optional[AutomationMetadata] = None
    
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
    def from_json(cls, json_str: str, metadata: Optional[AutomationMetadata] = None) -> "AutomationPlan":
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

