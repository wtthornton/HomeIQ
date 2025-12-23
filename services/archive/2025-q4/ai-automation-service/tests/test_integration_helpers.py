"""
Unit tests for Home Type Integration Helpers
"""

import pytest

from src.home_type.integration_helpers import (
    adjust_pattern_thresholds,
    calculate_home_type_boost,
    get_home_type_preferred_categories,
)


class TestGetHomeTypePreferredCategories:
    """Test preferred categories function"""

    def test_security_focused(self):
        """Test security-focused home preferences"""
        categories = get_home_type_preferred_categories("security_focused")
        assert categories == ["security", "monitoring", "lighting"]
        assert categories[0] == "security"  # Most preferred

    def test_climate_controlled(self):
        """Test climate-controlled home preferences"""
        categories = get_home_type_preferred_categories("climate_controlled")
        assert categories == ["climate", "energy", "monitoring"]
        assert categories[0] == "climate"  # Most preferred

    def test_high_activity(self):
        """Test high-activity home preferences"""
        categories = get_home_type_preferred_categories("high_activity")
        assert categories == ["lighting", "appliance", "convenience"]

    def test_smart_home(self):
        """Test smart home preferences"""
        categories = get_home_type_preferred_categories("smart_home")
        assert categories == ["automation", "integration", "convenience"]

    def test_standard_home(self):
        """Test standard home preferences"""
        categories = get_home_type_preferred_categories("standard_home")
        assert categories == ["lighting", "climate", "security"]

    def test_apartment(self):
        """Test apartment preferences"""
        categories = get_home_type_preferred_categories("apartment")
        assert categories == ["lighting", "climate", "space_optimization"]

    def test_unknown_home_type(self):
        """Test unknown home type (should return default)"""
        categories = get_home_type_preferred_categories("unknown_type")
        assert categories == ["general", "lighting", "climate"]


class TestCalculateHomeTypeBoost:
    """Test home type boost calculation"""

    def test_security_focused_security_category(self):
        """Test boost for security category in security-focused home"""
        boost = calculate_home_type_boost("security", "security_focused", base_boost=0.10)
        assert boost == 0.10  # First preference = full boost

    def test_security_focused_monitoring_category(self):
        """Test boost for monitoring category in security-focused home"""
        boost = calculate_home_type_boost("monitoring", "security_focused", base_boost=0.10)
        assert boost == 0.08  # Second preference = 0.8 * base

    def test_security_focused_lighting_category(self):
        """Test boost for lighting category in security-focused home"""
        boost = calculate_home_type_boost("lighting", "security_focused", base_boost=0.10)
        assert boost == 0.06  # Third preference = 0.6 * base

    def test_security_focused_non_preferred_category(self):
        """Test boost for non-preferred category"""
        boost = calculate_home_type_boost("appliance", "security_focused", base_boost=0.10)
        assert boost == 0.0  # Not in preferred list

    def test_climate_controlled_climate_category(self):
        """Test boost for climate category in climate-controlled home"""
        boost = calculate_home_type_boost("climate", "climate_controlled", base_boost=0.10)
        assert boost == 0.10  # First preference = full boost

    def test_standard_home_lighting_category(self):
        """Test boost for lighting in standard home"""
        boost = calculate_home_type_boost("lighting", "standard_home", base_boost=0.10)
        assert boost == 0.10  # First preference

    def test_custom_base_boost(self):
        """Test with custom base boost value"""
        boost = calculate_home_type_boost("security", "security_focused", base_boost=0.15)
        assert boost == 0.15  # Custom base boost


class TestAdjustPatternThresholds:
    """Test pattern threshold adjustment"""

    def test_security_focused_adjustment(self):
        """Test threshold adjustment for security-focused home"""
        conf, occ = adjust_pattern_thresholds(
            "security_focused", base_min_confidence=0.7, base_min_occurrences=10
        )
        # 0.7 * 0.93 = 0.651, 10 * 0.9 = 9
        assert conf == pytest.approx(0.651, rel=0.01)
        assert occ == 9

    def test_climate_controlled_adjustment(self):
        """Test threshold adjustment for climate-controlled home"""
        conf, occ = adjust_pattern_thresholds(
            "climate_controlled", base_min_confidence=0.7, base_min_occurrences=10
        )
        # 0.7 * 0.95 = 0.665, 10 * 0.85 = 8.5 -> 8
        assert conf == pytest.approx(0.665, rel=0.01)
        assert occ == 8

    def test_high_activity_adjustment(self):
        """Test threshold adjustment for high-activity home"""
        conf, occ = adjust_pattern_thresholds(
            "high_activity", base_min_confidence=0.7, base_min_occurrences=10
        )
        # 0.7 * 0.90 = 0.63, 10 * 0.8 = 8
        assert conf == pytest.approx(0.63, rel=0.01)
        assert occ == 8

    def test_apartment_adjustment(self):
        """Test threshold adjustment for apartment"""
        conf, occ = adjust_pattern_thresholds(
            "apartment", base_min_confidence=0.7, base_min_occurrences=10
        )
        # 0.7 * 0.95 = 0.665, 10 * 1.0 = 10
        assert conf == pytest.approx(0.665, rel=0.01)
        assert occ == 10

    def test_standard_home_no_adjustment(self):
        """Test threshold for standard home (no adjustment)"""
        conf, occ = adjust_pattern_thresholds(
            "standard_home", base_min_confidence=0.7, base_min_occurrences=10
        )
        # No adjustment = base values
        assert conf == 0.7
        assert occ == 10

    def test_unknown_home_type_no_adjustment(self):
        """Test threshold for unknown home type (no adjustment)"""
        conf, occ = adjust_pattern_thresholds(
            "unknown_type", base_min_confidence=0.7, base_min_occurrences=10
        )
        # No adjustment = base values
        assert conf == 0.7
        assert occ == 10

    def test_custom_base_values(self):
        """Test with custom base values"""
        conf, occ = adjust_pattern_thresholds(
            "security_focused", base_min_confidence=0.6, base_min_occurrences=5
        )
        # 0.6 * 0.93 = 0.558, 5 * 0.9 = 4.5 -> 4
        assert conf == pytest.approx(0.558, rel=0.01)
        assert occ == 4

    def test_lower_thresholds_for_security(self):
        """Test that security-focused homes have lower thresholds (more lenient)"""
        conf_security, occ_security = adjust_pattern_thresholds(
            "security_focused", base_min_confidence=0.7, base_min_occurrences=10
        )
        conf_standard, occ_standard = adjust_pattern_thresholds(
            "standard_home", base_min_confidence=0.7, base_min_occurrences=10
        )

        # Security should have lower thresholds (more patterns detected)
        assert conf_security < conf_standard
        assert occ_security < occ_standard

