"""
Evaluation Regression Detection — Story 5.3

Reads eval-history.jsonl, computes per-prompt rolling baselines,
and flags regressions where the latest score drops significantly
below the historical average.

Usage:
    python tests/integration/eval_regression_check.py
    python tests/integration/eval_regression_check.py --threshold 0.10
    python tests/integration/eval_regression_check.py --window 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict


def load_history(path: str) -> list[dict]:
    """Load JSONL history file into a list of dicts."""
    entries: list[dict] = []
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def check_regressions(
    entries: list[dict],
    window: int = 5,
    threshold: float = 0.10,
) -> list[dict]:
    """Check for regressions across prompts.

    Groups entries by prompt, computes a rolling average of the last
    ``window`` runs, and flags the latest score if it drops more than
    ``threshold`` below the average.
    """
    by_prompt: dict[str, list[float]] = defaultdict(list)
    for entry in entries:
        prompt = entry.get("prompt", "unknown")
        score = entry.get("eval_overall", 0.0)
        by_prompt[prompt].append(score)

    results: list[dict] = []
    for prompt, scores in sorted(by_prompt.items()):
        latest = scores[-1]
        recent = scores[-window:] if len(scores) >= window else scores
        baseline = sum(recent[:-1]) / len(recent[:-1]) if len(recent) > 1 else latest
        delta = latest - baseline

        status = "REGRESSION" if delta < -threshold else "OK"
        results.append({
            "prompt": prompt,
            "baseline": round(baseline, 3),
            "latest": round(latest, 3),
            "delta": round(delta, 3),
            "runs": len(scores),
            "status": status,
        })

    return results


def format_table(results: list[dict]) -> str:
    """Format results as a markdown-style table."""
    lines = [
        f"{'Prompt':<40} {'Baseline':>8} {'Latest':>8} {'Delta':>8} {'Runs':>5} {'Status':>12}",
        f"{'-'*40} {'-'*8} {'-'*8} {'-'*8} {'-'*5} {'-'*12}",
    ]
    for r in results:
        prompt_display = r["prompt"][:38] + ".." if len(r["prompt"]) > 40 else r["prompt"]
        delta_str = f"{r['delta']:+.3f}"
        lines.append(
            f"{prompt_display:<40} {r['baseline']:>8.3f} {r['latest']:>8.3f} "
            f"{delta_str:>8} {r['runs']:>5} {r['status']:>12}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluation Regression Check")
    parser.add_argument(
        "--threshold", type=float, default=0.10,
        help="Score drop threshold to flag as regression (default: 0.10)",
    )
    parser.add_argument(
        "--window", type=int, default=5,
        help="Rolling window size for baseline calculation (default: 5)",
    )
    parser.add_argument(
        "--history-file", default=None,
        help="Path to eval-history.jsonl (default: reports/eval-history.jsonl)",
    )
    args = parser.parse_args()

    history_path = args.history_file or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "reports", "eval-history.jsonl",
    )

    entries = load_history(history_path)
    if not entries:
        print(f"No history found at {history_path}")
        return 0

    results = check_regressions(entries, window=args.window, threshold=args.threshold)
    print(format_table(results))

    regressions = [r for r in results if r["status"] == "REGRESSION"]
    if regressions:
        print(f"\n{len(regressions)} REGRESSION(S) detected (threshold: {args.threshold})")
        return 1

    print(f"\nAll prompts OK (threshold: {args.threshold})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
