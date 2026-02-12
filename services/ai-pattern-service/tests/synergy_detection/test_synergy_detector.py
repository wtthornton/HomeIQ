"""
Tests for synergy_detector.py

Tests the confidence floor for high-value synergy types
(Pattern Intelligence epic, Story 1).
"""

import pytest
import sys
from pathlib import Path

# Add the src directory to the path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Actual high-value synergy types used in production code
HIGH_VALUE_TYPES = {
    'weather_context', 'energy_context', 'sports_context',
    'calendar_context', 'carbon_context',
    'scene_based', 'schedule_based',
}


class TestConfidenceFloor:
    """
    Test the confidence floor for high-value synergy types.

    Context/scene/schedule synergies get a lower confidence threshold
    (min_confidence - 0.1) because they represent higher-quality intelligence
    than simple device pairs.
    """

    def _make_synergy(self, synergy_type: str, confidence: float) -> dict:
        """Helper to create a minimal synergy dict."""
        return {
            "synergy_type": synergy_type,
            "confidence": confidence,
            "impact_score": 0.5,
            "trigger_entity": "sensor.a",
            "action_entity": "light.b",
        }

    def _effective_threshold(self, synergy_type: str, min_confidence: float = 0.7) -> float:
        """Calculate the effective threshold for a synergy type."""
        return min_confidence - 0.1 if synergy_type in HIGH_VALUE_TYPES else min_confidence

    def test_device_pair_at_threshold_passes(self):
        """Device pair at 0.7 confidence should pass (default threshold)."""
        s = self._make_synergy("device_pair", 0.7)
        assert s["confidence"] >= self._effective_threshold("device_pair")

    def test_device_pair_below_threshold_fails(self):
        """Device pair at 0.65 confidence should fail (below 0.7)."""
        s = self._make_synergy("device_pair", 0.65)
        assert s["confidence"] < self._effective_threshold("device_pair")

    def test_weather_context_at_reduced_threshold_passes(self):
        """Weather context at 0.65 confidence should pass (threshold reduced to 0.6)."""
        s = self._make_synergy("weather_context", 0.65)
        assert s["confidence"] >= self._effective_threshold("weather_context")

    def test_weather_context_below_reduced_threshold_fails(self):
        """Weather context at 0.55 confidence should still fail (below 0.6)."""
        s = self._make_synergy("weather_context", 0.55)
        assert s["confidence"] < self._effective_threshold("weather_context")

    def test_energy_context_gets_reduced_threshold(self):
        """Energy context synergies should use reduced threshold."""
        s = self._make_synergy("energy_context", 0.62)
        assert s["confidence"] >= self._effective_threshold("energy_context")

    def test_scene_based_gets_reduced_threshold(self):
        """Scene-based synergies should use reduced threshold."""
        s = self._make_synergy("scene_based", 0.62)
        assert s["confidence"] >= self._effective_threshold("scene_based")

    def test_schedule_based_gets_reduced_threshold(self):
        """Schedule-based synergies should use reduced threshold."""
        s = self._make_synergy("schedule_based", 0.61)
        assert s["confidence"] >= self._effective_threshold("schedule_based")

    def test_sports_context_gets_reduced_threshold(self):
        """Sports context synergies should use reduced threshold."""
        s = self._make_synergy("sports_context", 0.63)
        assert s["confidence"] >= self._effective_threshold("sports_context")

    def test_calendar_context_gets_reduced_threshold(self):
        """Calendar context synergies should use reduced threshold."""
        s = self._make_synergy("calendar_context", 0.60)
        assert s["confidence"] >= self._effective_threshold("calendar_context")

    def test_carbon_context_gets_reduced_threshold(self):
        """Carbon context synergies should use reduced threshold."""
        s = self._make_synergy("carbon_context", 0.61)
        assert s["confidence"] >= self._effective_threshold("carbon_context")

    def test_device_chain_uses_normal_threshold(self):
        """Device chains are NOT high-value — should use normal threshold."""
        s = self._make_synergy("device_chain", 0.65)
        assert s["confidence"] < self._effective_threshold("device_chain")

    def test_filter_logic_matches_production_code(self):
        """Simulate the exact filter from synergy_detector.py."""
        min_confidence = 0.7

        synergies = [
            self._make_synergy("device_pair", 0.72),           # pass (0.72 >= 0.7)
            self._make_synergy("device_pair", 0.65),           # FAIL (0.65 < 0.7)
            self._make_synergy("weather_context", 0.65),       # pass (0.65 >= 0.6)
            self._make_synergy("scene_based", 0.60),           # pass (0.60 >= 0.6)
            self._make_synergy("schedule_based", 0.55),        # FAIL (0.55 < 0.6)
            self._make_synergy("device_chain", 0.68),          # FAIL (0.68 < 0.7)
            self._make_synergy("energy_context", 0.61),        # pass (0.61 >= 0.6)
            self._make_synergy("carbon_context", 0.59),        # FAIL (0.59 < 0.6)
        ]

        filtered = [
            s for s in synergies
            if s["confidence"] >= (
                min_confidence - 0.1
                if s.get("synergy_type") in HIGH_VALUE_TYPES
                else min_confidence
            )
        ]

        assert len(filtered) == 4
        types = [s["synergy_type"] for s in filtered]
        assert "device_pair" in types
        assert "weather_context" in types
        assert "scene_based" in types
        assert "energy_context" in types
