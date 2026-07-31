#!/usr/bin/env python3
"""Audit a HomeIQ service through the AgentForge `homeiq-service-audit` workflow.

AgentForge runs in its own container and cannot see the HomeIQ working tree, so
source has to be collected here and passed in as a workflow input. This is the
consumer half of the pipeline+gateway split described in docs/AF-INTEGRATION.md:
file access and exit codes live in HomeIQ, cognition lives in AgentForge.

Exit codes: 0 = all ship, 1 = any block, 2 = an audit could not run.

    python scripts/af_audit_service.py domains/core-platform/data-api
    python scripts/af_audit_service.py --changed-only origin/master --max-spend 2.00

Runs cost real money (~$0.03-0.21 per service observed), so --max-services and
--max-spend are on by default and a capped run says what it skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = "homeiq-service-audit"
DEFAULT_BASE_URL = "http://localhost:8010"
DEFAULT_SLUG = "homeiq"

EXIT_SHIP = 0
EXIT_BLOCK = 1
EXIT_ERROR = 2


def resolve_api_key() -> str:
    """Return the afp_* project bearer, preferring .env over the environment.

    Deliberately the same precedence the AgentForge kit uses for MCP: a repo
    .env beats a machine-global export. A stale truncated AGENTFORGE_API_KEY in
    a shell profile is a real and hard-to-spot failure — it produces a HTTP 401
    "key-invalid-or-revoked" that looks like a server problem.
    """
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        match = re.search(
            r"^AGENTFORGE_API_KEY\s*=\s*[\"']?([^\"'\s]+)",
            env_file.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)

    key = os.environ.get("AGENTFORGE_API_KEY", "")
    if not key:
        raise SystemExit(
            "No AGENTFORGE_API_KEY found in .env or environment. "
            "See docs/AF-INTEGRATION.md § Credential custody."
        )
    return key


def collect_source(service_dir: Path, pattern: str, max_bytes: int) -> tuple[str, int]:
    """Concatenate matching files under service_dir into one delimited blob.

    Returns the blob and the number of files included. Files are added whole in
    sorted order until max_bytes would be exceeded; a partial file would produce
    misleading line numbers in the audit, so files are never truncated.
    """
    parts: list[str] = []
    total = 0
    included = 0

    for path in sorted(service_dir.rglob(pattern)):
        if not path.is_file():
            continue
        if any(seg in {"node_modules", ".venv", "__pycache__", ".git"} for seg in path.parts):
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(service_dir)
        chunk = f"=== FILE: {rel} ===\n{text}\n"
        if total + len(chunk) > max_bytes:
            print(f"  [budget] stopping at {included} file(s); {rel} would exceed --max-bytes", file=sys.stderr)
            break
        parts.append(chunk)
        total += len(chunk)
        included += 1

    return "".join(parts), included


def require_http_url(url: str) -> str:
    """Reject non-HTTP(S) URLs before they reach urlopen.

    urlopen honours file:/ and other schemes, so an unvalidated --base-url could
    be pointed at the local filesystem (bandit B310). AgentForge is only ever
    reachable over http/https.
    """
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in {"http", "https"}:
        raise SystemExit(f"Refusing non-HTTP URL (scheme {scheme!r}): {url}")
    return url


def post_json(url: str, payload: dict, key: str, timeout: float) -> dict:
    require_http_url(url)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:400]
        raise SystemExit(f"AgentForge returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach AgentForge at {url}: {exc.reason}") from exc


def get_json(url: str, key: str, timeout: float) -> dict:
    require_http_url(url)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


# RunState values that mean the run is still progressing. Everything else is
# terminal. GET /workflows/runs/{id} nests these under a "run" key; the
# /outputs endpoint reports "state" at the top level.
NON_TERMINAL_STATES = {"pending", "running"}


def wait_for_run(base_url: str, run_id: str, key: str, timeout_s: float) -> tuple[str, dict, float]:
    """Poll until terminal, then return (state, node_outputs, cost_usd)."""
    deadline = time.monotonic() + timeout_s
    run_url = f"{base_url}/workflows/runs/{run_id}"

    while time.monotonic() < deadline:
        state = (get_json(run_url, key, timeout=30).get("run") or {}).get("state", "")
        if state not in NON_TERMINAL_STATES:
            outputs = get_json(f"{run_url}/outputs", key, timeout=30)
            return state, outputs.get("node_outputs") or {}, float(outputs.get("total_cost_usd") or 0.0)
        time.sleep(5)

    raise SystemExit(f"Run {run_id} did not reach a terminal state within {timeout_s:.0f}s")


def discover_changed_services(base_ref: str) -> list[str]:
    """Return service dirs touched since base_ref, as domains/<group>/<service>.

    A "service" is the two-level directory under domains/ that HomeIQ organises
    code by; anything shallower (a stray file directly under a group) is skipped.
    """
    git = shutil.which("git")
    if git is None:
        raise SystemExit("--changed-only needs git on PATH")

    # Fixed argv, absolute binary, shell=False: base_ref cannot escape into a shell.
    completed = subprocess.run(
        [git, "diff", "--name-only", base_ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"git diff against {base_ref!r} failed: {completed.stderr.strip()}")

    services: set[str] = set()
    for line in completed.stdout.splitlines():
        parts = Path(line).parts
        if len(parts) >= 3 and parts[0] == "domains":
            services.add(str(Path(parts[0], parts[1], parts[2])))
    return sorted(services)


def report(decision_output: dict, audit_output: dict) -> None:
    findings = audit_output.get("findings") or []
    print(f"\nfindings: {len(findings)}")
    for finding in findings:
        print(
            f"  [{finding.get('severity', '?'):>6}] {finding.get('location', '?')}"
            f"\n           {finding.get('defect', '')}"
        )

    decision = decision_output.get("decision", "?")
    print(f"\ndecision: {decision.upper()}")
    print(f"reason:   {decision_output.get('reason', '')}")
    for blocker in decision_output.get("blocking_findings") or []:
        print(f"  blocks: {blocker}")


def audit_one(service_path: str, key: str, args: argparse.Namespace) -> dict:
    """Audit one service. Returns a result record; never raises for audit outcomes."""
    base_url = args.base_url.rstrip("/")
    service_dir = (REPO_ROOT / service_path).resolve()
    record: dict = {"service_path": service_path, "outcome": "error", "cost_usd": 0.0}

    if not service_dir.is_dir():
        record["detail"] = "not a directory"
        return record

    source, count = collect_source(service_dir, args.pattern, args.max_bytes)
    if not count:
        record["detail"] = f"no files matching {args.pattern!r}"
        return record
    print(f"  collected {count} file(s), {len(source)} chars")

    payload = {"inputs": {"service_path": service_path, "source": source}}

    if args.dry_run:
        run = post_json(
            f"{base_url}/projects/{args.slug}/workflows/{WORKFLOW}/run?mode=dry_run", payload, key, timeout=120
        )
        record["outcome"] = "ship" if run.get("state") == "dry_run" else "error"
        record["detail"] = f"dry_run state={run.get('state')}"
        return record

    kickoff = post_json(
        f"{base_url}/projects/{args.slug}/workflows/{WORKFLOW}/run?kickoff=async", payload, key, timeout=120
    )
    run_id = kickoff.get("run_id")
    if not run_id:
        record["detail"] = f"no run_id in kickoff: {kickoff}"
        return record
    print(f"  run {run_id} started; polling…")

    state, outputs, cost = wait_for_run(base_url, run_id, key, args.timeout)
    decision = outputs.get("decide") or {}
    audit = outputs.get("audit") or {}
    record.update({"run_id": run_id, "cost_usd": cost, "audit": audit, "decision": decision})

    if state != "complete" or not decision:
        record["detail"] = f"run ended in state={state!r} without a decision"
        return record
    if decision.get("assessment_status") == "blocked":
        record["detail"] = decision.get("reason", "audit reported blocked")
        return record

    report(decision, audit)
    record["outcome"] = "block" if decision.get("decision") == "block" else "ship"
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("service_path", nargs="*", help="Service directories, e.g. domains/core-platform/data-api")
    parser.add_argument("--changed-only", metavar="BASE_REF", help="Audit only services touched since BASE_REF")
    parser.add_argument("--max-services", type=int, default=10, help="Cap services per run (default: 10)")
    parser.add_argument("--max-spend", type=float, default=5.0, help="Stop once USD spent exceeds this (default: 5.0)")
    parser.add_argument("--pattern", default="*.py", help="Glob for files to collect (default: *.py)")
    parser.add_argument("--max-bytes", type=int, default=120_000, help="Source budget per service (default: 120000)")
    parser.add_argument("--base-url", default=os.environ.get("AGENTFORGE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--slug", default=os.environ.get("AGENTFORGE_PROJECT_SLUG", DEFAULT_SLUG))
    parser.add_argument("--timeout", type=float, default=600.0, help="Seconds to wait per run (default: 600)")
    parser.add_argument("--json", dest="json_out", help="Write all results to this path")
    parser.add_argument("--dry-run", action="store_true", help="Validate the DAG without LLM cost")
    return parser


def resolve_targets(args: argparse.Namespace) -> list[str]:
    targets = discover_changed_services(args.changed_only) if args.changed_only else list(args.service_path)
    if args.changed_only and args.service_path:
        print("note: --changed-only supersedes the positional service paths", file=sys.stderr)

    if len(targets) > args.max_services:
        dropped = targets[args.max_services:]
        print(
            f"note: capping at --max-services={args.max_services}; "
            f"skipping {len(dropped)}: {', '.join(dropped)}",
            file=sys.stderr,
        )
        targets = targets[: args.max_services]
    return targets


def main() -> int:
    args = build_parser().parse_args()

    targets = resolve_targets(args)
    if not targets:
        print("No services to audit.", file=sys.stderr)
        return EXIT_ERROR

    key = resolve_api_key()
    results: list[dict] = []
    spent = 0.0

    for index, service_path in enumerate(targets, start=1):
        if spent >= args.max_spend:
            print(f"\nstopping: spent ${spent:.2f} >= --max-spend ${args.max_spend:.2f}", file=sys.stderr)
            print(f"  {len(targets) - index + 1} service(s) not audited", file=sys.stderr)
            break
        print(f"\n[{index}/{len(targets)}] {service_path}")
        record = audit_one(service_path, key, args)
        spent += record["cost_usd"]
        results.append(record)

    print(f"\n{'=' * 60}\nsummary — {len(results)} audited, ${spent:.2f} spent")
    for record in results:
        detail = f"  ({record['detail']})" if record.get("detail") else ""
        print(f"  {record['outcome']:>5}  {record['service_path']}{detail}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"total_cost_usd": spent, "results": results}, indent=2), encoding="utf-8"
        )
        print(f"\nwrote {args.json_out}")

    if any(r["outcome"] == "error" for r in results):
        return EXIT_ERROR
    return EXIT_BLOCK if any(r["outcome"] == "block" for r in results) else EXIT_SHIP


if __name__ == "__main__":
    sys.exit(main())
