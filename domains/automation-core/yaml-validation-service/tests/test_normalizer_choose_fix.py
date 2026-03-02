"""
Tests for normalizer.py — YAMLNormalizer
"""

import pytest
import yaml
from src.yaml_validation_service.normalizer import YAMLNormalizer


class TestYAMLNormalizer:
    """Test YAMLNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        return YAMLNormalizer()

    def test___init__(self, normalizer):
        """Test initialization creates instance."""
        assert normalizer is not None

    def test_normalize_passthrough_valid_yaml(self, normalizer):
        """Test valid canonical YAML passes through with minimal changes."""
        valid_yaml = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        result, fixes = normalizer.normalize(valid_yaml)
        parsed = yaml.safe_load(result)
        assert parsed["alias"] == "Test"
        assert parsed["trigger"][0]["platform"] == "state"
        assert parsed["action"][0]["service"] == "light.turn_on"

    def test_normalize_plural_triggers_to_trigger(self, normalizer):
        """Test 'triggers' is renamed to 'trigger'."""
        raw = "alias: Test\ntriggers:\n  - platform: state\naction:\n  - service: light.turn_on"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert "trigger" in parsed
        assert "triggers" not in parsed
        assert any("triggers" in f and "trigger" in f for f in fixes)

    def test_normalize_plural_actions_to_action(self, normalizer):
        """Test 'actions' is renamed to 'action'."""
        raw = "alias: Test\ntrigger:\n  - platform: state\nactions:\n  - service: light.turn_on"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert "action" in parsed
        assert "actions" not in parsed

    def test_normalize_plural_conditions_to_condition(self, normalizer):
        """Test 'conditions' is renamed to 'condition'."""
        raw = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\nconditions:\n  - condition: state"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert "condition" in parsed
        assert "conditions" not in parsed

    def test_normalize_trigger_field_to_platform(self, normalizer):
        """Test trigger item 'trigger:' field is converted to 'platform:'."""
        raw = "alias: Test\ntrigger:\n  - trigger: state\n    entity_id: light.office\naction:\n  - service: light.turn_on"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert parsed["trigger"][0]["platform"] == "state"
        assert "trigger" not in parsed["trigger"][0] or parsed["trigger"][0].get("trigger") is None

    def test_normalize_action_field_to_service(self, normalizer):
        """Test action item 'action:' field is converted to 'service:'."""
        raw = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - action: light.turn_on"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert parsed["action"][0]["service"] == "light.turn_on"

    def test_normalize_continue_on_error_true(self, normalizer):
        """Test continue_on_error: true is converted to error: continue."""
        raw = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\ncontinue_on_error: true"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert parsed.get("error") == "continue"
        assert "continue_on_error" not in parsed

    def test_normalize_continue_on_error_false(self, normalizer):
        """Test continue_on_error: false is converted to error: stop."""
        raw = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\ncontinue_on_error: false"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert parsed.get("error") == "stop"

    def test_normalize_choose_then_to_sequence(self, normalizer):
        """Test choose action 'then:' is converted to 'sequence:'."""
        raw = """alias: Test
trigger:
  - platform: state
action:
  - choose:
      - conditions:
          - condition: state
        then:
          - service: light.turn_on
"""
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        choose_action = parsed["action"][0]["choose"][0]
        assert "sequence" in choose_action
        assert "then" not in choose_action
        assert any("then" in f and "sequence" in f for f in fixes)

    def test_normalize_adds_initial_state(self, normalizer):
        """Test initial_state: true is added when missing."""
        raw = "alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        result, fixes = normalizer.normalize(raw)
        parsed = yaml.safe_load(result)
        assert parsed.get("initial_state") is True

    def test_normalize_invalid_yaml_returns_original(self, normalizer):
        """Test invalid YAML returns original string."""
        invalid = "{{not: valid: yaml: [["
        result, fixes = normalizer.normalize(invalid)
        assert result == invalid
        assert fixes == []

    def test_normalize_non_dict_yaml_returns_original(self, normalizer):
        """Test non-dict YAML (e.g. list) returns original."""
        list_yaml = "- item1\n- item2"
        result, fixes = normalizer.normalize(list_yaml)
        assert result == list_yaml
