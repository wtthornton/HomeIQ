"""Tests for the device-knowledge rules.

The rules run against the real taxonomy, not a mocked one. The last time this
area was tested with mocks, the doubles encoded the caller's mistaken belief
about the collaborator's contract and hid a live bug (TAP-6392) — so the only
thing stubbed here is the shape of a Home Assistant payload.

Every case is drawn from a device that actually exists on this instance, because
the interesting failures are the awkward real ones: a Hue Room group that is not
a device, a Zigbee coordinator with no link to itself, an Aqara quirk that ZHA
itself refuses to call battery-powered.
"""

from dataclasses import dataclass

import pytest
from src.services.device_knowledge import DeviceKnowledge


@dataclass
class Entity:
    entity_id: str
    device_id: str | None
    domain: str
    entity_category: str | None = None


@dataclass
class Device:
    id: str
    integration: str = "hue"
    disabled_by: str | None = None
    zigbee_ieee: str | None = None


def state(entity_id: str, value, device_class: str | None = None) -> dict:
    return {
        "entity_id": entity_id,
        "state": value,
        "attributes": {"device_class": device_class} if device_class else {},
    }


class TestDeviceType:
    def test_a_light_is_a_light(self):
        k = DeviceKnowledge([Entity("light.a", "d1", "light")])
        values, _ = k.for_device(Device("d1"))
        assert values["device_type"] == "light"

    def test_config_and_diagnostic_entities_do_not_vote(self):
        # A Hue outdoor motion sensor exposes 2 binary_sensors plus 4 config
        # switches. Counting the switches would classify a motion sensor as a
        # switch, which is how a device ends up filed under the wrong kind.
        k = DeviceKnowledge(
            [
                Entity("binary_sensor.motion", "d1", "binary_sensor"),
                Entity("sensor.temp", "d1", "sensor"),
                Entity("switch.led_indication", "d1", "switch", entity_category="config"),
                Entity("switch.motion_enable", "d1", "switch", entity_category="config"),
                Entity("sensor.battery", "d1", "sensor", entity_category="diagnostic"),
            ]
        )
        values, _ = k.for_device(Device("d1"))
        assert values["device_type"] == "sensor"

    def test_domain_priority_decides_a_multi_domain_device(self):
        # An Inovelli VZM35-SN exposes both fan and light entities; the taxonomy
        # ranks light first, and that is the taxonomy's call to make, not ours.
        k = DeviceKnowledge([Entity("fan.a", "d1", "fan"), Entity("light.a", "d1", "light")])
        values, _ = k.for_device(Device("d1"))
        assert values["device_type"] == "light"

    def test_a_hue_room_group_is_not_a_device(self):
        # "Backyard" is a Hue Room exposing 19 scene entities. `scene` is not in
        # the domain map, so it falls out without needing to be named — which is
        # why these rules need no per-integration branches.
        k = DeviceKnowledge([Entity(f"scene.s{i}", "d1", "scene") for i in range(19)])
        values, exclusions = k.for_device(Device("d1"))
        assert "device_type" not in values
        assert "scene" in exclusions["device_type"]

    def test_a_device_with_no_entities_is_excluded_with_a_reason(self):
        # The Zigbee coordinator and the Bluetooth adapter.
        k = DeviceKnowledge([])
        values, exclusions = k.for_device(Device("d1"))
        assert "device_type" not in values
        assert "no functional entities" in exclusions["device_type"]

    def test_the_emitted_value_is_always_in_the_vocabulary(self):
        from homeiq_device_taxonomy import device_type_vocabulary

        vocabulary = device_type_vocabulary()
        for domain in ("light", "switch", "sensor", "binary_sensor", "media_player", "climate"):
            k = DeviceKnowledge([Entity(f"{domain}.a", "d1", domain)])
            values, _ = k.for_device(Device("d1"))
            if "device_type" in values:
                assert values["device_type"] in vocabulary


class TestPowerSource:
    def test_a_battery_entity_establishes_battery(self):
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", "100", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["power_source"] == "battery"

    def test_a_light_with_no_battery_is_mains(self):
        k = DeviceKnowledge([Entity("light.a", "d1", "light")])
        values, _ = k.for_device(Device("d1"))
        assert values["power_source"] == "mains"

    def test_zha_mains_is_believed(self):
        k = DeviceKnowledge(
            [], zha_devices=[{"ieee": "00:11:22", "power_source": "Mains", "lqi": 63}]
        )
        values, _ = k.for_device(Device("d1", zigbee_ieee="00:11:22"))
        assert values["power_source"] == "mains"

    def test_zha_hedging_is_not_believed(self):
        # ZHA reports "Battery or Unknown" for the aqara_fp1e quirk. It will not
        # commit, so neither will we — recording 'battery' here would turn ZHA's
        # explicit uncertainty into an established fact.
        k = DeviceKnowledge(
            [],
            zha_devices=[{"ieee": "00:11:22", "power_source": "Battery or Unknown", "lqi": 45}],
        )
        values, exclusions = k.for_device(Device("d1", zigbee_ieee="00:11:22"))
        assert "power_source" not in values
        assert "power_source" in exclusions

    def test_absence_of_a_battery_is_not_evidence_of_mains(self):
        # Flagged independently by three refuters. A device with only sensor
        # entities and no battery reading tells us nothing about its supply.
        k = DeviceKnowledge([Entity("sensor.x", "d1", "sensor")])
        values, exclusions = k.for_device(Device("d1"))
        assert "power_source" not in values
        assert "absence of a battery is not evidence" in exclusions["power_source"]


