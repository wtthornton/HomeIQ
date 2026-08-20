#!/usr/bin/env python3
"""Co-location evidence from behaviour, computed without ever reading a room label.

This is the evidence-gathering half of the room-inference gene. It answers only
one question — "do these two entities share a space?" — and deliberately cannot
answer "which room is this?". That separation is the whole design:

  * Correlation produces equivalence classes ("same space as"), never a name. A
    label has to come from somewhere outside the derived data.
  * This module therefore reads ONLY entity ids and event timestamps. It never
    reads `area_id`, a friendly name, or a group membership. If it did, the room
    label it eventually produced could be laundered from the very name-match
    that put a rename on the wrong physical dimmer.

`FORBIDDEN_TAGS` makes that structural rather than aspirational: the Flux query
drops those columns, and `assert_name_free()` fails loudly if a caller hands in
a record still carrying one.

The statistics follow the bar set in the design review:
  * at least MIN_EVENTS independent actuations, spanning more than one day
  * a response window bounded by physical plausibility for the sensor
  * lift against a matched CONTROL window, not raw co-occurrence — otherwise a
    hallway sensor that reacts to everything wins on volume alone
  * a MARGIN requirement: the best candidate must beat the runner-up. This is
    what lets a device with one clear partner report at moderate absolute lift
    while a device tied between two candidates abstains no matter how strong
    both look on their own.

Run:
  python3 scripts/correlate_colocation.py --days 30
  python3 scripts/correlate_colocation.py --days 30 --actuator light.inovelli_vzm31_sn
"""

from __future__ import annotations

import argparse
import bisect
import collections
import json
import subprocess
import sys
from dataclasses import dataclass, field

# Columns that carry a room label or a human name. Dropped in the query and
# rejected on ingest. Adding a tag here is cheaper than auditing every caller.
FORBIDDEN_TAGS = ("area_id", "friendly_name", "name", "location")

# Sensor classes whose reading responds to a light being switched, with the
# window inside which the response is physically plausible.
RESPONSE_WINDOW_S: dict[str, int] = {
    "illuminance": 90,
    "motion": 120,
    "occupancy": 120,
}

# Two lights switched together by a scene or a group correlate with the SAME
# sensor and with each other, and that is indistinguishable from co-location by
# response rate alone. The first run of this script "proved" one lux sensor was
# co-located with five lights at once, including the office and bar dimmers that
# are demonstrably in different rooms. So an actuation only counts as evidence if
# no OTHER light moved near it: what remains is the light's own effect.
ISOLATION_WINDOW_S = 30

MIN_EVENTS = 8  # independent ISOLATED actuations before any verdict is emitted
MIN_DISTINCT_DAYS = 2  # a single busy evening is one event, not eight
MIN_LIFT = 2.0  # response rate must at least double against control
MIN_MARGIN = 1.5  # best candidate must beat runner-up by this ratio
CONTROL_OFFSET_S = 3600  # matched control window, one hour before each actuation


@dataclass
class Evidence:
    """Why a pair was or was not judged co-located. Always emitted."""

    actuator: str
    sensor: str
    actuations: int
    distinct_days: int
    responses: int
    control_responses: int
    response_rate: float
    control_rate: float
    lift: float
    window_s: int

    def to_dict(self) -> dict:
        return {
            "actuator": self.actuator,
            "sensor": self.sensor,
            "n_actuations": self.actuations,
            "distinct_days": self.distinct_days,
            "responses": self.responses,
            "control_responses": self.control_responses,
            "response_rate": round(self.response_rate, 4),
            "control_rate": round(self.control_rate, 4),
            "lift": round(self.lift, 3),
            "window_s": self.window_s,
        }


@dataclass
class Verdict:
    """A co-location call, or an abstention with the reason it abstained."""

    actuator: str
    colocated_with: str | None
    confidence: str
    abstained: bool
    reason: str
    margin: float | None
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "actuator": self.actuator,
            "colocated_with": self.colocated_with,
            "confidence": self.confidence,
            "abstained": self.abstained,
            "reason": self.reason,
            "margin": None if self.margin is None else round(self.margin, 3),
            # The full bundle travels with the verdict so the thresholds stay a
            # tunable parameter of the caller rather than a magic number in here.
            "evidence": [e.to_dict() for e in self.evidence],
        }


def assert_name_free(record: dict) -> None:
    """Refuse any record still carrying a room label or human name."""
    leaked = sorted(set(record) & set(FORBIDDEN_TAGS))
    if leaked:
        raise ValueError(
            f"co-location input carries name/room columns {leaked}; correlation must "
            "never see them or the verdict can be laundered from a name match"
        )


def _flux(days: int) -> str:
    drop = ", ".join(f'"{tag}"' for tag in FORBIDDEN_TAGS)
    return f"""
from(bucket: "home_assistant_events")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r._measurement == "home_assistant_events")
  |> filter(fn: (r) => r.domain == "light" or r.device_class == "illuminance"
                    or r.device_class == "motion" or r.device_class == "occupancy")
  |> drop(columns: [{drop}])
  |> keep(columns: ["_time", "entity_id", "domain", "device_class"])
"""


