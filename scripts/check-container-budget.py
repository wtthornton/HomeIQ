#!/usr/bin/env python3
"""TAP-5303: fail when the production container count or memory footprint regrows.

The stack reached 58 containers one reasonable-seeming service at a time. This
is a ratchet, not a fixed bar: it pins the count to the number checked into
`infrastructure/container-budget.json` and fails in BOTH directions --- adding a
service fails until the ceiling is deliberately raised, and removing one fails
until the ceiling is lowered. A ceiling that only ever gets raised is not a
gate, and one that silently absorbs deletions loses the progress it recorded.

`TAP-5283`'s goal (12 services / 4 GiB) is recorded as `target` and is not yet
met --- enforcing it today would make the job red on every commit, which is
exactly the failure mode `TAP-6103` exists to fix. The ratchet is what makes the
target reachable: each consolidation lowers it and it can never drift back.

Compose is parsed with a YAML loader, never grep: `profiles`, anchors and
merge keys all change which services are actually in the production profile.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Seams so the logic is testable against synthetic compose trees, matching the
# PREFLIGHT_* convention in scripts/preflight-env.sh. Unset in normal use.
REPO = Path(os.environ.get("CONTAINER_BUDGET_ROOT") or Path(__file__).resolve().parent.parent)
BASELINE = Path(
    os.environ.get("CONTAINER_BUDGET_FILE") or REPO / "infrastructure" / "container-budget.json"
)
COMPOSE_GLOB = "domains/*/compose.yml"
PRODUCTION = "production"

_MIB = {"B": 1 / (1024 * 1024), "KIB": 1 / 1024, "MIB": 1.0, "GIB": 1024.0}


def production_services() -> dict[str, str]:
    """Map service name -> compose file, for every service in the production profile.

    A service with no `profiles` key runs in every profile, so it counts.
    """
    import yaml

    found: dict[str, str] = {}
    for path in sorted(REPO.glob(COMPOSE_GLOB)):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for name, body in (doc.get("services") or {}).items():
            profiles = (body or {}).get("profiles")
            if profiles is None or PRODUCTION in profiles:
                found[name] = path.relative_to(REPO).as_posix()
    return found


def _mib(usage: str) -> float:
    """Parse the used half of docker stats' `123.4MiB / 1.5GiB` into MiB."""
    raw = usage.split("/")[0].strip()
    digits = "".join(c for c in raw if c.isdigit() or c == ".")
    unit = raw[len(digits) :].strip().upper()
    if not digits or unit not in _MIB:
        raise ValueError(f"cannot parse docker stats memory value: {usage!r}")
    return float(digits) * _MIB[unit]


def measure_memory() -> dict[str, Any]:
    """Total resident memory of the running HomeIQ containers, via docker stats."""
    proc = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}"],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    total, names = 0.0, []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        name, _, usage = line.partition("\t")
        if name.startswith("agentforge"):  # a separate stack, not HomeIQ's budget
            continue
        total += _mib(usage)
        names.append(name)
    return {"memory_mib": round(total), "containers": len(names)}


def check(baseline: dict[str, Any]) -> int:
    services = production_services()
    ceiling = baseline["ceiling"]
    recorded = set(baseline["measured"]["services"])
    target = baseline["target"]
    count = len(services)
    failures: list[str] = []

    if count > ceiling["services"]:
        added = sorted(set(services) - recorded)
        failures.append(
            f"production container count {count} exceeds the ceiling of "
            f"{ceiling['services']}. Services added since the baseline:\n"
            + "\n".join(f"    {n}  ({services[n]})" for n in added)
            + "\n  Consolidate, or raise the ceiling deliberately with "
            "--update-baseline and say why in the commit message."
        )
    elif count < ceiling["services"]:
        removed = sorted(recorded - set(services))
        failures.append(
            f"production container count {count} is BELOW the ceiling of "
            f"{ceiling['services']} — the ratchet is stale and would let those "
            "slots refill silently. Services removed since the baseline:\n"
            + "\n".join(f"    {n}" for n in removed)
            + "\n  Run --update-baseline to lock in the reduction."
        )

    measured_mem = baseline["measured"]["memory_mib"]
    if measured_mem > ceiling["memory_mib"]:
        failures.append(
            f"recorded memory footprint {measured_mem} MiB exceeds the ceiling of "
            f"{ceiling['memory_mib']} MiB."
        )

    for line in failures:
        print(f"FAIL: {line}", file=sys.stderr)
    if failures:
        return 1

    print(
        f"OK: {count} production services (ceiling {ceiling['services']}, "
        f"target {target['services']}); {measured_mem} MiB recorded "
        f"(ceiling {ceiling['memory_mib']}, target {target['memory_mib']}), "
        f"measured {baseline['measured']['at']}."
    )
    gap = count - target["services"]
    if gap > 0:
        print(f"     {gap} services above the {target['ref']} target of {target['services']}.")
    return 0


def update(baseline: dict[str, Any], *, skip_memory: bool) -> int:
    services = production_services()
    baseline["measured"]["services"] = sorted(services)
    baseline["ceiling"]["services"] = len(services)
    if skip_memory:
        print("memory not re-measured (--no-memory); keeping the recorded figure.")
    else:
        stats = measure_memory()
        baseline["measured"].update(stats)
        baseline["ceiling"]["memory_mib"] = stats["memory_mib"]
        print(f"measured {stats['memory_mib']} MiB across {stats['containers']} containers.")
    baseline["measured"]["at"] = (
        subprocess.run(
            ["git", "log", "-1", "--format=%cs"], capture_output=True, text=True, check=True
        ).stdout.strip()
        or baseline["measured"]["at"]
    )
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {BASELINE.relative_to(REPO)}: ceiling now {len(services)} services.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="re-record the ceiling from the current compose files and running stack",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="with --update-baseline, skip the docker stats measurement",
    )
    args = parser.parse_args()

    if not BASELINE.exists():
        print(f"baseline not found at {BASELINE}", file=sys.stderr)
        return 1
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if args.update_baseline:
        return update(baseline, skip_memory=args.no_memory)
    return check(baseline)


if __name__ == "__main__":
    sys.exit(main())
