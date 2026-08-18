#!/usr/bin/env python3
"""Diff every published gene and workflow against what AgentForge actually serves.

TAP-5191. The publish CLI's ``unchanged`` verdict comes from a local hash cache
(``.tapps-mcp/af-publish-cache.json``), so a corrupted, stale, or hand-edited
cache reports a clean publish over live drift. This script never consults the
cache: it reads the repo, reads ``GET /projects/<slug>/agents/<name>``, and
compares the two. That is the only comparison that can fail when the cache is
wrong, which is the whole reason the issue asks for it.

Content normalisation is imported from the integration kit rather than
reimplemented. ``af_publish.py`` PUTs ``artifact.content`` — the include-resolved
text — so anything that resolves includes differently here would report drift
that publishing cannot fix. One implementation, imported, not copied.

Usage:
    AF_KIT_ROOT=/path/to/agentforge-integration-kit \\
      uv run --with httpx --with pyyaml python scripts/af_live_diff.py --slug homeiq

Exit status is 0 only when every repo artifact matches live byte for byte.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from af_kit import KitUnavailableError, load_api_key, resolve_kit_root

DEFAULT_BASE_URL = "http://localhost:8010"
DEFAULT_SLUG = "homeiq"
DEFAULT_LAYOUT = "scout"


def load_kit(kit_root: Path) -> Any:
    """Import the kit's discovery module so normalisation stays single-sourced."""
    scripts_dir = str(kit_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import af_publish_discover  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on kit layout
        msg = f"integration kit at {kit_root} is not importable: {exc}"
        raise KitUnavailableError(msg) from exc
    return af_publish_discover


def digest(content: str) -> str:
    """Return the ``sha256:<hex>`` form AgentForge reports in ``content_sha256``."""
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split YAML frontmatter from body so drift can be attributed to one of them.

    Content with no leading ``---`` fence is reported as all body, which is the
    honest answer rather than a guess at where a header would have started.
    """
    if not content.startswith("---"):
        return "", content
    # maxsplit=1, not 2: a body containing its own `---` fence (a markdown rule,
    # a nested example) would otherwise be truncated at the second one and its
    # drift misreported as unclassified.
    head, sep, rest = content.removeprefix("---").partition("\n---")
    if not sep:
        return "", content
    return head, rest


@dataclass
class Comparison:
    """One repo artifact measured against its live counterpart."""

    kind: str
    name: str
    verdict: str
    repo_digest: str
    live_digest: str
    live_version: str
    detail: str

    @property
    def is_drift(self) -> bool:
        """True when this artifact is not byte-identical to what AF serves."""
        return self.verdict != "MATCH"


def classify(repo_content: str, live: dict[str, Any] | None, kind: str, name: str) -> Comparison:
    """Compare one artifact, attributing any drift to frontmatter and/or body."""
    repo_sha = digest(repo_content)
    if live is None:
        return Comparison(kind, name, "MISSING_LIVE", repo_sha, "-", "-", "absent on AgentForge")

    live_content = live.get("content", "")
    live_sha = live.get("content_sha256") or live.get("content_hash") or digest(live_content)
    version = str(live.get("version", "?"))
    if live_sha == repo_sha:
        return Comparison(kind, name, "MATCH", repo_sha, live_sha, version, "")

    repo_fm, repo_body = split_frontmatter(repo_content)
    live_fm, live_body = split_frontmatter(live_content)
    drifted = [
        label
        for label, same in (("frontmatter", repo_fm == live_fm), ("body", repo_body == live_body))
        if not same
    ]
    delta = len(repo_content) - len(live_content)
    detail = f"{'+'.join(drifted) or 'unclassified'} differs ({delta:+d} bytes)"
    return Comparison(kind, name, "DRIFT", repo_sha, live_sha, version, detail)


def fetch_live(client: httpx.Client, slug: str, kind: str, name: str) -> dict[str, Any] | None:
    """GET one live artifact; ``None`` means AgentForge has never seen it."""
    resp = client.get(f"/projects/{slug}/{kind}/{name}")
    if resp.status_code == httpx.codes.NOT_FOUND:
        return None
    resp.raise_for_status()
    return resp.json()


def render_diff(name: str, repo_content: str, live_content: str, limit: int) -> str:
    """Return a truncated unified diff, live as the 'before' side."""
    lines = list(
        difflib.unified_diff(
            live_content.splitlines(),
            repo_content.splitlines(),
            fromfile=f"live/{name}",
            tofile=f"repo/{name}",
            lineterm="",
            n=1,
        )
    )
    shown = lines[:limit]
    if len(lines) > limit:
        shown.append(f"... {len(lines) - limit} more diff lines")
    return "\n".join(shown)


def render_table(results: list[Comparison]) -> str:
    """Render the per-artifact table the issue's acceptance asks to be pasted."""
    width = max((len(r.name) for r in results), default=4)
    header = f"{'ARTIFACT':<{width}}  {'KIND':<9}  {'LIVE':<5}  {'VERDICT':<12}  DETAIL"
    rows = [
        f"{r.name:<{width}}  {r.kind:<9}  {r.live_version:<5}  {r.verdict:<12}  {r.detail}"
        for r in results
    ]
    return "\n".join([header, "-" * len(header), *rows])


def build_client(base_url: str, api_key: str) -> httpx.Client:
    """Return a bearer-authenticated client against the AgentForge API."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


def compare_all(
    client: httpx.Client, slug: str, artifacts: list[tuple[str, str, str]]
) -> list[Comparison]:
    """Compare every discovered artifact against live, preserving publish order."""
    results = []
    for kind, name, content in artifacts:
        results.append(classify(content, fetch_live(client, slug, kind, name), kind, name))
    return results


def discover(kit: Any, repo_root: Path, slug: str, layout: str) -> list[tuple[str, str, str]]:
    """Return ``(kind, name, published_content)`` for every repo artifact."""
    agents, workflows = kit.discover_artifacts(repo_root, slug, layout)
    return [(a.kind, a.name, a.content) for a in (*agents, *workflows)]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--layout", default=DEFAULT_LAYOUT, choices=("scout", "nlt"))
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--base-url", default=os.environ.get("AGENTFORGE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=load_api_key())
    parser.add_argument("--kit-root", default=None)
    parser.add_argument(
        "--show-diff",
        type=int,
        default=0,
        metavar="N",
        help="print up to N unified-diff lines for each drifted artifact",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print the repo-vs-live table; exit non-zero on any drift."""
    args = parse_args(argv)
    try:
        kit_root = resolve_kit_root(args.kit_root)
        kit = load_kit(kit_root)
    except KitUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    artifacts = discover(kit, args.repo_root.resolve(), args.slug, args.layout)
    print(f"==> af-live-diff slug={args.slug} base={args.base_url} kit={kit_root}")
    print(f"    comparing {len(artifacts)} repo artifact(s) against live\n")
    if not artifacts:
        # "0/0 match, 0 drifted" would exit 0 and read as a clean bill of health.
        # Discovery finding nothing means a renamed directory or a wrong
        # --layout, never a repo that is genuinely in sync.
        print(
            f"error: discovered no artifacts under {args.repo_root} for slug={args.slug} "
            f"layout={args.layout} — check the path and layout, not the drift",
            file=sys.stderr,
        )
        return 2

    with build_client(args.base_url, args.api_key) as client:
        results = compare_all(client, args.slug, artifacts)

    print(render_table(results))
    drifted = [r for r in results if r.is_drift]

    if args.show_diff and drifted:
        live_by_name = {}
        with build_client(args.base_url, args.api_key) as client:
            for r in drifted:
                live = fetch_live(client, args.slug, r.kind, r.name)
                live_by_name[r.name] = (live or {}).get("content", "")
        repo_by_name = {name: content for _, name, content in artifacts}
        for r in drifted:
            print(f"\n--- diff {r.name} ---")
            print(render_diff(r.name, repo_by_name[r.name], live_by_name[r.name], args.show_diff))

    matched = len(results) - len(drifted)
    print(f"\n==> {matched}/{len(results)} match live; {len(drifted)} drifted")
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
