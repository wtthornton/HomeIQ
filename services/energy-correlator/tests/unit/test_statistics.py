"""
Unit tests for statistics tracking and reporting
Tests all statistics methods in EnergyEventCorrelator
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestStatisticsInitialization:
    """Test initial statistics state"""

    def test_initial_statistics(self, correlator_instance):
        """
        GIVEN: New correlator instance
        WHEN: Get statistics
        THEN: All counters should be 0
        """
        stats = correlator_instance.get_statistics()

        assert stats['total_events_processed'] == 0
        assert stats['correlations_found'] == 0
        assert stats['correlations_written'] == 0
        assert stats['errors'] == 0
        assert stats['correlation_rate_pct'] == 0.0
        assert stats['write_success_rate_pct'] == 100.0  # Default when no attempts

    def test_initial_config_in_statistics(self, correlator_instance):
        """
        GIVEN: New correlator instance
        WHEN: Get statistics
        THEN: Should include configuration values
        """
        stats = correlator_instance.get_statistics()

        assert 'config' in stats
        assert stats['config']['correlation_window_seconds'] == 10
        assert stats['config']['min_power_delta_w'] == 10.0


class TestEventCounterTracking:
    """Test event counter incrementation"""

    @pytest.mark.asyncio
    async def test_event_counter_increment(self, correlator_instance):
        """
        GIVEN: Process 10 events
        WHEN: Check total_events_processed
        THEN: Should be 10
        """
        # Mock power lookups to return None (skip correlation)
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.return_value = None

            # Process 10 events
            for i in range(10):
                event = {
                    'time': datetime.utcnow(),
                    'entity_id': f'switch.test_{i}',
                    'domain': 'switch',
                    'state': 'on',
                    'previous_state': 'off'
                }
                await correlator_instance._correlate_event_with_power(event)

            stats = correlator_instance.get_statistics()
            assert stats['total_events_processed'] == 10

    @pytest.mark.asyncio
    async def test_correlation_found_counter(self, correlator_instance):
        """
        GIVEN: Process events with varying power deltas
        WHEN: Count correlations found
        THEN: Should only count those above threshold
        """
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            # 5 events: 3 above threshold, 2 below
            mock_get_power.side_effect = [
                2450.0, 2510.0,  # +60W - above threshold
                2450.0, 2455.0,  # +5W - below threshold
                1850.0, 4350.0,  # +2500W - above threshold
                1000.0, 1003.0,  # +3W - below threshold
                2150.0, 2030.0,  # -120W - above threshold
            ]

            for i in range(5):
                event = {
                    'time': datetime.utcnow(),
                    'entity_id': f'switch.test_{i}',
                    'domain': 'switch',
                    'state': 'on',
                    'previous_state': 'off'
                }
                await correlator_instance._correlate_event_with_power(event)

            stats = correlator_instance.get_statistics()
            assert stats['total_events_processed'] == 5
            assert stats['correlations_found'] == 3  # Only 3 above 10W threshold
            assert stats['correlations_written'] == 3


class TestCorrelationRateCalculation:
    """Test correlation rate percentage calculations"""

    @pytest.mark.asyncio
    async def test_correlation_rate_calculation(self, correlator_instance):
        """
        GIVEN: 100 events processed, 15 correlations found
        WHEN: Calculate correlation_rate_pct
        THEN: Should be 15.0%
        """
        # Manually set counters for test
        correlator_instance.total_events_processed = 100
        correlator_instance.correlations_found = 15
        correlator_instance.correlations_written = 15

        stats = correlator_instance.get_statistics()
        assert stats['correlation_rate_pct'] == 15.0

    @pytest.mark.asyncio
    async def test_correlation_rate_zero_events(self, correlator_instance):
        """
        GIVEN: 0 events processed
        WHEN: Calculate correlation_rate_pct
        THEN: Should be 0.0 (not divide by zero)
        """
        stats = correlator_instance.get_statistics()
        assert stats['correlation_rate_pct'] == 0.0

    @pytest.mark.asyncio
    async def test_correlation_rate_high_percentage(self, correlator_instance):
        """
        GIVEN: 20 events processed, 18 correlations found
        WHEN: Calculate correlation_rate_pct
        THEN: Should be 90.0%
        """
        correlator_instance.total_events_processed = 20
        correlator_instance.correlations_found = 18
        correlator_instance.correlations_written = 18

        stats = correlator_instance.get_statistics()
        assert stats['correlation_rate_pct'] == 90.0

    @pytest.mark.asyncio
    async def test_correlation_rate_rounding(self, correlator_instance):
        """
        GIVEN: Non-round correlation rate
        WHEN: Get statistics
        THEN: Should round to 2 decimal places
        """
        correlator_instance.total_events_processed = 7
        correlator_instance.correlations_found = 2
        correlator_instance.correlations_written = 2

        stats = correlator_instance.get_statistics()
        # 2/7 = 28.571428...
        assert stats['correlation_rate_pct'] == 28.57


class TestWriteSuccessRate:
    """Test write success rate calculations"""

    def test_write_success_rate_all_successful(self, correlator_instance):
        """
        GIVEN: 15 correlations found, 15 written
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 100.0%
        """
        correlator_instance.correlations_found = 15
        correlator_instance.correlations_written = 15

        stats = correlator_instance.get_statistics()
        assert stats['write_success_rate_pct'] == 100.0

    def test_write_success_rate_with_failures(self, correlator_instance):
        """
        GIVEN: 15 correlations found, 12 written (3 failures)
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 80.0%
        """
        correlator_instance.correlations_found = 15
        correlator_instance.correlations_written = 12

        stats = correlator_instance.get_statistics()
        assert stats['write_success_rate_pct'] == 80.0

    def test_write_success_rate_all_failed(self, correlator_instance):
        """
        GIVEN: 10 correlations found, 0 written
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 0.0%
        """
        correlator_instance.correlations_found = 10
        correlator_instance.correlations_written = 0

        stats = correlator_instance.get_statistics()
        assert stats['write_success_rate_pct'] == 0.0

    def test_write_success_rate_no_correlations(self, correlator_instance):
        """
        GIVEN: 0 correlations found
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 100.0% (default when no attempts)
        """
        correlator_instance.correlations_found = 0
        correlator_instance.correlations_written = 0

        stats = correlator_instance.get_statistics()
        assert stats['write_success_rate_pct'] == 100.0


class TestStatisticsReset:
    """Test statistics reset functionality"""

    def test_statistics_reset(self, correlator_instance):
        """
        GIVEN: Correlator with existing statistics
        WHEN: Call reset_statistics()
        THEN: All counters should return to 0
        """
        # Set some statistics
        correlator_instance.total_events_processed = 100
        correlator_instance.correlations_found = 25
        correlator_instance.correlations_written = 20
        correlator_instance.errors = 5

        # Verify they're set
        stats_before = correlator_instance.get_statistics()
        assert stats_before['total_events_processed'] == 100
        assert stats_before['correlations_found'] == 25

        # Reset
        correlator_instance.reset_statistics()

        # Verify all reset to 0
        stats_after = correlator_instance.get_statistics()
        assert stats_after['total_events_processed'] == 0
        assert stats_after['correlations_found'] == 0
        assert stats_after['correlations_written'] == 0
        assert stats_after['errors'] == 0

    def test_statistics_reset_preserves_config(self, correlator_instance):
        """
        GIVEN: Correlator with statistics
        WHEN: Reset statistics
        THEN: Configuration should not change
        """
        # Reset statistics
        correlator_instance.reset_statistics()

        # Config should remain
        stats = correlator_instance.get_statistics()
        assert stats['config']['correlation_window_seconds'] == 10
        assert stats['config']['min_power_delta_w'] == 10.0


class TestErrorCounterTracking:
    """Test error counter incrementation"""

    @pytest.mark.asyncio
    async def test_error_counter_on_write_failure(self, correlator_instance):
        """
        GIVEN: InfluxDB write errors
        WHEN: Write correlation fails
        THEN: Should increment errors counter
        """
        # Mock write_points to raise exception
        correlator_instance.client.write_points.side_effect = Exception("InfluxDB write failed")

        # Mock power readings with valid correlation
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.side_effect = [2450.0, 2510.0]  # 60W delta

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'switch.test',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }

            with pytest.raises(Exception):
                await correlator_instance._correlate_event_with_power(event)

            # Should find correlation but fail to write
            stats = correlator_instance.get_statistics()
            assert stats['correlations_found'] == 1
            assert stats['correlations_written'] == 0
            assert stats['errors'] == 1

    @pytest.mark.asyncio
    async def test_multiple_errors_accumulate(self, correlator_instance):
        """
        GIVEN: Multiple write failures
        WHEN: Track errors
        THEN: Error counter should accumulate
        """
        # Mock write_points to raise exception
        correlator_instance.client.write_points.side_effect = Exception("InfluxDB write failed")

        # Mock power readings
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            # Process 3 events with valid correlations
            for i in range(3):
                mock_get_power.side_effect = [2450.0, 2510.0]  # 60W delta each

                event = {
                    'time': datetime.utcnow(),
                    'entity_id': f'switch.test_{i}',
                    'domain': 'switch',
                    'state': 'on',
                    'previous_state': 'off'
                }

                with pytest.raises(Exception):
                    await correlator_instance._correlate_event_with_power(event)

            # Should have 3 errors
            stats = correlator_instance.get_statistics()
            assert stats['errors'] == 3


class TestStatisticsResponseStructure:
    """Test statistics response structure and format"""

    def test_statistics_has_all_required_fields(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics
        THEN: Response should have all required fields
        """
        stats = correlator_instance.get_statistics()

        required_fields = [
            'total_events_processed',
            'correlations_found',
            'correlations_written',
            'correlation_rate_pct',
            'write_success_rate_pct',
            'errors',
            'config'
        ]

        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"

    def test_statistics_config_structure(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics config
        THEN: Should have correlation_window_seconds and min_power_delta_w
        """
        stats = correlator_instance.get_statistics()

        assert 'config' in stats
        assert 'correlation_window_seconds' in stats['config']
        assert 'min_power_delta_w' in stats['config']

    def test_statistics_types(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics
        THEN: All fields should have correct types
        """
        stats = correlator_instance.get_statistics()

        assert isinstance(stats['total_events_processed'], int)
        assert isinstance(stats['correlations_found'], int)
        assert isinstance(stats['correlations_written'], int)
        assert isinstance(stats['correlation_rate_pct'], (int, float))
        assert isinstance(stats['write_success_rate_pct'], (int, float))
        assert isinstance(stats['errors'], int)
        assert isinstance(stats['config'], dict)
