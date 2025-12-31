"""
Test for choose action 'then' → 'sequence' normalization fix.

This test verifies that the normalizer correctly converts deprecated 'then' keys
to 'sequence' keys in choose actions, fixing the Home Assistant API error:
"extra keys not allowed @ data['actions'][1]['then']"
"""

import pytest
import yaml
from yaml_validation_service.normalizer import YAMLNormalizer


class TestChooseThenToSequenceFix:
    """Test choose action 'then' → 'sequence' normalization."""
    
    def test_choose_then_to_sequence_conversion(self):
        """Test that 'then' keys in choose actions are converted to 'sequence'."""
        normalizer = YAMLNormalizer()
        
        # YAML with deprecated 'then' key (like the error in the image)
        yaml_content = """
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
        then:  # DEPRECATED - should be converted to 'sequence'
          - service: light.turn_on
            target:
              entity_id: light.office_desk
      - conditions:
          - condition: state
            entity_id: input_boolean.office_fun_mode
            state: "on"
        then:  # DEPRECATED - should be converted to 'sequence'
          - service: light.turn_on
            target:
              entity_id: light.office_ceiling
            data:
              brightness_pct: 80
"""
        
        normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
        
        # Verify 'then' was converted to 'sequence'
        assert "then:" not in normalized_yaml, "Deprecated 'then:' key should be removed"
        assert "sequence:" in normalized_yaml, "Should have 'sequence:' key after normalization"
        
        # Verify fix was logged
        then_fixes = [f for f in fixes_applied if "then:" in f and "sequence:" in f]
        assert len(then_fixes) >= 2, f"Expected at least 2 'then' → 'sequence' fixes, got: {fixes_applied}"
        
        # Verify YAML is still valid
        parsed = yaml.safe_load(normalized_yaml)
        assert "action" in parsed
        assert len(parsed["action"]) > 0
        assert "choose" in parsed["action"][0]
        
        # Verify choose structure is correct
        choose_action = parsed["action"][0]["choose"]
        assert isinstance(choose_action, list)
        assert len(choose_action) >= 2
        
        # Verify each choice has 'sequence' not 'then'
        for choice in choose_action:
            assert "sequence" in choice, f"Choice should have 'sequence' key: {choice}"
            assert "then" not in choice, f"Choice should not have 'then' key: {choice}"
    
    def test_choose_with_mixed_then_and_sequence(self):
        """Test choose action with both 'then' and 'sequence' (should normalize all)."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.temperature
            state: "hot"
        then:
          - service: climate.set_temperature
            target:
              entity_id: climate.living_room
            data:
              temperature: 20
      - conditions:
          - condition: state
            entity_id: sensor.temperature
            state: "cold"
        sequence:  # Already correct
          - service: climate.set_temperature
            target:
              entity_id: climate.living_room
            data:
              temperature: 25
"""
        
        normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
        
        # All should use 'sequence'
        assert "then:" not in normalized_yaml
        assert normalized_yaml.count("sequence:") == 2, "Both choices should use 'sequence'"
        
        # Verify structure
        parsed = yaml.safe_load(normalized_yaml)
        choose_action = parsed["action"][0]["choose"]
        for choice in choose_action:
            assert "sequence" in choice
            assert "then" not in choice
    
    def test_choose_with_nested_actions_in_sequence(self):
        """Test that nested actions in 'then' sequences are properly normalized."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: binary_sensor.motion
            state: "on"
        then:
          - service: light.turn_on
            target:
              entity_id: light.hallway
          - delay: "00:00:05"
          - service: light.turn_off
            target:
              entity_id: light.hallway
"""
        
        normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
        
        # Verify conversion
        assert "then:" not in normalized_yaml
        assert "sequence:" in normalized_yaml
        
        # Verify nested structure is preserved
        parsed = yaml.safe_load(normalized_yaml)
        sequence = parsed["action"][0]["choose"][0]["sequence"]
        assert len(sequence) == 3
        assert sequence[0]["service"] == "light.turn_on"
        assert sequence[1]["delay"] == "00:00:05"
        assert sequence[2]["service"] == "light.turn_off"
    
    def test_choose_default_without_then(self):
        """Test that 'default' in choose actions is not affected by 'then' conversion."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: input_boolean.mode
            state: "on"
        then:
          - service: script.enable_mode
      - conditions:
          - condition: state
            entity_id: input_boolean.mode
            state: "off"
        then:
          - service: script.disable_mode
    default:
      - service: notify.persistent_notification
        data:
          message: "Unknown mode"
"""
        
        normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
        
        # Verify 'then' → 'sequence' conversion
        assert "then:" not in normalized_yaml
        assert "sequence:" in normalized_yaml
        
        # Verify 'default' is preserved
        assert "default:" in normalized_yaml
        
        # Verify structure
        parsed = yaml.safe_load(normalized_yaml)
        choose_action = parsed["action"][0]["choose"]
        assert "default" in parsed["action"][0]
        assert len(choose_action) == 2
        for choice in choose_action:
            assert "sequence" in choice
    
    def test_real_world_office_automation_example(self):
        """Test with a real-world example similar to the error in the image."""
        normalizer = YAMLNormalizer()
        
        # This mimics the automation from the error image
        yaml_content = """
alias: "Office Motion Focus & Break Lighting"
description: "Advanced motion-based office lighting with focus mode, break reminders, welcome-back animation, and optional fun mode effects."
initial_state: true
mode: restart
trigger:
  - id: motion_on
    platform: state
    entity_id: group.office_motion_sensors
    from: "off"
    to: "on"
  - id: no_motion_1_min
    platform: state
    entity_id: group.office_motion_sensors
    to: "off"
    for: "00:01:00"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: motion_on
        then:
          - service: light.turn_on
            target:
              entity_id: light.office_desk
          - condition: state
            entity_id: input_boolean.office_fun_mode
            state: "on"
        then:
          - service: light.turn_on
            target:
              entity_id: light.office_ceiling
            data:
              brightness_pct: 80
"""
        
        normalized_yaml, fixes_applied = normalizer.normalize(yaml_content)
        
        # Critical: No 'then' keys should remain
        assert "then:" not in normalized_yaml, "All 'then' keys must be converted to 'sequence'"
        
        # Verify YAML is valid and can be parsed
        parsed = yaml.safe_load(normalized_yaml)
        assert parsed is not None
        assert "action" in parsed
        
        # Verify choose action structure
        action = parsed["action"][0]
        assert "choose" in action
        choose_list = action["choose"]
        assert isinstance(choose_list, list)
        
        # Verify each choice uses 'sequence'
        for choice in choose_list:
            if isinstance(choice, dict):
                assert "sequence" in choice or "conditions" in choice
                if "sequence" in choice:
                    assert "then" not in choice, "Choice should not have 'then' key"
        
        # This should now pass Home Assistant API validation
        # (no "extra keys not allowed @ data['actions'][1]['then']" error)
