"""Tests for the home-atlas intake generator's evidence classification.

These pin the rule the atlas exists to enforce: a friendly name is never a way
of knowing where a device is. Two identically-modelled dimmers on this instance
carried swapped names, so a name-derived "office" row pointed at the bar switch.
The classifier must place that row in `unverified` and mark it non-actionable,
so a gene abstains rather than writing to the wrong physical device.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_home_intake import (  # noqa: E402
    ROOM_GROUP,
    classify_identity,
    classify_placement,
    placement_rows,
    room_membership,
)

ORDERED = ["measured", "upstream_source", "attestation", "unverified"]


class TestClassifyIdentity:
    def test_zha_ieee_is_measured(self):
        assert classify_identity({"zha"}, set()) == ("zha ieee", "measured")

    def test_mac_connection_is_measured(self):
        assert classify_identity({"hue"}, {"mac"}) == ("mac", "measured")

    def test_zha_wins_over_mac(self):
        # A protocol-native address beats a network address for the same device.
        identity, evidence = classify_identity({"zha"}, {"mac"})
        assert identity == "zha ieee"
        assert evidence == "measured"

    def test_integration_id_only_is_upstream_source(self):
        identity, evidence = classify_identity({"cast"}, set())
        assert identity == "cast id"
        assert evidence == "upstream_source"

    def test_no_identifier_at_all_is_unverified(self):
        assert classify_identity(set(), set()) == ("none", "unverified")

    @pytest.mark.parametrize("identifiers,connections", [({"zha"}, set()), ({"x"}, set()), (set(), set())])
    def test_evidence_is_always_from_the_ordered_vocabulary(self, identifiers, connections):
        assert classify_identity(identifiers, connections)[1] in ORDERED


class TestClassifyPlacement:
    def test_hue_membership_confers_no_evidence_upgrade(self):
        # A friendly name is a presentation artifact and may never set an evidence
        # class. The Hue group matches members by NAME, so it is a name match one
        # hop removed and must confer nothing at all.
        row = classify_placement("Office", "Office Front Right", corroborated=True, area_id="office")
        assert row["area_evidence"] == "unverified"
        assert row["actionable"] == "false"
        assert "observation only" in row["method"]

    def test_no_input_whatsoever_produces_a_non_unverified_class(self):
        # Every reachable branch, corroborated or not, echoing or not.
        for corroborated in (True, False):
            for device in ("Office Front Right", "Office Light Dimmer", "Dishwasher"):
                row = classify_placement("Office", device, corroborated, "office")
                assert row["area_evidence"] == "unverified", (corroborated, device)

    def test_name_echo_is_unverified_and_non_actionable(self):
        # The exact shape of the swapped-dimmer defect.
        row = classify_placement("Office", "Office Light Dimmer", corroborated=False, area_id="office")
        assert row["area_evidence"] == "unverified"
        assert row["confidence"] == "low"
        assert row["actionable"] == "false"

    def test_name_echo_records_the_echo_as_method_not_as_evidence_class(self):
        row = classify_placement("Bar", "Bar Light Dimmer", corroborated=False, area_id="bar")
        assert "echoes" in row["method"]
        # The echo must never become a class of its own that could outrank unverified.
        assert row["area_evidence"] not in {"name_match", "name", "friendly_name"}
        assert row["area_evidence"] in ORDERED

    def test_registry_only_is_unverified_and_non_actionable(self):
        row = classify_placement("Kitchen", '50" The Frame', corroborated=False, area_id="kitchen")
        assert row["area_evidence"] == "unverified"
        assert row["actionable"] == "false"
        assert "no provenance" in row["method"]

    def test_every_row_carries_a_next_verification_step(self):
        for corroborated in (True, False):
            row = classify_placement("Office", "Office Lamp", corroborated=corroborated, area_id="office")
            assert row["next_verification_step"].strip()

    def test_no_branch_ever_returns_a_name_based_evidence_class(self):
        cases = [
            ("Office", "Office Light Dimmer", False),
            ("Office", "Office Front Right", True),
            ("Kitchen", "Dishwasher", False),
        ]
        for area, device, corroborated in cases:
            assert classify_placement(area, device, corroborated, "x")["area_evidence"] in ORDERED

    def test_no_branch_is_ever_actionable(self):
        # Every placement signal available from HA alone is name-dependent, so
        # nothing in this home is an actionable placement yet. A future branch
        # that returns true must come with a measurement, and this test is the
        # thing that will fail if one is added without.
        for corroborated in (True, False):
            for device in ("Office Lamp", "Kitchen Sink"):
                assert classify_placement("Office", device, corroborated, "office")["actionable"] == "false"


class TestRoomMembership:
    def test_doubled_slug_is_a_room(self):
        assert ROOM_GROUP.match("light.office_office")
        assert ROOM_GROUP.match("light.garage_hallway_garage_hallway")

    def test_single_slug_is_a_zone_and_is_excluded(self):
        # `light.garage` is a Hue ZONE that contains a light called "Office Go";
        # treating it as a room would place that bulb in the garage.
        assert ROOM_GROUP.match("light.garage") is None
        assert ROOM_GROUP.match("light.first_floor") is None
        assert ROOM_GROUP.match("light.notification") is None

    def test_membership_lowercases_and_strips(self):
        states = [
            {"entity_id": "light.office_office", "attributes": {"lights": ["  Office Front Right ", "Office Go"]}},
            {"entity_id": "light.garage", "attributes": {"lights": ["Office Go"]}},
        ]
        rooms = room_membership(states)
        assert rooms == {"office": {"office front right", "office go"}}

    def test_group_without_a_lights_attribute_is_ignored(self):
        assert room_membership([{"entity_id": "light.office_office", "attributes": {}}]) == {}


class TestPlacementRows:
    def _reg(self, devices):
        return {"devices": devices, "entities": [], "areas": []}

    def test_device_with_no_area_is_skipped(self):
        reg = self._reg([{"name": "Nowhere", "area_id": None}])
        assert placement_rows(reg, {}, {}) == []

    def test_swapped_dimmer_pair_both_abstain(self):
        reg = self._reg(
            [
                {"name_by_user": "Office Light Dimmer", "area_id": "office", "identifiers": [["zha", "0e:8f"]]},
                {"name_by_user": "Bar Light Dimmer", "area_id": "bar", "identifiers": [["zha", "11:ef"]]},
            ]
        )
        rows = placement_rows(reg, {"office": "Office", "bar": "Bar"}, {})
        assert len(rows) == 2
        for row in rows:
            # Identified perfectly, placed on nothing but a name.
            assert row["identity_evidence"] == "measured"
            assert row["area_evidence"] == "unverified"
            assert row["actionable"] == "false"

    def test_hue_bulb_in_its_room_group_gains_nothing_from_that_membership(self):
        # Membership is matched on the bulb's NAME, so it is inert to the system.
        reg = self._reg(
            [{"name_by_user": "Office Front Right", "area_id": "office", "identifiers": [["hue", "abc"]]}]
        )
        rows = placement_rows(reg, {"office": "Office"}, {"office": {"office front right"}})
        assert rows[0]["area_evidence"] == "unverified"
        assert rows[0]["actionable"] == "false"

    def test_hue_bulb_absent_from_its_room_group_is_not_corroborated(self):
        reg = self._reg(
            [{"name_by_user": "Office Front Right", "area_id": "office", "identifiers": [["hue", "abc"]]}]
        )
        rows = placement_rows(reg, {"office": "Office"}, {"office": {"something else"}})
        assert rows[0]["area_evidence"] == "unverified"

    def test_non_hue_device_is_never_corroborated_by_a_room_group(self):
        # Only the Hue bridge has a room model; a ZHA switch listed by name in a
        # Hue group would still not be evidence.
        reg = self._reg(
            [{"name_by_user": "Office Light Dimmer", "area_id": "office", "identifiers": [["zha", "0e:8f"]]}]
        )
        rows = placement_rows(reg, {"office": "Office"}, {"office": {"office light dimmer"}})
        assert rows[0]["area_evidence"] == "unverified"

    def test_every_row_has_all_declared_columns(self):
        columns = {
            "device", "area", "identity", "identity_evidence", "area_evidence",
            "confidence", "actionable", "method", "next_verification_step",
        }
        reg = self._reg([{"name_by_user": "X", "area_id": "office", "identifiers": [["zha", "a"]]}])
        assert set(placement_rows(reg, {"office": "Office"}, {})[0]) == columns
