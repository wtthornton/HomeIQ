"""Pins how the naming rubric reconstructs HA's friendly name.

HA does not persist `friendly_name` — it composes it at runtime from the device
name and the entity's own name. Scoring the stored `name` column directly made
`/api/naming/audit` report "entity has no friendly name" for entities that
plainly have one, costing every such entity 20 of 100 rubric points.

The expectations below were read off the live instance (HA 2026.8.2) via
`/api/states`, not derived from the docs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.naming_router import compose_friendly_name  # noqa: E402


class TestComposeFriendlyName:
    def test_has_entity_name_with_no_original_name_uses_the_device_name(self):
        # light.inovelli_vzm31_sn -> "Office Light Dimmer"
        assert (
            compose_friendly_name(None, None, True, "Office Light Dimmer") == "Office Light Dimmer"
        )

    def test_has_entity_name_with_original_name_appends_it(self):
        # sensor.inovelli_vzm31_sn_power -> "Office Light Dimmer Power"
        assert (
            compose_friendly_name(None, "Power", True, "Office Light Dimmer")
            == "Office Light Dimmer Power"
        )

    def test_hue_bulb_takes_its_device_name(self):
        # light.office_office_front_right -> "Office Front Right"
        assert compose_friendly_name(None, None, True, "Office Front Right") == "Office Front Right"

    def test_user_set_entity_name_overrides_everything(self):
        assert compose_friendly_name("My Lamp", "Power", True, "Office Light Dimmer") == "My Lamp"

    def test_without_has_entity_name_the_original_name_stands_alone(self):
        assert compose_friendly_name(None, "Front Porch", False, "Some Device") == "Front Porch"

    def test_no_signal_at_all_is_empty_not_a_guess(self):
        # An entity with nothing to compose from must score as unnamed rather
        # than inherit an id-derived guess.
        assert compose_friendly_name(None, None, True, None) == ""
        assert compose_friendly_name(None, None, False, None) == ""

    def test_device_name_is_not_used_when_has_entity_name_is_false(self):
        # has_entity_name False means the entity names itself; borrowing the
        # device name would invent a name HA never shows.
        assert compose_friendly_name(None, None, False, "Office Light Dimmer") == ""

    @pytest.mark.parametrize("original", ["", None], ids=["empty-string", "none"])
    def test_falsy_original_name_does_not_leave_a_trailing_space(self, original):
        assert compose_friendly_name(None, original, True, "Office Light Dimmer") == (
            "Office Light Dimmer"
        )
