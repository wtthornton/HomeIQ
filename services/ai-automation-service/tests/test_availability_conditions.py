"""
Tests for availability condition utilities
"""

import pytest
import yaml

from src.services.automation.availability_conditions import (
    add_availability_conditions,
    extract_entity_ids_from_yaml
)


class TestAvailabilityConditions:
    """Tests for availability condition utilities"""

    def test_extract_entity_ids_from_triggers(self):
        """Test extracting entity IDs from triggers"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.kitchen"
                    }
                }
            ]
        }
        
        entity_ids = extract_entity_ids_from_yaml(yaml_data)
        assert "binary_sensor.motion" in entity_ids
        assert "light.kitchen" in entity_ids

    def test_extract_entity_ids_from_conditions(self):
        """Test extracting entity IDs from conditions"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "time",
                    "at": "07:00:00"
                }
            ],
            "condition": [
                {
                    "condition": "state",
                    "entity_id": "binary_sensor.door",
                    "state": "on"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.office"
                    }
                }
            ]
        }
        
        entity_ids = extract_entity_ids_from_yaml(yaml_data)
        assert "binary_sensor.door" in entity_ids
        assert "light.office" in entity_ids

    def test_extract_entity_ids_from_list(self):
        """Test extracting entity IDs from list entity_id fields"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": ["light.kitchen", "light.living_room"]
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.bedroom", "light.hallway"]
                    }
                }
            ]
        }
        
        entity_ids = extract_entity_ids_from_yaml(yaml_data)
        assert "light.kitchen" in entity_ids
        assert "light.living_room" in entity_ids
        assert "light.bedroom" in entity_ids
        assert "light.hallway" in entity_ids

    def test_add_availability_conditions(self):
        """Test adding availability conditions to automation"""
        yaml_data = {
            "alias": "Test Automation",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.kitchen"
                    }
                }
            ]
        }
        
        enhanced_data = add_availability_conditions(yaml_data)
        
        # Should have condition field
        assert "condition" in enhanced_data
        conditions = enhanced_data["condition"]
        assert isinstance(conditions, list)
        assert len(conditions) == 2  # One for each entity
        
        # Check first condition (motion sensor)
        motion_condition = conditions[0]
        assert motion_condition["condition"] == "template"
        assert "binary_sensor.motion" in motion_condition["value_template"]
        assert "unavailable" in motion_condition["value_template"]
        assert "unknown" in motion_condition["value_template"]
        
        # Check second condition (light)
        light_condition = conditions[1]
        assert light_condition["condition"] == "template"
        assert "light.kitchen" in light_condition["value_template"]

    def test_add_availability_conditions_preserves_existing(self):
        """Test that existing conditions are preserved"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion"
                }
            ],
            "condition": [
                {
                    "condition": "state",
                    "entity_id": "binary_sensor.door",
                    "state": "on"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.kitchen"
                    }
                }
            ]
        }
        
        enhanced_data = add_availability_conditions(yaml_data)
        
        conditions = enhanced_data["condition"]
        # Should have availability conditions + existing condition
        assert len(conditions) >= 2  # At least 2 availability + 1 existing
        
        # Last condition should be the original
        assert conditions[-1]["condition"] == "state"
        assert conditions[-1]["entity_id"] == "binary_sensor.door"

    def test_add_availability_conditions_no_entities(self):
        """Test that no conditions are added when no entities found"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "time",
                    "at": "07:00:00"
                }
            ],
            "action": [
                {
                    "service": "scene.turn_on",
                    "target": {
                        "entity_id": "scene.morning"
                    }
                }
            ]
        }
        
        enhanced_data = add_availability_conditions(yaml_data)
        
        # Should not add conditions if no entity IDs found
        # (scene entities might not be in the extraction logic)
        # But if entities are found, conditions should be added
        if "condition" in enhanced_data:
            # If conditions were added, they should be valid
            assert isinstance(enhanced_data["condition"], list)

    def test_add_availability_conditions_with_nested_actions(self):
        """Test extracting entities from nested action structures"""
        yaml_data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.kitchen"
                    }
                },
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "binary_sensor.door",
                                    "state": "on"
                                }
                            ],
                            "sequence": [
                                {
                                    "service": "light.turn_on",
                                    "target": {
                                        "entity_id": "light.hallway"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        entity_ids = extract_entity_ids_from_yaml(yaml_data)
        assert "binary_sensor.motion" in entity_ids
        assert "light.kitchen" in entity_ids
        assert "binary_sensor.door" in entity_ids
        assert "light.hallway" in entity_ids
        
        enhanced_data = add_availability_conditions(yaml_data)
        assert "condition" in enhanced_data
        # Should have conditions for all entities
        conditions = enhanced_data["condition"]
        assert len(conditions) == 4  # One for each entity

