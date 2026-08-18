"""Refresh the committed snapshot of AgentForge's capabilities manifest.

`kit_rules.py` used to hand-mirror `NodeSpec.kind` from `backend/workflows/models.py`
— an *internal* AF module this repo cannot import and does not track. It drifted
twice. The second drift was measured: `kind: sql` is a real node kind the platform
accepts (`PUT` returned 201), and the validator rejected it with a fabricated
"publish would 422".

AF publishes the truth at `GET /capabilities/manifest`, so the constants now come
from a committed copy of that response instead of from memory of another repo's
source. This script is the only thing that writes it.

## Why a committed snapshot rather than a live fetch

`scripts/validate.py` must stay offline and deterministic. A validator that phones
home fails differently depending on whether AF happens to be up, and a reviewer
reading the diff cannot see what it validated against. Committing the response
makes the platform contract a reviewable artifact and the refresh an explicit,
dated step — the same reason skill packs travel as generated input defaults rather
than being read at runtime.

Run after every AF image bump, alongside the `af-kit-upgrade` flow:

    make af-capabilities        # or: python3 scripts/capabilities_snapshot.py

`--check` compares without writing, so a stale snapshot is visible without one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from kit_rules import CAPABILITIES_SNAPSHOT

DEFAULT_URL = os.environ.get("AGENTFORGE_URL", "http://localhost:8010")
ENDPOINT = "/capabilities/manifest"
TIMEOUT_SECONDS = 15
ALLOWED_SCHEMES = frozenset({"http", "https"})


def fetch(base_url: str, token: str | None) -> dict[str, Any]:
    """GET the live manifest. Raises rather than returning a partial snapshot."""
    url = base_url.rstrip("/") + ENDPOINT
    # `--url` and `AGENTFORGE_URL` both reach here, and urlopen honours `file:`
    # and any registered custom scheme. A `file:` URL would happily "fetch" a
    # local JSON blob and write it out as the platform's own answer, which is the
    # one thing this file exists to stop being.
    if urllib.parse.urlparse(url).scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"refusing non-HTTP AF URL {url!r} — expected one of {sorted(ALLOWED_SCHEMES)}")
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or "workflow" not in payload:
        raise ValueError(f"unexpected manifest shape from {base_url}{ENDPOINT}: {sorted(payload)}")
    return payload


def snapshot(manifest: dict[str, Any], *, source: str, today: date | None = None) -> dict[str, Any]:
    """Wrap the verbatim response in the provenance a reader needs to trust it.

    `af_version` is lifted to the top level because it is the question every reader
    of this file actually has — "which platform said this?" — and burying it one
    level down is how the previous constants were read as timeless.
    """
    return {
        "af_version": manifest.get("version"),
        "fetched_at": (today or date.today()).isoformat(),
        "source": source + ENDPOINT,
        "manifest": manifest,
    }


def render(doc: dict[str, Any]) -> str:
    """Stable text for the committed file — sorted, so a re-run diffs cleanly."""
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="AF base URL")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift against the committed snapshot and exit non-zero; write nothing",
    )
    args = parser.parse_args(argv)

    try:
        manifest = fetch(args.url, os.environ.get("AGENTFORGE_API_KEY"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cannot read {args.url}{ENDPOINT}: {exc}", file=sys.stderr)
        return 2

    doc = snapshot(manifest, source=args.url.rstrip("/"))
    path = Path(CAPABILITIES_SNAPSHOT)
    committed = path.read_text(encoding="utf-8") if path.is_file() else ""

    # `fetched_at` moves on every run and is not drift. Compare the payload only,
    # or `--check` would report a stale snapshot every day regardless of AF.
    live_manifest = json.dumps(doc["manifest"], sort_keys=True)
    old_manifest = json.dumps(json.loads(committed)["manifest"], sort_keys=True) if committed else ""

    if live_manifest == old_manifest:
        print(f"capabilities manifest matches AF {doc['af_version']}", file=sys.stderr)
        return 0

    if args.check:
        print(
            f"STALE {path.name}: committed snapshot disagrees with AF "
            f"{doc['af_version']} at {args.url} — run scripts/capabilities_snapshot.py",
            file=sys.stderr,
        )
        return 1

    path.write_text(render(doc), encoding="utf-8")
    print(f"wrote {path} from AF {doc['af_version']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
