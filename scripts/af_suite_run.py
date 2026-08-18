#!/usr/bin/env python3
"""Drive the golden suite against the live AgentForge instance, one case per run.

Why this exists rather than the kit's ``af_eval.py``: the kit posts one run per
*agent* (no ``case_ids``), and a whole-agent POST never completes — one sat at
``pending`` with zero cases for 40+ minutes while smaller runs against the same
agent finished around it (TAP-5730). Driving PER CASE is the only shape that
produces verdicts, so that is what this does.

Three more mechanics this encodes, each already paid for once:

* **Poll on a fresh request.** The kit holds one client and dies on "Connection
  reset by peer" while the run survives server-side.
* **Wait for ``passed`` to appear, not for a terminal ``status``.** A run reports
  ``completed`` before its ``cases`` array fills; read it there and a healthy
  platform looks like a red lane.
* **Serial, never concurrent.** Concurrent diagnostic runs caused a per-case
  timeout on 2026-08-06 that was nearly filed as a second platform defect.

Output is a JSON map of ``agent::case_id`` to the graded result, shaped to
compare directly against a prior run's file (see ``scripts/af_suite_diff.py``).
Unlike the case-level ``assertions`` array — which is a copy of the LAST trial
and hides variance (TAP-5767) — ``pass_rate`` is the aggregate, so a flip is
read from ``passed`` + ``pass_rate``, never from the assertion detail alone.

**One rule governs both granularities: an ungraded run is not evidence about the
gene** (TAP-5831). A case that errors is already counted apart from pass/fail in
the summary; a *trial* that errors was not, and the platform's own
``pass_rate`` folds it in as a failure. On 2026-08-07
``wstore-expert-brand::off-voice-and-mimicry-flagged`` returned rate 0.8 with
four graded trials and four passes — the fifth never received a verdict, and
scoring it zero turned a passing case into a failing one. So ``pass_rate`` here
is re-derived over graded trials only, ``platform_pass_rate`` keeps what AF
returned so nothing is hidden, and a case whose trials were *all* ungraded is an
error rather than a 0.0. Excluding the trial and scoring it zero are not two
readings of the same evidence: one reports what was measured, the other invents
a measurement.

The poll obeys the same rule (TAP-5835). ``POLL_TIMEOUT_S`` was raised 900 to
2400 after a case tripped it, and a case then tripped 2400 as well — the same
case, unchanged, took 2402 s and then 106 s on re-run, a factor of 22. A
constant tuned that way measures opus lane contention, not the case, and every
expiry costs a targeted re-run to tell "slow" from "broken". The primary bound
is now the platform's own terminal state; a run the platform is still answering
for keeps polling. What ends it early is a genuine stall — no successful poll
for ``POLL_STALL_S`` — and ``POLL_BACKSTOP_S`` is a runaway guard, not a case
budget. The two outcomes are distinct in the payload (``error_kind``), because
an expiry that reads the same as "never reached the model" is the thing that
cost the re-runs.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agentforge" / "projects" / "homeiq" / "agents"
DEFAULT_BASE_URL = "http://localhost:8010"
DEFAULT_SLUG = "homeiq"
# 5.0 spent ~2.5s of dead wait per case on average — ~3 minutes across 77 cases,
# for no signal. The platform is polled, not pushed, so this is pure latency.
POLL_INTERVAL_S = 2.0
# TAP-5835. Raising a fixed budget was tried twice and failed twice: 900 s tripped
# at 905 s, 2400 s tripped at 2402 s, and that same case then passed in 106 s
# untouched. A factor of 22 on identical work means the constant was measuring how
# contended the opus lane was, not how long the case needs, so a third number would
# buy time until the next contended run and teach nothing.
#
# The bound is therefore the platform's terminal state, not a clock. What ends a
# poll early is the platform going quiet — no successful response for POLL_STALL_S.
# Measured 2026-08-07: a run reports `pending` with `cases: []` and then flips
# straight to `completed` with all 5 trials at t+136 s. There is NO incremental
# fill, so "the payload stopped changing" is not a stall signal — on a healthy
# 40-minute run it never changes at all. A 200 for the run id is the only liveness
# the API offers, and it is what this waits on.
POLL_STALL_S = 300.0
# Not a case budget — a runaway guard for a run the platform answers for forever.
# Kept far clear of the 2402 s worst case so that hitting it means something is
# genuinely wrong rather than that the lane was busy.
POLL_BACKSTOP_S = 10800.0
# Each says which of the two an operator is looking at, so nobody has to spend a
# targeted re-run finding out (TAP-5835).
POLL_FAILURES = {
    "no_progress": f"platform stopped answering for this run ({POLL_STALL_S:.0f}s without a response) — the run, not the case, is the suspect",
    "still_running": f"platform still reported this run as live at the {POLL_BACKSTOP_S:.0f}s runaway guard — no verdict, and not evidence the gene failed",
    "http": "platform refused the run lookup",
}


def api_key() -> str:
    """Read the bearer from the environment, falling back to ``.env``.

    The kit's ``af_eval.py`` does neither, which is why every documented
    invocation of it has to be prefixed with ``set -a && . ./.env``.
    """
    if key := os.environ.get("AGENTFORGE_API_KEY", "").strip():
        return key
    env_file = ROOT / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == "AGENTFORGE_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def frontmatter(path: Path) -> dict[str, Any]:
    """Parse an agent markdown file's YAML frontmatter."""
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1]) or {}


