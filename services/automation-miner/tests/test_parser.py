"""
Unit Tests for AutomationParser

Tests YAML parsing, device extraction, classification, quality scoring.
"""
import pytest
from datetime import datetime, timedelta

from src.miner.parser import AutomationParser
from src.miner.models import AutomationMetadata


class TestAutomationParser:
    """Test AutomationParser functionality"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return AutomationParser()
    
    def test_parse_yaml_valid(self, parser):
        """Test parsing valid YAML automation"""
        yaml_str = """
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: 'on'
action:
  - service: light.turn_on
    entity_id: light.bedroom
"""
        result = parser.parse_yaml(yaml_str)
        
        assert result is not None
        assert 'trigger' in result
        assert 'action' in result
    
    def test_parse_yaml_invalid(self, parser):
        """Test parsing invalid YAML"""
        yaml_str = "invalid: yaml: structure:"
        result = parser.parse_yaml(yaml_str)
        
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_extract_devices(self, parser):
        """Test device extraction from automation"""
        automation = {
            'trigger': [
                {'platform': 'state', 'entity_id': 'binary_sensor.motion'}
            ],
            'action': [
                {'service': 'light.turn_on', 'entity_id': 'light.bedroom'}
            ]
        }
        
        devices = parser.extract_devices(automation)
        
        assert 'light' in devices
        assert 'binary_sensor' in devices
    
    def test_extract_integrations(self, parser):
        """Test integration extraction"""
        automation = {
            'trigger': [
                {'platform': 'mqtt', 'topic': 'test'}
            ]
        }
        
        integrations = parser.extract_integrations(automation)
        
        assert 'mqtt' in integrations
    
    def test_classify_use_case_security(self, parser):
        """Test use case classification - security"""
        automation = {}
        title = "Motion-activated alarm system"
        description = "Trigger alarm when motion detected at door"
        
        use_case = parser.classify_use_case(automation, title, description)
        
        assert use_case == 'security'
    
    def test_classify_use_case_energy(self, parser):
        """Test use case classification - energy"""
        automation = {}
        title = "Power saving automation"
        description = "Turn off devices to save electricity"
        
        use_case = parser.classify_use_case(automation, title, description)
        
        assert use_case == 'energy'
    
    def test_classify_use_case_comfort(self, parser):
        """Test use case classification - comfort"""
        automation = {}
        title = "Temperature control"
        description = "Adjust thermostat for comfort"
        
        use_case = parser.classify_use_case(automation, title, description)
        
        assert use_case == 'comfort'
    
    def test_calculate_complexity_low(self, parser):
        """Test complexity calculation - low"""
        automation = {
            'trigger': [{'platform': 'state'}],
            'action': [{'service': 'light.turn_on'}]
        }
        
        complexity = parser.calculate_complexity(automation)
        
        assert complexity == 'low'
    
    def test_calculate_complexity_medium(self, parser):
        """Test complexity calculation - medium"""
        automation = {
            'trigger': [{'platform': 'state'}, {'platform': 'time'}],
            'condition': [{'condition': 'state'}, {'condition': 'time'}],
            'action': [{'service': 'light.turn_on'}, {'service': 'notify.send'}]
        }
        
        complexity = parser.calculate_complexity(automation)
        
        assert complexity == 'medium'
    
    def test_calculate_complexity_high(self, parser):
        """Test complexity calculation - high"""
        automation = {
            'trigger': [{'platform': 'state'}] * 3,
            'condition': [{'condition': 'state'}] * 3,
            'action': [{'service': 'light.turn_on'}] * 3
        }
        
        complexity = parser.calculate_complexity(automation)
        
        assert complexity == 'high'
    
    def test_calculate_quality_score(self, parser):
        """Test quality score calculation"""
        # High votes, recent, complete
        score1 = parser.calculate_quality_score(
            votes=1000,
            age_days=30,
            completeness=1.0
        )
        assert score1 >= 0.8
        
        # Low votes, old, incomplete
        score2 = parser.calculate_quality_score(
            votes=10,
            age_days=700,
            completeness=0.3
        )
        assert score2 < 0.5
    
    def test_remove_pii(self, parser):
        """Test PII removal"""
        text = "Turn on light.bedroom_lamp when motion detected at 192.168.1.100"
        cleaned = parser.remove_pii(text)
        
        assert 'bedroom_lamp' not in cleaned
        assert '192.168.1.100' not in cleaned
        assert 'light' in cleaned


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

