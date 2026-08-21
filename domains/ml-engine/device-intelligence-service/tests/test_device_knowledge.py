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


class _HADevice:
    def __init__(self, entry_type=None, identifiers=None):
        self.entry_type = entry_type
        self.identifiers = identifiers or []


class ServiceDevice(Device):
    """A device Home Assistant registers as a service, not hardware."""

    def __init__(self, id_: str, **kw):
        super().__init__(id_, **kw)
        self.ha_device = _HADevice(entry_type="service")


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

    def test_a_hue_room_group_with_a_light_entity_is_still_not_a_device(self):
        # THE REGRESSION. Most Hue Rooms and Zones expose a `light` GROUP entity
        # alongside their scenes, so the domain vote types them as physical
        # lights on mains — 16 of them were, and downstream inventory and energy
        # consumers then double-count hardware that does not exist.
        #
        # The earlier fixture here used scene-only entities, which is the shape
        # of the two Rooms that happen to have no light group. It encoded the
        # belief instead of testing it, so it passed while production was wrong.
        k = DeviceKnowledge(
            [
                Entity("light.downstairs", "d1", "light"),
                Entity("scene.relax", "d1", "scene"),
            ]
        )
        values, exclusions = k.for_device(ServiceDevice("d1"))
        assert values.get("device_type") is None, "a Hue Room group was typed as a physical light"
        assert values.get("power_source") is None
        assert "service entry" in exclusions["device_type"]

    def test_a_scene_only_group_is_also_not_a_device(self):
        k = DeviceKnowledge([Entity(f"scene.s{i}", "d1", "scene") for i in range(19)])
        values, exclusions = k.for_device(Device("d1"))
        assert values.get("device_type") is None
        assert "scene" in exclusions["device_type"]

    def test_a_stateless_controller_is_a_button(self):
        # Hue tap dials and Smart buttons expose only `event` entities. They were
        # excluded as "an integration or grouping construct" — false, and
        # insulting to a physical device sitting on a wall. HA models a stateless
        # controller as the event domain; `button` is already in the vocabulary.
        k = DeviceKnowledge([Entity("event.button_1", "d1", "event")])
        values, _ = k.for_device(Device("d1"))
        assert values["device_type"] == "button"

    def test_an_event_entity_does_not_outvote_a_real_domain(self):
        k = DeviceKnowledge([Entity("light.a", "d1", "light"), Entity("event.a", "d1", "event")])
        values, _ = k.for_device(Device("d1"))
        assert values["device_type"] == "light"

    def test_a_device_with_no_entities_is_excluded_with_a_reason(self):
        # The Zigbee coordinator and the Bluetooth adapter.
        k = DeviceKnowledge([])
        values, exclusions = k.for_device(Device("d1"))
        assert values.get("device_type") is None
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
        assert values.get("power_source") is None
        assert "power_source" in exclusions

    def test_absence_of_a_battery_is_not_evidence_of_mains(self):
        # Flagged independently by three refuters. A device with only sensor
        # entities and no battery reading tells us nothing about its supply.
        k = DeviceKnowledge([Entity("sensor.x", "d1", "sensor")])
        values, exclusions = k.for_device(Device("d1"))
        assert values.get("power_source") is None
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
        assert values.get("battery_level") is None
        assert "battery_level" in exclusions

    @pytest.mark.parametrize("out_of_range", ["-5", "150"])
    def test_an_out_of_range_percent_is_refused(self, out_of_range):
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", out_of_range, device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values.get("battery_level") is None

    def test_no_battery_entity_yields_a_reason(self):
        k = DeviceKnowledge([Entity("light.a", "d1", "light")])
        _, exclusions = k.for_device(Device("d1"))
        assert "no battery-class entity" in exclusions["battery_level"]


