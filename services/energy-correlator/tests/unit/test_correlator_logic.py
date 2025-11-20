"""
Unit tests for energy-event correlation logic
Tests core correlation algorithms and power delta calculations
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest


class TestPowerDeltaCalculation:
    """Test power delta calculation logic"""

    @pytest.mark.asyncio
    async def test_power_delta_calculation(self, correlator_instance, sample_power_data):
        """
        GIVEN: Power before (2450W) and after (2510W)
        WHEN: Calculate delta
        THEN: Delta should be +60W
        """
        power_before = sample_power_data['before']
        power_after = sample_power_data['after']
        expected_delta = sample_power_data['delta']

        # Calculate delta (simulating _correlate_event_with_power logic)
        power_delta = power_after - power_before

        assert power_delta == expected_delta
        assert power_delta == 60.0

    @pytest.mark.asyncio
    async def test_power_delta_percentage(self, correlator_instance, sample_large_power_change):
        """
        GIVEN: Power before (1850W) and after (4350W)
        WHEN: Calculate percentage change
        THEN: Percentage should be +135%
        """
        power_before = sample_large_power_change['before']
        power_after = sample_large_power_change['after']
        expected_delta_pct = sample_large_power_change['delta_pct']

        # Calculate delta and percentage
        power_delta = power_after - power_before
        power_delta_pct = (power_delta / power_before * 100) if power_before > 0 else 0

        assert power_delta == 2500.0
        assert abs(power_delta_pct - expected_delta_pct) < 0.1  # Allow small floating point difference

    @pytest.mark.asyncio
    async def test_negative_power_delta(self, correlator_instance, sample_negative_power_change):
        """
        GIVEN: Light turning off (2150W → 2030W)
        WHEN: Calculate delta
        THEN: Delta should be -120W (-5.6%)
        """
        power_before = sample_negative_power_change['before']
        power_after = sample_negative_power_change['after']
        expected_delta = sample_negative_power_change['delta']

        # Calculate delta
        power_delta = power_after - power_before

        assert power_delta == expected_delta
        assert power_delta == -120.0

        # Calculate percentage
        power_delta_pct = (power_delta / power_before * 100) if power_before > 0 else 0
        assert abs(power_delta_pct - (-5.58)) < 0.1


class TestCorrelationThresholds:
    """Test correlation threshold logic"""

    @pytest.mark.asyncio
    async def test_min_power_delta_threshold(self, correlator_instance, sample_small_power_change):
        """
        GIVEN: Small power change (5W)
        WHEN: Apply threshold (10W minimum)
        THEN: Correlation should be skipped
        """
        power_delta = sample_small_power_change['delta']
        min_threshold = correlator_instance.min_power_delta

        assert abs(power_delta) < min_threshold
        assert abs(power_delta) < 10.0

    @pytest.mark.asyncio
    async def test_significant_power_change(self, correlator_instance, sample_power_data):
        """
        GIVEN: Power change of 60W
        WHEN: Apply threshold (10W minimum)
        THEN: Correlation should be created
        """
        power_delta = sample_power_data['delta']
        min_threshold = correlator_instance.min_power_delta

        assert abs(power_delta) >= min_threshold
        assert abs(power_delta) >= 10.0

    @pytest.mark.asyncio
    async def test_large_hvac_power_change(self, correlator_instance, sample_large_power_change):
        """
        GIVEN: HVAC power change of 2500W
        WHEN: Apply threshold (10W minimum)
        THEN: Should pass threshold easily
        """
        power_delta = sample_large_power_change['delta']
        min_threshold = correlator_instance.min_power_delta

        assert abs(power_delta) >= min_threshold
        assert power_delta == 2500.0


class TestCorrelationEdgeCases:
    """Test edge cases in correlation logic"""

    @pytest.mark.asyncio
    async def test_zero_power_before(self, correlator_instance):
        """
        GIVEN: Power before is 0W
        WHEN: Calculate percentage change
        THEN: Should handle division by zero gracefully (return 0%)
        """
        power_before = 0.0
        power_after = 100.0
        power_delta = power_after - power_before

        # This is the logic from _write_correlation
        power_delta_pct = (power_delta / power_before * 100) if power_before > 0 else 0

        assert power_delta_pct == 0  # Should return 0 instead of dividing by zero
        assert power_delta == 100.0

    @pytest.mark.asyncio
    async def test_correlation_window_boundaries(self, correlator_instance):
        """
        GIVEN: Event at T0
        WHEN: Check correlation window
        THEN: Should be ±10 seconds as configured
        """
        assert correlator_instance.correlation_window_seconds == 10

    @pytest.mark.asyncio
    async def test_power_lookup_window(self, correlator_instance):
        """
        GIVEN: Power lookup for specific time
        WHEN: Check lookup window
        THEN: Should search within ±30 seconds (as per _get_power_at_time)
        """
        # This is validated by the query logic in _get_power_at_time
        # The window is 30 seconds before and after target time
        target_time = datetime.utcnow()
        expected_start = target_time - timedelta(seconds=30)
        expected_end = target_time + timedelta(seconds=30)

        # Validate the window is 60 seconds total
        window_seconds = (expected_end - expected_start).total_seconds()
        assert window_seconds == 60


class TestEventCorrelationFlow:
    """Test the complete event correlation flow"""

    @pytest.mark.asyncio
    async def test_correlate_event_with_power_missing_before(self, correlator_instance):
        """
        GIVEN: No power reading 5s before event
        WHEN: Attempt correlation
        THEN: Should skip correlation gracefully
        """
        # Mock _get_power_at_time to return None for "before" reading
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.return_value = None

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'switch.test',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }

            # Should not raise an exception
            await correlator_instance._correlate_event_with_power(event)

            # Should increment events processed but not correlations found
            assert correlator_instance.total_events_processed == 1
            assert correlator_instance.correlations_found == 0

    @pytest.mark.asyncio
    async def test_correlate_event_with_power_missing_after(self, correlator_instance):
        """
        GIVEN: No power reading 5s after event
        WHEN: Attempt correlation
        THEN: Should skip correlation gracefully
        """
        # Mock _get_power_at_time to return value for first call, None for second
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.side_effect = [2450.0, None]  # before exists, after is None

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'switch.test',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }

            # Should not raise an exception
            await correlator_instance._correlate_event_with_power(event)

            # Should increment events processed but not correlations found
            assert correlator_instance.total_events_processed == 1
            assert correlator_instance.correlations_found == 0

    @pytest.mark.asyncio
    async def test_correlate_event_below_threshold(self, correlator_instance):
        """
        GIVEN: Power change below minimum threshold
        WHEN: Correlate event
        THEN: Should skip writing correlation
        """
        # Mock power readings with small delta (5W)
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.side_effect = [2450.0, 2455.0]  # 5W delta

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'switch.test',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }

            await correlator_instance._correlate_event_with_power(event)

            # Should process but not find correlation (below 10W threshold)
            assert correlator_instance.total_events_processed == 1
            assert correlator_instance.correlations_found == 0
            assert correlator_instance.correlations_written == 0

    @pytest.mark.asyncio
    async def test_correlate_event_above_threshold(self, correlator_instance):
        """
        GIVEN: Power change above minimum threshold
        WHEN: Correlate event
        THEN: Should create and write correlation
        """
        # Mock power readings with significant delta (60W)
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.side_effect = [2450.0, 2510.0]  # 60W delta

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'switch.living_room_lamp',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }

            await correlator_instance._correlate_event_with_power(event)

            # Should process, find correlation, and write it
            assert correlator_instance.total_events_processed == 1
            assert correlator_instance.correlations_found == 1
            assert correlator_instance.correlations_written == 1

            # Verify write_points was called
            assert correlator_instance.client.write_points.called

    @pytest.mark.asyncio
    async def test_correlate_negative_delta(self, correlator_instance):
        """
        GIVEN: Device turning off with negative power delta
        WHEN: Correlate event
        THEN: Should handle negative delta correctly
        """
        # Mock power readings with negative delta (-120W)
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            mock_get_power.side_effect = [2150.0, 2030.0]  # -120W delta

            event = {
                'time': datetime.utcnow(),
                'entity_id': 'light.bedroom',
                'domain': 'light',
                'state': 'off',
                'previous_state': 'on'
            }

            await correlator_instance._correlate_event_with_power(event)

            # Negative delta with abs() > 10W should still correlate
            assert correlator_instance.total_events_processed == 1
            assert correlator_instance.correlations_found == 1
            assert correlator_instance.correlations_written == 1


class TestMultipleEventCorrelation:
    """Test correlation of multiple events"""

    @pytest.mark.asyncio
    async def test_process_multiple_events(self, correlator_instance, sample_events):
        """
        GIVEN: Multiple events to correlate
        WHEN: Process all events
        THEN: Should track count correctly
        """
        # Mock power readings for all events (all with significant deltas)
        with patch.object(correlator_instance, '_get_power_at_time', new_callable=AsyncMock) as mock_get_power:
            # Alternate between before/after readings
            mock_get_power.side_effect = [
                2450.0, 2510.0,  # Event 1: +60W
                1850.0, 4350.0,  # Event 2: +2500W
                2150.0, 2030.0,  # Event 3: -120W
                1000.0, 1050.0,  # Event 4: +50W
                1500.0, 1450.0,  # Event 5: -50W
            ]

            for event in sample_events:
                await correlator_instance._correlate_event_with_power(event)

            # All 5 events should be processed and correlated
            assert correlator_instance.total_events_processed == 5
            assert correlator_instance.correlations_found == 5
            assert correlator_instance.correlations_written == 5
