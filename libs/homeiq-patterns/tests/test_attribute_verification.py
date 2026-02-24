"""Tests for attribute-aware post-action verification (Story 3).

Tests cover:
- verify_state_match() state field mismatch
- verify_state_match() attribute mismatch
- verify_state_match() partial match (some attributes ok, some not)
- verify_state_match() no expected → no warnings
- VerificationResult new fields (verified_attributes, expected_state)
- Backward compatibility (new fields have defaults)
- Integration with AutomationDeployVerifier
- Integration with SceneVerifier
- Integration with TaskExecutionVerifier
"""

import pytest
from typing import Any
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import PostActionVerifier, VerificationResult, VerificationWarning


# --- Test fixtures ---

class SimpleVerifier(PostActionVerifier):
    """Minimal verifier for testing base class methods."""

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        return VerificationResult(success=True, state="on")


# --- verify_state_match() Tests ---

class TestVerifyStateMatch:
    def setup_method(self):
        self.verifier = SimpleVerifier()

    def test_state_mismatch_warning(self):
        """State field mismatch produces a 'warning' severity."""
        actual = {"state": "off", "entity_id": "light.kitchen"}
        expected = {"state": "on"}
        warnings = self.verifier.verify_state_match(actual, expected)
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"
        assert "'off'" in warnings[0].message
        assert "'on'" in warnings[0].message

    def test_state_match_no_warning(self):
        """Matching state produces no warnings."""
        actual = {"state": "on", "entity_id": "light.kitchen"}
        expected = {"state": "on"}
        warnings = self.verifier.verify_state_match(actual, expected)
        assert len(warnings) == 0

    def test_attribute_mismatch_info(self):
        """Attribute mismatch produces an 'info' severity."""
        actual = {
            "state": "on",
            "attributes": {"brightness": 128},
        }
        expected = {"brightness": 255}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        assert len(warnings) == 1
        assert warnings[0].severity == "info"
        assert "brightness" in warnings[0].message
        assert "'128'" in warnings[0].message
        assert "'255'" in warnings[0].message

    def test_multiple_attribute_mismatches(self):
        """Multiple attribute mismatches each produce separate warnings."""
        actual = {
            "state": "on",
            "attributes": {"brightness": 128, "color_temp": 300},
        }
        expected = {"brightness": 255, "color_temp": 400}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        assert len(warnings) == 2
        attrs = {w.message.split("'")[3] for w in warnings}
        assert "brightness" in attrs
        assert "color_temp" in attrs

    def test_state_and_attribute_mismatch(self):
        """Both state and attribute mismatches produce combined warnings."""
        actual = {
            "state": "off",
            "attributes": {"brightness": 0},
        }
        expected = {"state": "on", "brightness": 255}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        # 1 state warning + 1 attribute warning
        assert len(warnings) == 2
        severities = {w.severity for w in warnings}
        assert "warning" in severities
        assert "info" in severities

    def test_partial_match(self):
        """Some attributes match, some don't — only mismatches warned."""
        actual = {
            "state": "on",
            "attributes": {"brightness": 255, "color_temp": 300},
        }
        expected = {"state": "on", "brightness": 255, "color_temp": 400}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        # Only color_temp mismatches
        assert len(warnings) == 1
        assert "color_temp" in warnings[0].message

    def test_no_expected_state_no_warnings(self):
        """No expected state field → no state warning."""
        actual = {"state": "off", "attributes": {"brightness": 128}}
        expected = {"brightness": 128}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        assert len(warnings) == 0

    def test_missing_actual_attribute_skipped(self):
        """Expected attribute not in actual → skipped (no warning)."""
        actual = {
            "state": "on",
            "attributes": {},
        }
        expected = {"brightness": 255}
        warnings = self.verifier.verify_state_match(actual, expected, "light.test")
        assert len(warnings) == 0

    def test_entity_id_from_actual(self):
        """Entity ID extracted from actual dict when not provided."""
        actual = {"state": "off", "entity_id": "light.auto_detected"}
        expected = {"state": "on"}
        warnings = self.verifier.verify_state_match(actual, expected)
        assert warnings[0].entity_id == "light.auto_detected"

    def test_entity_id_parameter_override(self):
        """Explicit entity_id parameter overrides actual dict."""
        actual = {"state": "off", "entity_id": "light.from_dict"}
        expected = {"state": "on"}
        warnings = self.verifier.verify_state_match(
            actual, expected, "light.explicit"
        )
        assert warnings[0].entity_id == "light.explicit"

    def test_hvac_mode_attribute(self):
        """HVAC-specific attributes are checked."""
        actual = {
            "state": "heat",
            "attributes": {"temperature": 20, "hvac_mode": "heat"},
        }
        expected = {"temperature": 22}
        warnings = self.verifier.verify_state_match(actual, expected, "climate.test")
        assert len(warnings) == 1
        assert "temperature" in warnings[0].message

    def test_cover_position_attribute(self):
        """Cover position attribute is checked."""
        actual = {
            "state": "open",
            "attributes": {"position": 50},
        }
        expected = {"position": 100}
        warnings = self.verifier.verify_state_match(actual, expected, "cover.test")
        assert len(warnings) == 1
        assert "position" in warnings[0].message


# --- VerificationResult new fields ---

class TestVerificationResultNewFields:
    def test_default_verified_attributes(self):
        """verified_attributes defaults to empty dict."""
        result = VerificationResult(success=True, state="on")
        assert result.verified_attributes == {}

    def test_default_expected_state(self):
        """expected_state defaults to None."""
        result = VerificationResult(success=True, state="on")
        assert result.expected_state is None

    def test_verified_attributes_populated(self):
        """verified_attributes can hold actual attribute values."""
        result = VerificationResult(
            success=True,
            state="on",
            verified_attributes={"brightness": 255, "color_temp": 300},
        )
        assert result.verified_attributes["brightness"] == 255

    def test_expected_state_populated(self):
        """expected_state can hold the expected state dict."""
        expected = {"state": "on", "brightness": 255}
        result = VerificationResult(
            success=True,
            state="on",
            expected_state=expected,
        )
        assert result.expected_state["state"] == "on"

    def test_backward_compat_no_new_fields(self):
        """Existing code creating VerificationResult without new fields still works."""
        result = VerificationResult(
            success=True,
            state="on",
            warnings=[],
            metadata={"entity_id": "test"},
        )
        assert result.verified_attributes == {}
        assert result.expected_state is None