class TestDefectsAnAdversarialVerifierFound:
    """Each of these shipped, and none was visible to a green suite."""

    def test_a_zha_hedge_outranks_a_battery_entity(self):
        # Both Aqara FP1E expose a battery entity stuck at 0% since pairing,
        # because the quirk surfaces a battery cluster the mains-powered device
        # does not use. Believing it produced "battery, 0%" on a USB device —
        # a fabricated dead battery, which downstream reads as an urgent fault.
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor", entity_category="diagnostic")],
            [state("sensor.batt", "0.0", device_class="battery")],
            zha_devices=[{"ieee": "AA:BB", "power_source": "Battery or Unknown", "lqi": 31}],
        )
        values, exclusions = k.for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert values.get("power_source") is None
        assert "declines to commit" in exclusions["power_source"]
        # The reading itself is still mirrored: it is a measurement, and it
        # answers a different question from "what supplies this device".
        assert values["battery_level"] == 0

    def test_diagnostic_battery_entities_still_count(self):
        # Seven of the eight battery entities on this instance are `diagnostic`
        # — that is simply the Home Assistant convention for battery sensors.
        # Filtering them out of the battery scan, as was once proposed, would
        # drop battery_level from 8 devices to 1.
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor", entity_category="diagnostic")],
            [state("sensor.batt", "100", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["battery_level"] == 100
        assert values["power_source"] == "battery"

    def test_is_battery_powered_agrees_with_power_source(self):
        # These disagreed on 8 rows: the flag was computed upstream from a
        # pre-enrichment value and never recomputed.
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", "90", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["power_source"] == "battery"
        assert values["is_battery_powered"] is True

        mains = DeviceKnowledge([Entity("light.a", "d2", "light")]).for_device(Device("d2"))[0]
        assert mains["power_source"] == "mains"
        assert mains["is_battery_powered"] is False

    @pytest.mark.parametrize(
        "column,stamp",
        [
            ("lqi", "lqi_updated_at"),
            ("battery_level", "battery_updated_at"),
            ("availability_status", "availability_updated_at"),
        ],
    )
    def test_a_written_value_is_stamped(self, column, stamp):
        # These columns are preserved on conflict, so without a timestamp a
        # device that leaves the mesh keeps its last reading forever with
        # nothing to age it out by.
        k = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", "77", device_class="battery")],
            zha_devices=[{"ieee": "AA:BB", "lqi": 44}],
        )
        values, _ = k.for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert column in values
        assert stamp in values, f"{column} was written without stamping {stamp}"

    def test_an_authoritative_clear_clears_its_stamp(self):
        # A non-Zigbee device authoritatively has no LQI, so the column is
        # written as an explicit None — clearing any stale value rather than
        # letting it stand. The stamp is written as None alongside it, so the
        # row never carries a timestamp for a reading it does not have.
        values, _ = DeviceKnowledge([]).for_device(Device("d1"))
        assert values["lqi"] is None
        assert values["lqi_updated_at"] is None

    def test_a_column_whose_inputs_were_unavailable_is_omitted_entirely(self):
        # states=None means the caller could not fetch them. Clearing
        # battery_level on that basis would wipe good data on a transient
        # failure, so the key is omitted and the stored value stands.
        values, _ = DeviceKnowledge([], states=None).for_device(Device("d1"))
        assert values.get("battery_level") is None

    def test_a_column_whose_inputs_were_empty_is_cleared(self):
        # states=[] means they WERE fetched and held nothing. That is a real
        # answer, so it clears.
        values, _ = DeviceKnowledge([], states=[]).for_device(Device("d1"))
        assert "battery_level" in values
        assert values["battery_level"] is None


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
        assert values.get("lqi") is None
        assert "no link to itself" in exclusions["lqi"]


class TestSourceAndAvailability:
    def test_source_is_the_integration_slug(self):
        k = DeviceKnowledge([])
        values, _ = k.for_device(Device("d1", integration="zha"))
        assert values["source"] == "zha"

    def test_an_unresolved_integration_is_excluded(self):
        k = DeviceKnowledge([])
        values, exclusions = k.for_device(Device("d1", integration="unknown"))
        assert values.get("source") is None
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

        # Compare the derived values. The *_updated_at stamps are wall-clock and
        # differ between two calls by construction, so including them would make
        # this fail for a reason that has nothing to do with renaming.
        def derived(values):
            return {k: v for k, v in values.items() if not k.endswith("_updated_at")}

        assert before["device_type"] == "light"
        assert before["battery_level"] == 55
        # A battery entity outranks the mains-domain inference; this fixture has one.
        assert before["power_source"] == "battery"
        assert derived(after) == derived(before)
        # And the stamps are present, so trimming them above hides nothing.
        assert "battery_updated_at" in before

    def test_entities_belonging_to_another_device_do_not_leak(self):
        # The join is device_id. A battery on a neighbouring device must not
        # make this one battery-powered.
        k = DeviceKnowledge(
            [Entity("light.a", "d1", "light"), Entity("sensor.batt", "d2", "sensor")],
            [state("sensor.batt", "80", device_class="battery")],
        )
        values, _ = k.for_device(Device("d1"))
        assert values["power_source"] == "mains"
        assert values.get("battery_level") is None


class TestATransientFetchFailureCannotWipeData:
    """The most dangerous property of an authoritative clear.

    `None` and `[]` must not collapse into each other. `_safe_states` originally
    returned `[]` on exception, which this module reads as "Home Assistant was
    asked and had nothing" — so a single flaky call would have cleared
    battery_level, power_source and lqi across the entire fleet, silently and
    on a five-minute loop.
    """

    def _established(self):
        return DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            [state("sensor.batt", "88", device_class="battery")],
            zha_devices=[{"ieee": "AA:BB", "lqi": 70, "power_source": "Mains"}],
        ).for_device(Device("d1", zigbee_ieee="AA:BB"))[0]

    def test_the_happy_path_establishes_all_three(self):
        # Positive control, so the assertions below cannot pass vacuously.
        values = self._established()
        assert values["battery_level"] == 88
        assert values["lqi"] == 70
        assert values["power_source"] == "battery"

    def test_unfetched_states_omit_rather_than_clear(self):
        values, _ = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            states=None,
            zha_devices=[{"ieee": "AA:BB", "lqi": 70}],
        ).for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert "battery_level" not in values, "a failed states fetch cleared battery_level"
        assert "power_source" not in values, "a failed states fetch cleared power_source"

    def test_unfetched_zha_omits_rather_than_clears_lqi(self):
        values, _ = DeviceKnowledge(
            [Entity("sensor.batt", "d1", "sensor")],
            states=[state("sensor.batt", "88", device_class="battery")],
            zha_devices=None,
        ).for_device(Device("d1", zigbee_ieee="AA:BB"))
        assert "lqi" not in values, "a failed ZHA command cleared lqi"

    def test_a_genuinely_empty_response_still_clears(self):
        # Otherwise a value could never be retracted, which is the defect the
        # authoritative clear exists to fix.
        values, _ = DeviceKnowledge([], states=[], zha_devices=[]).for_device(
            Device("d1", zigbee_ieee="AA:BB")
        )
        assert values["battery_level"] is None
        assert values["lqi"] is None

    def test_a_non_zigbee_device_clears_lqi_even_without_zha(self):
        # No ZHA payload is needed to know a non-Zigbee device has no LQI.
        values, _ = DeviceKnowledge([], states=[], zha_devices=None).for_device(Device("d1"))
        assert values["lqi"] is None


