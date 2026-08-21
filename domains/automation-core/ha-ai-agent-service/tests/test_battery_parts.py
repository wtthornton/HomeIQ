"""A battery figure must not be reported for a device with no battery.

Two Aqara FP1E presence sensors expose a battery entity stuck at 0% — a phantom
cluster the ZHA quirk surfaces on a mains-powered device. This summary is fed to
a language model, and "Battery: 0%" reads to it as an urgent fault on hardware
that has no battery at all (TAP-6393).

device-intelligence mirrors the reading faithfully but records `power_source` as
NULL, declining to claim the device is battery-powered. These tests pin that the
summary honours that refusal rather than re-asserting what the data layer would
not.
"""

import pytest

from src.services.devices_summary_service import _battery_parts


class TestOnlyBatteryDevicesReportBatteries:
    def test_a_battery_device_reports_its_level(self):
        assert _battery_parts({"power_source": "battery", "battery_level": 87}) == ["Battery: 87%"]

    def test_a_battery_device_reports_a_low_warning(self):
        parts = _battery_parts({"power_source": "battery", "battery_level": 4, "battery_low": True})
        assert parts == ["Battery: 4%", "Battery Low"]

    def test_zero_percent_is_reported_when_the_device_really_has_a_battery(self):
        # A genuinely dead battery must still surface. Suppressing 0 outright
        # would hide the one reading that most needs reporting.
        assert _battery_parts({"power_source": "battery", "battery_level": 0}) == ["Battery: 0%"]

    @pytest.mark.parametrize("power_source", [None, "mains", ""])
    def test_a_phantom_reading_is_not_reported(self, power_source):
        # The FP1E case: a reading exists, but nothing established that the
        # device runs on a battery.
        assert _battery_parts({"power_source": power_source, "battery_level": 0, "battery_low": True}) == []

    def test_a_mains_device_with_no_reading_says_nothing(self):
        assert _battery_parts({"power_source": "mains"}) == []

    def test_a_battery_device_with_no_reading_says_nothing(self):
        assert _battery_parts({"power_source": "battery"}) == []

    def test_an_empty_device_does_not_raise(self):
        assert _battery_parts({}) == []
