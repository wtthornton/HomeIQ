"""Tests for error-to-domain mapping (Story 7).

Tests cover:
- Entity errors map to device_capability domain
- Service errors map to automation domain
- Attribute errors map to comfort domain
- Energy errors map to energy domain
- Security errors map to security domain
- Multiple domains from mixed errors
- Empty errors return empty list
- Unknown errors return empty list
"""

import pytest
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import get_error_domain_hints


class TestErrorDomainHints:
    def test_entity_not_found_maps_to_device_capability(self):
        """Entity errors map to device_capability domain."""
        errors = ["entity_id 'light.nonexistent' not found"]
        hints = get_error_domain_hints(errors)
        assert "device_capability" in hints

    def test_unknown_entity_maps_to_device_capability(self):
        """Unknown entity errors map to device_capability."""
        errors = ["Unknown entity: sensor.missing_temp"]
        hints = get_error_domain_hints(errors)
        assert "device_capability" in hints

    def test_invalid_service_maps_to_automation(self):
        """Service errors map to automation domain."""
        errors = ["Invalid service: climate.set_temp"]
        hints = get_error_domain_hints(errors)
        assert "automation" in hints

    def test_service_not_found_maps_to_automation(self):
        """Service not found maps to automation."""
        errors = ["Service not found: light.turn_off_all"]
        hints = get_error_domain_hints(errors)
        assert "automation" in hints

    def test_brightness_error_maps_to_comfort(self):
        """Brightness-related errors map to comfort domain."""
        errors = ["brightness value 300 exceeds maximum 255"]
        hints = get_error_domain_hints(errors)
        assert "comfort" in hints

    def test_temperature_error_maps_to_comfort(self):
        """Temperature errors map to comfort."""
        errors = ["temperature must be between 16 and 30"]
        hints = get_error_domain_hints(errors)
        assert "comfort" in hints

    def test_color_temp_error_maps_to_comfort(self):
        """Color temp errors map to comfort."""
        errors = ["color_temp 100 is below minimum"]
        hints = get_error_domain_hints(errors)
        assert "comfort" in hints

    def test_energy_keyword_maps_to_energy(self):
        """Energy-related errors map to energy domain."""
        errors = ["power reading sensor not available"]
        hints = get_error_domain_hints(errors)
        assert "energy" in hints

    def test_battery_error_maps_to_energy(self):
        """Battery errors map to energy."""
        errors = ["battery state of charge unavailable"]
        hints = get_error_domain_hints(errors)
        assert "energy" in hints

    def test_alarm_error_maps_to_security(self):
        """Alarm errors map to security domain."""
        errors = ["alarm panel not responding"]
        hints = get_error_domain_hints(errors)
        assert "security" in hints

    def test_lock_error_maps_to_security(self):
        """Lock errors map to security."""
        errors = ["lock entity returned error"]
        hints = get_error_domain_hints(errors)
        assert "security" in hints

    def test_multiple_domains_from_mixed_errors(self):
        """Multiple error types produce multiple domain hints."""
        errors = [
            "entity_id 'light.test' not found",
            "Invalid service: climate.set_temp",
            "brightness value out of range",
        ]
        hints = get_error_domain_hints(errors)
        assert "device_capability" in hints
        assert "automation" in hints
        assert "comfort" in hints

    def test_empty_errors_returns_empty(self):
        """Empty error list returns empty domain list."""
        assert get_error_domain_hints([]) == []

    def test_unknown_errors_returns_empty(self):
        """Errors matching no pattern return empty list."""
        errors = ["Something completely unrelated went wrong"]
        hints = get_error_domain_hints(errors)
        assert hints == []

    def test_results_sorted(self):
        """Domain hints are returned in sorted order."""
        errors = [
            "Invalid service: light.turn_on",
            "entity_id not found",
        ]
        hints = get_error_domain_hints(errors)
        assert hints == sorted(hints)