def fetch_events(days: int) -> list[dict]:
    """Raw (time, entity_id, domain, device_class) rows straight from InfluxDB."""
    # The query goes in over STDIN, not as an argument. Embedding multi-line Flux
    # in a `bash -c` string means three levels of quoting (python -> docker ->
    # bash) and it does not survive them. The trailing `-` is POSITIONAL ("query
    # literal or '-' for stdin"); `-f -` is read as a filename and fails. And note
    # `docker exec -i`: without it the container gets no stdin at all and the
    # command succeeds having read nothing.
    proc = subprocess.run(
        [
            "docker", "exec", "-i", "homeiq-influxdb", "bash", "-c",
            'influx query --token "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" '
            '-o "$DOCKER_INFLUXDB_INIT_ORG" --raw -',
        ],
        input=_flux(days), capture_output=True, text=True, check=True,
    )
    rows: list[dict] = []
    header: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cells = line.split(",")
        if "_time" in cells or "result" in cells:
            header = cells
            continue
        if not header:
            continue
        record = dict(zip(header, cells, strict=False))
        assert_name_free(record)
        time = record.get("_time", "").strip()
        entity = record.get("entity_id", "").strip()
        if time and entity:
            rows.append(
                {
                    "t": time,
                    "entity_id": entity,
                    "domain": record.get("domain", "").strip(),
                    "device_class": record.get("device_class", "").strip(),
                }
            )
    return rows


def isolated_actuations(
    act_times: list[float], other_light_times: list[float], window: int = ISOLATION_WINDOW_S
) -> list[float]:
    """Actuations with no other light switching within +/- `window`.

    Without this the method measures which lights are switched TOGETHER, not
    which share a room — a scene that turns on the whole floor makes every light
    in it correlate with every sensor that happens to report afterwards.
    """
    keep = []
    for t in act_times:
        left = bisect.bisect_left(other_light_times, t - window)
        right = bisect.bisect_right(other_light_times, t + window)
        if left == right:
            keep.append(t)
    return keep


def _epoch(stamp: str) -> float:
    import datetime

    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def _responded(sensor_times: list[float], start: float, window: int) -> bool:
    """Did the sensor emit anything in (start, start + window]?"""
    index = bisect.bisect_right(sensor_times, start)
    return index < len(sensor_times) and sensor_times[index] <= start + window


