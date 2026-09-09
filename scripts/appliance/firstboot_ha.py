#!/usr/bin/env python3
"""First-boot HA onboarding caller and tier-2 persistence (TAP-6570, TAP-6572).

Drives `homeiq_ha.agent.onboarding.run_first_boot` against a running HA instance
and persists the minted credential in the appliance secret store, so a second
boot reuses it instead of asking HA for another one.

The order is the ADR's, not the obvious one
-------------------------------------------
`docs/architecture/adr-appliance-secret-store.md` says the caller "reads
`core.appliance_secret` first; on a hit it uses the stored token and never calls
HA". So this script reads the store BEFORE it touches the network, and that
ordering is what makes two of its three interesting outcomes correct:

* A second boot is a store read. HA is never contacted, so there is no window in
  which a transient HA failure could be mistaken for a fresh appliance.
* A rotated or absent `HOMEIQ_SECRET_DEK` is caught before any onboarding call.
  The stored row will not decrypt, the script reports `SecretStoreUnsealed` and
  exits non-zero, and HA's onboarding state is untouched. Onboarding again would
  mint a *second* owner and orphan the credential the customer's appliance is
  already using — the failure this ordering exists to make impossible.

`ALREADY_ONBOARDED` with no stored row is therefore not "load it from storage" —
storage was already checked and was empty. It means something other than this
appliance owns the HA instance, which is `SecretNotProvisioned`: a named,
non-zero stop. Re-onboarding is not attempted, and no second owner is minted.

Nothing here prints the token. The credential leaves this process only through
the store, encrypted; stdout carries the state, the key name and the username.
Lane B1 printed the token because it had nowhere to put it; it now has one.

Usage:
    HA_FIRSTBOOT_BASE_URL=http://127.0.0.1:28123 \\
        HOMEIQ_STATE_DIR=/var/lib/homeiq \\
        python scripts/appliance/firstboot_ha.py

    python scripts/appliance/firstboot_ha.py --base-url http://127.0.0.1:28123

Exit codes:
    0  - the credential is in the store: either minted and written this boot
         (COMPLETED), or already present and reused (the skip path).
    1  - a named onboarding failure (UNREACHABLE, USER_STEP_REJECTED,
         TOKEN_EXCHANGE_FAILED, LONG_LIVED_MINT_FAILED).
    2  - the base URL precondition failed: no --base-url and
         $HA_FIRSTBOOT_BASE_URL is unset. A failed precondition, not a silent
         default target.
    75 - SecretStoreUnavailable. Retryable; the store is down, not wrong.
    79 - SecretStoreUnsealed. The DEK is missing, malformed, or no longer the one
         the stored row was written under. Fatal, and deliberately not retried.
    80 - SecretNotProvisioned. HA is already onboarded by someone else and this
         appliance holds no row for it.

    75/79/80 come from homeiq_ha.secrets.states.EXIT_CODES, so this script,
    firstboot-secrets.sh and the ADR's failure table use one set of numbers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

from homeiq_ha.agent.onboarding import OnboardingState, run_first_boot
from homeiq_ha.secrets.states import SecretState, SecretStoreError
from homeiq_ha.secrets.store import HA_TOKEN_KEY, ApplianceSecretStore

_BASE_URL_ENV = "HA_FIRSTBOOT_BASE_URL"

#: The line a second boot logs. Pinned as a constant because it is a documented
#: observable — scripts/appliance/README.md quotes it and an integration test
#: greps for it, so changing the wording in one place changes it everywhere.
SKIP_LOG_LINE = "onboarding skipped: reusing stored credential"

logger = logging.getLogger("homeiq.firstboot")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="First-boot HA onboarding and persistence")
    parser.add_argument(
        "--base-url",
        default=os.environ.get(_BASE_URL_ENV, ""),
        help=f"HA base URL, e.g. http://127.0.0.1:28123. Defaults to ${_BASE_URL_ENV}.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args(argv)


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload))


def _emit_store_error(exc: SecretStoreError) -> int:
    """Report a named store state on stderr and stdout, and return its exit code."""
    logger.error("%s: %s", exc.state.value, exc.detail)
    _emit({"state": exc.state.value, "detail": exc.detail, "key": exc.key})
    return exc.exit_code


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code.

    Never raises for a named outcome — an onboarding state, a store state and an
    unset base URL all come back as a code plus one JSON line.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s %(message)s", stream=sys.stderr
    )
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

    try:
        store = ApplianceSecretStore.from_env()
    except SecretStoreError as exc:
        return _emit_store_error(exc)

    # Store first — see the module docstring. A hit ends the boot without a
    # single call to HA.
    try:
        store.get(HA_TOKEN_KEY)
    except SecretStoreError as exc:
        if exc.state is not SecretState.SECRET_NOT_PROVISIONED:
            return _emit_store_error(exc)
    else:
        logger.info(SKIP_LOG_LINE)
        _emit({"state": "reused", "detail": SKIP_LOG_LINE, "key": HA_TOKEN_KEY})
        return 0

    result = asyncio.run(run_first_boot(args.base_url, timeout=args.timeout))

    if result.state is OnboardingState.ALREADY_ONBOARDED:
        exc = SecretStoreError(
            SecretState.SECRET_NOT_PROVISIONED,
            key=HA_TOKEN_KEY,
            detail=(
                "Home Assistant is already onboarded but this appliance holds no "
                "credential for it, so it was onboarded by something else. Not "
                "re-onboarding: a second owner would orphan the existing token."
            ),
        )
        return _emit_store_error(exc)

    if result.state is not OnboardingState.COMPLETED or result.credential is None:
        logger.error("%s: %s", result.state.value, result.detail)
        _emit({"state": result.state.value, "detail": result.detail})
        return 1

    try:
        store.put(HA_TOKEN_KEY, result.credential.token)
    except SecretStoreError as exc:
        return _emit_store_error(exc)

    logger.info("stored the minted credential as %s", HA_TOKEN_KEY)
    _emit(
        {
            "state": result.state.value,
            "detail": result.detail,
            "key": HA_TOKEN_KEY,
            "username": result.credential.username,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
