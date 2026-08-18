#!/usr/bin/env python3
"""Prove each AgentForge lane with a probe, not with a status field (TAP-5679).

On 2026-08-06 a six-hour test sweep spent its preflight reading
``GET /health``, which reported ``llm_auth.oauth_cli.ready: true``,
``session_probe: "logged_in"`` and ``bare_invoke_ready: true``. Every actual
invocation returned ``401 OAuth access token has been revoked``. Two genes, two
models, zero turns, zero cost. The same payload carried
``canary_probe: "canary_disabled"``, which is the explanation: readiness was
inferred from a credentials file existing and a session record being present,
never from a model call. The run committed to a 271-trial eval plan against a
platform that could not answer a single prompt.

So this script refuses to report a lane green on anything but that lane's own
evidence:

===========  =========================================================
lane         what counts as proof
===========  =========================================================
reachable    ``GET /health`` returns ``status: ok`` — the *only* claim
             that endpoint is entitled to make
auth         an authenticated project-scoped GET returns 200. Health
             passing does not prove the bearer; the endpoint is open
llm          one real golden-case run reaches a per-assertion verdict.
             A run that errors before assertions is a red lane no
             matter what any status field says
===========  =========================================================

## The llm lane costs one model call, and that is the point

There is no free probe for "can this platform answer a prompt". A free one
would be another inference from configuration — exactly the thing that failed.
So the check spends one trial on the cheapest declared golden case and reads
the platform's own per-assertion body. Roughly a cent, once, before a plan that
would spend far more.

``--skip-llm`` exists for callers that only need the transport lanes (a publish
parity check, say). It prints the lane as ``skipped``, never as green: a lane
nobody probed is not a lane that works.

Usage:
    uv run --with httpx python scripts/af_preflight.py
    uv run --with httpx python scripts/af_preflight.py --skip-llm

Exit 0 only when every probed lane is green.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
from af_kit import load_api_key

DEFAULT_BASE_URL = "http://localhost:8010"
DEFAULT_SLUG = "homeiq"
# The cheapest agent that declares a golden case: one case, one trial.
DEFAULT_PROBE_AGENT = "hiq-summarize"
POLL_INTERVAL_S = 2.0
POLL_TIMEOUT_S = 180.0

GREEN = "green"
RED = "red"
SKIPPED = "skipped"


def probe_reachable(client: httpx.Client) -> tuple[str, str]:
    """`GET /health` — process up. Deliberately reads nothing else from it."""
    try:
        resp = client.get("/health", timeout=10.0)
    except httpx.HTTPError as exc:
        return RED, f"unreachable: {exc}"
    if resp.status_code != 200:
        return RED, f"HTTP {resp.status_code}"
    status = resp.json().get("status")
    if status != "ok":
        return RED, f"status: {status!r}"
    return GREEN, f"status ok, version {resp.json().get('version', '?')}"


def probe_auth(client: httpx.Client, slug: str, api_key: str) -> tuple[str, str]:
    """One authenticated project-scoped GET. Health passing does not prove this."""
    if not api_key:
        return RED, "no AGENTFORGE_API_KEY in the environment or .env"
    try:
        resp = client.get(f"/projects/{slug}/agents", timeout=15.0)
    except httpx.HTTPError as exc:
        return RED, f"request failed: {exc}"
    if resp.status_code == 401:
        return RED, "401 — bearer missing, invalid, or revoked"
    if resp.status_code == 403:
        return RED, f"403 — this bearer does not own {slug!r}"
    if resp.status_code != 200:
        return RED, f"HTTP {resp.status_code}"
    agents = resp.json().get("agents", [])
    return GREEN, f"bearer accepted on /projects/{slug}/agents ({len(agents)} agents)"


def _poll_eval(client: httpx.Client, path: str, deadline: float) -> dict | None:
    """Poll a started run until its results are populated, or the deadline passes.

    `status` reaching a terminal value is not the signal — a run reports
    `completed` with an empty `cases` list for a moment before the per-case
    results land, and reading it there says "completed with no cases", which is
    a red lane for a platform that is fine. `passed` is the field that appears
    with the results, so it is what this waits for. The kit's own poller uses
    the same condition (`af_eval_http.poll_golden_run`).
    """
    while time.monotonic() < deadline:
        resp = client.get(path, timeout=30.0)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        if "passed" in payload or payload.get("status") in ("failed", "error"):
            return payload
        time.sleep(POLL_INTERVAL_S)
    return None


def probe_llm(client: httpx.Client, slug: str, agent: str) -> tuple[str, str]:
    """One real golden-case trial, read for a per-assertion verdict.

    The distinction that matters is between a case that *failed* and a case that
    never ran. A failing assertion means the lane works and the gene is wrong —
    green here, because this probe grades the platform, not the gene. A case
    carrying `is_error` never reached the model, and its error is the diagnosis.
    """
    base = f"/projects/{slug}/agents/{agent}/eval"
    try:
        started = client.post(base, json={"max_trials": 1}, timeout=60.0)
    except httpx.HTTPError as exc:
        return RED, f"eval POST failed: {exc}"
    if started.status_code == 404:
        return RED, f"no eval endpoint at {base} — regression, or {agent!r} declares no cases"
    if started.status_code >= 400:
        return RED, f"eval POST HTTP {started.status_code}: {started.text[:200]}"

    run_id = started.json().get("run_id")
    if not run_id:
        return RED, f"eval POST returned no run_id: {started.text[:200]}"

    payload = _poll_eval(client, f"{base}/{run_id}", time.monotonic() + POLL_TIMEOUT_S)
    if payload is None:
        return RED, f"run {run_id} did not finish within {POLL_TIMEOUT_S:.0f}s"

    cases = payload.get("cases") or []
    errored = [c for c in cases if c.get("is_error")]
    if errored:
        detail = str(errored[0].get("error", "")).strip() or "no error text"
        return RED, f"run {run_id}: the case never reached the model — {detail}"
    if not cases:
        return RED, f"run {run_id} completed with no cases"

    graded = sum(len(c.get("assertions") or []) for c in cases)
    verdict = "passed" if payload.get("passed") else "failed"
    return GREEN, (
        f"run {run_id}: {len(cases)} case(s), {graded} assertion(s) graded "
        f"(suite {verdict} — a gene verdict, not a platform one)"
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--agent", default=DEFAULT_PROBE_AGENT, help="agent for the llm probe")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="probe transport lanes only; the llm lane prints as skipped, never green",
    )
    parser.add_argument("--repo-root", default=None, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = args.api_key or load_api_key(args.repo_root)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    print(f"==> af-preflight slug={args.slug} base={args.base_url}")
    lanes: list[tuple[str, str, str]] = []
    with httpx.Client(base_url=args.base_url.rstrip("/"), headers=headers) as client:
        state, detail = probe_reachable(client)
        lanes.append(("reachable", state, detail))

        if state is GREEN:
            state, detail = probe_auth(client, args.slug, api_key)
            lanes.append(("auth", state, detail))
        else:
            lanes.append(("auth", SKIPPED, "not probed: AgentForge is not reachable"))

        if args.skip_llm:
            lanes.append(("llm", SKIPPED, "not probed: --skip-llm"))
        elif lanes[-1][1] is GREEN:
            lanes.append(("llm", *probe_llm(client, args.slug, args.agent)))
        else:
            lanes.append(("llm", SKIPPED, "not probed: the auth lane is not green"))

    for name, state, detail in lanes:
        print(f"    {name:<10} {state:<8} {detail}")

    failed = [name for name, state, _ in lanes if state is RED]
    if failed:
        print(f"==> NOT READY — {', '.join(failed)}", file=sys.stderr)
        return 1
    skipped = [name for name, state, _ in lanes if state is SKIPPED]
    note = f" ({', '.join(skipped)} not probed)" if skipped else ""
    print(f"==> ready{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
