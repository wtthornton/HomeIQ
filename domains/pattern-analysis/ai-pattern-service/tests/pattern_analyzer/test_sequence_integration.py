"""
Integration test for SequencePatternDetector with realistic Home Assistant data.

Epic 37, Story 37.1: Sequence Detector integration testing.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from src.pattern_analyzer.sequence import SequencePatternDetector


class TestSequenceIntegration:
    """Integration tests with realistic Home Assistant event data."""

    @pytest.fixture
    def detector(self):
        """Production-like detector configuration."""
        return SequencePatternDetector(
            min_occurrences=3,
            min_confidence=0.7,
            window_minutes=30,
            gap_tolerance_minutes=5,
            filter_system_noise=True,
        )

    def generate_morning_routine_events(
        self, base_date: datetime, num_days: int = 7
    ) -> pd.DataFrame:
        """
        Generate realistic morning routine events.

        Pattern: binary_sensor.bedroom_motion → light.bedroom → light.bathroom → switch.coffee_maker
        """
        events = []

        for day in range(num_days):
            day_start = base_date + timedelta(days=day)

            # Slight variation in timing (±15 minutes)
            time_offset = timedelta(minutes=(day % 5) * 3 - 6)
            routine_start = day_start.replace(hour=6, minute=45) + time_offset

            # Morning routine sequence
            events.extend([
                {'device_id': 'binary_sensor.bedroom_motion', 'timestamp': routine_start, 'state': 'on'},
                {'device_id': 'light.bedroom', 'timestamp': routine_start + timedelta(seconds=15), 'state': 'on'},
                {'device_id': 'light.bathroom', 'timestamp': routine_start + timedelta(minutes=2), 'state': 'on'},
                {'device_id': 'switch.coffee_maker', 'timestamp': routine_start + timedelta(minutes=5), 'state': 'on'},
            ])

            # Add some noise events
            events.extend([
                {'device_id': 'sensor.temperature', 'timestamp': routine_start + timedelta(minutes=1), 'state': '68'},
                {'device_id': 'light.kitchen', 'timestamp': routine_start + timedelta(minutes=10), 'state': 'on'},
            ])

        return pd.DataFrame(events)

    def generate_arrival_sequence_events(
        self, base_date: datetime, num_occurrences: int = 5
    ) -> pd.DataFrame:
        """
        Generate arrival home sequence events.

        Pattern: cover.garage_door → binary_sensor.door_hallway → light.hallway → light.living_room
        """
        events = []

        for i in range(num_occurrences):
            arrival_time = base_date.replace(hour=17, minute=30) + timedelta(days=i)

            events.extend([
                {'device_id': 'cover.garage_door', 'timestamp': arrival_time, 'state': 'open'},
                {'device_id': 'binary_sensor.door_hallway', 'timestamp': arrival_time + timedelta(seconds=45), 'state': 'on'},
                {'device_id': 'light.hallway', 'timestamp': arrival_time + timedelta(seconds=50), 'state': 'on'},
                {'device_id': 'light.living_room', 'timestamp': arrival_time + timedelta(minutes=1, seconds=30), 'state': 'on'},
            ])

        return pd.DataFrame(events)

    def test_morning_routine_detection(self, detector):
        """Test detection of morning routine sequence pattern."""
        base_date = datetime(2026, 3, 1)
        events = self.generate_morning_routine_events(base_date, num_days=10)

        patterns = detector.detect_patterns(events)

        # Should detect at least one sequence
        assert len(patterns) >= 1

        # Should include bedroom motion → bedroom light
        two_step = [
            p for p in patterns
            if len(p['sequence']) == 2 and
            'bedroom_motion' in p['sequence'][0] and
            'bedroom' in p['sequence'][1]
        ]
        assert len(two_step) >= 1

    def test_arrival_sequence_detection(self, detector):
        """Test detection of arrival sequence pattern."""
        base_date = datetime(2026, 3, 1)
        events = self.generate_arrival_sequence_events(base_date, num_occurrences=5)

        patterns = detector.detect_patterns(events)

        # Should detect arrival pattern
        assert len(patterns) >= 1

        # Check for garage → hallway pattern
        garage_patterns = [
            p for p in patterns
            if any('garage' in d for d in p['sequence']) and
            any('hallway' in d for d in p['sequence'])
        ]
        assert len(garage_patterns) >= 1

    def test_combined_patterns(self, detector):
        """Test detection with multiple pattern types in same dataset."""
        base_date = datetime(2026, 3, 1)

        morning_events = self.generate_morning_routine_events(base_date, num_days=7)
        arrival_events = self.generate_arrival_sequence_events(base_date, num_occurrences=5)

        all_events = pd.concat([morning_events, arrival_events], ignore_index=True)
        patterns = detector.detect_patterns(all_events)

        # Should detect patterns from both routines
        assert len(patterns) >= 2

        # Verify we got morning patterns
        morning_patterns = [
            p for p in patterns
            if any('bedroom' in d for d in p['sequence'])
        ]
        assert len(morning_patterns) >= 1

        # Verify we got arrival patterns
        arrival_patterns = [
            p for p in patterns
            if any('garage' in d or 'hallway' in d for d in p['sequence'])
        ]
        assert len(arrival_patterns) >= 1

    def test_noise_filtering_in_integration(self, detector):
        """Test that system noise doesn't pollute patterns."""
        events = pd.DataFrame({
            'device_id': [
                # Valid sequence
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                # System noise interspersed
                'sensor.home_assistant_cpu', 'sensor.nfl_team_tracker',
                'image.roborock_map', 'camera.front_door',
            ],
            'timestamp': [
                datetime(2026, 3, 6, 8, 0, 0),
                datetime(2026, 3, 6, 8, 0, 30),
                datetime(2026, 3, 6, 9, 0, 0),
                datetime(2026, 3, 6, 9, 0, 30),
                datetime(2026, 3, 6, 10, 0, 0),
                datetime(2026, 3, 6, 10, 0, 30),
                datetime(2026, 3, 6, 8, 0, 15),
                datetime(2026, 3, 6, 9, 0, 15),
                datetime(2026, 3, 6, 10, 0, 15),
                datetime(2026, 3, 6, 11, 0, 0),
            ],
            'state': ['on'] * 10,
        })

        patterns = detector.detect_patterns(events)

        # Should detect motion → light pattern
        assert len(patterns) >= 1

        # No system noise in detected patterns
        for pattern in patterns:
            for device in pattern['sequence']:
                assert 'home_assistant' not in device
                assert 'nfl_' not in device
                assert 'roborock' not in device
                assert 'camera' not in device

    def test_automation_suggestion_from_real_pattern(self, detector):
        """Test automation suggestion generation from detected pattern."""
        base_date = datetime(2026, 3, 1)
        events = self.generate_morning_routine_events(base_date, num_days=10)

        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1

        # Get suggestion from first pattern
        suggestion = detector.suggest_automation(patterns[0])

        assert suggestion != {}
        assert suggestion['automation_type'] == 'sequence'
        assert 'trigger' in suggestion
        assert 'action' in suggestion
        assert suggestion['confidence'] >= 0.5

    def test_pattern_summary_with_real_data(self, detector):
        """Test pattern summary with realistic data."""
        base_date = datetime(2026, 3, 1)
        events = self.generate_morning_routine_events(base_date, num_days=14)

        patterns = detector.detect_patterns(events)
        summary = detector.get_pattern_summary(patterns)

        assert summary['total_patterns'] >= 1
        assert summary['avg_confidence'] >= 0.5
        assert summary['avg_sequence_length'] >= 2
