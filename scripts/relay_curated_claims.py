#!/usr/bin/env python3
"""Relay a curator's approved claims into the device-knowledge store.

The `device-kb-enrich` workflow ends at `hiq-device-kb-curator`, and that gene is
the approval authority: its `approved` array is the complete set of claim bodies
that may be written. This script is the transport between the two and **adds no
judgement of its own** — it does not filter, reshape, infer, default, or reorder.
If a payload would be refused by the server, it is refused; that refusal is
reported, not worked around.

That restraint is the point rather than laziness. The curator holds no HTTP
capability at all (`mcp_servers: []`, `allowed_tools: ''`), so the single write
path exists as an *approval* chokepoint, not a network one — device-intelligence
publishes 8028 on 0.0.0.0 and any container reaches it over the host gateway. A
relay that "helpfully" filled in a missing `source_url` or downgraded an
evidence class would be inventing provenance nobody asserted, which is exactly
what the provenance ADR exists to prevent.

Usage:
    python3 scripts/relay_curated_claims.py approved.json [--dry-run]

`approved.json` is either a curator `output` object (with an `approved` key) or a
bare array of claim bodies.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://localhost:8028"
CLAIMS_PATH = "/api/device-knowledge/claims"


def _api_key() -> str:
    """The device-intelligence API key, from the env or the running container."""
    key = os.environ.get("DEVICE_INTELLIGENCE_API_KEY")
    if key:
        return key
    return subprocess.check_output(
        ["docker", "exec", "homeiq-device-intelligence", "printenv", "API_KEY"],
        text=True,
    ).strip()


def _load_approved(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        approved = payload.get("approved")
        if approved is None:
            raise SystemExit(f"{path}: object has no 'approved' key")
        payload = approved
    if not isinstance(payload, list):
        raise SystemExit(f"{path}: expected a list of claim bodies")
    return payload


def _post(base_url: str, key: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        base_url.rstrip("/") + CLAIMS_PATH,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            detail = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            detail = {"raw": raw.decode("utf-8", "replace")}
        return exc.code, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approved_json")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be posted, verbatim, without writing.",
    )
    args = parser.parse_args()

    approved = _load_approved(args.approved_json)
    if not approved:
        print("nothing approved — nothing to relay")
        return 0

    if args.dry_run:
        for body in approved:
            print(json.dumps(body, sort_keys=True))
        print(f"\n{len(approved)} claim(s) would be posted, verbatim")
        return 0

    key = _api_key()
    written = 0
    refused: list[tuple[dict[str, Any], int, dict[str, Any]]] = []

    for body in approved:
        status, response = _post(args.base_url, key, body)
        if status in (200, 201):
            written += 1
            marker = "" if response.get("accepted") else "  (outranked by a stronger claim)"
            print(f"  ok   {body.get('fact_key')}{marker}")
        else:
            refused.append((body, status, response))
            print(f"  HTTP {status}  {body.get('fact_key')}")

    print(f"\nwritten: {written}/{len(approved)}")

    if refused:
        # A refusal is a finding, not a thing to route around. Printed in full so
        # the curator's payload can be corrected at the source.
        print(f"\n{len(refused)} refused by the server:")
        for body, status, response in refused:
            print(f"\n  fact_key       : {body.get('fact_key')}")
            print(f"  evidence_class : {body.get('evidence_class')}")
            print(f"  HTTP           : {status}")
            print(f"  detail         : {json.dumps(response.get('detail', response))}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
