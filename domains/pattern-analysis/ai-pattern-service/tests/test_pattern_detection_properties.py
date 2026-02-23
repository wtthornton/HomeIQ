"""
Property-based tests for pattern detection using Hypothesis.

Tests invariants and properties that should hold for any valid input,
rather than specific test cases.

Created: January 2026
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st, assume

# Import modules under test
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from pattern_analyzer.time_of_day import TimeOfDayPatternDetector


# ============================================================================
# Custom Strategies
# ============================================================================

@st.composite
def device_id_strategy(draw):
    """Generate valid device IDs."""
    domains = ["light", "switch", "climate", "cover", "lock", "sensor", "binary_sensor"]
    domain = draw(st.sampled_from(domains))
    name = draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_",
        min_size=3,
        max_size=20
    ))
    return f"{domain}.{name}"


@st.composite
def timestamp_strategy(draw, base_date=None):
    """Generate timestamps within a reasonable range."""
    if base_date is None:
        base_date = datetime(2026, 1, 1)
    
    # Generate offset in hours (up to 30 days)
    hours_offset = draw(st.integers(min_value=0, max_value=720))
    return base_date + timedelta(hours=hours_offset)


@st.composite
def event_dataframe_strategy(draw, min_events=5, max_events=100):
    """Generate valid event DataFrames for pattern detection."""
    n_events = draw(st.integers(min_value=min_events, max_value=max_events))
    n_devices = draw(st.integers(min_value=1, max_value=min(5, n_events)))
    
    # Generate device IDs
    device_ids = [draw(device_id_strategy()) for _ in range(n_devices)]
    
    # Generate events
    events = []
    base_date = datetime(2026, 1, 1)
    
    for _ in range(n_events):
        device_id = draw(st.sampled_from(device_ids))
        timestamp = draw(timestamp_strategy(base_date))
        state = draw(st.sampled_from(["on", "off", "open", "closed"]))
        
        events.append({
            "device_id": device_id,
            "timestamp": timestamp,
            "state": state,
        })
    
    return pd.DataFrame(events)


@st.composite
def clustered_event_strategy(draw, device_id=None, target_hour=None, n_events=None):
    """Generate events clustered around a specific time."""
    if device_id is None:
        device_id = draw(device_id_strategy())
    
    if target_hour is None:
        target_hour = draw(st.integers(min_value=0, max_value=23))
    
    if n_events is None:
        n_events = draw(st.integers(min_value=5, max_value=20))
    
    # Generate events clustered around target hour
    events = []
    base_date = datetime(2026, 1, 1)
    
    for day in range(n_events):
        # Add some variance (±30 minutes)
        minute_variance = draw(st.integers(min_value=-30, max_value=30))
        hour = target_hour
        minute = 30 + minute_variance
        
        # Handle hour overflow
        if minute < 0:
            hour = (hour - 1) % 24
            minute += 60
        elif minute >= 60:
            hour = (hour + 1) % 24
            minute -= 60
        
        timestamp = base_date.replace(hour=hour, minute=minute) + timedelta(days=day)
        
        events.append({
            "device_id": device_id,
            "timestamp": timestamp,
            "state": "on",
        })
    
    return pd.DataFrame(events)


# ============================================================================
# Property Tests - TimeOfDayPatternDetector
# ============================================================================

class TestTimeOfDayPatternDetectorProperties:
    """Property-based tests for TimeOfDayPatternDetector."""
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_patterns_have_valid_structure(self, events):
        """Property: All detected patterns have valid structure."""
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.5)
        patterns = detector.detect_patterns(events)
        
        for pattern in patterns:
            # Required fields exist
            assert "device_id" in pattern
            assert "pattern_type" in pattern
            assert "hour" in pattern
            assert "minute" in pattern
            assert "confidence" in pattern
            assert "occurrences" in pattern
            
            # Valid ranges
            assert 0 <= pattern["hour"] <= 23
            assert 0 <= pattern["minute"] <= 59
            assert 0.0 <= pattern["confidence"] <= 1.0
            assert pattern["occurrences"] >= 0
            assert pattern["pattern_type"] == "time_of_day"
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_patterns_reference_existing_devices(self, events):
        """Property: Patterns only reference devices that exist in input."""
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.5)
        patterns = detector.detect_patterns(events)
        
        input_devices = set(events["device_id"].unique())
        
        for pattern in patterns:
            assert pattern["device_id"] in input_devices
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_occurrences_not_exceed_total_events(self, events):
        """Property: Pattern occurrences don't exceed total events for device."""
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.5)
        patterns = detector.detect_patterns(events)
        
        for pattern in patterns:
            device_id = pattern["device_id"]
            device_events = len(events[events["device_id"] == device_id])
            
            assert pattern["occurrences"] <= device_events
            assert pattern["total_events"] == device_events
    
    @given(events=event_dataframe_strategy(min_events=10, max_events=50))
    @settings(max_examples=30, deadline=5000)
    def test_confidence_calculation_is_bounded(self, events):
        """Property: Confidence is always between 0 and 1."""
        detector = TimeOfDayPatternDetector(min_occurrences=2, min_confidence=0.3)
        patterns = detector.detect_patterns(events)
        
        for pattern in patterns:
            assert 0.0 <= pattern["confidence"] <= 1.0
    
    @given(
        target_hour=st.integers(min_value=0, max_value=23),
        n_events=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=30, deadline=5000)
    def test_clustered_events_detected(self, target_hour, n_events):
        """Property: Tightly clustered events should be detected as patterns."""
        # Generate clustered events
        device_id = "light.test_device"
        events = []
        base_date = datetime(2026, 1, 1)
        
        for day in range(n_events):
            # Very tight clustering (±5 minutes)
            minute_variance = np.random.randint(-5, 6)
            hour = target_hour
            minute = 30 + minute_variance
            
            if minute < 0:
                hour = (hour - 1) % 24
                minute += 60
            elif minute >= 60:
                hour = (hour + 1) % 24
                minute -= 60
            
            timestamp = base_date.replace(hour=hour, minute=minute) + timedelta(days=day)
            events.append({
                "device_id": device_id,
                "timestamp": timestamp,
                "state": "on",
            })
        
        df = pd.DataFrame(events)
        
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.5)
        patterns = detector.detect_patterns(df)
        
        # Should detect at least one pattern for this device
        device_patterns = [p for p in patterns if p["device_id"] == device_id]
        assert len(device_patterns) >= 1, f"Expected pattern for {device_id} at hour {target_hour}"
        
        # Pattern hour should be close to target
        detected_hour = device_patterns[0]["hour"]
        hour_diff = min(
            abs(detected_hour - target_hour),
            24 - abs(detected_hour - target_hour)  # Handle wrap-around
        )
        assert hour_diff <= 1, f"Detected hour {detected_hour} too far from target {target_hour}"
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_empty_result_on_insufficient_data(self, events):
        """Property: No patterns when min_occurrences is very high."""
        # Set impossibly high threshold
        detector = TimeOfDayPatternDetector(
            min_occurrences=len(events) + 100,
            min_confidence=0.99
        )
        patterns = detector.detect_patterns(events)
        
        assert len(patterns) == 0
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_deterministic_results(self, events):
        """Property: Same input produces same output."""
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.5)
        
        patterns1 = detector.detect_patterns(events.copy())
        patterns2 = detector.detect_patterns(events.copy())
        
        # Same number of patterns
        assert len(patterns1) == len(patterns2)
        
        # Same device IDs
        devices1 = {p["device_id"] for p in patterns1}
        devices2 = {p["device_id"] for p in patterns2}
        assert devices1 == devices2
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_external_sources_filtered(self, events):
        """Property: External data sources are not included in patterns."""
        # Add some external source events
        external_events = pd.DataFrame([
            {"device_id": "sensor.weather_temperature", "timestamp": datetime(2026, 1, 1, 12), "state": "72"},
            {"device_id": "sensor.nfl_scores", "timestamp": datetime(2026, 1, 1, 12), "state": "active"},
            {"device_id": "sensor.calendar_event", "timestamp": datetime(2026, 1, 1, 12), "state": "busy"},
        ])
        
        combined = pd.concat([events, external_events], ignore_index=True)
        
        detector = TimeOfDayPatternDetector(min_occurrences=1, min_confidence=0.3)
        patterns = detector.detect_patterns(combined)
        
        # No patterns for external sources
        for pattern in patterns:
            device_id = pattern["device_id"].lower()
            assert "weather" not in device_id
            assert "nfl" not in device_id
            assert "calendar" not in device_id


