#!/usr/bin/env python3
"""Assert the fields the platform historically dropped survive a publish (TAP-5318).

The epic's hard-won rule is "publish via a lane that preserves ``mcp_servers``,
``risk_level``, ``guardrails`` and ``completion_criteria``" — the old global
agents endpoint silently discarded them. This check does not trust the publish
path's own report: it reads ``GET /projects/<slug>/agents/<name>`` (the stored
artifact), parses the served frontmatter, and compares those four fields against
the repo's authored frontmatter for every agent in the kit.

It also pins the AF version: ``agentforge/capabilities-manifest.json`` records
the version the kit was validated against; a live ``/health`` that reports a
different version fails the check until the manifest is refreshed and the kit
revalidated (offline validation runs against that snapshot).

Exit 0 only when every agent round-trips and the version pin holds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from af_kit import load_api_key

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agentforge" / "projects" / "homeiq" / "agents"
MANIFEST = ROOT / "agentforge" / "capabilities-manifest.json"
DEFAULT_BASE_URL = "http://localhost:8010"
ROUND_TRIP_FIELDS = ("mcp_servers", "risk_level", "guardrails", "completion_criteria")


def frontmatter(content: str) -> dict[str, Any]:
    if not content.startswith("---"):
        return {}
    try:
        _, fm, _ = content.split("---", 2)
    except ValueError:
        return {}
    loaded = yaml.safe_load(fm)
    return loaded if isinstance(loaded, dict) else {}


def normalise(value: Any) -> Any:
    """Compare semantically: YAML round-trips may reorder nothing but re-quote strings."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def check_agent(client: httpx.Client, slug: str, path: Path) -> list[str]:
    name = path.stem
    authored = frontmatter(path.read_text(encoding="utf-8"))
    response = client.get(f"/projects/{slug}/agents/{name}")
    if response.status_code == 404:
        return [f"{name}: not published (404) — publish before running the round-trip check"]
    response.raise_for_status()
    served = frontmatter(response.json().get("content", ""))
    problems = []
    for field in ROUND_TRIP_FIELDS:
        if field not in authored:
            continue
        if field not in served:
            problems.append(f"{name}: served artifact DROPPED {field!r}")
        elif normalise(served[field]) != normalise(authored[field]):
            problems.append(f"{name}: {field!r} differs between repo and served artifact")
    return problems


def check_version_pin(client: httpx.Client) -> list[str]:
    pinned = json.loads(MANIFEST.read_text(encoding="utf-8")).get("af_version", "")
    live = client.get("/health").json().get("version", "")
    if pinned and live and pinned != live:
        return [
            f"AF version drift: kit validated against {pinned}, live instance is {live} — "
            "refresh agentforge/capabilities-manifest.json and revalidate the kit"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", default="homeiq")
    parser.add_argument("--base-url", default=os.environ.get("AGENTFORGE_URL", DEFAULT_BASE_URL))
    args = parser.parse_args(argv)

    key = load_api_key(ROOT)
    if not key:
        print("no AGENTFORGE_API_KEY in the environment or .env", file=sys.stderr)
        return 2
    client = httpx.Client(
        base_url=args.base_url, headers={"Authorization": f"Bearer {key}"}, timeout=60
    )
    agents = sorted(AGENTS_DIR.glob("*.md"))
    problems: list[str] = []
    for path in agents:
        problems.extend(check_agent(client, args.slug, path))
    problems.extend(check_version_pin(client))
    for problem in problems:
        print(f"FAIL {problem}")
    if not problems:
        print(
            f"round-trip OK: {len(agents)} agent(s) preserve {', '.join(ROUND_TRIP_FIELDS)}; version pin holds"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
