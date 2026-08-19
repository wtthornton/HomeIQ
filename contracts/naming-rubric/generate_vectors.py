"""Regenerate the naming-rubric golden vectors from the authoritative Python engine.

The rubric in `device-intelligence-service` is the single source of truth for
naming/area scoring (TAP-6230). This script freezes its output into
`golden-vectors.json`, which both the Python suite and the dashboard's vitest
suite assert against — so a rubric change that reaches only one side fails CI.

Run from the repo root after any intentional rubric change:
    .venv/bin/python contracts/naming-rubric/generate_vectors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = REPO_ROOT / "domains/ml-engine/device-intelligence-service"
sys.path.insert(0, str(SERVICE_SRC))

from src.services.naming_convention.score_engine import ScoreEngine  # noqa: E402

# Each vector probes an axis where the dashboard's former TypeScript copy of the
# rubric disagreed with this engine. `why` documents the axis so a future reader
# knows what a regression on that vector means.
VECTORS: list[dict[str, object]] = [
    {
        "name": "perfect_sensor",
        "why": "All six rules satisfied; anchors the top of the 100-point scale.",
        "entity": {
            "entity_id": "sensor.kitchen_temperature",
            "domain": "sensor",
            "area_id": "kitchen",
            "friendly_name": "Kitchen Temperature",
            "device_class": "temperature",
            "aliases": ["kitchen temp", "the kitchen thermometer"],
            "labels": ["ai:monitor-only", "role:temperature"],
        },
    },
    {
        "name": "bare_entity",
        "why": "Nothing set; anchors the bottom. Non-sensor domains still earn the sensor_role rule.",
        "entity": {"entity_id": "light.unknown", "domain": "light"},
    },
    {
        "name": "single_alias",
        "why": "One alias earns 15, not 20. The TS copy awarded a flat 20 here.",
        "entity": {
            "entity_id": "light.office_lamp",
            "domain": "light",
            "area_id": "office",
            "friendly_name": "Office Lamp",
            "device_class": "light",
            "aliases": ["desk lamp"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "ai_intent_label",
        "why": "An ai: label earns the flat 20 for labels. The TS copy added a +10 bonus, overflowing past 100.",
        "entity": {
            "entity_id": "light.office_ceiling",
            "domain": "light",
            "area_id": "office",
            "friendly_name": "Office Ceiling",
            "device_class": "light",
            "aliases": ["ceiling", "office light"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "light_missing_device_class",
        "why": "device_class is scored on every domain. The TS copy only scored it for sensors.",
        "entity": {
            "entity_id": "light.hallway_main",
            "domain": "light",
            "area_id": "hallway",
            "friendly_name": "Hallway Main",
            "aliases": ["hall light", "hallway"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "brand_esp32",
        "why": "esp32 is a brand token here but absent from the TS brand list.",
        "entity": {
            "entity_id": "switch.garage_esp32_relay",
            "domain": "switch",
            "area_id": "garage",
            "friendly_name": "Garage Esp32 Relay",
            "device_class": "switch",
            "aliases": ["garage relay", "relay"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "brand_tapo",
        "why": "tapo is in the TS brand list but not this engine's, so the two disagreed in the other direction.",
        "entity": {
            "entity_id": "switch.office_tapo_plug",
            "domain": "switch",
            "area_id": "office",
            "friendly_name": "Office Tapo Plug",
            "device_class": "outlet",
            "aliases": ["office plug", "plug"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "sensor_role_namespace",
        "why": "The sensor_role rule requires a 'role:' prefix; the dashboard suggested 'sensor:' labels that earn nothing.",
        "entity": {
            "entity_id": "sensor.bedroom_motion",
            "domain": "sensor",
            "area_id": "bedroom",
            "friendly_name": "Bedroom Motion",
            "device_class": "motion",
            "aliases": ["bedroom pir", "motion"],
            "labels": ["sensor:trigger"],
        },
    },
    {
        "name": "integration_prefix",
        "why": "A leading integration name is not penalised here; the TS copy docked 4 points for it.",
        "entity": {
            "entity_id": "light.mqtt_porch",
            "domain": "light",
            "area_id": "porch",
            "friendly_name": "Mqtt Porch",
            "device_class": "light",
            "aliases": ["porch", "porch light"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "lowercase_name",
        "why": "Title Case is a strict regex here, far stricter than the TS per-word first-letter check.",
        "entity": {
            "entity_id": "light.den_lamp",
            "domain": "light",
            "area_id": "den",
            "friendly_name": "den lamp",
            "device_class": "light",
            "aliases": ["den", "den light"],
            "labels": ["ai:automatable"],
        },
    },
    {
        "name": "no_area_prefix",
        "why": "A name that omits its area prefix loses 5 of the friendly_name points.",
        "entity": {
            "entity_id": "light.attic_bulb",
            "domain": "light",
            "area_id": "attic",
            "friendly_name": "Spare Bulb",
            "device_class": "light",
            "aliases": ["spare", "attic bulb"],
            "labels": ["ai:automatable"],
        },
    },
]


def main() -> None:
    engine = ScoreEngine()
    out = []
    for vector in VECTORS:
        score = engine.score_entity(dict(vector["entity"]))  # type: ignore[arg-type]
        out.append(
            {
                "name": vector["name"],
                "why": vector["why"],
                "entity": vector["entity"],
                "expected": score.to_dict(),
            }
        )

    target = Path(__file__).with_name("golden-vectors.json")
    target.write_text(json.dumps({"vectors": out}, indent=2) + "\n")
    print(f"wrote {len(out)} vectors to {target.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