class TestValueAndStampMoveTogether:
    """A stamp asserts that a reading happened. It must not outlive one."""

    def _batt(self, raw):
        return DeviceKnowledge(
            [Entity("sensor.b", "d1", "sensor")],
            [state("sensor.b", raw, device_class="battery")],
        ).for_device(Device("d1"))[0]

    def test_a_reading_writes_both(self):
        values = self._batt("100")
        assert values["battery_level"] == 100
        assert "battery_updated_at" in values

    def test_a_clearing_pass_clears_the_stamp_too(self):
        # The invariant: the stamp is non-NULL exactly when the value is.
        #
        # Stamping only non-None values left the previous pass's timestamp on a
        # row with no reading. Stamping every write put a FRESH timestamp beside
        # a NULL, which is the same lie with a newer date. Reachable on any HA
        # restart, when a battery entity reports `unknown`.
        values = self._batt("unknown")
        assert values["battery_level"] is None
        assert "battery_updated_at" in values, "the stale stamp was left in place"
        assert values["battery_updated_at"] is None, (
            "a NULL reading was stamped with a fresh timestamp, claiming a "
            "measurement that did not happen"
        )

    def test_a_preserved_column_stamps_nothing(self):
        # states=None means the column is omitted entirely; stamping it would
        # claim a reading on a pass that never looked.
        values, _ = DeviceKnowledge([], states=None).for_device(Device("d1"))
        assert "battery_level" not in values
        assert "battery_updated_at" not in values


class TestTheDerivedFlagFollowsPowerSource:
    def test_it_is_written_when_power_source_is(self):
        values, _ = DeviceKnowledge(
            [Entity("sensor.b", "d1", "sensor")],
            [state("sensor.b", "50", device_class="battery")],
        ).for_device(Device("d1"))
        assert values["power_source"] == "battery"
        assert values["is_battery_powered"] is True

    def test_it_is_omitted_when_power_source_is_preserved(self):
        # The preserve path. Writing the flag here while power_source keeps its
        # stored value is what produced power_source='battery' alongside
        # is_battery_powered=false.
        values, _ = DeviceKnowledge([], states=None).for_device(Device("d1"))
        assert "power_source" not in values
        assert "is_battery_powered" not in values, (
            "the derived flag was written while its source was preserved, so the two can disagree"
        )

    def test_it_is_omitted_when_power_source_is_cleared(self):
        # An explicit clear says "no supply established". Asserting
        # is_battery_powered=false alongside would be a claim we cannot make.
        values, _ = DeviceKnowledge([], states=[]).for_device(Device("d1"))
        assert values["power_source"] is None
        assert "is_battery_powered" not in values


class TestTheStampInvariant:
    """One property, checked across every path: stamp non-NULL iff value non-NULL."""

    @pytest.mark.parametrize(
        "states,zha,label",
        [
            ([], [], "everything cleared"),
            (
                [
                    {
                        "entity_id": "sensor.b",
                        "state": "60",
                        "attributes": {"device_class": "battery"},
                    }
                ],
                [{"ieee": "AA:BB", "lqi": 90}],
                "everything established",
            ),
            (
                [
                    {
                        "entity_id": "sensor.b",
                        "state": "unknown",
                        "attributes": {"device_class": "battery"},
                    }
                ],
                [],
                "battery unreadable",
            ),
        ],
    )
    def test_stamp_is_set_exactly_when_its_value_is(self, states, zha, label):
        values, _ = DeviceKnowledge([Entity("sensor.b", "d1", "sensor")], states, zha).for_device(
            Device("d1", zigbee_ieee="AA:BB")
        )

        for column, stamp in (
            ("lqi", "lqi_updated_at"),
            ("battery_level", "battery_updated_at"),
            ("availability_status", "availability_updated_at"),
        ):
            if column not in values:
                assert stamp not in values, f"{label}: {stamp} written for a preserved column"
                continue
            assert stamp in values, f"{label}: {column} written without {stamp}"
            assert (values[column] is None) == (values[stamp] is None), (
                f"{label}: {column}={values[column]!r} but {stamp}={values[stamp]!r}"
            )
