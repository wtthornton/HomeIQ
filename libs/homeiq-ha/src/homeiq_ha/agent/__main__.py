"""Command-line entry point for the HA init/setup agent.

``audit`` is the default and writes nothing::

    python -m homeiq_ha.agent                 # audit
    python -m homeiq_ha.agent plan --phase 3
    python -m homeiq_ha.agent apply --phase 1

Reads ``HOME_ASSISTANT_URL``/``HOME_ASSISTANT_TOKEN`` (or ``HA_URL``/``HA_TOKEN``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from homeiq_ha.client import HAClient

from .engine import HAInitAgent, Mode
from .recipes import default_recipes
from .snapshot import Snapshot, capture, diff, restore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homeiq-ha-agent", description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default=Mode.AUDIT.value,
        choices=[*[m.value for m in Mode], "snapshot", "diff", "restore"],
        help=(
            "audit (default, writes nothing), plan, apply, "
            "snapshot (capture a baseline), diff (compare against one), "
            "or restore (put the instance back to one)"
        ),
    )
    parser.add_argument("--phase", type=int, default=None, help="restrict to one phase")
    parser.add_argument("--only", default=None, help="restrict to one recipe by name")
    parser.add_argument(
        "--baseline",
        default="ha-baseline.json",
        help="baseline file for snapshot/diff/restore (default: ha-baseline.json)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


async def _run_state_mode(args: argparse.Namespace) -> int:
    """snapshot / diff / restore — the loop that makes live testing repeatable."""
    path = Path(args.baseline)

    async with HAClient.from_env() as ha:
        if args.mode == "snapshot":
            snapshot = await capture(ha)
            path.write_text(snapshot.to_json())
            print(f"baseline written to {path}\n  {snapshot.summary()}")
            return 0

        if not path.exists():
            print(f"No baseline at {path}. Run `snapshot` first.", file=sys.stderr)
            return 2
        baseline = Snapshot.from_json(path.read_text())

        if args.mode == "diff":
            changes = await diff(ha, baseline)
            for change in changes:
                print(f"  {change.describe()}")
            print(f"\n{len(changes)} difference(s) from {path}")
            return 0 if not changes else 1

        reverted = await restore(ha, baseline)
        for change in reverted:
            print(f"  {change.describe()}")
        print(f"\nrestored to {path}: {len(reverted)} action(s), instance matches baseline")
        return 0


async def _run(args: argparse.Namespace) -> int:
    if args.mode in {"snapshot", "diff", "restore"}:
        return await _run_state_mode(args)

    agent = HAInitAgent(default_recipes())
    async with HAClient.from_env() as ha:
        if args.mode == Mode.AUDIT.value:
            report = await agent.audit(ha, only=args.only)
        elif args.mode == Mode.PLAN.value:
            report = await agent.plan(ha, phase=args.phase, only=args.only)
        else:
            report = await agent.apply(ha, phase=args.phase, only=args.only)

    print(report.describe())
    if args.mode == Mode.AUDIT.value:
        # The audit's headline claim, stated as a checkable assertion.
        print(
            f"\nASSERTION: audit issued 0 write calls "
            f"({len(report.reads)} read calls) — wrote_nothing={report.wrote_nothing}"
        )
    return 0 if all(outcome.error is None for outcome in report.outcomes) else 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
