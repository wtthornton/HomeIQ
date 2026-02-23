"""Local copies of schemas from ai-pattern-service.

These are copied from ai-pattern-service/src/blueprint_opportunity/schemas.py
and device_matcher.py to avoid sys.path manipulation for cross-service imports.
If the ai-pattern-service schemas change, these should be updated to match.

Origin: ai-pattern-service (blueprint_opportunity.schemas, blueprint_opportunity.device_matcher)
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class DeviceSignature(BaseModel):
    """Represents a device's signature for matching."""

    entity_id: str
    domain: str
    device_class: str | None = None
    area_id: str | None = None
    area_name: str | None = None
    device_id: str | None = None
    friendly_name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    integration: str | None = None


class BlueprintSummary(BaseModel):
    """Summary of a blueprint."""

    id: str
    name: str
    description: str | None = None
    source_url: str
    source_type: str
    domain: str = "automation"
    use_case: str | None = None
    required_domains: list[str] = Field(default_factory=list)
    required_device_classes: list[str] = Field(default_factory=list)
    community_rating: float = 0.0
    quality_score: float = 0.5
    stars: int = 0
    complexity: str = "medium"
    author: str | None = None


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