# ============================================================================
# Property Tests - Automation Suggestions
# ============================================================================

class TestAutomationSuggestionProperties:
    """Property-based tests for automation suggestions."""
    
    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        confidence=st.floats(min_value=0.5, max_value=1.0),
        device_id=device_id_strategy()
    )
    @settings(max_examples=50, deadline=5000)
    def test_suggestion_structure(self, hour, minute, confidence, device_id):
        """Property: Suggestions have valid structure."""
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": device_id,
            "hour": hour,
            "minute": minute,
            "confidence": confidence,
            "occurrences": 10,
            "metadata": {}
        }
        
        detector = TimeOfDayPatternDetector()
        suggestion = detector.suggest_automation(pattern)
        
        # Required fields
        assert "automation_type" in suggestion
        assert "trigger" in suggestion
        assert "action" in suggestion
        assert "confidence" in suggestion
        assert "description" in suggestion
        assert "device_id" in suggestion
        
        # Safety fields (new)
        assert "requires_confirmation" in suggestion
        assert "safety_level" in suggestion
        assert "safety_warnings" in suggestion
        
        # Valid values
        assert suggestion["automation_type"] == "schedule"
        assert suggestion["confidence"] == confidence
        assert suggestion["device_id"] == device_id
    
    @given(device_id=device_id_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_security_domains_require_confirmation(self, device_id):
        """Property: Security-sensitive domains require confirmation."""
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": device_id,
            "hour": 7,
            "minute": 0,
            "confidence": 0.8,
            "occurrences": 10,
        }
        
        detector = TimeOfDayPatternDetector()
        suggestion = detector.suggest_automation(pattern)
        
        domain = device_id.split(".")[0]
        security_domains = {"lock", "cover", "garage", "alarm_control_panel", "gate", "door"}
        
        if domain in security_domains:
            assert suggestion["requires_confirmation"] is True
            assert suggestion["safety_level"] == "high"
            assert len(suggestion["safety_warnings"]) > 0
        else:
            # Non-security domains may or may not require confirmation
            assert isinstance(suggestion["requires_confirmation"], bool)
    
    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=30, deadline=5000)
    def test_trigger_time_format(self, hour, minute):
        """Property: Trigger time is correctly formatted."""
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": "light.test",
            "hour": hour,
            "minute": minute,
            "confidence": 0.8,
            "occurrences": 10,
        }
        
        detector = TimeOfDayPatternDetector()
        suggestion = detector.suggest_automation(pattern)
        
        trigger_time = suggestion["trigger"]["at"]
        
        # Format should be HH:MM:SS
        assert len(trigger_time) == 8
        assert trigger_time[2] == ":"
        assert trigger_time[5] == ":"
        
        # Parse and verify
        parts = trigger_time.split(":")
        assert int(parts[0]) == hour
        assert int(parts[1]) == minute
        assert int(parts[2]) == 0
    
    @given(device_id=device_id_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_action_service_matches_domain(self, device_id):
        """Property: Action service matches device domain."""
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": device_id,
            "hour": 7,
            "minute": 0,
            "confidence": 0.8,
            "occurrences": 10,
        }
        
        detector = TimeOfDayPatternDetector()
        suggestion = detector.suggest_automation(pattern)
        
        domain = device_id.split(".")[0]
        service = suggestion["action"]["service"]
        
        # Service should start with domain
        assert service.startswith(f"{domain}.")
    
    def test_wrong_pattern_type_returns_empty(self):
        """Property: Wrong pattern type returns empty dict."""
        pattern = {
            "pattern_type": "co_occurrence",  # Wrong type
            "device_id": "light.test",
            "hour": 7,
            "minute": 0,
            "confidence": 0.8,
        }
        
        detector = TimeOfDayPatternDetector()
        suggestion = detector.suggest_automation(pattern)
        
        assert suggestion == {}