def declared_cases(agents: list[str] | None = None) -> list[tuple[str, str, dict[str, Any]]]:
    """Every ``(agent, case_id, case)`` the kit declares, in file order.

    Skips any case carrying ``retired_because`` — repo-local, like
    ``shape_only_because`` and ``trap_for`` (AgentForge's ``GoldenCase`` ignores
    unknown keys). A retired case is kept in the file for its reasoning and its
    reusable assertions, but is never spent against a live run again, single-case
    or full-suite, until someone removes the key.
    """
    out: list[tuple[str, str, dict[str, Any]]] = []
    for path in sorted(AGENTS_DIR.glob("*.md")):
        fm = frontmatter(path)
        name = fm.get("name", path.stem)
        if agents and name not in agents:
            continue
        for case in fm.get("golden_cases") or []:
            if isinstance(case, dict) and case.get("id") and not str(case.get("retired_because", "")).strip():
                out.append((name, case["id"], case))
    return out


def poll(client: httpx.Client, path: str) -> tuple[dict[str, Any] | None, str]:
    """Poll until the run is terminal, issuing a fresh request each time.

    Returns ``(payload, "")`` on a terminal run, or ``(None, error_kind)``. The
    kind is the whole point: ``no_progress`` means the platform stopped answering
    for this run, ``still_running`` means it kept answering past the runaway
    guard, and ``http`` means it refused. Collapsing those into one `is_error`
    is what made every expiry cost a targeted re-run to interpret (TAP-5835).
    """
    started = time.monotonic()
    last_live = started
    while True:
        now = time.monotonic()
        if now - started > POLL_BACKSTOP_S:
            return None, "still_running"
        if now - last_live > POLL_STALL_S:
            return None, "no_progress"
        try:
            resp = client.get(path, timeout=30.0)
        except httpx.HTTPError:
            time.sleep(POLL_INTERVAL_S)
            continue
        if resp.status_code != 200:
            return None, "http"
        payload = resp.json()
        if "passed" in payload or payload.get("status") in ("failed", "error"):
            return payload, ""
        # A 200 for the run id is the platform vouching that the run exists and is
        # still its problem. That is the only liveness this API exposes — the
        # payload itself does not change until the run finishes.
        last_live = time.monotonic()
        time.sleep(POLL_INTERVAL_S)


# AF's wording when the judge call itself fails, from the `rubric` assertion's
# `detail`. Matching prose is fragile, and it is the only signal available: on a
# failed judge call AF leaves `is_error` false and writes a real-looking
# `judge_score: 0.0` / `judge_verdict: "fail"`, identical in shape to a harsh but
# genuine verdict. The durable fix belongs upstream — AF should mark the trial
# `is_error`, as it already does when the same quota exhaustion hits the gene call
# rather than the judge call. Until then this prefix is the discriminator, so a
# change in AF's phrasing reopens the false red rather than failing loudly.
JUDGE_CALL_FAILED = "judge call failed:"


def judge_call_failed(trial: dict[str, Any]) -> bool:
    """True when a rubric assertion reports the judge never returned a verdict.

    Observed 2026-08-10 on `fails-closed-when-matrix-absent`, run `51d7c072a72e`:
    the weekly judge quota ran out, and the trial was written as a 0.00 failure
    with `is_error: false`. Counted as graded, it makes a case nobody scored read
    as a case that scored zero — the exact false red `regrade` exists to prevent,
    arriving through the one door its `is_error` guard does not cover.
    """
    for assertion in trial.get("assertions") or []:
        if assertion.get("kind") == "rubric" and JUDGE_CALL_FAILED in (assertion.get("detail") or ""):
            return True
    return False


