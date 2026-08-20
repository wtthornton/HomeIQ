#!/usr/bin/env python3
"""Generate the `home` intake section for the home-atlas pack from measured state.

Why this is a script and not a hand-written YAML block: the atlas it feeds was
previously hand-authored, and by 2026-08-19 every one of its four naming
examples and six of its seven "key entity groups" named entities that do not
exist on the instance, while its header claimed 18 areas against a live 17. A
gene drafting an automation against `binary_sensor.garage_presence_group` emits
YAML for an entity that was never there. Facts a human types drift; facts read
off the instance do not.

Every claim carries how it was established. The ordering is the atlas evidence
vocabulary from `.claude/rules/friendly-names.md`:

    measured > upstream_source > attestation > unverified

(The `device_knowledge_claims` table in
docs/architecture/adr-device-knowledge-provenance.md uses its own five-class
vocabulary; these classes are not valid there and its CHECK constraint will
reject them.)

`unverified` rows are kept, never dropped. Omitting a weak row is
indistinguishable from never having modelled it, so a gene gets the same empty
answer either way and cannot tell "no such device" from "we don't know where it
is" — which is the failure that put a rename on the wrong physical dimmer. A
row that is present and typed `unverified` is a row a gene can abstain on.

Run:
  python3 scripts/generate_home_intake.py            # print the section
  python3 scripts/generate_home_intake.py --write    # splice into dna-core/intake/homeiq.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
INTAKE = ROOT / "dna-core" / "intake" / "homeiq.yaml"
HA_HOST = os.environ.get("HOMEIQ_HA_HOST", "192.168.1.80:8123")
# The container that already holds a working long-lived token. Reading it here
# keeps the token out of the repo, out of argv, and out of this file's output.
TOKEN_CONTAINER = os.environ.get("HOMEIQ_HA_TOKEN_CONTAINER", "homeiq-websocket")

# A Hue *room* group surfaces in HA as `<area_slug>_<area_slug>`; a bare single
# slug (`light.garage`, `light.first_floor`) is a Hue *zone*, which spans rooms
# and therefore asserts nothing about which room a bulb sits in. Conflating the
# two is why `light.garage` "contains" a light called Office Go.
ROOM_GROUP = re.compile(r"^light\.(?P<slug>[a-z0-9_]+?)_(?P=slug)$")


def _token() -> str:
    out = subprocess.run(
        ["docker", "inspect", TOKEN_CONTAINER], capture_output=True, text=True, check=True
    ).stdout
    for match in re.finditer(r"HOME_ASSISTANT_TOKEN=([^\"]+)", out):
        return match.group(1)
    raise SystemExit(f"no HOME_ASSISTANT_TOKEN in `docker inspect {TOKEN_CONTAINER}`")


def _rest(token: str, path: str) -> Any:
    request = urllib.request.Request(
        f"http://{HA_HOST}{path}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed local host
        return json.load(response)


async def _registries(token: str) -> dict[str, list[dict[str, Any]]]:
    import websockets

    async with websockets.connect(f"ws://{HA_HOST}/api/websocket", max_size=40 * 1024 * 1024) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        await ws.recv()
        out: dict[str, list[dict[str, Any]]] = {}
        for index, (key, kind) in enumerate(
            [
                ("devices", "config/device_registry/list"),
                ("entities", "config/entity_registry/list"),
                ("areas", "config/area_registry/list"),
            ],
            start=2,
        ):
            await ws.send(json.dumps({"id": index, "type": kind}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == index and message.get("type") == "result":
                    out[key] = message["result"]
                    break
        return out


def _tokens(text: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def classify_identity(identifiers: set[str], connections: set[str]) -> tuple[str, str]:
    """How durably this device can be named, independent of where it is.

    Separate from placement because the two fail independently: the two swapped
    dimmers were identified perfectly by ieee and still placed by a friendly
    name.
    """
    if "zha" in identifiers:
        return "zha ieee", "measured"
    if "mac" in connections:
        return "mac", "measured"
    if identifiers:
        return f"{sorted(identifiers)[0]} id", "upstream_source"
    return "none", "unverified"


def classify_placement(
    area_name: str, device_name: str, corroborated: bool, area_id: str
) -> dict[str, str]:
    """How this device's area was established, and whether a gene may act on it.

    NO branch returns an evidence class derived from a name, and no branch
    returns `actionable: true`. A friendly name is a presentation artifact: it
    is what the system shows a person, never something the system reasons from.
    So a name can appear in a `method` string — that text is for a human reading
    the atlas — but it may never set the class, the confidence, or the
    actionable flag.

    That rule retires the Hue room-group signal as evidence. Group membership
    looked like a second system independently corroborating placement, and it
    is keyed on member *names*, not stable ids: rename the device and the
    corroboration silently vanishes (pinned by
    `test_hue_membership_confers_no_evidence_upgrade`). It is the same
    name-string match that put the "office" row on the bar switch, one hop
    removed, so it now confers nothing and is recorded as an observation only.

    The consequence is that every placement claim in this home is `unverified`,
    which is simply true: no signal available from HA alone establishes where a
    device is. Behavioural correlation against a sensor is the only path to an
    actionable placement — that gene is the base case, not an enhancement.
    """
    if corroborated:
        return {
            "area_evidence": "unverified",
            "confidence": "low",
            "actionable": "false",
            "method": (
                f"observation only: hue room group light.{area_id}_{area_id} lists this "
                "device, but that group matches members by NAME, so it is a name match "
                "one hop removed and confers no evidence"
            ),
            "next_verification_step": (
                "establish by behavioural correlation against a sensor in the area"
            ),
        }
    if _tokens(area_name) & _tokens(device_name):
        return {
            "area_evidence": "unverified",
            "confidence": "low",
            "actionable": "false",
            "method": "area name echoes the device's friendly name; no independent signal",
            "next_verification_step": (
                "correlate actuation against a sensor in the area, or read protocol identity"
            ),
        }
    return {
        "area_evidence": "unverified",
        "confidence": "low",
        "actionable": "false",
        "method": "registry area_id only; HA records no provenance for it",
        "next_verification_step": (
            "correlate actuation against a sensor in the area, or confirm with the owner and date it"
        ),
    }


def room_membership(states: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Each Hue *room* group's member names, keyed by area slug.

    Zones are excluded by ROOM_GROUP: a zone spans rooms and so asserts nothing
    about which room a bulb sits in.
    """
    members: dict[str, set[str]] = {}
    for state in states:
        match = ROOM_GROUP.match(state["entity_id"])
        lights = state.get("attributes", {}).get("lights")
        if match and isinstance(lights, list):
            members[match.group("slug")] = {m.lower().strip() for m in lights}
    return members