def score_pair(
    actuator: str, act_times: list[float], sensor: str, sensor_times: list[float], window: int
) -> Evidence:
    """Response rate after each actuation against a matched control window."""
    responses = sum(1 for t in act_times if _responded(sensor_times, t, window))
    controls = sum(
        1 for t in act_times if _responded(sensor_times, t - CONTROL_OFFSET_S, window)
    )
    total = len(act_times)
    response_rate = responses / total if total else 0.0
    control_rate = controls / total if total else 0.0
    # A control rate of zero would divide by zero; the +1 floor on both sides is
    # a Laplace correction, so a pair with few controls cannot show infinite lift.
    lift = ((responses + 1) / (total + 2)) / ((controls + 1) / (total + 2))
    days = {int(t // 86400) for t in act_times}
    return Evidence(
        actuator=actuator,
        sensor=sensor,
        actuations=total,
        distinct_days=len(days),
        responses=responses,
        control_responses=controls,
        response_rate=response_rate,
        control_rate=control_rate,
        lift=lift,
        window_s=window,
    )


def judge(actuator: str, evidence: list[Evidence]) -> Verdict:
    """Best candidate, or an abstention naming which bar it failed."""
    ranked = sorted(evidence, key=lambda e: e.lift, reverse=True)
    if not ranked:
        return Verdict(actuator, None, "none", True, "no candidate sensors had events", None)

    best = ranked[0]
    if best.actuations < MIN_EVENTS:
        return Verdict(
            actuator, None, "none", True,
            f"only {best.actuations} actuations, need {MIN_EVENTS}", None, ranked[:3],
        )
    if best.distinct_days < MIN_DISTINCT_DAYS:
        return Verdict(
            actuator, None, "none", True,
            f"actuations span {best.distinct_days} day(s), need {MIN_DISTINCT_DAYS}",
            None, ranked[:3],
        )
    if best.lift < MIN_LIFT:
        return Verdict(
            actuator, None, "none", True,
            f"best lift {best.lift:.2f} below {MIN_LIFT}", None, ranked[:3],
        )

    runner_up = ranked[1].lift if len(ranked) > 1 else 0.0
    margin = best.lift / runner_up if runner_up > 0 else float("inf")
    if margin < MIN_MARGIN:
        return Verdict(
            actuator, None, "none", True,
            f"top two candidates within {margin:.2f}x — cannot separate "
            f"{best.sensor} from {ranked[1].sensor}",
            margin, ranked[:3],
        )

    confidence = "high" if best.lift >= 4 and margin >= 2 else "medium"
    return Verdict(
        actuator, best.sensor, confidence, False,
        f"lift {best.lift:.2f} over control across {best.actuations} actuations on "
        f"{best.distinct_days} days, beating runner-up by {margin:.2f}x",
        margin, ranked[:3],
    )


def fold_clusters(verdicts: list[Verdict]) -> dict:
    """Fold pairwise calls into equivalence classes and surface contradictions.

    A per-actuator verdict cannot see that the SAME sensor was named the partner
    of two actuators which are themselves in different rooms — each call beats
    its own runner-up, so each looks clean in isolation. Folding them makes the
    collision visible: it shows up as one cluster containing devices that cannot
    share a space.

    Clusters are ANONYMOUS. This function never assigns a room, because nothing
    here is entitled to; naming is a separate step that may only consume an
    attestation-rooted label.
    """
    partners: dict[str, list[str]] = collections.defaultdict(list)
    for verdict in verdicts:
        if not verdict.abstained and verdict.colocated_with:
            partners[verdict.colocated_with].append(verdict.actuator)

    clusters = []
    for index, (sensor, actuators) in enumerate(sorted(partners.items()), start=1):
        clusters.append(
            {
                "cluster_id": f"C{index:02d}",
                "anchor_sensor": sensor,
                "members": sorted(actuators),
                "member_count": len(actuators),
                # More than one actuator folding onto one sensor is not proof of a
                # shared room — it is the signature of either an open-plan space or
                # a residual confound. Flagged, never silently merged.
                "contested": len(actuators) > 1,
            }
        )
    contested = [c for c in clusters if c["contested"]]
    return {
        "clusters": clusters,
        "contested_clusters": len(contested),
        "note": (
            "Clusters are anonymous equivalence classes. A contested cluster holds "
            "actuators that all correlate with one sensor; that is open-plan space or "
            "a residual confound, and it must be resolved before any of its members "
            "can be assigned a room."
        ) if contested else "No contested clusters.",
    }


def correlate(events: list[dict], only: str | None = None) -> list[Verdict]:
    by_entity: dict[str, list[float]] = collections.defaultdict(list)
    classes: dict[str, str] = {}
    domains: dict[str, str] = {}
    for row in events:
        by_entity[row["entity_id"]].append(_epoch(row["t"]))
        if row["device_class"]:
            classes[row["entity_id"]] = row["device_class"]
        domains[row["entity_id"]] = row["domain"]
    for times in by_entity.values():
        times.sort()

    actuators = [e for e, d in domains.items() if d == "light" and (only is None or e == only)]
    sensors = [e for e, c in classes.items() if c in RESPONSE_WINDOW_S]

    all_light_times: dict[str, list[float]] = {
        e: by_entity[e] for e, d in domains.items() if d == "light"
    }

    verdicts = []
    for actuator in sorted(actuators):
        others = sorted(
            t for entity, times in all_light_times.items() if entity != actuator for t in times
        )
        act_times = isolated_actuations(by_entity[actuator], others)
        evidence = [
            score_pair(
                actuator, act_times, sensor, by_entity[sensor],
                RESPONSE_WINDOW_S[classes[sensor]],
            )
            for sensor in sorted(sensors)
            if sensor != actuator and by_entity[sensor]
        ]
        verdicts.append(judge(actuator, evidence))
    return verdicts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--actuator", default=None, help="score a single actuator")
    parser.add_argument("--json", action="store_true", help="emit the full bundle as JSON")
    args = parser.parse_args()

    events = fetch_events(args.days)
    verdicts = correlate(events, args.actuator)

    if args.json:
        print(json.dumps(
            {"verdicts": [v.to_dict() for v in verdicts], **fold_clusters(verdicts)}, indent=2
        ))
        return 0

    called = [v for v in verdicts if not v.abstained]
    print(f"{len(events)} events over {args.days}d | {len(verdicts)} actuators scored")
    print(f"co-location called: {len(called)} | abstained: {len(verdicts) - len(called)}\n")
    for verdict in verdicts:
        mark = "ABSTAIN" if verdict.abstained else f"CO-LOCATED ({verdict.confidence})"
        print(f"{mark:24s} {verdict.actuator}")
        if verdict.colocated_with:
            print(f"{'':24s}   with {verdict.colocated_with}")
        print(f"{'':24s}   {verdict.reason}")

    folded = fold_clusters(verdicts)
    print("\n--- co-location clusters (anonymous; naming is a separate step) ---")
    for cluster in folded["clusters"]:
        flag = "  <-- CONTESTED" if cluster["contested"] else ""
        print(f"  {cluster['cluster_id']}  anchor={cluster['anchor_sensor']}{flag}")
        for member in cluster["members"]:
            print(f"        {member}")
    print(f"\n{folded['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
