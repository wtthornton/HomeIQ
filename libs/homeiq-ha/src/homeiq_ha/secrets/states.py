"""Named failure states for the appliance secret store (TAP-6573).

This module is the ADR's failure table
(``docs/architecture/adr-appliance-secret-store.md``, "When the store is
unavailable -- named states, never a default") turned into code:

===============================================  ==========================
Condition                                        State
===============================================  ==========================
Tier-1 file missing, or a key empty              ``preflight-failure``
``HOMEIQ_SECRET_DEK`` gone while tier-2 rows     ``SecretStoreUnsealed``
exist
Postgres unreachable                             ``SecretStoreUnavailable``
Tier-2 row absent for a required key             ``SecretNotProvisioned``
===============================================  ==========================

Why there is no ``default=`` anywhere below
-------------------------------------------
A fallback is not a smaller version of a failure -- it is a different outcome
wearing the failure's clothes. ``rows.get("ha_token", "")`` hands the caller an
anonymous client that connects, gets refused, and reports the refusal as a
Home Assistant problem; ``rows.get(key) or mint_new()`` silently replaces the
customer's real credential and orphans everything encrypted under the old one.
Both read as "handled" at the call site. So the accessors here raise, the
enum carries the reason, and the caller decides -- which is the whole content
of the ADR's decision, and the reason ``SecretStoreUnavailable`` is marked
retryable while the other three are not.

``OnboardingState`` in :mod:`homeiq_ha.agent.onboarding` is the existing
precedent for this shape.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The tier-1 key that seals the tier-2 store. Absent, every tier-2 row is
#: undecryptable, which is a fatal state rather than a reason to mint a new one.
DEK_KEY = "HOMEIQ_SECRET_DEK"


class SecretState(StrEnum):
    """Outcomes of a secret lookup. Never a silent fallback to a default.

    The failure values are spelled exactly as the ADR table spells them, so a
    log line, an exit-code lookup and the ADR all use one vocabulary.
    """

    OK = "ok"
    PREFLIGHT_FAILURE = "preflight-failure"
    SECRET_STORE_UNSEALED = "SecretStoreUnsealed"
    SECRET_STORE_UNAVAILABLE = "SecretStoreUnavailable"
    SECRET_NOT_PROVISIONED = "SecretNotProvisioned"


#: Every state that is not :attr:`SecretState.OK`.
FAILURE_STATES: frozenset[SecretState] = frozenset(SecretState) - {SecretState.OK}

#: Process exit codes, for the first-boot script and any CLI entry point.
#: ``78`` is ``EX_CONFIG`` and ``75`` is ``EX_TEMPFAIL`` from ``sysexits(3)`` --
#: the temp-fail code is deliberately the retryable one, so a supervisor that
#: distinguishes them restarts on an unreachable Postgres and gives up on a
#: misconfigured appliance. ``scripts/appliance/firstboot-secrets.sh`` pins
#: ``EXIT_PREFLIGHT_FAILURE`` to the value below and a test compares the two.
EXIT_CODES: Mapping[SecretState, int] = {
    SecretState.OK: 0,
    SecretState.PREFLIGHT_FAILURE: 78,
    SecretState.SECRET_STORE_UNSEALED: 79,
    SecretState.SECRET_STORE_UNAVAILABLE: 75,
    SecretState.SECRET_NOT_PROVISIONED: 80,
}

#: Only an unreachable store is worth retrying. A missing key and an unsealed
#: store are settled facts about the appliance's configuration; retrying them
#: turns a loud failure into a slow one.
_RETRYABLE = frozenset({SecretState.SECRET_STORE_UNAVAILABLE})


class SecretStoreError(Exception):
    """A secret could not be produced, reported as a named state.

    ``key`` is empty only for failures that are not about one key, such as an
    unreachable store.
    """

    def __init__(self, state: SecretState, *, key: str = "", detail: str = "") -> None:
        self.state = state
        self.key = key
        self.detail = detail
        parts = [str(state.value)]
        if key:
            parts.append(key)
        if detail:
            parts.append(detail)
        super().__init__(": ".join(parts))

    @property
    def retryable(self) -> bool:
        return self.state in _RETRYABLE

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.state]


def require_secret(values: Mapping[str, str], key: str) -> str:
    """Return ``values[key]``, or raise ``SecretNotProvisioned``.

    An empty string is treated as absence, not as a value: a row written empty
    by a half-finished provisioning pass is the same standby condition as a row
    that was never written, and the caller must not be able to tell them apart
    by accident.
    """
    value = values.get(key, "")
    if not value:
        raise SecretStoreError(
            SecretState.SECRET_NOT_PROVISIONED,
            key=key,
            detail="no value provisioned; the capability is standby, not defaulted",
        )
    return value


def require_dek(values: Mapping[str, str], *, tier2_rows_exist: bool) -> str:
    """Return the tier-1 DEK, or raise ``SecretStoreUnsealed``.

    ``tier2_rows_exist`` is what separates fatal from merely fresh. On a brand
    new appliance with no rows there is nothing to decrypt and nothing is lost;
    with rows present a missing DEK means the customer's stored credentials are
    unrecoverable, and continuing would mint replacements over the top of them.
    """
    dek = values.get(DEK_KEY, "")
    if dek:
        return dek
    detail = (
        "tier-2 rows exist but the DEK is absent; they are undecryptable"
        if tier2_rows_exist
        else "tier-1 file has no DEK"
    )
    raise SecretStoreError(SecretState.SECRET_STORE_UNSEALED, key=DEK_KEY, detail=detail)


def store_unavailable(detail: str) -> SecretStoreError:
    """Build the ``SecretStoreUnavailable`` error to raise from a connection failure.

    Returned rather than raised so the caller can ``raise store_unavailable(...)
    from exc`` and keep the driver traceback.
    """
    return SecretStoreError(SecretState.SECRET_STORE_UNAVAILABLE, detail=detail)


def preflight_failure(key: str, path: str) -> SecretStoreError:
    """Build the tier-1 ``preflight-failure`` error naming the key and the file."""
    return SecretStoreError(
        SecretState.PREFLIGHT_FAILURE,
        key=key,
        detail=f"missing or empty in {path}",
    )
