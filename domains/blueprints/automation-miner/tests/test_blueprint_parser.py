"""
Unit tests for blueprint parser
Tests YAML parsing for Home Assistant blueprints
"""

from src.miner.parser import AutomationParser


class TestAutomationParser:
    """Test automation parser functionality"""

    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = AutomationParser()
        assert parser is not None

    def test_parse_simple_blueprint(self):
        """Test parsing a simple blueprint YAML"""
        blueprint_yaml = """
blueprint:
  name: Test Automation
  domain: automation
  input:
    entity:
      name: Entity
      selector:
        entity: {}
"""
        parser = AutomationParser()
        # parse_yaml handles string input and dispatches to parse_blueprint
        result = parser.parse_yaml(blueprint_yaml)
        assert result is not None
        assert "_blueprint_metadata" in result
