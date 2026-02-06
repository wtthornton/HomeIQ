"""Local copies of schemas from ai-pattern-service.

These are copied from ai-pattern-service/src/blueprint_opportunity/schemas.py
and device_matcher.py to avoid sys.path manipulation for cross-service imports.
If the ai-pattern-service schemas change, these should be updated to match.

Origin: ai-pattern-service (blueprint_opportunity.schemas, blueprint_opportunity.device_matcher)
"""

from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field


class DeviceSignature(BaseModel):
    """Represents a device's signature for matching."""

    entity_id: str
    domain: str
    device_class: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    device_id: Optional[str] = None
    friendly_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    integration: Optional[str] = None


class BlueprintSummary(BaseModel):
    """Summary of a blueprint."""

    id: str
    name: str
    description: Optional[str] = None
    source_url: str
    source_type: str
    domain: str = "automation"
    use_case: Optional[str] = None
    required_domains: list[str] = Field(default_factory=list)
    required_device_classes: list[str] = Field(default_factory=list)
    community_rating: float = 0.0
    quality_score: float = 0.5
    stars: int = 0
    complexity: str = "medium"
    author: Optional[str] = None


@dataclass
class UserProfile:
    """User profile for personalized blueprint recommendations."""

    preferred_domains: list[str] = field(default_factory=list)
    preferred_use_cases: list[str] = field(default_factory=list)
    prefers_simple_automations: bool = True
    prefers_energy_saving: bool = False
    prefers_security_focused: bool = False
    deployed_blueprint_ids: list[str] = field(default_factory=list)
    dismissed_blueprint_ids: list[str] = field(default_factory=list)
    has_presence_detection: bool = False
    has_voice_assistant: bool = False
    home_type: str = "house"
    active_hours_start: int = 6
    active_hours_end: int = 22
