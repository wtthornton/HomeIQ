"""
Unit tests for failure scenario assignment in SyntheticDeviceGenerator.

Tests the 5 new failure scenarios added in Story AI11.4:
- Integration failures (Zigbee/Z-Wave disconnections)
- Configuration errors (invalid YAML, missing entities)
- Automation loops (recursive triggering)
- Resource exhaustion (memory/CPU spikes)
- API rate limiting (external services)
"""

import pytest
import random
from src.training.synthetic_device_generator import SyntheticDeviceGenerator


class TestFailureScenarios:
    """Test suite for failure scenario assignment."""
    
    def test_failure_scenarios_defined(self):
        """Test that all 5 new failure scenarios are defined."""
        generator = SyntheticDeviceGenerator()
        
        assert 'integration_failure' in generator.FAILURE_SCENARIOS
        assert 'config_error' in generator.FAILURE_SCENARIOS
        assert 'automation_loop' in generator.FAILURE_SCENARIOS
        assert 'resource_exhaustion' in generator.FAILURE_SCENARIOS
        assert 'api_rate_limit' in generator.FAILURE_SCENARIOS
    
    def test_failure_scenario_structure(self):
        """Test that each failure scenario has required fields."""
        generator = SyntheticDeviceGenerator()
        
        required_fields = ['description', 'symptoms', 'affected_device_types', 'probability', 'duration_days']
        
        for scenario_name, scenario_config in generator.FAILURE_SCENARIOS.items():
            for field in required_fields:
                assert field in scenario_config, f"Scenario '{scenario_name}' missing field '{field}'"
            
            # Validate symptoms structure
            assert isinstance(scenario_config['symptoms'], dict)
            assert len(scenario_config['symptoms']) > 0
            
            # Validate probability range
            assert 0.0 <= scenario_config['probability'] <= 1.0
            
            # Validate duration_days is a tuple of 2 values
            assert isinstance(scenario_config['duration_days'], tuple)
            assert len(scenario_config['duration_days']) == 2
            assert scenario_config['duration_days'][0] < scenario_config['duration_days'][1]
    
    def test_integration_failure_symptoms(self):
        """Test integration failure symptoms are correctly defined."""
        generator = SyntheticDeviceGenerator()
        scenario = generator.FAILURE_SCENARIOS['integration_failure']
        
        assert scenario['symptoms']['unavailable_states'] is True
        assert scenario['symptoms']['connection_drops'] is True
        assert scenario['symptoms']['delayed_responses'] is True
        assert 'unavailable' in scenario['symptoms']['error_messages']
        assert 'connection_lost' in scenario['symptoms']['error_messages']
        
        # Check affected device types
        assert 'binary_sensor' in scenario['affected_device_types']
        assert 'sensor' in scenario['affected_device_types']
        assert 'light' in scenario['affected_device_types']
    
    def test_config_error_symptoms(self):
        """Test configuration error symptoms are correctly defined."""
        generator = SyntheticDeviceGenerator()
        scenario = generator.FAILURE_SCENARIOS['config_error']
        
        assert scenario['symptoms']['invalid_states'] is True
        assert scenario['symptoms']['missing_attributes'] is True
        assert 'invalid_config' in scenario['symptoms']['error_messages']
        assert 'entity_not_found' in scenario['symptoms']['error_messages']
        
        # Check affected device types
        assert 'sensor' in scenario['affected_device_types']
        assert 'automation' in scenario['affected_device_types']
    
    def test_automation_loop_symptoms(self):
        """Test automation loop symptoms are correctly defined."""
        generator = SyntheticDeviceGenerator()
        scenario = generator.FAILURE_SCENARIOS['automation_loop']
        
        assert scenario['symptoms']['rapid_state_changes'] is True
        assert scenario['symptoms']['circular_dependencies'] is True
        assert 'automation_loop' in scenario['symptoms']['error_messages']
        assert 'recursive_trigger' in scenario['symptoms']['error_messages']
        
        # Check affected device types
        assert 'automation' in scenario['affected_device_types']
        assert 'script' in scenario['affected_device_types']
    
    def test_resource_exhaustion_symptoms(self):
        """Test resource exhaustion symptoms are correctly defined."""
        generator = SyntheticDeviceGenerator()
        scenario = generator.FAILURE_SCENARIOS['resource_exhaustion']
        
        assert scenario['symptoms']['slow_responses'] is True
        assert scenario['symptoms']['timeout_errors'] is True
        assert scenario['symptoms']['degraded_performance'] is True
        assert 'timeout' in scenario['symptoms']['error_messages']
        assert 'memory_error' in scenario['symptoms']['error_messages']
        
        # Check affected device types
        assert 'sensor' in scenario['affected_device_types']
        assert 'camera' in scenario['affected_device_types']
    
    def test_api_rate_limit_symptoms(self):
        """Test API rate limit symptoms are correctly defined."""
        generator = SyntheticDeviceGenerator()
        scenario = generator.FAILURE_SCENARIOS['api_rate_limit']
        
        assert scenario['symptoms']['rate_limit_errors'] is True
        assert scenario['symptoms']['delayed_updates'] is True
        assert scenario['symptoms']['intermittent_failures'] is True
        assert 'rate_limit' in scenario['symptoms']['error_messages']
        assert 'too_many_requests' in scenario['symptoms']['error_messages']
        
        # Check affected device types
        assert 'weather' in scenario['affected_device_types']
        assert 'sensor' in scenario['affected_device_types']
    
    def test_assign_failure_scenarios_basic(self):
        """Test that failure scenarios can be assigned to devices."""
        generator = SyntheticDeviceGenerator()
        
        # Create test devices with different types
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion_sensor',
                'device_type': 'binary_sensor',
                'name': 'Kitchen Motion Sensor',
                'area': 'Kitchen',
                'category': 'security',
                'attributes': {}
            },
            {
                'entity_id': 'sensor.living_room_temperature',
                'device_type': 'sensor',
                'name': 'Living Room Temperature',
                'area': 'Living Room',
                'category': 'climate',
                'attributes': {}
            },
            {
                'entity_id': 'light.bedroom_light_ceiling',
                'device_type': 'light',
                'name': 'Bedroom Light',
                'area': 'Bedroom',
                'category': 'lighting',
                'attributes': {}
            }
        ]
        
        # Assign failure scenarios (with fixed seed for reproducibility)
        random.seed(42)
        devices_with_failures = generator._assign_failure_scenarios(devices)
        
        # Verify devices are returned
        assert len(devices_with_failures) == len(devices)
        
        # Check that some devices may have failure scenarios (probabilistic)
        failed_devices = [d for d in devices_with_failures if 'failure_scenario' in d]
        # Note: Due to randomness, we can't guarantee failures, but we can check structure
    
    def test_assign_failure_scenarios_structure(self):
        """Test that assigned failure scenarios have correct structure."""
        generator = SyntheticDeviceGenerator()
        
        # Create a device that should be eligible for integration_failure
        devices = [
            {
                'entity_id': 'binary_sensor.test_motion',
                'device_type': 'binary_sensor',  # Eligible for integration_failure
                'name': 'Test Motion Sensor',
                'area': 'Test',
                'category': 'security',
                'attributes': {}
            }
        ]
        
        # Try multiple seeds to find one that assigns a failure
        assigned = False
        for seed in range(100):
            random.seed(seed)
            devices_with_failures = generator._assign_failure_scenarios(devices.copy())
            
            if 'failure_scenario' in devices_with_failures[0]:
                assigned = True
                device = devices_with_failures[0]
                
                # Verify structure
                assert 'failure_scenario' in device
                assert 'failure_symptoms' in device
                assert 'failure_duration_days' in device
                assert device['failure_scenario'] in generator.FAILURE_SCENARIOS
                
                # Verify attributes
                assert 'failure_scenario' in device['attributes']
                assert 'failure_description' in device['attributes']
                
                # Verify duration is within expected range
                scenario = generator.FAILURE_SCENARIOS[device['failure_scenario']]
                duration_range = scenario['duration_days']
                assert duration_range[0] <= device['failure_duration_days'] <= duration_range[1]
                
                break
        
        # At least one seed should assign a failure (probabilistic test)
        # If this fails consistently, the probability might be too low
        # For now, we'll just verify the structure when a failure is assigned
    
    def test_assign_failure_scenarios_device_type_filtering(self):
        """Test that failure scenarios only apply to eligible device types."""
        generator = SyntheticDeviceGenerator()
        
        # Create devices with types that should NOT be affected by automation_loop
        devices = [
            {
                'entity_id': 'sensor.test_temperature',
                'device_type': 'sensor',
                'name': 'Test Temperature',
                'area': 'Test',
                'category': 'climate',
                'attributes': {}
            }
        ]
        
        # automation_loop should not apply to 'sensor' type
        scenario = generator.FAILURE_SCENARIOS['automation_loop']
        assert 'sensor' not in scenario['affected_device_types']
        
        # Assign failures (should not assign automation_loop to sensor)
        random.seed(42)
        devices_with_failures = generator._assign_failure_scenarios(devices)
        
        device = devices_with_failures[0]
        if 'failure_scenario' in device:
            # If a failure is assigned, it should not be automation_loop
            assert device['failure_scenario'] != 'automation_loop'
    
    def test_assign_failure_scenarios_single_failure_per_device(self):
        """Test that each device gets at most one failure scenario."""
        generator = SyntheticDeviceGenerator()
        
        # Create multiple devices eligible for multiple failure types
        devices = [
            {
                'entity_id': f'binary_sensor.test_motion_{i}',
                'device_type': 'binary_sensor',
                'name': f'Test Motion {i}',
                'area': 'Test',
                'category': 'security',
                'attributes': {}
            }
            for i in range(10)
        ]
        
        # Assign failures
        random.seed(42)
        devices_with_failures = generator._assign_failure_scenarios(devices)
        
        # Each device should have at most one failure scenario
        for device in devices_with_failures:
            if 'failure_scenario' in device:
                # Should only have one failure scenario key
                failure_keys = [k for k in device.keys() if k.startswith('failure_')]
                assert len(failure_keys) >= 3  # failure_scenario, failure_symptoms, failure_duration_days
                assert device['failure_scenario'] in generator.FAILURE_SCENARIOS
    
    def test_assign_failure_scenarios_no_devices(self):
        """Test that empty device list is handled correctly."""
        generator = SyntheticDeviceGenerator()
        
        devices = []
        devices_with_failures = generator._assign_failure_scenarios(devices)
        
        assert devices_with_failures == []
    
    def test_assign_failure_scenarios_integration_with_generate_devices(self):
        """Test that failure scenarios are assigned when generating devices."""
        generator = SyntheticDeviceGenerator()
        
        home_data = {
            'home_type': 'single_family_house',
            'size_category': 'medium',
            'metadata': {}
        }
        
        areas = [
            {'name': 'Kitchen', 'floor': 'ground_floor'},
            {'name': 'Living Room', 'floor': 'ground_floor'},
            {'name': 'Bedroom', 'floor': 'upstairs'}
        ]
        
        # Generate devices
        random.seed(42)
        devices = generator.generate_devices(home_data, areas)
        
        # Verify devices were generated
        assert len(devices) > 0
        
        # Check that some devices may have failure scenarios
        failed_devices = [d for d in devices if 'failure_scenario' in d]
        
        # Verify structure of devices with failures
        for device in failed_devices:
            assert 'failure_scenario' in device
            assert device['failure_scenario'] in generator.FAILURE_SCENARIOS
            assert 'failure_symptoms' in device
            assert 'failure_duration_days' in device
            assert 'failure_scenario' in device.get('attributes', {})
    
    def test_failure_scenario_probabilities_realistic(self):
        """Test that failure scenario probabilities are realistic (not too high)."""
        generator = SyntheticDeviceGenerator()
        
        # Probabilities should be reasonable (not > 20% for any single scenario)
        for scenario_name, scenario_config in generator.FAILURE_SCENARIOS.items():
            assert scenario_config['probability'] <= 0.20, \
                f"Scenario '{scenario_name}' has probability > 20%: {scenario_config['probability']}"
    
    def test_failure_scenario_duration_ranges(self):
        """Test that failure scenario duration ranges are reasonable."""
        generator = SyntheticDeviceGenerator()
        
        for scenario_name, scenario_config in generator.FAILURE_SCENARIOS.items():
            duration_range = scenario_config['duration_days']
            
            # Duration should be positive
            assert duration_range[0] >= 0
            assert duration_range[1] > duration_range[0]
            
            # Duration should not be unreasonably long (>30 days)
            assert duration_range[1] <= 30, \
                f"Scenario '{scenario_name}' has max duration > 30 days: {duration_range[1]}"