def regrade(result: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Re-derive ``passed``/``pass_rate`` over the trials that were actually graded.

    A trial the platform marks ``is_error`` never reached a verdict — its
    assertions come back with ``judge_score: null`` and ``passed: false``, which
    is the shape of "nobody looked", not of "the judge said no". AF folds it into
    ``pass_rate`` as a failure anyway, so a 4-of-4 case reads 0.8 (TAP-5831).

    A failed *judge call* is the same thing wearing the other shape: AF leaves
    ``is_error`` false and writes a real-looking ``judge_score: 0.0``, so it is
    excluded on its rationale text instead (see ``judge_call_failed``). Both are
    "nobody graded this"; neither is evidence about the gene.

    This is not second-guessing the platform's grading: every per-trial verdict is
    taken exactly as given, and ``platform_pass_rate`` preserves AF's own number.
    The only change is the denominator, at a granularity the platform aggregates
    over but does not expose a choice about. When nothing was graded there is no
    rate to report and the case is an error, the same way a whole-case failure is.
    """
    trials = result.get("trials") or []
    graded = [t for t in trials if not t.get("is_error") and not judge_call_failed(t)]
    ungraded = len(trials) - len(graded)
    if not ungraded:
        return {}
    if not graded:
        return {
            "passed": False,
            "is_error": True,
            "error_kind": "no_graded_trials",
            "error": f"all {len(trials)} trial(s) errored before assertions were checked",
            "pass_rate": None,
            "graded_trials": 0,
            "ungraded_trials": ungraded,
        }
    rate = sum(1 for t in graded if t.get("passed")) / len(graded)
    # kit_checks.py uses the same default, so a case that omits the key is held to
    # the same bar here as it is at validation time.
    threshold = case.get("pass_threshold", 1.0)
    return {
        "passed": rate >= threshold,
        "pass_rate": rate,
        "graded_trials": len(graded),
        "ungraded_trials": ungraded,
    }


def run_case(client: httpx.Client, slug: str, agent: str, case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    """Run one case at its declared trials and return its graded result."""
    base = f"/projects/{slug}/agents/{agent}/eval"
    started = client.post(base, json={"case_ids": [case_id]}, timeout=60.0)
    if started.status_code >= 400:
        return {"run_id": "", "passed": False, "is_error": True, "error_kind": "http", "error": f"eval POST HTTP {started.status_code}: {started.text[:300]}"}
    run_id = started.json().get("run_id", "")
    payload, kind = poll(client, f"{base}/{run_id}")
    if payload is None:
        return {"run_id": run_id, "passed": False, "is_error": True, "error_kind": kind, "error": POLL_FAILURES[kind]}
    cases = payload.get("cases") or []
    if not cases:
        return {"run_id": run_id, "passed": False, "is_error": True, "error_kind": "no_cases", "error": "run completed with no cases"}
    result = cases[0]
    graded = {
        "run_id": run_id,
        "passed": bool(result.get("passed")),
        "is_error": bool(result.get("is_error")),
        "error_kind": "case_error" if result.get("is_error") else "",
        "error": str(result.get("error", "")),
        "pass_rate": result.get("pass_rate"),
        # AF's own aggregate, kept beside the re-derived one so the correction is
        # auditable rather than a silent overwrite.
        "platform_pass_rate": result.get("pass_rate"),
        "graded_trials": len(result.get("trials") or []),
        "ungraded_trials": 0,
        "assertions": result.get("assertions") or [],
        # The case-level `assertions` array is a copy of the LAST trial and hides
        # variance (TAP-5767). `cases[].trials` carries every trial's own verdict
        # and judge score, so a case that failed 3 of 5 can be told apart from one
        # that failed flat — keep it, or the file records a single sample as if it
        # were the result.
        "trials": result.get("trials") or [],
        "declared_trials": case.get("trials", 1),
        "tier": case.get("tier", ""),
    }
    return {**graded, **regrade(result, case)}


def trial_totals(results: dict[str, Any]) -> tuple[int, int]:
    """Aggregate graded/ungraded trials across a result map.

    A single-trial case cannot be counted from ``graded_trials``: AgentForge only
    fills ``cases[].trials`` when ``trials > 1``
    (``backend/services/agent_eval.py:415``), so every k=1 case reports an empty
    list and reads as zero graded. That understated the total by the 13 k=1 cases
    on the 2026-08-07 baseline — 259 graded + 19 ungraded against 291 declared.

    Verdicts were never affected (``regrade`` returns early when nothing is
    ungraded, leaving AF's own ``passed``/``pass_rate`` intact). But this total is
    the tripwire a parallel run is judged against, so it has to be true: a k=1
    case counts as one trial, graded unless the case itself errored.
    """
    graded = ungraded = 0
    for res in results.values():
        if res.get("trials"):
            graded += res.get("graded_trials") or 0
            ungraded += res.get("ungraded_trials") or 0
        elif res.get("is_error"):
            ungraded += 1
        else:
            graded += 1
    return graded, ungraded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--agent", action="append", help="restrict to these agents (repeatable)")
    parser.add_argument("--case", action="append", help="restrict to these case ids (repeatable)")
    parser.add_argument("--out", default="", help="write the result map here as JSON")
    # Default 1: the serial path is what produced the reference baseline, and it
    # stays the default until a calibration run shows a higher value does not cost
    # graded trials (reports/suite-speedup-plan-2026-08-07.md).
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="cases to run at once (default 1 — serial, the reference path)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.concurrency < 1:
        print("error: --concurrency must be >= 1", file=sys.stderr)
        return 2

    key = api_key()
    if not key:
        print("error: no AGENTFORGE_API_KEY in env or .env", file=sys.stderr)
        return 2

    cases = declared_cases(args.agent)
    if args.case:
        cases = [c for c in cases if c[1] in set(args.case)]
    if not cases:
        print("error: no cases matched", file=sys.stderr)
        return 2

    # Longest-first only above N=1. At N=1 declaration order is preserved, so the
    # default path stays exactly what produced the reference baseline. Above it,
    # a 291s case submitted last would strand the tail behind a single worker.
    if args.concurrency > 1:
        cases = sorted(cases, key=lambda c: c[2].get("trials", 1), reverse=True)

    results: dict[str, Any] = {}
    lock = threading.Lock()
    done = 0

    def run_one(entry: tuple[str, str, dict]) -> None:
        nonlocal done
        agent, case_id, case = entry
        key_name = f"{agent}::{case_id}"
        t0 = time.monotonic()
        res = run_case(client, args.slug, agent, case_id, case)
        elapsed = time.monotonic() - t0
        mark = "ERROR" if res["is_error"] else ("pass " if res["passed"] else "FAIL ")
        rate = res.get("pass_rate")
        # An excluded trial changes what the rate means, so it is named on the
        # line that reports the rate rather than left for whoever opens the JSON.
        skipped = res.get("ungraded_trials") or 0
        note = f" [{skipped} ungraded trial(s) excluded]" if skipped else ""
        kind = res.get("error_kind") or ""
        note += f" [{kind}]" if res["is_error"] and kind else ""
        # The dict, the counter and the file move together: with workers finishing
        # out of order, an unlocked write can serialise a half-updated map.
        with lock:
            results[key_name] = res
            done += 1
            print(
                f"[{done:>2}/{len(cases)}] {mark} {key_name} "
                f"rate={rate if rate is not None else '-'} ({elapsed:.0f}s){note}",
                flush=True,
            )
            if args.out:
                Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Shared across threads by design — httpx.Client is documented as safe to share
    # and pools connections, so N workers reuse one pool rather than opening N.
    with httpx.Client(base_url=args.base_url, headers={"Authorization": f"Bearer {key}"}) as client:
        if args.concurrency == 1:
            for entry in cases:
                run_one(entry)
        else:
            with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                for future in cf.as_completed([pool.submit(run_one, e) for e in cases]):
                    future.result()

    passed = sum(1 for r in results.values() if r["passed"])
    errored = sum(1 for r in results.values() if r["is_error"])
    # The tripwire for a parallel run. Trials that never got a verdict leave the
    # denominator (TAP-5831), so a contended run can report healthy rates over a
    # k far below what each case declared. Printing the total is what makes a
    # faster run comparable to the serial reference rather than merely quicker.
    graded, ungraded = trial_totals(results)
    print(f"\n==> {len(results)} case(s): {passed} pass, {len(results) - passed - errored} fail, {errored} error")
    print(f"==> trials: {graded} graded, {ungraded} ungraded (concurrency={args.concurrency})")
    if ungraded:
        print(f"==> WARNING: {ungraded} trial(s) never received a verdict — rates are computed over fewer trials than declared")
    if args.out:
        print(f"==> wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
