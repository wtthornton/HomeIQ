#!/usr/bin/env python3
"""Compare two golden-suite result files case by case and print every flip.

A flipped verdict is the point of a re-run, not noise. A case that newly fails
may be a rubric now doing its job, a stricter cross-family judge, or a real
regression — and those are three different answers that look identical in a
pass count. So this reports per case, never a total, and marks cases that
appear in only one run rather than quietly dropping them.

`pass_rate` is read alongside `passed` because a case can fail at rate 0.8 —
four of five trials — and a single-trial re-run would have called it green.
The case-level `assertions` array is deliberately NOT the comparison key: it is
a copy of the last trial and hides exactly that variance (TAP-5767).

Run: python3 scripts/af_suite_diff.py BASELINE.json CURRENT.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def verdict(result: dict[str, Any]) -> str:
    """One word for what happened, distinguishing an error from a fail."""
    if result.get("is_error"):
        return "ERROR"
    return "pass" if result.get("passed") else "FAIL"


def rate(result: dict[str, Any]) -> str:
    value = result.get("pass_rate")
    return "-" if value is None else f"{value:.2f}"


def runner_artifact(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Name a flip the runner explains, so it is not read as a gene change.

    Before TAP-5831 an ungraded trial was scored as a failed one, so a baseline
    recorded then can carry a rate the gene never earned — 0.8 on a case that
    went four for four. Re-run today it reads 1.0, and the diff would call that a
    FAIL-to-pass flip: the exact "runner artifact mistaken for a real result"
    this whole comparison exists to prevent.

    The tell is in the baseline's own `trials` array, not in the current run. A
    re-run rarely reproduces a rare ungraded trial — the observed one was 1 in 291
    — so the current side usually looks perfectly clean while the baseline is the
    side carrying the bad denominator. Keying on the current run's
    `ungraded_trials` misses precisely the case this exists to catch.
    """
    if "ungraded_trials" in before:
        return ""  # baseline was recorded post-fix; its rate already excludes them
    stale = sum(1 for t in before.get("trials") or [] if t.get("is_error"))
    if stale:
        return f"runner: baseline counted {stale} ungraded trial(s) as failures (pre-TAP-5831); its rate is not comparable"
    return ""


def judge_detail(result: dict[str, Any]) -> str:
    """The rubric assertion's detail, which carries the judge's own reasoning."""
    for assertion in result.get("assertions") or []:
        if assertion.get("kind") == "rubric":
            return str(assertion.get("detail", ""))
    return str(result.get("error", ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("baseline")
    parser.add_argument("current")
    parser.add_argument("--detail", action="store_true", help="print each flip's judge detail")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    cur = json.loads(Path(args.current).read_text(encoding="utf-8"))

    flips, only_base, only_cur = [], sorted(set(base) - set(cur)), sorted(set(cur) - set(base))
    for case in sorted(set(base) & set(cur)):
        was, now = verdict(base[case]), verdict(cur[case])
        if was != now or rate(base[case]) != rate(cur[case]):
            flips.append((case, was, rate(base[case]), now, rate(cur[case])))

    print(f"baseline {args.baseline}: {len(base)} case(s)")
    print(f"current  {args.current}: {len(cur)} case(s)")
    for case in only_base:
        print(f"  DROPPED  {case} — in the baseline, absent from this run")
    for case in only_cur:
        print(f"  NEW      {case} — not in the baseline, no flip to report")

    if not flips:
        print("\nno flipped verdicts")
        return 0

    print(f"\n{len(flips)} flipped verdict(s):\n")
    width = max(len(f[0]) for f in flips)
    print(f"{'case':<{width}}  was          now")
    for case, was, was_rate, now, now_rate in flips:
        note = runner_artifact(base[case], cur[case])
        print(f"{case:<{width}}  {was} {was_rate:<6}  {now} {now_rate}{'  <- ' + note if note else ''}")
        if args.detail:
            print(f"{'':<{width}}    {judge_detail(cur[case])[:300]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
