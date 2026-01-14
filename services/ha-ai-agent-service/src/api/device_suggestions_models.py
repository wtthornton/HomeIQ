"""
Device Suggestions API Models
Phase 2: Device-Based Automation Suggestions Feature

Pydantic models for device suggestion request/response.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeviceSuggestionContext(BaseModel):
    """Context configuration for suggestion generation"""
    
    include_synergies: bool = Field(default=True, description="Include device synergies")
    include_blueprints: bool = Field(default=True, description="Include Home Assistant blueprints")
    include_sports: bool = Field(default=True, description="Include sports data (Team Tracker)")
    include_weather: bool = Field(default=True, description="Include weather data")


class DeviceSuggestionsRequest(BaseModel):
    """Request model for device suggestions endpoint"""
    
    device_id: str = Field(..., description="Device ID to generate suggestions for")
    conversation_id: str | None = Field(
        None, description="Optional conversation ID for context"
    )
    context: DeviceSuggestionContext = Field(
        default_factory=DeviceSuggestionContext,
        description="Context configuration for data aggregation"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "device_123",
                "conversation_id": "conv-456",
                "context": {
                    "include_synergies": True,
                    "include_blueprints": True,
                    "include_sports": True,
                    "include_weather": True,
                }
            }
        }
    )


class AutomationPreview(BaseModel):
    """Automation preview information"""
    
    trigger: str = Field(..., description="Home Assistant trigger description")
    action: str = Field(..., description="Home Assistant action description")
    yaml_preview: str | None = Field(
        None, description="Optional preview of Home Assistant YAML structure"
    )


class DataSources(BaseModel):
    """Data sources used for suggestion generation"""
    
    synergies: list[str] | None = Field(
        None, description="Synergy IDs used in suggestion"
    )
    blueprints: list[str] | None = Field(
        None, description="Blueprint IDs used in suggestion"
    )
    sports: bool = Field(default=False, description="Includes sports data")
    weather: bool = Field(default=False, description="Includes weather data")
    device_capabilities: bool = Field(
        default=False, description="Based on device capabilities"
    )


class HomeAssistantEntities(BaseModel):
    """Home Assistant entities involved in automation"""
    
    trigger_entities: list[str] = Field(
        default_factory=list, description="Trigger entity IDs"
    )
    action_entities: list[str] = Field(
        default_factory=list, description="Action entity IDs"
    )
    condition_entities: list[str] = Field(
        default_factory=list, description="Condition entity IDs"
    )


class HomeAssistantServices(BaseModel):
    """Home Assistant services used in automation"""
    
    actions: list[str] = Field(
        default_factory=list, description="Service calls (e.g., 'switch.turn_on')"
    )
    validated: bool = Field(
        default=False, description="Whether services are validated against HA registry"
    )


class DeviceSuggestion(BaseModel):
    """Single automation suggestion"""
    
    suggestion_id: str = Field(..., description="Unique suggestion ID")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    automation_preview: AutomationPreview = Field(..., description="Automation preview")
    data_sources: DataSources = Field(..., description="Data sources used")
    home_assistant_entities: HomeAssistantEntities | None = Field(
        None, description="Home Assistant entities involved"
    )
    home_assistant_services: HomeAssistantServices | None = Field(
        None, description="Home Assistant services used"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Quality score (0.0-1.0)"
    )
    enhanceable: bool = Field(
        default=True, description="Whether suggestion can be enhanced via chat"
    )
    home_assistant_compatible: bool = Field(
        default=True, description="Whether suggestion is Home Assistant 2025.10+ compatible"
    )


class DeviceContext(BaseModel):
    """Device context information"""
    
    device_id: str = Field(..., description="Device ID")
    capabilities: list[dict[str, Any]] = Field(
        default_factory=list, description="Device capabilities"
    )
    related_synergies: list[dict[str, Any]] = Field(
        default_factory=list, description="Related synergies"
    )
    compatible_blueprints: list[dict[str, Any]] = Field(
        default_factory=list, description="Compatible Home Assistant blueprints"
    )
    home_assistant_entities: list[dict[str, Any]] = Field(
        default_factory=list, description="Home Assistant entities for device"
    )
    home_assistant_services: list[dict[str, Any]] = Field(
        default_factory=list, description="Available Home Assistant services"
    )


class DeviceSuggestionsResponse(BaseModel):
    """Response model for device suggestions endpoint"""
    
    suggestions: list[DeviceSuggestion] = Field(
        ..., description="List of automation suggestions (3-5)"
    )
    device_context: DeviceContext = Field(..., description="Device context information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestions": [
                    {
                        "suggestion_id": "sug-123",
                        "title": "Motion-Activated Light",
                        "description": "Turn on the light when motion is detected",
                        "automation_preview": {
                            "trigger": "Motion sensor detects movement",
                            "action": "Turn on Office Light Switch",
                        },
                        "data_sources": {
                            "synergies": ["synergy-1"],
                            "device_capabilities": True,
                        },
                        "confidence_score": 0.85,
                        "quality_score": 0.78,
                        "enhanceable": True,
                        "home_assistant_compatible": True,
                    }
                ],
                "device_context": {
                    "device_id": "device_123",
                    "capabilities": [],
                    "related_synergies": [],
                    "compatible_blueprints": [],
                    "home_assistant_entities": [],
                    "home_assistant_services": [],
                }
            }
        }
    )
