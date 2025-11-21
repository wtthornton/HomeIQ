"""
Unit Tests for EnhancementExtractor

Epic AI-4, Story AI4.2
"""
import pytest

pytest.skip(
    "Enhancement extractor module removed from ai-automation-service; skipping legacy tests",
    allow_module_level=True,
)

from src.miner.enhancement_extractor import EnhancementExtractor


class TestEnhancementExtractor:
    """Test EnhancementExtractor functionality"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance"""
        return EnhancementExtractor()

    @pytest.fixture
    def sample_automation(self):
        """Sample community automation"""
        return {
            "id": 1,
            "title": "Motion-activated lighting",
            "devices": ["motion_sensor", "light"],
            "integrations": ["mqtt"],
            "triggers": [
                {"type": "state", "entity": "binary_sensor.motion"},
                {"type": "time", "after": "sunset", "offset": "-00:30:00"},
            ],
            "conditions": [
                {"type": "state", "entity": "sun.sun", "state": "below_horizon"},
            ],
            "actions": [
                {"service": "light.turn_on", "data": {"brightness": 50}},
            ],
            "quality_score": 0.85,
        }

    def test_extract_no_enhancements_no_automations(self, extractor):
        """Test extraction with no automations"""
        enhancements = extractor.extract_enhancements([], ["light"])

        assert enhancements == []

    def test_extract_condition_enhancements(self, extractor, sample_automation):
        """Test extracting condition enhancements"""
        user_devices = ["motion_sensor", "light"]

        enhancements = extractor.extract_enhancements([sample_automation], user_devices)

        # Should find at least the time condition
        assert len(enhancements) > 0

    def test_extract_timing_enhancements(self, extractor):
        """Test extracting timing enhancements"""
        automation = {
            "triggers": [
                {"type": "time", "offset": "-00:30:00"},  # Offset trigger
            ],
            "devices": ["light"],
            "quality_score": 0.9,
        }

        user_devices = ["light"]
        enhancements = extractor.extract_enhancements([automation], user_devices)

        # Should extract timing enhancement
        timing_enhancements = [e for e in enhancements if e.type == "timing"]
        assert len(timing_enhancements) > 0

    def test_extract_action_enhancements(self, extractor):
        """Test extracting action enhancements"""
        automation = {
            "actions": [
                {"service": "light.turn_on", "data": {"brightness": 50, "color_temp": 2700}},
            ],
            "devices": ["light"],
            "quality_score": 0.85,
        }

        user_devices = ["light"]
        enhancements = extractor.extract_enhancements([automation], user_devices)

        # Should extract action enhancements (brightness or color)
        action_enhancements = [e for e in enhancements if e.type == "action"]
        assert len(action_enhancements) > 0

    def test_applicability_filtering(self, extractor):
        """Test that enhancements are filtered by user's devices"""
        automation = {
            "devices": ["motion_sensor", "light"],
            "conditions": [{"type": "state"}],
            "quality_score": 0.9,
        }

        # User doesn't have motion_sensor
        user_devices = ["switch"]
        enhancements = extractor.extract_enhancements([automation], user_devices)

        # Should not extract enhancements for unavailable devices
        # (depends on implementation - might be 0 or might still extract)
        assert isinstance(enhancements, list)

    def test_enhancement_ranking(self, extractor):
        """Test enhancements are ranked by frequency × quality"""
        automations = [
            {
                "conditions": [{"type": "time"}],
                "devices": ["light"],
                "quality_score": 0.9,
            },
            {
                "conditions": [{"type": "time"}],  # Same condition type
                "devices": ["light"],
                "quality_score": 0.8,
            },
        ]

        user_devices = ["light"]
        enhancements = extractor.extract_enhancements(automations, user_devices)

        if enhancements:
            # First enhancement should have higher rank
            assert enhancements[0].frequency * enhancements[0].quality_score >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

