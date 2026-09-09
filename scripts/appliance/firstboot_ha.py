#!/usr/bin/env python3
"""First-boot HA onboarding caller (TAP-6570).

Drives `homeiq_ha.agent.onboarding.run_first_boot` against a running HA
instance and prints the outcome as one line of JSON on stdout. This script
mints; it does not persist. Where the credential is stored is Lane B3's
decision (the appliance secret store, TAP-6571) — this script only hands the
result back to whoever invoked it.

Usage:
    HA_FIRSTBOOT_BASE_URL=http://127.0.0.1:28123 \\
        python scripts/appliance/firstboot_ha.py

    python scripts/appliance/firstboot_ha.py --base-url http://127.0.0.1:28123

Exit codes:
    0 - state is COMPLETED or ALREADY_ONBOARDED (both are "nothing left to do
        that this script can do"; ALREADY_ONBOARDED means a prior boot already
        minted the credential and the caller must load it from storage instead)
    1 - any other named failure state (UNREACHABLE, USER_STEP_REJECTED,
        TOKEN_EXCHANGE_FAILED, LONG_LIVED_MINT_FAILED)
    2 - the base URL precondition failed: no --base-url and
        $HA_FIRSTBOOT_BASE_URL is unset. A failed precondition, not a silent
        default target.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from homeiq_ha.agent.onboarding import OnboardingState, run_first_boot

_BASE_URL_ENV = "HA_FIRSTBOOT_BASE_URL"
_SUCCESS_STATES = frozenset({OnboardingState.COMPLETED, OnboardingState.ALREADY_ONBOARDED})


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get(_BASE_URL_ENV, ""),
        help=f"HA base URL, e.g. http://127.0.0.1:28123. Defaults to ${_BASE_URL_ENV}.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code; never raises for a named
    onboarding outcome — only an unset base URL is treated as a hard error."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not args.base_url:
        print(
            json.dumps(
                {
                    "state": "missing_base_url",
                    "detail": f"${_BASE_URL_ENV} is unset and --base-url was not given",
                }
            ),
            file=sys.stderr,
        )
        return 2

    result = asyncio.run(run_first_boot(args.base_url, timeout=args.timeout))

    payload: dict[str, object] = {"state": result.state.value, "detail": result.detail}
    if result.credential is not None:
        payload["token"] = result.credential.token
        payload["username"] = result.credential.username
    print(json.dumps(payload))

    return 0 if result.state in _SUCCESS_STATES else 1


if __name__ == "__main__":
    raise SystemExit(main())
