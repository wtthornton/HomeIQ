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

from homeiq_ha.client import HAClient

from .engine import HAInitAgent, Mode
from .recipes import default_recipes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homeiq-ha-agent", description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default=Mode.AUDIT.value,
        choices=[m.value for m in Mode],
        help="audit (default, writes nothing), plan, or apply",
    )
    parser.add_argument("--phase", type=int, default=None, help="restrict to one phase")
    parser.add_argument("--only", default=None, help="restrict to one recipe by name")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
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
