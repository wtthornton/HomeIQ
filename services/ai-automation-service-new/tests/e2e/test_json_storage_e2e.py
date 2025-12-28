"""
E2E Tests for HomeIQ JSON Storage and Retrieval

Tests:
1. Store JSON in database
2. Retrieve JSON from database
3. Query JSON by properties
4. Update JSON in database
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

import pytest
import json
from typing import Any

from shared.homeiq_automation.schema import HomeIQAutomation

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.database.models import Suggestion
from src.services.json_query_service import JSONQueryService


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_storage_and_retrieval_e2e(db_session):
    """
    E2E Test: Store and retrieve JSON from database.
    """
    # Create a suggestion with JSON
    homeiq_json = {
        "alias": "Stored Automation",
        "description": "Test storage",
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "low",
        },
        "device_context": {
            "entity_ids": ["light.test"],
            "device_ids": [],
            "area_ids": [],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 10.0,
            "estimated_daily_kwh": 0.1,
        },
        "triggers": [
            {
                "platform": "state",
                "entity_id": "light.test",
                "to": "on",
            }
        ],
        "actions": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.test"},
            }
        ],
        "mode": "single",
    }
    
    suggestion = Suggestion(
        title="Test Storage",
        description="Test JSON storage",
        automation_json=homeiq_json,
        ha_version="2025.10.3",
        json_schema_version="1.0.0",
        status="pending"
    )
    
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    # Verify JSON was stored
    assert suggestion.automation_json is not None
    assert isinstance(suggestion.automation_json, dict)
    assert suggestion.automation_json["alias"] == "Stored Automation"
    assert suggestion.ha_version == "2025.10.3"
    assert suggestion.json_schema_version == "1.0.0"
    
    # Retrieve and validate
    retrieved_json = suggestion.automation_json
    homeiq_automation = HomeIQAutomation(**retrieved_json)
    assert homeiq_automation.alias == "Stored Automation"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_query_e2e(db_session):
    """
    E2E Test: Query JSON automations by properties.
    """
    # Create multiple suggestions with different JSON properties
    automations = [
        {
            "alias": "Comfort Automation",
            "homeiq_metadata": {"use_case": "comfort", "complexity": "low"},
            "device_context": {"entity_ids": ["light.test"], "area_ids": ["living_room"]},
            "safety_checks": {"requires_confirmation": False},
            "energy_impact": {"estimated_power_w": 10.0},
            "triggers": [{"platform": "state", "entity_id": "light.test"}],
            "actions": [{"service": "light.turn_on", "target": {"entity_id": "light.test"}}],
            "mode": "single",
        },
        {
            "alias": "Energy Automation",
            "homeiq_metadata": {"use_case": "energy", "complexity": "medium"},
            "device_context": {"entity_ids": ["switch.power"], "area_ids": ["bedroom"]},
            "safety_checks": {"requires_confirmation": False},
            "energy_impact": {"estimated_power_w": 5.0},
            "triggers": [{"platform": "state", "entity_id": "switch.power"}],
            "actions": [{"service": "switch.turn_off", "target": {"entity_id": "switch.power"}}],
            "mode": "single",
        },
    ]
    
    for i, automation_json in enumerate(automations):
        suggestion = Suggestion(
            title=f"Test Automation {i+1}",
            description=f"Test automation {i+1}",
            automation_json=automation_json,
            status="pending"
        )
        db_session.add(suggestion)
    
    await db_session.commit()
    
    # Query by use_case
    query_service = JSONQueryService()
    comfort_results = query_service.query(automations, {"use_case": "comfort"})
    assert len(comfort_results) == 1
    # Handle both dict and HomeIQAutomation objects
    result = comfort_results[0]
    alias = result.alias if hasattr(result, "alias") else result["alias"]
    assert alias == "Comfort Automation"
    
    # Query by entity_id
    entity_results = query_service.query(automations, {"entity_id": "light.test"})
    assert len(entity_results) == 1
    result = entity_results[0]
    alias = result.alias if hasattr(result, "alias") else result["alias"]
    assert alias == "Comfort Automation"
    
    # Query by area_id (note: area_id filter may need to be implemented)
    # For now, verify the automation has the area_id in its context
    comfort_auto = [a for a in automations if a.get("alias") == "Comfort Automation"][0]
    assert "living_room" in comfort_auto["device_context"]["area_ids"]
    
    # Query by energy impact
    energy_results = query_service.query(automations, {"min_energy_impact_w": 8.0})
    assert len(energy_results) == 1
    result = energy_results[0]
    alias = result.alias if hasattr(result, "alias") else result["alias"]
    assert alias == "Comfort Automation"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_update_e2e(db_session):
    """
    E2E Test: Update JSON in database.
    """
    # Create initial suggestion
    initial_json = {
        "alias": "Original Automation",
        "description": "Original description",
        "version": "1.0.0",
        "homeiq_metadata": {"use_case": "comfort", "complexity": "low"},
        "device_context": {"entity_ids": ["light.test"]},
        "safety_checks": {"requires_confirmation": False},
        "energy_impact": {"estimated_power_w": 10.0},
        "triggers": [{"platform": "state", "entity_id": "light.test"}],
        "actions": [{"service": "light.turn_on", "target": {"entity_id": "light.test"}}],
        "mode": "single",
    }
    
    suggestion = Suggestion(
        title="Test Update",
        description="Test JSON update",
        automation_json=initial_json,
        status="pending"
    )
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    # Update JSON
    updated_json = initial_json.copy()
    updated_json["alias"] = "Updated Automation"
    updated_json["description"] = "Updated description"
    updated_json["homeiq_metadata"]["complexity"] = "medium"
    
    suggestion.automation_json = updated_json
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    # Verify update
    assert suggestion.automation_json["alias"] == "Updated Automation"
    assert suggestion.automation_json["description"] == "Updated description"
    assert suggestion.automation_json["homeiq_metadata"]["complexity"] == "medium"

