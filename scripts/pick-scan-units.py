#!/usr/bin/env python3
"""Pick scan units from the manifest based on priority-weighted scoring.

Usage:
    python3 scripts/pick-scan-units.py [--manifest PATH] [--units LIST] [--all] [--max N]

Output: one line per selected unit: id|path|name|scan_hint
"""
import argparse
import json
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Pick scan units by priority score")
    parser.add_argument("--manifest", default="docs/scan-manifest.json")
    parser.add_argument("--units", default="", help="Comma-separated unit IDs")
    parser.add_argument("--all", action="store_true", help="Select all units")
    parser.add_argument("--max", type=int, default=3, help="Max units to select")
    parser.add_argument("--target-unit", default="", help="Select a specific unit")
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    requested = [u.strip() for u in args.units.split(",") if u.strip()]
    now = datetime.now(timezone.utc)
    scored = []

    for unit in manifest["units"]:
        if requested and unit["id"] not in requested:
            continue
        if args.target_unit and unit["id"] != args.target_unit:
            continue

        if unit["last_scanned"]:
            last = datetime.fromisoformat(unit["last_scanned"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            days = max((now - last).total_seconds() / 86400, 0.1)
        else:
            days = 365

        bug_boost = 1 + unit["total_bugs_found"] / 5
        fp_rate = unit["false_positives"] / max(unit["total_bugs_found"], 1)
        fp_penalty = max(1 - fp_rate * 0.3, 0.5)
        score = unit["priority_weight"] * days * bug_boost * fp_penalty

        scored.append((score, unit))

    scored.sort(key=lambda x: x[0], reverse=True)

    if requested or args.target_unit:
        selected = [u for _, u in scored]
    elif args.all:
        selected = [u for _, u in scored]
    else:
        selected = [u for _, u in scored[: args.max]]

    if not selected:
        print("ERROR: No matching units found", file=sys.stderr)
        sys.exit(1)

    for u in selected:
        print(f"{u['id']}|{u['path']}|{u['name']}|{u['scan_hint']}")


if __name__ == "__main__":
    main()
