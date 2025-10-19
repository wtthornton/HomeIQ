"""
API Request/Response Schemas

Pydantic models for API validation and documentation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Search filter parameters"""
    device: Optional[str] = None
    integration: Optional[str] = None
    use_case: Optional[str] = None
    min_quality: float = Field(default=0.7, ge=0.0, le=1.0)
    limit: int = Field(default=50, ge=1, le=500)


class AutomationResponse(BaseModel):
    """Single automation response"""
    id: int
    source: str
    source_id: str
    title: str
    description: str
    devices: List[str]
    integrations: List[str]
    triggers: List[Dict[str, Any]]
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    use_case: str
    complexity: str
    quality_score: float
    vote_count: int
    created_at: str
    updated_at: str
    last_crawled: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "source": "discourse",
                "source_id": "12345",
                "title": "Motion-activated night lighting",
                "description": "Turn on lights when motion detected at night",
                "devices": ["motion_sensor", "light"],
                "integrations": ["mqtt", "zigbee2mqtt"],
                "triggers": [{"type": "state", "entity": "binary_sensor.motion"}],
                "conditions": [{"type": "time", "after": "sunset"}],
                "actions": [{"device": "light", "action": "turn_on"}],
                "use_case": "comfort",
                "complexity": "low",
                "quality_score": 0.85,
                "vote_count": 542,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-10-01T00:00:00",
                "last_crawled": "2025-10-18T00:00:00",
                "metadata": {"tags": ["lighting", "motion"], "views": 1500}
            }
        }


class SearchResponse(BaseModel):
    """Search results response"""
    automations: List[Dict[str, Any]]
    count: int
    filters: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "automations": [
                    {
                        "id": 1,
                        "title": "Motion-activated night lighting",
                        "use_case": "comfort",
                        "quality_score": 0.85
                    }
                ],
                "count": 1,
                "filters": {
                    "device": "motion_sensor",
                    "use_case": "comfort",
                    "min_quality": 0.7,
                    "limit": 50
                }
            }
        }


class StatsResponse(BaseModel):
    """Corpus statistics response"""
    total: int
    avg_quality: float
    device_count: int
    integration_count: int
    devices: List[str]
    integrations: List[str]
    by_use_case: Dict[str, int]
    by_complexity: Dict[str, int]
    last_crawl_time: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 2543,
                "avg_quality": 0.76,
                "device_count": 52,
                "integration_count": 35,
                "devices": ["light", "motion_sensor", "switch", "..."],
                "integrations": ["mqtt", "zigbee2mqtt", "zha", "..."],
                "by_use_case": {
                    "energy": 450,
                    "comfort": 890,
                    "security": 780,
                    "convenience": 423
                },
                "by_complexity": {
                    "low": 1200,
                    "medium": 980,
                    "high": 363
                },
                "last_crawl_time": "2025-10-18T02:00:00"
            }
        }

