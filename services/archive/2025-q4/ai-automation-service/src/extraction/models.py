"""
Automation Extraction Models (2025)

This module defines the unified data structure (AutomationContext) that captures
all understanding of a user's automation request.

It leverages Pydantic V2 for strict validation and schema generation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SpatialContext(BaseModel):
    """Context related to where the automation happens."""
    areas: List[str] = Field(default_factory=list, description="Identified areas (e.g., 'office', 'kitchen')")
    locations: List[str] = Field(default_factory=list, description="Specific locations (e.g., 'desk', 'couch')")
    floors: List[str] = Field(default_factory=list, description="Floors (e.g., 'upstairs', 'basement')")
    
    # Validation flags
    area_matched: bool = Field(False, description="True if valid HA areas were found")

class DeviceContext(BaseModel):
    """Context related to devices involved in the automation."""
    # Primary Action Devices (The target of the action)
    action_entities: List[str] = Field(default_factory=list, description="Validated entity IDs to control")
    action_device_names: List[str] = Field(default_factory=list, description="Friendly names of devices to control")
    
    # Trigger Devices (The sensors initiating the action)
    trigger_entities: List[str] = Field(default_factory=list, description="Validated entity IDs acting as triggers")
    trigger_device_names: List[str] = Field(default_factory=list, description="Friendly names of trigger devices")
    
    # Metadata
    domains: List[str] = Field(default_factory=list, description="Inferred domains (e.g., 'light', 'switch')")
    missing_devices: List[str] = Field(default_factory=list, description="Devices mentioned in query but not found in HA")
    
    # Capabilities needed for this automation
    required_capabilities: List[str] = Field(default_factory=list, description="Capabilities required (e.g. 'brightness', 'color')")

class TemporalContext(BaseModel):
    """Context related to time and schedules."""
    time_references: List[str] = Field(default_factory=list, description="Explicit times (e.g., '7 AM', 'sunset')")
    schedules: List[str] = Field(default_factory=list, description="Recurring schedules (e.g., 'every 10 minutes')")
    durations: List[str] = Field(default_factory=list, description="Durations (e.g., 'for 10 minutes')")
    delays: List[str] = Field(default_factory=list, description="Delays between actions (e.g., 'wait 5 seconds')")
    time_conditions: List[str] = Field(default_factory=list, description="Time constraints (e.g. 'only at night')")

class TriggerContext(BaseModel):
    """Context related to what initiates the automation."""
    trigger_type: str = Field(..., description="Primary trigger type (presence, time, state, zone, etc.)")
    raw_condition: str = Field("", description="The natural language text describing the trigger")
    platform: str = Field("state", description="HA trigger platform (state, numeric_state, time, etc.)")
    
    # Specific details
    to_state: Optional[str] = Field(None, description="Target state (e.g., 'on', 'home')")
    from_state: Optional[str] = Field(None, description="Previous state")
    attribute: Optional[str] = Field(None, description="Attribute to monitor")
    above: Optional[float] = Field(None, description="Numeric threshold (above)")
    below: Optional[float] = Field(None, description="Numeric threshold (below)")

class ActionContext(BaseModel):
    """Context related to what the automation does."""
    intent_type: str = Field(..., description="High level intent: turn_on, turn_off, toggle, set_value, notify")
    service: str = Field(..., description="Target HA service (e.g., light.turn_on)")
    
    # Parameters for the action
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Service data (brightness, color, message, etc.)")
    
    # Execution flow
    is_sequence: bool = Field(False, description="True if this is part of a multi-step sequence")
    repeat_count: int = Field(0, description="Number of repetitions (0 = none)")

class BehavioralContext(BaseModel):
    """Context related to how the automation behaves."""
    mode: str = Field("single", description="Execution mode: single, restart, queued, parallel")
    conditions: List[str] = Field(default_factory=list, description="Additional conditions (e.g., 'if I am home')")
    confidence: float = Field(0.0, description="Overall confidence score (0.0 - 1.0)")
    rationale: str = Field("", description="Explanation of why this automation was constructed this way")

class AutomationContext(BaseModel):
    """
    The Unified Source of Truth for an Automation Request.
    
    This object captures the user's intent and the system's understanding of the physical world
    (devices, areas) required to fulfill that intent.
    """
    raw_query: str = Field(..., description="Original user query")
    
    spatial: SpatialContext = Field(default_factory=SpatialContext)
    devices: DeviceContext = Field(default_factory=DeviceContext)
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    triggers: List[TriggerContext] = Field(default_factory=list)
    actions: List[ActionContext] = Field(default_factory=list)
    behavioral: BehavioralContext = Field(default_factory=BehavioralContext)
    
    def summarize(self) -> str:
        """Returns a human-readable summary of the context."""
        summary = f"Intent: {self.behavioral.rationale or 'Unknown'}\n"
        summary += f"Devices: {len(self.devices.action_entities)} action, {len(self.devices.trigger_entities)} trigger\n"
        summary += f"Areas: {', '.join(self.spatial.areas)}\n"
        return summary

