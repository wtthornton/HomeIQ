"""Tests for the co-location correlation engine.

Two confounders were found by running this against 30 days of real events, and
each one produced a confident WRONG answer before it was fixed. Both are pinned
here because both are silent — the output looked clean in each case.

  1. Group switching. Lights turned on together by a scene correlate with the
     same sensor and with each other. The first run "proved" one lux sensor was
     co-located with five lights at once, including two dimmers that are
     demonstrably in different rooms.
  2. A contested anchor. After isolation, the office and bar dimmers still both
     folded onto one sensor. Each beat its own runner-up, so each looked clean
     alone; only folding them into clusters made the collision visible.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from correlate_colocation import (  # noqa: E402
    FORBIDDEN_TAGS,
    MIN_EVENTS,
    Evidence,
    Verdict,
    _flux,
    assert_name_free,
    fold_clusters,
    isolated_actuations,
    judge,
    score_pair,
)

import pytest  # noqa: E402


class TestNameBlindness:
    """The engine must be structurally unable to read a room label."""

    def test_forbidden_tags_are_dropped_in_the_query(self):
        flux = _flux(30)
        for tag in FORBIDDEN_TAGS:
            assert f'"{tag}"' in flux.split("drop(columns:")[1].split("]")[0]

    def test_query_keeps_only_ids_and_timestamps(self):
        kept = _flux(30).split('keep(columns: [')[1].split("]")[0]
        assert "area_id" not in kept
        assert "friendly_name" not in kept
        assert "_time" in kept and "entity_id" in kept

    @pytest.mark.parametrize("tag", FORBIDDEN_TAGS)
    def test_a_record_carrying_a_room_or_name_column_is_refused(self, tag):
        with pytest.raises(ValueError, match="laundered from a name match"):
            assert_name_free({"entity_id": "light.x", tag: "office"})

    def test_a_clean_record_passes(self):
        assert assert_name_free({"entity_id": "light.x", "_time": "t", "domain": "light"}) is None


class TestIsolatedActuations:
    def test_an_actuation_with_another_light_nearby_is_dropped(self):
        # The group-switching confound: two lights on the same scene.
        assert isolated_actuations([100.0], [105.0], window=30) == []

    def test_an_actuation_with_no_other_light_nearby_is_kept(self):
        assert isolated_actuations([100.0], [500.0], window=30) == [100.0]

    def test_boundary_is_inclusive_so_a_simultaneous_switch_is_dropped(self):
        assert isolated_actuations([100.0], [130.0], window=30) == []
        assert isolated_actuations([100.0], [70.0], window=30) == []

    def test_other_light_just_outside_the_window_is_ignored(self):
        assert isolated_actuations([100.0], [131.0], window=30) == [100.0]

    def test_no_other_lights_at_all_keeps_everything(self):
        assert isolated_actuations([1.0, 2.0, 3.0], [], window=30) == [1.0, 2.0, 3.0]


class TestScorePair:
    def _times(self, n, step=86400.0, start=0.0):
        return [start + i * step for i in range(n)]

    def test_a_sensor_that_always_responds_and_never_in_control_scores_high_lift(self):
        acts = self._times(10)
        # responds 5s after each actuation, and nowhere near the control window
        sensor = sorted(t + 5 for t in acts)
        ev = score_pair("light.a", acts, "sensor.s", sensor, 90)
        assert ev.responses == 10
        assert ev.control_responses == 0
        assert ev.lift > 5

    def test_a_sensor_that_responds_equally_in_control_scores_no_lift(self):
        # A sensor that fires constantly reacts to everything; it must not win.
        acts = self._times(10)
        sensor = sorted([t + 5 for t in acts] + [t - 3600 + 5 for t in acts])
        ev = score_pair("light.a", acts, "sensor.busy", sensor, 90)
        assert ev.responses == 10
        assert ev.control_responses == 10
        assert ev.lift == pytest.approx(1.0)

    def test_lift_is_bounded_when_controls_are_zero(self):
        # Laplace correction: a pair with few samples cannot show infinite lift.
        acts = self._times(10)
        ev = score_pair("light.a", acts, "sensor.s", sorted(t + 5 for t in acts), 90)
        assert ev.lift < len(acts) + 2

    def test_distinct_days_counts_days_not_events(self):
        acts = [0.0, 60.0, 120.0, 180.0]  # four events, one day
        ev = score_pair("light.a", acts, "sensor.s", [], 90)
        assert ev.actuations == 4
        assert ev.distinct_days == 1


class TestJudge:
    def _ev(self, sensor, lift, n=20, days=5):
        return Evidence(
            actuator="light.a", sensor=sensor, actuations=n, distinct_days=days,
            responses=0, control_responses=0, response_rate=0.0, control_rate=0.0,
            lift=lift, window_s=90,
        )

    def test_no_candidates_abstains(self):
        v = judge("light.a", [])
        assert v.abstained and "no candidate" in v.reason

    def test_too_few_actuations_abstains_and_says_so(self):
        v = judge("light.a", [self._ev("sensor.s", 10.0, n=MIN_EVENTS - 1)])
        assert v.abstained
        assert str(MIN_EVENTS) in v.reason

    def test_a_single_day_abstains_even_with_many_events(self):
        v = judge("light.a", [self._ev("sensor.s", 10.0, n=500, days=1)])
        assert v.abstained and "day" in v.reason

    def test_weak_lift_abstains(self):
        v = judge("light.a", [self._ev("sensor.s", 1.2)])
        assert v.abstained and "lift" in v.reason

    def test_two_close_candidates_abstain_however_strong_both_are(self):
        # The margin rule: strong but tied must abstain, not pick one.
        v = judge("light.a", [self._ev("sensor.s1", 50.0), self._ev("sensor.s2", 49.0)])
        assert v.abstained
        assert "cannot separate" in v.reason

    def test_a_clear_winner_is_called_with_its_evidence(self):
        v = judge("light.a", [self._ev("sensor.s1", 40.0), self._ev("sensor.s2", 2.0)])
        assert not v.abstained
        assert v.colocated_with == "sensor.s1"
        assert v.evidence, "a verdict must carry the bundle it was derived from"

    def test_every_verdict_carries_a_reason(self):
        for evidence in ([], [self._ev("s", 1.0)], [self._ev("s", 40.0), self._ev("t", 2.0)]):
            assert judge("light.a", evidence).reason.strip()


class TestFoldClusters:
    def _called(self, actuator, sensor):
        return Verdict(actuator, sensor, "high", False, "ok", 9.0)

    def _abstained(self, actuator):
        return Verdict(actuator, None, "none", True, "weak", None)

    def test_two_actuators_on_one_sensor_are_flagged_contested(self):
        # The office/bar dimmer collision. Each call is clean alone.
        folded = fold_clusters([
            self._called("light.office_dimmer", "sensor.aqara"),
            self._called("light.bar_dimmer", "sensor.aqara"),
        ])
        assert folded["contested_clusters"] == 1
        assert folded["clusters"][0]["contested"] is True
        assert folded["clusters"][0]["member_count"] == 2

    def test_one_actuator_per_sensor_is_not_contested(self):
        folded = fold_clusters([
            self._called("light.a", "sensor.one"),
            self._called("light.b", "sensor.two"),
        ])
        assert folded["contested_clusters"] == 0
        assert all(not c["contested"] for c in folded["clusters"])

    def test_abstentions_never_enter_a_cluster(self):
        folded = fold_clusters([self._abstained("light.a"), self._called("light.b", "sensor.s")])
        members = [m for c in folded["clusters"] for m in c["members"]]
        assert members == ["light.b"]

    def test_clusters_are_anonymous_and_carry_no_room(self):
        folded = fold_clusters([self._called("light.a", "sensor.s")])
        cluster = folded["clusters"][0]
        assert cluster["cluster_id"].startswith("C")
        # Naming is a separate, attestation-rooted step; nothing here may name a room.
        assert "room" not in cluster and "area" not in cluster

    def test_no_calls_at_all_yields_no_clusters(self):
        folded = fold_clusters([self._abstained("light.a")])
        assert folded["clusters"] == []
        assert folded["contested_clusters"] == 0
