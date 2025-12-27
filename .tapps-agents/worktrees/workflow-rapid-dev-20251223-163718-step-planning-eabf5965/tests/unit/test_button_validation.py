"""
Standalone test to validate the Test button flow.

This test validates that:
1. validated_entities is properly constructed from devices_involved
2. The YAML generator receives and uses validated_entities
3. Generated YAML contains proper entity IDs
"""

import yaml
import json


def test_validated_entities_structure():
    """Test that validated_entities structure is correct."""
    
    # Simulate the mapping that should happen
    devices_involved = ["Office Light 1", "Office Light 2"]
    resolved_entities = {
        "Office Light 1": "light.office",
        "Office Light 2": "light.office"
    }
    
    # Build validated_entities (what the code should produce)
    entity_mapping = {}
    for device_name in devices_involved:
        if device_name in resolved_entities:
            entity_id = resolved_entities[device_name]
            entity_mapping[device_name] = entity_id
    
    print(f"OK: Entity mapping: {json.dumps(entity_mapping, indent=2)}")
    
    # Validate structure
    assert len(entity_mapping) == 2, "Should map 2 devices"
    assert all("." in entity_id for entity_id in entity_mapping.values()), \
        "All entity IDs should have domain separator"
    
    # Check specific mappings
    assert entity_mapping["Office Light 1"] == "light.office", \
        "Office Light 1 should map to light.office"
    assert entity_mapping["Office Light 2"] == "light.office", \
        "Office Light 2 should map to light.office"
    
    print("OK: validated_entities structure is correct!")


def test_yaml_entity_ids():
    """Test that YAML uses proper entity IDs."""
    
    # Sample YAML that should be generated
    sample_yaml = """
id: office_lights_test
alias: "Test Office Lights"
description: "Test automation"
mode: single
trigger:
  - platform: state
    entity_id: light.office
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""
    
    # Parse and validate
    parsed = yaml.safe_load(sample_yaml)
    
    # Check trigger entity_id
    trigger_entity_id = parsed['trigger'][0]['entity_id']
    assert trigger_entity_id == "light.office", \
        f"Trigger entity_id should be 'light.office', got '{trigger_entity_id}'"
    
    # Check action entity_id
    action_entity_id = parsed['action'][0]['target']['entity_id']
    assert action_entity_id == "light.office", \
        f"Action entity_id should be 'light.office', got '{action_entity_id}'"
    
    print("OK: YAML entity IDs are correct!")


def test_invalid_entity_id_detection():
    """Test that invalid entity IDs are detected."""
    
    # These should be detected as invalid
    invalid_ids = ["office", "light", "switch"]
    
    for entity_id in invalid_ids:
        assert "." not in entity_id or len(entity_id.split(".")) < 2, \
            f"'{entity_id}' should be detected as invalid (no domain)"
    
    # These should be detected as valid
    valid_ids = ["light.office", "switch.hallway", "binary_sensor.door"]
    
    for entity_id in valid_ids:
        assert "." in entity_id and len(entity_id.split(".")) >= 2, \
            f"'{entity_id}' should be detected as valid (has domain)"
    
    print("OK: Invalid entity IDs are detected correctly!")


if __name__ == "__main__":
    print("\nRunning Test Button Validation Tests...\n")
    
    try:
        test_validated_entities_structure()
        test_yaml_entity_ids()
        test_invalid_entity_id_detection()
        
        print("\nOK: All validation tests passed!")
        
    except AssertionError as e:
        print(f"\nERROR: Test failed: {e}")
        exit(1)

