"""
Unit tests for blueprint parser
Tests YAML parsing for Home Assistant blueprints
"""
import sys
from pathlib import Path

# Add service src to path
service_dir = Path(__file__).parent.parent
src_path = service_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from miner.parser import AutomationParser


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
        result = parser.parse_blueprint(blueprint_yaml)
        assert result is not None
        assert "blueprint" in result