def placement_rows(
    reg: dict[str, list[dict[str, Any]]], areas: dict[str, str], rooms: dict[str, set[str]]
) -> list[dict[str, str]]:
    """One evidence-bearing row per device that claims an area."""
    rows = []
    for device in sorted(reg["devices"], key=lambda d: (d.get("area_id") or "", d.get("name") or "")):
        area_id = device.get("area_id")
        if not area_id:
            continue
        name = device.get("name_by_user") or device.get("name") or ""
        identifiers = {i[0] for i in (device.get("identifiers") or []) if isinstance(i, list) and i}
        connections = {c[0] for c in (device.get("connections") or []) if isinstance(c, list) and c}
        identity, identity_evidence = classify_identity(identifiers, connections)
        corroborated = "hue" in identifiers and name.lower().strip() in rooms.get(area_id, set())
        # A device can reference an area that was since deleted from the area
        # registry; keep the row (falling back to the raw id) so the dangling
        # reference is visible instead of aborting the whole intake.
        area_name = areas.get(area_id, area_id)
        rows.append(
            {
                "device": name,
                "area": area_name,
                "identity": identity,
                "identity_evidence": identity_evidence,
                **classify_placement(area_name, name, corroborated, area_id),
            }
        )
    return rows


def build_section(states: list[dict[str, Any]], config: dict[str, Any],
                  reg: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_id = {s["entity_id"]: s for s in states}

    areas = {a["area_id"]: a["name"] for a in reg["areas"]}
    live_ids = {s["entity_id"] for s in states}

    rooms = room_membership(states)

    devices_per_area: collections.Counter[str] = collections.Counter()
    for device in reg["devices"]:
        if device.get("area_id"):
            devices_per_area[device["area_id"]] += 1

    area_rows = [
        {
            "area_id": area_id,
            "name": name,
            "devices": str(devices_per_area.get(area_id, 0)),
            "evidence": "measured",
            "method": "config/area_registry/list; device count from device_registry.area_id",
        }
        for area_id, name in sorted(areas.items(), key=lambda kv: kv[1])
    ]

    claim_rows = placement_rows(reg, areas, rooms)

    # Only groups that exist. The predecessor atlas named seven and six were
    # fiction; a gene cannot tell an invented id from a real one.
    group_rows = [
        {
            "entity_id": entity_id,
            "members": str(len(by_id[entity_id].get("attributes", {}).get("entity_id", []) or [])),
            "evidence": "measured",
            "method": "present in /api/states at verification time",
        }
        for entity_id in sorted(live_ids)
        if entity_id.endswith("_group") and entity_id.split(".")[0] in {"binary_sensor", "sensor", "light", "switch"}
    ]

    integration_rows = []
    counts: collections.Counter[str] = collections.Counter()
    for device in reg["devices"]:
        for identifier in device.get("identifiers") or []:
            if isinstance(identifier, list) and identifier:
                counts[identifier[0]] += 1
    for domain, count in counts.most_common():
        integration_rows.append(
            {
                "integration": domain,
                "devices": str(count),
                "evidence": "measured",
                "method": "device_registry identifiers",
            }
        )

    # Real entity ids, so a gene copying the shape copies something that exists.
    sample = [e for e in sorted(live_ids) if e.startswith("light.")][:3]
    sample += [e for e in sorted(live_ids) if e.startswith("binary_sensor.")][:2]
    naming_rows = [
        {
            "entity_id": entity_id,
            "friendly_name": by_id[entity_id].get("attributes", {}).get("friendly_name") or "",
            "evidence": "measured",
            "method": "present in /api/states at verification time",
        }
        for entity_id in sample
    ]

    unassigned = sum(1 for d in reg["devices"] if not d.get("area_id"))
    verified_at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "instance_name": str(config.get("location_name") or "UNSET"),
        "ha_version": str(config.get("version") or "UNSET"),
        "verified_at": verified_at,
        "verify_method": (
            "config/{area,device,entity}_registry/list over the HA websocket API, "
            "plus /api/states and /api/config over REST"
        ),
        "area_count": str(len(areas)),
        "device_count": str(len(reg["devices"])),
        "entity_count": str(len(reg["entities"])),
        "unassigned_device_count": str(unassigned),
        "areas": area_rows,
        "device_area_claims": claim_rows,
        "verified_groups": group_rows,
        "integrations": integration_rows,
        "naming_examples": naming_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="splice into dna-core/intake/homeiq.yaml")
    args = parser.parse_args()

    token = _token()
    section = build_section(
        _rest(token, "/api/states"), _rest(token, "/api/config"), asyncio.run(_registries(token))
    )
    if not args.write:
        print(yaml.safe_dump({"home": section}, sort_keys=False, width=100, allow_unicode=True))
        return 0

    intake = yaml.safe_load(INTAKE.read_text(encoding="utf-8")) or {}
    intake["home"] = section
    INTAKE.write_text(
        yaml.safe_dump(intake, sort_keys=False, width=100, allow_unicode=True), encoding="utf-8"
    )
    counts = collections.Counter(r["area_evidence"] for r in section["device_area_claims"])
    print(f"wrote {INTAKE.relative_to(ROOT)}")
    print(f"  areas={section['area_count']} devices={section['device_count']} claims={len(section['device_area_claims'])}")
    print(f"  area_evidence: {dict(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
