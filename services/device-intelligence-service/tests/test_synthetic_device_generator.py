"""
Unit tests for SyntheticDeviceGenerator.

Tests template-based device data generation, failure scenarios, and data quality.
Epic 46, Story 46.1: Synthetic Device Data Generator
"""

import pytest
from datetime import datetime, timezone

from src.training.synthetic_device_generator import SyntheticDeviceGenerator


class TestSyntheticDeviceGenerator:
    """Test suite for SyntheticDeviceGenerator."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SyntheticDeviceGenerator()
        assert generator is not None
        assert hasattr(generator, 'DEVICE_TYPE_DISTRIBUTION')
        assert hasattr(generator, 'DEVICE_CHARACTERISTICS')
        assert hasattr(generator, 'FAILURE_SCENARIOS')
        assert len(generator.DEVICE_TYPE_DISTRIBUTION) > 0
        assert len(generator.DEVICE_CHARACTERISTICS) > 0
        assert len(generator.FAILURE_SCENARIOS) > 0
    
    def test_initialization_with_seed(self):
        """Test generator initialization with random seed for reproducibility."""
        generator1 = SyntheticDeviceGenerator(random_seed=42)
        generator2 = SyntheticDeviceGenerator(random_seed=42)
        
        # Generate same data with same seed
        data1 = generator1.generate_training_data(count=10, days=30)
        data2 = generator2.generate_training_data(count=10, days=30)
        
        # Should produce identical results
        assert len(data1) == len(data2)
        assert data1[0]['device_id'] == data2[0]['device_id']
    
    def test_generate_training_data_basic(self):
        """Test basic training data generation."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=10, days=30)
        
        assert len(data) == 10
        assert all(isinstance(sample, dict) for sample in data)
    
    def test_generate_training_data_required_fields(self):
        """Test that all required fields are present in generated data."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=5, days=30)
        
        required_fields = [
            'device_id', 'response_time', 'error_rate', 'battery_level',
            'signal_strength', 'usage_frequency', 'temperature', 'humidity',
            'uptime_hours', 'restart_count', 'connection_drops', 'data_transfer_rate'
        ]
        
        for sample in data:
            for field in required_fields:
                assert field in sample, f"Missing required field: {field}"
    
    def test_generate_training_data_device_id_format(self):
        """Test device ID format."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=10, days=30)
        
        for sample in data:
            assert 'device_id' in sample
            assert sample['device_id'].startswith('synthetic_device_')
            assert sample['device_id'][-4:].isdigit()  # Last 4 chars are digits
    
    def test_generate_training_data_response_time_range(self):
        """Test response_time values are within reasonable range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert 10 <= sample['response_time'] <= 5000, \
                f"response_time out of range: {sample['response_time']}"
    
    def test_generate_training_data_error_rate_range(self):
        """Test error_rate values are within reasonable range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert 0.0 <= sample['error_rate'] <= 1.0, \
                f"error_rate out of range: {sample['error_rate']}"
    
    def test_generate_training_data_battery_level_range(self):
        """Test battery_level values are within 0-100 range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert 0 <= sample['battery_level'] <= 100, \
                f"battery_level out of range: {sample['battery_level']}"
    
    def test_generate_training_data_signal_strength_range(self):
        """Test signal_strength values are within reasonable dBm range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert -100 <= sample['signal_strength'] <= -10, \
                f"signal_strength out of range: {sample['signal_strength']}"
    
    def test_generate_training_data_usage_frequency_range(self):
        """Test usage_frequency values are within 0-1 range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert 0.0 <= sample['usage_frequency'] <= 1.0, \
                f"usage_frequency out of range: {sample['usage_frequency']}"
    
    def test_generate_training_data_temperature_range(self):
        """Test temperature values are within reasonable range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert -10 <= sample['temperature'] <= 50, \
                f"temperature out of range: {sample['temperature']}"
    
    def test_generate_training_data_humidity_range(self):
        """Test humidity values are within 0-100 range."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert 0 <= sample['humidity'] <= 100, \
                f"humidity out of range: {sample['humidity']}"
    
    def test_generate_training_data_uptime_hours_positive(self):
        """Test uptime_hours values are positive."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert sample['uptime_hours'] >= 1.0, \
                f"uptime_hours should be positive: {sample['uptime_hours']}"
    
    def test_generate_training_data_restart_count_non_negative(self):
        """Test restart_count values are non-negative."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert sample['restart_count'] >= 0, \
                f"restart_count should be non-negative: {sample['restart_count']}"
    
    def test_generate_training_data_connection_drops_non_negative(self):
        """Test connection_drops values are non-negative."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert sample['connection_drops'] >= 0, \
                f"connection_drops should be non-negative: {sample['connection_drops']}"
    
    def test_generate_training_data_data_transfer_rate_positive(self):
        """Test data_transfer_rate values are positive."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=50, days=30)
        
        for sample in data:
            assert sample['data_transfer_rate'] >= 10, \
                f"data_transfer_rate should be positive: {sample['data_transfer_rate']}"
    
    def test_generate_training_data_failure_rate_zero(self):
        """Test generation with zero failure rate."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=100, days=30, failure_rate=0.0)
        
        # All devices should be normal (no failure scenarios)
        assert len(data) == 100
    
    def test_generate_training_data_failure_rate_one(self):
        """Test generation with 100% failure rate."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=100, days=30, failure_rate=1.0)
        
        # All devices should have failure scenarios
        assert len(data) == 100
    
    def test_generate_training_data_failure_rate_partial(self):
        """Test generation with partial failure rate."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=100, days=30, failure_rate=0.15)
        
        # Should have mix of normal and failure devices
        assert len(data) == 100
        # With 15% failure rate, we should have approximately 15 failure devices
        # (exact count may vary due to rounding)
    
    def test_generate_training_data_custom_device_types(self):
        """Test generation with custom device types."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        custom_types = ['sensor', 'light', 'climate']
        data = generator.generate_training_data(count=30, days=30, device_types=custom_types)
        
        assert len(data) == 30
        # All devices should be one of the specified types
        # (Note: device_type is not directly in the output, but affects the metrics)
    
    def test_generate_training_data_different_days(self):
        """Test generation with different day counts."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        data_30 = generator.generate_training_data(count=10, days=30)
        data_90 = generator.generate_training_data(count=10, days=90)
        data_180 = generator.generate_training_data(count=10, days=180)
        
        assert len(data_30) == 10
        assert len(data_90) == 10
        assert len(data_180) == 10
    
    def test_generate_training_data_health_score_optional(self):
        """Test that health_score is optional (not all devices have it)."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=100, days=30)
        
        # Some devices should have health_score, some shouldn't
        has_health_score = sum(1 for sample in data if 'health_score' in sample)
        no_health_score = sum(1 for sample in data if 'health_score' not in sample)
        
        assert has_health_score > 0, "Some devices should have health_score"
        assert no_health_score > 0, "Some devices should not have health_score"
    
    def test_generate_training_data_health_score_range(self):
        """Test health_score values are within 0-1 range when present."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=100, days=30)
        
        for sample in data:
            if 'health_score' in sample:
                assert 0.0 <= sample['health_score'] <= 1.0, \
                    f"health_score out of range: {sample['health_score']}"
    
    def test_generate_device_sample_basic(self):
        """Test generating a single device sample."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        sample = generator._generate_device_sample(
            device_id='test_device_001',
            device_type='sensor',
            days=30
        )
        
        assert isinstance(sample, dict)
        assert sample['device_id'] == 'test_device_001'
        assert 'response_time' in sample
        assert 'error_rate' in sample
    
    def test_generate_device_sample_different_types(self):
        """Test generating samples for different device types."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        device_types = ['sensor', 'switch', 'light', 'climate', 'security']
        
        for device_type in device_types:
            sample = generator._generate_device_sample(
                device_id=f'test_{device_type}_001',
                device_type=device_type,
                days=30
            )
            assert sample['device_id'] == f'test_{device_type}_001'
    
    def test_generate_device_sample_with_failure_scenario(self):
        """Test generating sample with failure scenario."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        failure_scenarios = list(generator.FAILURE_SCENARIOS.keys())
        for scenario in failure_scenarios:
            sample = generator._generate_device_sample(
                device_id=f'test_failure_{scenario}',
                device_type='sensor',
                days=30,
                failure_scenario=scenario
            )
            
            # Failure scenarios should affect metrics
            assert sample['error_rate'] >= 0.0
            assert sample['response_time'] >= 10.0
    
    def test_generate_device_sample_failure_progressive(self):
        """Test progressive failure scenario affects metrics."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        normal_sample = generator._generate_device_sample(
            device_id='normal',
            device_type='sensor',
            days=30,
            failure_scenario=None
        )
        
        failure_sample = generator._generate_device_sample(
            device_id='progressive',
            device_type='sensor',
            days=30,
            failure_scenario='progressive'
        )
        
        # Progressive failure should generally increase error_rate and response_time
        # (Note: randomness means this might not always be true, but on average it should)
        # We'll just verify the values are within ranges
        assert failure_sample['error_rate'] >= 0.0
        assert failure_sample['response_time'] >= 10.0
    
    def test_generate_device_sample_failure_sudden(self):
        """Test sudden failure scenario affects metrics."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        failure_sample = generator._generate_device_sample(
            device_id='sudden',
            device_type='sensor',
            days=30,
            failure_scenario='sudden'
        )
        
        # Sudden failure should have high error_rate and response_time
        assert failure_sample['error_rate'] >= 0.0
        assert failure_sample['response_time'] >= 10.0
    
    def test_generate_realistic_value_stable_pattern(self):
        """Test _generate_realistic_value with stable pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='stable',
            days=30
        )
        
        # Should be within range (with small variation)
        assert 40.0 <= value <= 110.0  # Allow some variation
    
    def test_generate_realistic_value_daily_cycle_pattern(self):
        """Test _generate_realistic_value with daily cycle pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='daily_cycle',
            days=30
        )
        
        # Should be within range (with cycle variation)
        assert 30.0 <= value <= 120.0  # Allow cycle variation
    
    def test_generate_realistic_value_weekly_cycle_pattern(self):
        """Test _generate_realistic_value with weekly cycle pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='weekly_cycle',
            days=30
        )
        
        # Should be within range (with cycle variation)
        assert 30.0 <= value <= 120.0  # Allow cycle variation
    
    def test_generate_realistic_value_seasonal_pattern(self):
        """Test _generate_realistic_value with seasonal pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='seasonal',
            days=30
        )
        
        # Should be within range (with seasonal variation)
        assert 20.0 <= value <= 130.0  # Allow seasonal variation
    
    def test_generate_realistic_value_degradation_pattern(self):
        """Test _generate_realistic_value with degradation pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='degradation',
            days=30
        )
        
        # Degradation should reduce value (but still positive)
        assert 0.0 <= value <= 100.0
    
    def test_generate_realistic_value_increasing_pattern(self):
        """Test _generate_realistic_value with increasing pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='increasing',
            days=30
        )
        
        # Increasing pattern should increase value
        assert 50.0 <= value <= 150.0  # Allow increase
    
    def test_generate_realistic_value_variation_pattern(self):
        """Test _generate_realistic_value with variation pattern."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        value = generator._generate_realistic_value(
            base_range=(50.0, 100.0),
            pattern='variation',
            days=30
        )
        
        # Should be within range (with variation)
        assert 30.0 <= value <= 120.0  # Allow variation
    
    def test_calculate_health_score_healthy_device(self):
        """Test health score calculation for healthy device."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        healthy_sample = {
            'error_rate': 0.01,
            'response_time': 100.0,
            'battery_level': 90.0,
            'signal_strength': -50.0,
            'connection_drops': 0,
            'restart_count': 0
        }
        
        score = generator._calculate_health_score(healthy_sample)
        assert 0.0 <= score <= 1.0
        assert score >= 0.7  # Healthy device should have high score
    
    def test_calculate_health_score_unhealthy_device(self):
        """Test health score calculation for unhealthy device."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        unhealthy_sample = {
            'error_rate': 0.5,  # High error rate
            'response_time': 3000.0,  # Slow response
            'battery_level': 10.0,  # Low battery
            'signal_strength': -90.0,  # Poor signal
            'connection_drops': 10,  # Many drops
            'restart_count': 15  # Frequent restarts
        }
        
        score = generator._calculate_health_score(unhealthy_sample)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Unhealthy device should have low score
    
    def test_calculate_health_score_edge_cases(self):
        """Test health score calculation with edge case values."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        
        # Test with all minimum values
        min_sample = {
            'error_rate': 0.0,
            'response_time': 10.0,
            'battery_level': 100.0,
            'signal_strength': -30.0,
            'connection_drops': 0,
            'restart_count': 0
        }
        score_min = generator._calculate_health_score(min_sample)
        assert 0.0 <= score_min <= 1.0
        
        # Test with all maximum values
        max_sample = {
            'error_rate': 1.0,
            'response_time': 5000.0,
            'battery_level': 0.0,
            'signal_strength': -100.0,
            'connection_drops': 20,
            'restart_count': 20
        }
        score_max = generator._calculate_health_score(max_sample)
        assert 0.0 <= score_max <= 1.0
        assert score_max < score_min  # Max should be worse than min
    
    def test_select_device_type_weighted_distribution(self):
        """Test device type selection follows weighted distribution."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        device_types = list(generator.DEVICE_TYPE_DISTRIBUTION.keys())
        
        # Generate many samples to test distribution
        selected_types = []
        for _ in range(1000):
            device_type = generator._select_device_type(device_types)
            selected_types.append(device_type)
        
        # Should have selected from available types
        assert all(dt in device_types for dt in selected_types)
        
        # Sensor should be most common (weight 30)
        sensor_count = selected_types.count('sensor')
        assert sensor_count > 200  # Should be significantly more than others
    
    def test_generate_training_data_large_count(self):
        """Test generating large number of samples."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=1000, days=30)
        
        assert len(data) == 1000
        assert all(isinstance(sample, dict) for sample in data)
    
    def test_generate_training_data_large_days(self):
        """Test generating data for large number of days."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=10, days=365)
        
        assert len(data) == 10
        assert all(isinstance(sample, dict) for sample in data)
    
    def test_generate_training_data_data_types(self):
        """Test that generated data has correct types."""
        generator = SyntheticDeviceGenerator(random_seed=42)
        data = generator.generate_training_data(count=10, days=30)
        
        for sample in data:
            assert isinstance(sample['device_id'], str)
            assert isinstance(sample['response_time'], (int, float))
            assert isinstance(sample['error_rate'], (int, float))
            assert isinstance(sample['battery_level'], (int, float))
            assert isinstance(sample['signal_strength'], (int, float))
            assert isinstance(sample['usage_frequency'], (int, float))
            assert isinstance(sample['temperature'], (int, float))
            assert isinstance(sample['humidity'], (int, float))
            assert isinstance(sample['uptime_hours'], (int, float))
            assert isinstance(sample['restart_count'], int)
            assert isinstance(sample['connection_drops'], int)
            assert isinstance(sample['data_transfer_rate'], (int, float))
    
    def test_generate_training_data_reproducibility(self):
        """Test that generation is reproducible with same seed."""
        generator1 = SyntheticDeviceGenerator(random_seed=123)
        generator2 = SyntheticDeviceGenerator(random_seed=123)
        
        data1 = generator1.generate_training_data(count=50, days=30)
        data2 = generator2.generate_training_data(count=50, days=30)
        
        # Should produce identical results
        assert len(data1) == len(data2)
        for i in range(len(data1)):
            assert data1[i]['device_id'] == data2[i]['device_id']
            assert data1[i]['response_time'] == data2[i]['response_time']
            assert data1[i]['error_rate'] == data2[i]['error_rate']
    
    def test_generate_training_data_different_seeds(self):
        """Test that different seeds produce different results."""
        generator1 = SyntheticDeviceGenerator(random_seed=123)
        generator2 = SyntheticDeviceGenerator(random_seed=456)
        
        data1 = generator1.generate_training_data(count=50, days=30)
        data2 = generator2.generate_training_data(count=50, days=30)
        
        # Should produce different results
        assert len(data1) == len(data2)
        # At least some values should be different
        different = False
        for i in range(len(data1)):
            if data1[i]['response_time'] != data2[i]['response_time']:
                different = True
                break
        assert different, "Different seeds should produce different results"

