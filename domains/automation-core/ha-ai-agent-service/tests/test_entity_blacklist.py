"""Tests for EntityBlacklist — Epic 93 Story 93.1."""

import os
from pathlib import Path
from unittest import mock

import pytest

from src.config.entity_blacklist import EntityBlacklist

# Path to the real config shipped with the service
_REAL_CONFIG = Path(__file__).resolve().parent.parent / "src" / "config" / "entity_blacklist.yaml"


class TestEntityBlacklistLoading:
    """93.1 AC: Blacklist config loads at service startup."""

    def test_loads_real_config(self):
        bl = EntityBlacklist(_REAL_CONFIG)
        assert bl.blocked_domains, "Should have at least one blocked domain"
        assert bl.blocked_services, "Should have at least one blocked service"

    def test_missing_config_returns_empty(self, tmp_path):
        bl = EntityBlacklist(tmp_path / "nonexistent.yaml")
        assert bl.blocked_domains == set()
        assert bl.blocked_entities == set()

    def test_custom_config(self, tmp_path):
        cfg = tmp_path / "custom.yaml"
        cfg.write_text(
            "blocked_domains:\n  - lock\nblocked_entities:\n  - switch.danger\n"
            "blocked_services:\n  - lock.unlock\nwarn_domains:\n  - cover\n"
        )
        bl = EntityBlacklist(cfg)
        assert "lock" in bl.blocked_domains
        assert "switch.danger" in bl.blocked_entities
        assert "lock.unlock" in bl.blocked_services
        assert "cover" in bl.warn_domains


class TestIsBlocked:
    """93.1 AC: is_blocked returns correct results."""

    @pytest.fixture()
    def bl(self):
        return EntityBlacklist(_REAL_CONFIG)

    def test_lock_entity_blocked(self, bl):
        assert bl.is_blocked("lock.front_door") is True

    def test_alarm_entity_blocked(self, bl):
        assert bl.is_blocked("alarm_control_panel.home") is True

    def test_light_entity_not_blocked(self, bl):
        assert bl.is_blocked("light.office") is False

    def test_sensor_entity_not_blocked(self, bl):
        assert bl.is_blocked("sensor.temperature") is False

    def test_switch_not_blocked_by_default(self, bl):
        assert bl.is_blocked("switch.kitchen") is False

    def test_case_insensitive(self, bl):
        assert bl.is_blocked("Lock.Front_Door") is True


class TestIsWarned:
    """93.1 AC: is_warned returns correct results."""

    @pytest.fixture()
    def bl(self):
        return EntityBlacklist(_REAL_CONFIG)

    def test_cover_warned(self, bl):
        assert bl.is_warned("cover.garage_door") is True

    def test_siren_warned(self, bl):
        assert bl.is_warned("siren.alarm") is True

    def test_valve_warned(self, bl):
        assert bl.is_warned("valve.main_water") is True

    def test_light_not_warned(self, bl):
        assert bl.is_warned("light.office") is False

    def test_blocked_entity_not_warned(self, bl):
        """Blocked entities are hidden, not warned."""
        assert bl.is_warned("lock.front_door") is False


class TestServiceBlocked:
    """93.1: Blocked services."""

    @pytest.fixture()
    def bl(self):
        return EntityBlacklist(_REAL_CONFIG)

    def test_lock_unlock_blocked(self, bl):
        assert bl.is_service_blocked("lock.unlock") is True

    def test_alarm_disarm_blocked(self, bl):
        assert bl.is_service_blocked("alarm_control_panel.alarm_disarm") is True

    def test_light_turn_on_not_blocked(self, bl):
        assert bl.is_service_blocked("light.turn_on") is False


class TestOverride:
    """93.1 AC: Override env var unblocks specified domains."""

    def test_override_unblocks_domain(self):
        with mock.patch.dict(os.environ, {"ENTITY_BLACKLIST_OVERRIDE": "lock"}):
            bl = EntityBlacklist(_REAL_CONFIG)
            assert bl.is_blocked("lock.front_door") is False
            # alarm_control_panel still blocked
            assert bl.is_blocked("alarm_control_panel.home") is True

    def test_override_unblocks_services(self):
        with mock.patch.dict(os.environ, {"ENTITY_BLACKLIST_OVERRIDE": "lock"}):
            bl = EntityBlacklist(_REAL_CONFIG)
            assert bl.is_service_blocked("lock.unlock") is False
            # alarm services still blocked
            assert bl.is_service_blocked("alarm_control_panel.alarm_disarm") is True

    def test_override_multiple_domains(self):
        with mock.patch.dict(
            os.environ,
            {"ENTITY_BLACKLIST_OVERRIDE": "lock,alarm_control_panel"},
        ):
            bl = EntityBlacklist(_REAL_CONFIG)
            assert bl.is_blocked("lock.front_door") is False
            assert bl.is_blocked("alarm_control_panel.home") is False
            assert bl.override_active is True

    def test_no_override_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is not set
            os.environ.pop("ENTITY_BLACKLIST_OVERRIDE", None)
            bl = EntityBlacklist(_REAL_CONFIG)
            assert bl.override_active is False
