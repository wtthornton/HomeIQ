"""Tests for the presence sensor-class taxonomy (TAP-7590).

The contract these pin: classification reads only device/integration
metadata (never entity_id or friendly name), mmWave is split into two
classes that do not share behaviour, every prior is a machine-checkable
provisional placeholder, and a rate-limited class carries its own freshness
bound.
"""

import pytest
from homeiq_device_taxonomy.sensor_class import (
    PRESENCE_RELEVANT_SENSOR_CLASSES,
    SENSOR_CLASS_PROFILES,
    PriorStatus,
    SensorClass,
    Transport,
    UnfittedPriorError,
    classify_from_records,
    classify_sensor,
    fails_on_stillness,
    require_fitted,
)


class TestVocabularyCoverage:
    def test_every_declared_class_has_a_profile(self):
        for sensor_class in SensorClass:
            assert sensor_class in SENSOR_CLASS_PROFILES

    def test_every_profile_declares_a_failure_mode(self):
        for profile in SENSOR_CLASS_PROFILES.values():
            assert isinstance(profile.dominant_failure_mode, str)
            assert profile.dominant_failure_mode


class TestMmwaveSplit:
    def test_presence_and_doppler_are_distinct_classes(self):
        assert SensorClass.MMWAVE_PRESENCE != SensorClass.MMWAVE_DOPPLER

    def test_no_single_prior_object_spans_both(self):
        presence = SENSOR_CLASS_PROFILES[SensorClass.MMWAVE_PRESENCE]
        doppler = SENSOR_CLASS_PROFILES[SensorClass.MMWAVE_DOPPLER]
        assert presence.prior is not doppler.prior

    def test_only_presence_capable_mmwave_detects_a_stationary_person(self):
        presence = SENSOR_CLASS_PROFILES[SensorClass.MMWAVE_PRESENCE]
        doppler = SENSOR_CLASS_PROFILES[SensorClass.MMWAVE_DOPPLER]
        assert presence.detects_stationary_person is True
        assert doppler.detects_stationary_person is False

    def test_aqara_fp1e_classifies_mmwave_presence_by_metadata_alone(self):
        sensor_class = classify_sensor(
            domain="binary_sensor",
            device_class="occupancy",
            manufacturer="Aqara",
            model="lumi.sensor_occupy.agl8",
        )
        assert sensor_class is SensorClass.MMWAVE_PRESENCE

    def test_fp1e_after_quirk_friendly_name_rewrite_still_classifies_presence(self):
        sensor_class = classify_sensor(
            domain="binary_sensor",
            device_class="occupancy",
            manufacturer="Aqara",
            model="Presence Sensor FP1E",
        )
        assert sensor_class is SensorClass.MMWAVE_PRESENCE

    def test_rd03d_class_module_classifies_mmwave_doppler(self):
        sensor_class = classify_sensor(
            domain="binary_sensor",
            device_class="motion",
            manufacturer="Ai-Thinker",
            model="RD-03D",
        )
        assert sensor_class is SensorClass.MMWAVE_DOPPLER


class TestRenameProof:
    """`classify_sensor` and `classify_from_records` take no entity_id or
    friendly-name argument, so a rename cannot change the result."""

    def test_classify_sensor_has_no_name_bearing_parameter(self):
        import inspect

        params = set(inspect.signature(classify_sensor).parameters)
        assert "entity_id" not in params
        assert "friendly_name" not in params
        assert "name" not in params

    def test_renamed_fp1e_entity_still_classifies_mmwave_presence(self):
        device = {"manufacturer": "Aqara", "model": "lumi.sensor_occupy.agl8"}
        original = {
            "entity_id": "binary_sensor.bar_fp2",
            "domain": "binary_sensor",
            "device_class": "occupancy",
        }
        renamed = {
            "entity_id": "binary_sensor.bar_renamed_totally_different",
            "domain": "binary_sensor",
            "device_class": "occupancy",
        }
        assert classify_from_records(original, device) is SensorClass.MMWAVE_PRESENCE
        assert classify_from_records(renamed, device) is SensorClass.MMWAVE_PRESENCE

    def test_a_room_label_cannot_be_classified_as_mmwave(self):
        for label in ("office", "kitchen", "Bar", "Fp2 Renamed"):
            sensor_class = classify_sensor(domain=label, device_class=None)
            assert sensor_class is SensorClass.UNKNOWN