class TestBatteryLevel:
    def test_a_numeric_state_is_read_as_a_percent(self):
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", "97.6", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["battery_level"] == 98

    @pytest.mark.parametrize("bad", ["unknown", "unavailable", None, "", "n/a"])
    def test_a_non_numeric_state_is_excluded_not_crashed_on(self, bad):
        # HA reports unknown/unavailable as state strings; a bare float() raises
        # on perfectly normal devices.
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", bad, device_class="battery")],
        )
        values, exclusions = k.for_device(Device("d1"))
        assert "battery_level" not in values
        assert "battery_level" in exclusions

    @pytest.mark.parametrize("out_of_range", ["-5", "150"])
    def test_an_out_of_range_percent_is_refused(self, out_of_range):
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", out_of_range, device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert "battery_level" not in values

    def test_no_battery_entity_yields_a_reason(self):
        k = DeviceKnowledge([Entity("light.a", "d1", "light")])
        _, exclusions = k.for_device(Device("d1"))
        assert "no battery-class entity" in exclusions["battery_level"]


class TestZigbeeIeeeDerivation:
    """The join key must not depend on when this runs relative to its caller."""

    def test_the_ieee_is_read_from_ha_identifiers(self):
        # The discovery service fills its own zigbee_ieee key AFTER calling this,
        # so reading the caller's payload produced None for every device and
        # excluded every LQI reading.
        class HADevice:
            identifiers = [["mac", "aa:bb"], ["zha", "00:11:22:33"]]

        class D:
            id = "d1"
            integration = "zha"
            disabled_by = None
            ha_device = HADevice()

        k = DeviceKnowledge([], zha_devices=[{"ieee": "00:11:22:33", "lqi": 63}])
        values, _ = k.for_device(D())
        assert values["lqi"] == 63

    def test_a_direct_attribute_wins_when_present(self):
        k = DeviceKnowledge([], zha_devices=[{"ieee": "AA:BB", "lqi": 12}])
        values, _ = k.for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert values["lqi"] == 12

    def test_a_non_zha_identifier_is_not_mistaken_for_one(self):
        class HADevice:
            identifiers = [["hue", "some-hue-id"]]

        class D:
            id = "d1"
            integration = "hue"
            disabled_by = None
            ha_device = HADevice()

        _, exclusions = DeviceKnowledge([]).for_device(D())
        assert "not a Zigbee device" in exclusions["lqi"]


class TestLqi:
    def test_lqi_comes_from_zha_keyed_on_ieee(self):
        k = DeviceKnowledge([], zha_devices=[{"ieee": "AA:BB", "lqi": 127}])
        values, _ = k.for_device(Device("d1", zigbee_ieee="aa:bb"))
        assert values["lqi"] == 127

    def test_a_non_zigbee_device_has_no_link_quality(self):
        k = DeviceKnowledge([])
        _, exclusions = k.for_device(Device("d1"))
        assert "not a Zigbee device" in exclusions["lqi"]

    def test_the_coordinator_reporting_none_is_the_honest_value(self):
        # A radio has no link-quality reading to itself. This is not a gap in
        # the method.
        k = DeviceKnowledge([], zha_devices=[{"ieee": "AA:BB", "lqi": None}])
        values, exclusions = k.for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert "lqi" not in values
        assert "no link to itself" in exclusions["lqi"]


class TestSourceAndAvailability:
    def test_source_is_the_integration_slug(self):
        k = DeviceKnowledge([])
        values, _ = k.for_device(Device("d1", integration="zha"))
        assert values["source"] == "zha"

    def test_an_unresolved_integration_is_excluded(self):
        k = DeviceKnowledge([])
        values, exclusions = k.for_device(Device("d1", integration="unknown"))
        assert "source" not in values
        assert "source" in exclusions

    def test_a_present_device_is_enabled(self):
        k = DeviceKnowledge([])
        values, _ = k.for_device(Device("d1"))
        assert values["availability_status"] == "enabled"

    def test_a_disabled_device_says_disabled(self):
        k = DeviceKnowledge([])
        values, _ = k.for_device(Device("d1", disabled_by="user"))
        assert values["availability_status"] == "disabled"

    def test_availability_never_emits_a_value_outside_the_vocabulary(self):
        # ha-ai-agent-service branches on the raw string, so an out-of-vocabulary
        # value is silently missed by consumers rather than rejected at write.
        allowed = {"enabled", "disabled", "unavailable"}
        for disabled_by in (None, "user", "integration", "config_entry"):
            k = DeviceKnowledge([])
            values, _ = k.for_device(Device("d1", disabled_by=disabled_by))
            assert values["availability_status"] in allowed


class TestNameBlindness:
    def test_renaming_everything_changes_nothing(self):
        # The rules take no name at all, but the guarantee worth asserting is
        # behavioural: identical structure with different labels, same answer.
        entities = [
            Entity("light.office_lamp", "d1", "light"),
            Entity("sensor.office_lamp_battery", "d1", "sensor"),
        ]
        renamed = [
            Entity("light.zzz_nonsense", "d1", "light"),
            Entity("sensor.zzz_nonsense_battery", "d1", "sensor"),
        ]
        states_a = [state("sensor.office_lamp_battery", "55", device_class="battery")]
        states_b = [state("sensor.zzz_nonsense_battery", "55", device_class="battery")]

        before, _ = DeviceKnowledge(entities, states_a).for_device(Device("d1"))
        after, _ = DeviceKnowledge(renamed, states_b).for_device(Device("d1"))

        assert before["device_type"] == "light"
        assert before["battery_level"] == 55
        assert after == before

    def test_entities_belonging_to_another_device_do_not_leak(self):
        # The join is device_id. A battery on a neighbouring device must not
        # make this one battery-powered.
        k = DeviceKnowledge(
            [Entity("light.a", "d1", "light"), Entity("sensor.batt", "d2", "sensor")],
            [state("sensor.batt", "80", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["power_source"] == "mains"
        assert "battery_level" not in values