# ============================================================================
# Property Tests - Pattern Summary
# ============================================================================

class TestPatternSummaryProperties:
    """Property-based tests for pattern summary statistics."""
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_summary_statistics_valid(self, events):
        """Property: Summary statistics are valid."""
        detector = TimeOfDayPatternDetector(min_occurrences=2, min_confidence=0.3)
        patterns = detector.detect_patterns(events)
        summary = detector.get_pattern_summary(patterns)
        
        # Required fields
        assert "total_patterns" in summary
        assert "unique_devices" in summary
        assert "avg_confidence" in summary
        assert "avg_occurrences" in summary
        
        # Valid values
        assert summary["total_patterns"] == len(patterns)
        assert summary["unique_devices"] <= len(patterns)
        
        if patterns:
            assert 0.0 <= summary["avg_confidence"] <= 1.0
            assert summary["avg_occurrences"] >= 0
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_empty_patterns_summary(self, events):
        """Property: Empty patterns produce valid summary."""
        detector = TimeOfDayPatternDetector()
        summary = detector.get_pattern_summary([])
        
        assert summary["total_patterns"] == 0
        assert summary["unique_devices"] == 0
        assert summary["avg_confidence"] == 0.0
        assert summary["avg_occurrences"] == 0.0


# ============================================================================
# Invariant Tests
# ============================================================================

class TestInvariants:
    """Tests for invariants that should always hold."""
    
    @given(
        min_occurrences=st.integers(min_value=1, max_value=10),
        min_confidence=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=20, deadline=5000)
    def test_threshold_invariant(self, min_occurrences, min_confidence):
        """Invariant: All patterns meet threshold requirements."""
        # Generate some test data
        events = pd.DataFrame([
            {"device_id": "light.test", "timestamp": datetime(2026, 1, d, 7, 0), "state": "on"}
            for d in range(1, 20)
        ])
        
        detector = TimeOfDayPatternDetector(
            min_occurrences=min_occurrences,
            min_confidence=min_confidence
        )
        patterns = detector.detect_patterns(events)
        
        for pattern in patterns:
            assert pattern["occurrences"] >= min_occurrences
            assert pattern["confidence"] >= min_confidence
    
    @given(events=event_dataframe_strategy())
    @settings(max_examples=30, deadline=5000)
    def test_no_negative_values(self, events):
        """Invariant: No negative values in pattern output."""
        detector = TimeOfDayPatternDetector(min_occurrences=2, min_confidence=0.3)
        patterns = detector.detect_patterns(events)
        
        for pattern in patterns:
            assert pattern["hour"] >= 0
            assert pattern["minute"] >= 0
            assert pattern["confidence"] >= 0
            assert pattern["occurrences"] >= 0
            assert pattern["total_events"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