class TestUnknownFallback:
    def test_unmatched_entity_classifies_unknown_not_dropped(self):
        sensor_class = classify_sensor(domain="sensor", device_class="illuminance")
        assert sensor_class is SensorClass.UNKNOWN

    def test_unknown_ties_for_the_weakest_prior(self):
        unknown_value = SENSOR_CLASS_PROFILES[SensorClass.UNKNOWN].prior.value
        for sensor_class, profile in SENSOR_CLASS_PROFILES.items():
            assert unknown_value <= profile.prior.value, sensor_class


class TestTransportAndFreshness:
    def test_rate_limited_classes_carry_their_own_positive_freshness_bound(self):
        for profile in SENSOR_CLASS_PROFILES.values():
            if profile.transport is Transport.RATE_LIMITED:
                assert profile.freshness_bound_seconds is not None
                assert profile.freshness_bound_seconds > 0

    def test_continuous_classes_carry_no_freshness_bound(self):
        for profile in SENSOR_CLASS_PROFILES.values():
            if profile.transport is Transport.CONTINUOUS:
                assert profile.freshness_bound_seconds is None

    def test_offgrid_radar_freshness_bound_is_its_own_not_shared(self):
        offgrid = SENSOR_CLASS_PROFILES[SensorClass.OFFGRID_RADAR]
        tracker = SENSOR_CLASS_PROFILES[SensorClass.DEVICE_TRACKER]
        assert offgrid.transport is Transport.RATE_LIMITED
        assert tracker.transport is Transport.RATE_LIMITED
        assert offgrid.freshness_bound_seconds != tracker.freshness_bound_seconds

    def test_continuous_class_rejects_a_freshness_bound_at_construction(self):
        from homeiq_device_taxonomy.sensor_class import ReliabilityPrior, SensorClassProfile

        with pytest.raises(ValueError):
            SensorClassProfile(
                sensor_class=SensorClass.PIR,
                dominant_failure_mode="x",
                transport=Transport.CONTINUOUS,
                freshness_bound_seconds=60,
                detects_stationary_person=False,
                prior=ReliabilityPrior(value=0.5, status=PriorStatus.PROVISIONAL, source="x"),
            )

    def test_rate_limited_class_rejects_a_missing_freshness_bound_at_construction(self):
        from homeiq_device_taxonomy.sensor_class import ReliabilityPrior, SensorClassProfile

        with pytest.raises(ValueError):
            SensorClassProfile(
                sensor_class=SensorClass.OFFGRID_RADAR,
                dominant_failure_mode="x",
                transport=Transport.RATE_LIMITED,
                freshness_bound_seconds=None,
                detects_stationary_person=False,
                prior=ReliabilityPrior(value=0.5, status=PriorStatus.PROVISIONAL, source="x"),
            )


class TestStillnessFlag:
    def test_fails_on_stillness_reads_the_flag_not_the_class_name(self):
        assert fails_on_stillness(SensorClass.PIR) is True
        assert fails_on_stillness(SensorClass.MMWAVE_DOPPLER) is True
        assert fails_on_stillness(SensorClass.MMWAVE_PRESENCE) is False


class TestProvisionalPriorsAreMachineCheckable:
    def test_every_prior_is_provisional_not_fitted(self):
        for profile in SENSOR_CLASS_PROFILES.values():
            assert profile.prior.status is PriorStatus.PROVISIONAL
            assert profile.prior.is_fitted is False

    def test_require_fitted_raises_on_a_provisional_prior(self):
        provisional = SENSOR_CLASS_PROFILES[SensorClass.PIR].prior
        with pytest.raises(UnfittedPriorError):
            require_fitted(provisional)

    def test_require_fitted_accepts_a_genuinely_fitted_prior(self):
        from homeiq_device_taxonomy.sensor_class import ReliabilityPrior

        fitted = ReliabilityPrior(
            value=0.83, status=PriorStatus.FITTED, source="query: room_occupancy 2026-09-14"
        )
        assert require_fitted(fitted) is fitted


class TestPresenceRelevantClasses:
    def test_door_contact_and_power_draw_are_not_presence_evidence(self):
        assert SensorClass.DOOR_CONTACT not in PRESENCE_RELEVANT_SENSOR_CLASSES
        assert SensorClass.POWER_DRAW not in PRESENCE_RELEVANT_SENSOR_CLASSES

    def test_every_mmwave_and_pir_class_is_presence_evidence(self):
        assert SensorClass.PIR in PRESENCE_RELEVANT_SENSOR_CLASSES
        assert SensorClass.MMWAVE_PRESENCE in PRESENCE_RELEVANT_SENSOR_CLASSES
        assert SensorClass.MMWAVE_DOPPLER in PRESENCE_RELEVANT_SENSOR_CLASSES
