"""
Integration test to verify the fix for Home Assistant API error:
"extra keys not allowed @ data['actions'][1]['then']"

This test simulates the exact error scenario from the automation preview modal.
"""

import pytest
import yaml
from yaml_validation_service.normalizer import YAMLNormalizer


def test_api_error_scenario_fix():
    """
    Test that YAML with 'then' keys in choose actions is normalized correctly,
    preventing the Home Assistant API error.
    
    This simulates the exact error from the image:
    "Failed to create automation: 400 - {"message":"Message malformed: 
     extra keys not allowed @ data['actions'][1]['then']"}"
    """
    normalizer = YAMLNormalizer()
    
    # This is the problematic YAML structure that causes the API error
    problematic_yaml = """
alias: "Office Motion Focus & Break Lighting"
description: "Advanced motion-based office lighting"
initial_state: true
mode: restart
trigger:
  - id: motion_on
    platform: state
    entity_id: group.office_motion_sensors
    from: "off"
    to: "on"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: motion_on
        then:  # THIS CAUSES THE ERROR - should be 'sequence'
          - service: light.turn_on
            target:
              entity_id: light.office_desk
"""
    
    # Normalize the YAML
    normalized_yaml, fixes_applied = normalizer.normalize(problematic_yaml)
    
    # CRITICAL CHECKS:
    # 1. No 'then' keys should remain
    assert "then:" not in normalized_yaml, (
        "ERROR: 'then' key still present! This will cause API error: "
        "'extra keys not allowed @ data['actions'][1]['then']'"
    )
    
    # 2. 'sequence' key should be present
    assert "sequence:" in normalized_yaml, (
        "ERROR: 'sequence' key missing! Normalization failed."
    )
    
    # 3. YAML should be valid
    parsed = yaml.safe_load(normalized_yaml)
    assert parsed is not None, "Normalized YAML should be parseable"
    
    # 4. Structure should be correct for Home Assistant API
    assert "action" in parsed, "Should have 'action' key"
    assert len(parsed["action"]) > 0, "Should have at least one action"
    
    action = parsed["action"][0]
    assert "choose" in action, "Should have 'choose' action"
    
    choose_list = action["choose"]
    assert isinstance(choose_list, list), "Choose should be a list"
    assert len(choose_list) > 0, "Choose should have at least one choice"
    
    # 5. Each choice should have 'sequence' not 'then'
    for i, choice in enumerate(choose_list):
        assert isinstance(choice, dict), f"Choice {i} should be a dict"
        assert "sequence" in choice, (
            f"Choice {i} should have 'sequence' key (not 'then'). "
            f"Choice content: {choice}"
        )
        assert "then" not in choice, (
            f"Choice {i} should NOT have 'then' key. "
            f"This would cause API error. Choice content: {choice}"
        )
    
    # 6. Verify fix was logged
    then_fixes = [f for f in fixes_applied if "then" in f.lower() and "sequence" in f.lower()]
    assert len(then_fixes) > 0, (
        f"Expected fix log for 'then' → 'sequence' conversion. "
        f"Fixes applied: {fixes_applied}"
    )
    
    # 7. Verify the normalized YAML structure matches Home Assistant API requirements
    # The API expects: action[0].choose[0].sequence (not .then)
    first_choice = choose_list[0]
    sequence = first_choice["sequence"]
    assert isinstance(sequence, list), "Sequence should be a list of actions"
    assert len(sequence) > 0, "Sequence should have at least one action"
    assert "service" in sequence[0], "First action should have 'service' key"
    
    print("\n✅ SUCCESS: YAML normalized correctly!")
    print(f"   - Removed {len(then_fixes)} 'then' key(s)")
    print(f"   - Added 'sequence' key(s)")
    print(f"   - YAML structure is valid for Home Assistant API")
    print(f"   - This will NOT cause 'extra keys not allowed' error")


def test_multiple_choose_actions_with_then():
    """Test that multiple choose actions with 'then' are all fixed."""
    normalizer = YAMLNormalizer()
    
    yaml_content = """
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.temp1
            state: "hot"
        then:
          - service: climate.set_temperature
            data:
              temperature: 20
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.temp2
            state: "cold"
        then:
          - service: climate.set_temperature
            data:
              temperature: 25
"""
    
    normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
    
    # Both choose actions should be fixed
    assert normalized_yaml.count("then:") == 0
    assert normalized_yaml.count("sequence:") == 2
    
    parsed = yaml.safe_load(normalized_yaml)
    for action in parsed["action"]:
        if "choose" in action:
            for choice in action["choose"]:
                assert "sequence" in choice
                assert "then" not in choice
