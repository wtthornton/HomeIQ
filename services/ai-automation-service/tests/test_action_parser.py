"""
Unit tests for ActionParser
"""

import pytest
from services.automation.action_exceptions import ActionParseError
from services.automation.action_parser import ActionParser


class TestActionParser:
    """Test ActionParser functionality"""

    def test_parse_simple_service_call(self):
        """Test parsing simple service call"""
        yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_pct: 100
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['type'] == 'service_call'
        assert actions[0]['domain'] == 'light'
        assert actions[0]['service'] == 'turn_on'
        assert actions[0]['target']['entity_id'] == 'light.office'
        assert actions[0]['data']['brightness_pct'] == 100

    def test_parse_delay(self):
        """Test parsing delay action"""
        yaml_str = """
actions:
  - delay: '00:00:02'
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['type'] == 'delay'
        assert actions[0]['delay'] == 2.0

    def test_parse_delay_dict(self):
        """Test parsing delay as dictionary"""
        yaml_str = """
actions:
  - delay:
      seconds: 2
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['type'] == 'delay'
        assert actions[0]['delay'] == 2.0

    def test_parse_sequence(self):
        """Test parsing sequence of actions"""
        yaml_str = """
actions:
  - sequence:
      - action: light.turn_on
        target:
          entity_id: light.office
      - delay: '00:00:01'
      - action: light.turn_off
        target:
          entity_id: light.office
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['type'] == 'sequence'
        assert len(actions[0]['actions']) == 3

    def test_parse_parallel(self):
        """Test parsing parallel actions"""
        yaml_str = """
actions:
  - parallel:
      - action: light.turn_on
        target:
          entity_id: light.office
      - action: light.turn_on
        target:
          entity_id: light.kitchen
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['type'] == 'parallel'
        assert len(actions[0]['actions']) == 2

    def test_parse_multiple_actions(self):
        """Test parsing multiple top-level actions"""
        yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
  - delay: '00:00:02'
  - action: light.turn_off
    target:
      entity_id: light.office
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 3
        assert actions[0]['type'] == 'service_call'
        assert actions[1]['type'] == 'delay'
        assert actions[2]['type'] == 'service_call'

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML"""
        yaml_str = "invalid: yaml: content: ["

        with pytest.raises(ActionParseError):
            ActionParser.parse_actions_from_yaml(yaml_str)

    def test_parse_empty_actions(self):
        """Test parsing YAML with no actions"""
        yaml_str = """
actions: []
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 0

    def test_parse_delay_minutes_hours(self):
        """Test parsing delay with minutes and hours"""
        yaml_str = """
actions:
  - delay:
      hours: 1
      minutes: 30
      seconds: 15
"""
        actions = ActionParser.parse_actions_from_yaml(yaml_str)

        assert len(actions) == 1
        assert actions[0]['delay'] == 5415.0  # 1 hour + 30 minutes + 15 seconds

