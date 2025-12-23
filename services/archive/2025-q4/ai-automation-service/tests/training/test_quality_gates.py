"""
Unit tests for quality gates validator.

Tests for Story AI11.9: End-to-End Pipeline Integration
"""

import pytest
from src.training.quality_gates import QualityGateValidator


class TestQualityGateValidator:
    """Test QualityGateValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = QualityGateValidator()
        assert validator.naming_threshold == 0.95
        assert validator.event_diversity_min == 7
        assert validator.precision_threshold == 0.80
        assert validator.false_positive_threshold == 0.20
        assert validator.performance_threshold_ms == 200
    
    def test_validate_naming_consistency(self):
        """Test naming consistency validation."""
        validator = QualityGateValidator(naming_threshold=0.95)
        
        # Create home with compliant devices
        home = {
            'devices': [
                {
                    'entity_id': 'light.kitchen_main',
                    'friendly_name': 'Kitchen Main Light',
                    'voice_friendly_name': 'Kitchen Light'
                },
                {
                    'entity_id': 'switch.living_room_lamp',
                    'friendly_name': 'Living Room Lamp',
                    'voice_friendly_name': 'Living Room Lamp'
                }
            ]
        }
        
        result = validator._validate_naming_consistency(home)
        
        assert 'pass' in result
        assert 'score' in result
        assert result['score'] >= 0.95  # Should pass threshold
        assert result['compliant'] == 2
        assert result['total'] == 2
    
    def test_validate_naming_consistency_fail(self):
        """Test naming consistency validation failure."""
        validator = QualityGateValidator(naming_threshold=0.95)
        
        # Create home with non-compliant devices
        home = {
            'devices': [
                {
                    'entity_id': 'light.kitchen_main',  # Compliant
                    'friendly_name': 'Kitchen Main Light',
                    'voice_friendly_name': 'Kitchen Light'
                },
                {
                    'entity_id': '',  # Non-compliant
                    'friendly_name': '',  # Non-compliant
                }
            ]
        }
        
        result = validator._validate_naming_consistency(home)
        
        assert 'pass' in result
        assert result['score'] < 0.95  # Should fail threshold
        assert result['compliant'] == 1
        assert result['total'] == 2
    
    def test_validate_event_diversity(self):
        """Test event diversity validation."""
        validator = QualityGateValidator(event_diversity_min=7)
        
        # Create home with diverse events
        home = {
            'events': [
                {'event_type': 'state_changed'},
                {'event_type': 'automation_triggered'},
                {'event_type': 'script_started'},
                {'event_type': 'scene_activated'},
                {'event_type': 'voice_command'},
                {'event_type': 'webhook_triggered'},
                {'event_type': 'api_call'},
                {'event_type': 'state_changed'},  # Duplicate
            ]
        }
        
        result = validator._validate_event_diversity(home)
        
        assert 'pass' in result
        assert result['score'] == 7  # 7 unique types
        assert result['pass'] is True
        assert len(result['event_types']) == 7
    
    def test_validate_event_diversity_fail(self):
        """Test event diversity validation failure."""
        validator = QualityGateValidator(event_diversity_min=7)
        
        # Create home with limited event types
        home = {
            'events': [
                {'event_type': 'state_changed'},
                {'event_type': 'automation_triggered'},
            ]
        }
        
        result = validator._validate_event_diversity(home)
        
        assert 'pass' in result
        assert result['score'] == 2  # Only 2 types
        assert result['pass'] is False
    
    def test_validate_ground_truth(self):
        """Test ground truth validation."""
        validator = QualityGateValidator()
        
        # Create home with ground truth
        home = {
            'ground_truth': {
                'home_id': 'test_home',
                'expected_patterns': [
                    {'pattern_type': 'motion_light', 'entities': ['binary_sensor.motion', 'light.kitchen']},
                    {'pattern_type': 'time_of_day', 'entities': ['light.living_room']}
                ]
            }
        }
        
        result = validator._validate_ground_truth(home)
        
        assert 'pass' in result
        assert result['expected_patterns_count'] == 2
    
    def test_validate_ground_truth_missing(self):
        """Test ground truth validation when missing."""
        validator = QualityGateValidator()
        
        home = {
            'events': []
        }
        
        result = validator._validate_ground_truth(home)
        
        assert 'pass' in result
        assert result['pass'] is False
        assert 'message' in result
    
    def test_validate_performance(self):
        """Test performance validation."""
        validator = QualityGateValidator(performance_threshold_ms=200)
        
        # Create home with good performance
        home = {
            'generation_metadata': {
                'generation_time_ms': 150
            }
        }
        
        result = validator._validate_performance(home)
        
        assert 'pass' in result
        assert result['time_ms'] == 150
        assert result['pass'] is True
    
    def test_validate_performance_fail(self):
        """Test performance validation failure."""
        validator = QualityGateValidator(performance_threshold_ms=200)
        
        # Create home with poor performance
        home = {
            'generation_metadata': {
                'generation_time_ms': 300
            }
        }
        
        result = validator._validate_performance(home)
        
        assert 'pass' in result
        assert result['time_ms'] == 300
        assert result['pass'] is False
    
    def test_validate_data_completeness(self):
        """Test data completeness validation."""
        validator = QualityGateValidator()
        
        # Create complete home
        home = {
            'home_type': 'single_family_house',
            'areas': [{'area_id': 'kitchen'}],
            'devices': [
                {'entity_id': 'light.kitchen', 'friendly_name': 'Kitchen Light'}
            ],
            'events': [
                {'event_type': 'state_changed', 'timestamp': '2025-12-02T12:00:00Z'}
            ]
        }
        
        result = validator._validate_data_completeness(home)
        
        assert 'pass' in result
        assert result['pass'] is True
        assert len(result['issues']) == 0
    
    def test_validate_data_completeness_fail(self):
        """Test data completeness validation failure."""
        validator = QualityGateValidator()
        
        # Create incomplete home
        home = {
            'home_type': 'single_family_house',
            # Missing areas, devices, events
        }
        
        result = validator._validate_data_completeness(home)
        
        assert 'pass' in result
        assert result['pass'] is False
        assert len(result['issues']) > 0
    
    def test_validate_home_full(self):
        """Test full home validation."""
        validator = QualityGateValidator()
        
        home = {
            'home_id': 'test_home',
            'home_type': 'single_family_house',
            'areas': [{'area_id': 'kitchen'}],
            'devices': [
                {
                    'entity_id': 'light.kitchen_main',
                    'friendly_name': 'Kitchen Main Light',
                    'voice_friendly_name': 'Kitchen Light'
                }
            ],
            'events': [
                {'event_type': 'state_changed', 'timestamp': '2025-12-02T12:00:00Z'},
                {'event_type': 'automation_triggered', 'timestamp': '2025-12-02T12:01:00Z'},
                {'event_type': 'script_started', 'timestamp': '2025-12-02T12:02:00Z'},
                {'event_type': 'scene_activated', 'timestamp': '2025-12-02T12:03:00Z'},
                {'event_type': 'voice_command', 'timestamp': '2025-12-02T12:04:00Z'},
                {'event_type': 'webhook_triggered', 'timestamp': '2025-12-02T12:05:00Z'},
                {'event_type': 'api_call', 'timestamp': '2025-12-02T12:06:00Z'},
            ],
            'ground_truth': {
                'home_id': 'test_home',
                'expected_patterns': [{'pattern_type': 'motion_light'}]
            },
            'generation_metadata': {
                'generation_time_ms': 150
            }
        }
        
        result = validator.validate_home(home)
        
        assert 'overall_pass' in result
        assert 'naming_consistency' in result
        assert 'event_diversity' in result
        assert 'ground_truth_validation' in result
        assert 'performance' in result
        assert 'data_completeness' in result
    
    def test_validate_batch(self):
        """Test batch validation."""
        validator = QualityGateValidator()
        
        homes = [
            {
                'home_id': f'test_home_{i}',
                'home_type': 'single_family_house',
                'areas': [{'area_id': 'kitchen'}],
                'devices': [
                    {
                        'entity_id': 'light.kitchen',
                        'friendly_name': 'Kitchen Light',
                        'voice_friendly_name': 'Kitchen Light'
                    }
                ],
                'events': [
                    {'event_type': 'state_changed', 'timestamp': '2025-12-02T12:00:00Z'}
                ],
                'generation_metadata': {
                    'generation_time_ms': 150
                }
            }
            for i in range(3)
        ]
        
        result = validator.validate_batch(homes)
        
        assert 'total_homes' in result
        assert 'passed_homes' in result
        assert 'failed_homes' in result
        assert 'pass_rate' in result
        assert 'summary' in result
        assert 'results' in result
        assert result['total_homes'] == 3

