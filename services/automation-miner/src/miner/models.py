"""
Pydantic Models for Automation Metadata

Context7-validated data validation using Pydantic BaseModel
"""
from datetime import datetime
from typing import List, Dict, Any, Literal, Optional, Annotated
from pydantic import BaseModel, Field, field_validator


class AutomationMetadata(BaseModel):
    """
    Structured metadata for a community automation
    
    Validated using Pydantic for data quality assurance.
    """
    # Core fields
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(max_length=2000)
    
    # Structured data
    devices: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Classification
    use_case: Literal['energy', 'comfort', 'security', 'convenience']
    complexity: Literal['low', 'medium', 'high']
    
    # Quality metrics
    quality_score: Annotated[float, Field(ge=0.0, le=1.0)]
    vote_count: int = Field(ge=0, default=0)
    
    # Source tracking
    source: Literal['discourse', 'github']
    source_id: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('devices')
    @classmethod
    def normalize_devices(cls, v: List[str]) -> List[str]:
        """
        Normalize device names (lowercase, underscores)
        
        Example: "Motion Sensor" → "motion_sensor"
        """
        if not v:
            return []
        return [device.lower().replace(' ', '_').replace('-', '_') for device in v]
    
    @field_validator('integrations')
    @classmethod
    def normalize_integrations(cls, v: List[str]) -> List[str]:
        """Normalize integration names"""
        if not v:
            return []
        return [integration.lower().replace(' ', '_').replace('-', '_') for integration in v]
    
    @field_validator('title')
    @classmethod
    def clean_title(cls, v: str) -> str:
        """Remove extra whitespace and normalize title"""
        return ' '.join(v.split()).strip()
    
    @field_validator('description')
    @classmethod
    def clean_description(cls, v: str) -> str:
        """Remove extra whitespace and normalize description"""
        # Remove multiple newlines
        cleaned = '\n'.join(line.strip() for line in v.split('\n') if line.strip())
        return cleaned.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Motion-activated night lighting",
                "description": "Turn on lights when motion detected at night",
                "devices": ["motion_sensor", "light"],
                "integrations": ["mqtt", "zigbee2mqtt"],
                "triggers": [{"type": "state", "entity": "binary_sensor.motion"}],
                "conditions": [{"type": "time", "after": "sunset"}],
                "actions": [{"device": "light", "action": "turn_on", "brightness": 50}],
                "use_case": "comfort",
                "complexity": "low",
                "quality_score": 0.85,
                "vote_count": 542,
                "source": "discourse",
                "source_id": "12345",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-10-01T00:00:00Z"
            }
        }


class ParsedAutomation(BaseModel):
    """
    Intermediate model for parsed YAML automation
    
    Used during normalization before creating AutomationMetadata
    """
    raw_yaml: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    
    # Extracted components
    devices: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Classification
    use_case: Optional[str] = None
    complexity: Optional[str] = None
    
    # Metadata
    has_yaml: bool = False
    has_description: bool = False
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)

