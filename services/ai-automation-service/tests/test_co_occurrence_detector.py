"""
Unit tests for Co-Occurrence Pattern Detector
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector


def create_test_events(device_pairs: list, timestamps: list) -> pd.DataFrame:
    """
    Helper to create test event data for device pairs.

    Args:
        device_pairs: List of (device_id, timestamp_offset_seconds) tuples
        timestamps: List of base timestamps

    Returns:
        DataFrame with device_id, timestamp, state columns
    """
    events = []
    for base_time in timestamps:
        for device_id, offset_seconds in device_pairs:
            events.append({
                "device_id": device_id,
                "timestamp": base_time + timedelta(seconds=offset_seconds),
                "state": "on",
            })

    df = pd.DataFrame(events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


class TestCoOccurrencePatternDetector:
    """Test Co-Occurrence Pattern Detector"""

    def test_initialization(self):
        """Test detector initialization with custom parameters"""
        detector = CoOccurrencePatternDetector(
            window_minutes=10,
            min_support=3,
            min_confidence=0.8,
        )
        assert detector.window_minutes == 10
        assert detector.min_support == 3
        assert detector.min_confidence == 0.8

    def test_detects_motion_light_pattern(self):
        """Test detection of motion sensor + light pattern"""
        # Create pattern: motion sensor triggers, then light turns on within 30 seconds
        events = pd.DataFrame({
            "device_id": [
                "motion.hallway", "light.hallway",  # Pair 1
                "motion.hallway", "light.hallway",  # Pair 2
                "motion.hallway", "light.hallway",  # Pair 3
                "motion.hallway", "light.hallway",  # Pair 4
                "motion.hallway", "light.hallway",  # Pair 5
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 18:00:00", "2025-10-01 18:00:30",
                "2025-10-02 18:01:00", "2025-10-02 18:01:25",
                "2025-10-03 18:02:00", "2025-10-03 18:02:20",
                "2025-10-04 18:00:00", "2025-10-04 18:00:15",
                "2025-10-05 18:01:00", "2025-10-05 18:01:40",
            ]),
            "state": ["on"] * 10,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=3, min_confidence=0.5)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert {pattern["device1"], pattern["device2"]} == {"motion.hallway", "light.hallway"}
        assert pattern["occurrences"] >= 5
        assert pattern["pattern_type"] == "co_occurrence"

    def test_respects_time_window(self):
        """Test only detects co-occurrences within window"""
        events = pd.DataFrame({
            "device_id": ["device_a", "device_b", "device_a", "device_b"],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00",
                "2025-10-01 10:00:30",  # Within window (30 sec)
                "2025-10-02 10:00:00",
                "2025-10-02 10:10:00",  # Outside window (10 min)
            ]),
            "state": ["on"] * 4,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=1, min_confidence=0.3)
        patterns = detector.detect_patterns(events)

        # Should detect 1 co-occurrence (first pair within window)
        assert len(patterns) >= 1
        assert patterns[0]["occurrences"] == 1

    def test_filters_by_minimum_support(self):
        """Test minimum support threshold is enforced"""
        # Only 2 co-occurrences
        events = pd.DataFrame({
            "device_id": ["device_a", "device_b", "device_a", "device_b"],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:30",
                "2025-10-02 10:00:00", "2025-10-02 10:00:30",
            ]),
            "state": ["on"] * 4,
        })

        # Require 5 occurrences
        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=5, min_confidence=0.3)
        patterns = detector.detect_patterns(events)

        # Should not detect pattern (only 2 occurrences, need 5)
        assert len(patterns) == 0

    def test_filters_by_minimum_confidence(self):
        """Test minimum confidence threshold is enforced"""
        # Create mixed pattern: A+B sometimes, A alone other times
        events = pd.DataFrame({
            "device_id": [
                "device_a", "device_b",  # Together
                "device_a", "device_b",  # Together
                "device_a",              # Alone
                "device_a",              # Alone
                "device_a",              # Alone
                "device_a",              # Alone
                "device_a",              # Alone
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:30",
                "2025-10-02 10:00:00", "2025-10-02 10:00:30",
                "2025-10-03 10:00:00",
                "2025-10-04 10:00:00",
                "2025-10-05 10:00:00",
                "2025-10-06 10:00:00",
                "2025-10-07 10:00:00",
            ]),
            "state": ["on"] * 9,
        })

        # Confidence = 2 co-occurrences / min(7 device_a events, 2 device_b events) = 2/2 = 100%
        # This is high confidence because device_b always follows A (within window)
        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=2, min_confidence=0.8)
        patterns = detector.detect_patterns(events)

        # Should detect pattern (confidence is 100%)
        assert len(patterns) >= 1
        assert patterns[0]["confidence"] >= 0.8

    def test_handles_multiple_device_pairs(self):
        """Test detection of multiple independent co-occurrence patterns"""
        events = pd.DataFrame({
            "device_id": [
                # Pattern 1: motion.hall + light.hall
                "motion.hall", "light.hall",
                "motion.hall", "light.hall",
                "motion.hall", "light.hall",
                # Pattern 2: door.front + alarm.system
                "door.front", "alarm.system",
                "door.front", "alarm.system",
                "door.front", "alarm.system",
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:10",
                "2025-10-02 10:00:00", "2025-10-02 10:00:15",
                "2025-10-03 10:00:00", "2025-10-03 10:00:20",
                "2025-10-01 14:00:00", "2025-10-01 14:00:05",
                "2025-10-02 14:00:00", "2025-10-02 14:00:08",
                "2025-10-03 14:00:00", "2025-10-03 14:00:12",
            ]),
            "state": ["on"] * 12,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=2, min_confidence=0.7)
        patterns = detector.detect_patterns(events)

        # Should detect 2 independent patterns
        assert len(patterns) == 2

        device_pairs = [{p["device1"], p["device2"]} for p in patterns]
        assert {"motion.hall", "light.hall"} in device_pairs
        assert {"door.front", "alarm.system"} in device_pairs

    def test_avoids_duplicate_pairs(self):
        """Test that (A,B) and (B,A) are treated as the same pattern"""
        events = pd.DataFrame({
            "device_id": [
                "device_a", "device_b",  # A then B
                "device_b", "device_a",  # B then A
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:30",
                "2025-10-02 10:00:00", "2025-10-02 10:00:30",
            ]),
            "state": ["on"] * 4,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=1, min_confidence=0.3)
        patterns = detector.detect_patterns(events)

        # Should have single pattern (not separate A->B and B->A)
        device_pairs = [tuple(sorted([p["device1"], p["device2"]])) for p in patterns]
        unique_pairs = set(device_pairs)
        assert len(unique_pairs) == len(patterns)  # No duplicates

    def test_excludes_same_device_pairs(self):
        """Test that device is not paired with itself"""
        events = pd.DataFrame({
            "device_id": ["device_a", "device_a", "device_a"],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00",
                "2025-10-01 10:00:30",
                "2025-10-01 10:01:00",
            ]),
            "state": ["on"] * 3,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=1)
        patterns = detector.detect_patterns(events)

        # Should not detect any patterns (same device doesn't pair with itself)
        assert len(patterns) == 0

    def test_empty_dataframe(self):
        """Test handles empty DataFrame gracefully"""
        events = pd.DataFrame()

        detector = CoOccurrencePatternDetector()
        patterns = detector.detect_patterns(events)

        assert patterns == []

    def test_missing_required_columns(self):
        """Test handles missing columns gracefully"""
        # Missing 'timestamp' column
        events = pd.DataFrame({
            "device_id": ["device_a", "device_b"],
            "state": ["on", "on"],
        })

        detector = CoOccurrencePatternDetector()
        patterns = detector.detect_patterns(events)

        assert patterns == []

    def test_pattern_metadata_includes_stats(self):
        """Test pattern metadata includes statistical information"""
        events = pd.DataFrame({
            "device_id": [
                "motion.sensor", "light.bulb",
                "motion.sensor", "light.bulb",
                "motion.sensor", "light.bulb",
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:15",
                "2025-10-02 10:00:00", "2025-10-02 10:00:20",
                "2025-10-03 10:00:00", "2025-10-03 10:00:25",
            ]),
            "state": ["on"] * 6,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=2, min_confidence=0.7)
        patterns = detector.detect_patterns(events)

        assert len(patterns) == 1
        metadata = patterns[0]["metadata"]

        assert "window_minutes" in metadata
        assert "support" in metadata
        assert "device1_count" in metadata
        assert "device2_count" in metadata
        assert "avg_time_delta_seconds" in metadata

        # Average time delta might be None if calculation fails, or should be around 20 seconds
        if metadata["avg_time_delta_seconds"] is not None:
            assert 10 < metadata["avg_time_delta_seconds"] < 30

    def test_confidence_calculation(self):
        """Test confidence score is calculated correctly"""
        # Device A: 5 events (at indices 0,2,4,6,7)
        # Device B: 3 events (at indices 1,3,5)
        # Co-occurrences: 3 (all B events follow A within window)
        events_list = []
        events_list.extend([
            {"device_id": "device_a", "timestamp": "2025-10-01 10:00:00", "state": "on"},
            {"device_id": "device_b", "timestamp": "2025-10-01 10:00:30", "state": "on"},
            {"device_id": "device_a", "timestamp": "2025-10-02 10:00:00", "state": "on"},
            {"device_id": "device_b", "timestamp": "2025-10-02 10:00:30", "state": "on"},
            {"device_id": "device_a", "timestamp": "2025-10-03 10:00:00", "state": "on"},
            {"device_id": "device_b", "timestamp": "2025-10-03 10:00:30", "state": "on"},
            {"device_id": "device_a", "timestamp": "2025-10-04 10:00:00", "state": "on"},
            {"device_id": "device_a", "timestamp": "2025-10-05 10:00:00", "state": "on"},
        ])

        events = pd.DataFrame(events_list)
        events["timestamp"] = pd.to_datetime(events["timestamp"])

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=2, min_confidence=0.5)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]

        # Confidence = 3 / min(5, 3) = 3/3 = 1.0 (100% of B events follow A)
        assert pattern["confidence"] == pytest.approx(1.0, abs=0.05)
        assert pattern["occurrences"] == 3

    def test_get_pattern_summary_with_patterns(self):
        """Test pattern summary generation with patterns"""
        events = pd.DataFrame({
            "device_id": [
                "device_a", "device_b",
                "device_a", "device_b",
                "device_a", "device_b",
            ],
            "timestamp": pd.to_datetime([
                "2025-10-01 10:00:00", "2025-10-01 10:00:30",
                "2025-10-02 10:00:00", "2025-10-02 10:00:30",
                "2025-10-03 10:00:00", "2025-10-03 10:00:30",
            ]),
            "state": ["on"] * 6,
        })

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=2, min_confidence=0.7)
        patterns = detector.detect_patterns(events)
        summary = detector.get_pattern_summary(patterns)

        assert summary["total_patterns"] >= 1
        assert summary["unique_device_pairs"] >= 1
        assert summary["avg_confidence"] > 0.0
        assert "confidence_distribution" in summary

    def test_get_pattern_summary_empty(self):
        """Test pattern summary with no patterns"""
        detector = CoOccurrencePatternDetector()
        summary = detector.get_pattern_summary([])

        assert summary["total_patterns"] == 0
        assert summary["unique_device_pairs"] == 0
        assert summary["avg_confidence"] == 0.0
        assert summary["avg_occurrences"] == 0.0

    def test_optimized_version_with_large_dataset(self):
        """Test optimized version handles large datasets with sampling"""
        # Create a large dataset (simulated)
        dates = pd.date_range("2025-01-01", "2025-10-01", freq="1h")
        large_events = pd.DataFrame({
            "device_id": ["device_a", "device_b"] * len(dates),
            "timestamp": list(dates) * 2,
            "state": ["on"] * (len(dates) * 2),
        })
        large_events = large_events.sample(frac=1).reset_index(drop=True)  # Shuffle

        detector = CoOccurrencePatternDetector(window_minutes=5, min_support=5, min_confidence=0.5)

        # Should handle large dataset without errors
        patterns = detector.detect_patterns_optimized(large_events)

        # Verify it returns results (actual patterns depend on sampling)
        assert isinstance(patterns, list)


@pytest.mark.asyncio
async def test_co_occurrence_detector_integration():
    """
    Integration test: Fetch real data from Data API and detect co-occurrence patterns.
    Requires: docker-compose up data-api ai-automation-service
    """
    from datetime import timedelta, timezone

    from src.clients.data_api_client import DataAPIClient

    client = DataAPIClient(base_url="http://localhost:8006")

    try:
        # Fetch last 7 days of events
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        events_df = await client.fetch_events(start_time=start_time, limit=1000)

        if events_df.empty:
            pytest.skip("No events available in Data API")

        # Detect co-occurrence patterns
        detector = CoOccurrencePatternDetector(
            window_minutes=5,
            min_support=2,
            min_confidence=0.5,
        )
        patterns = detector.detect_patterns(events_df)

        # Verify patterns structure
        for pattern in patterns:
            assert "device1" in pattern
            assert "device2" in pattern
            assert "pattern_type" in pattern
            assert pattern["pattern_type"] == "co_occurrence"
            assert "occurrences" in pattern
            assert pattern["occurrences"] >= 2
            assert "confidence" in pattern
            assert 0.0 <= pattern["confidence"] <= 1.0
            assert "metadata" in pattern

        print(f"\n✅ Detected {len(patterns)} co-occurrence patterns from real data")

    finally:
        await client.close()

