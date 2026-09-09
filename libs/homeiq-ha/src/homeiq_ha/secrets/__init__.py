"""Appliance secret-store states and no-fallback accessors (TAP-6573).

The tier-2 store itself (an encrypted Postgres table, per
``docs/architecture/adr-appliance-secret-store.md``) lands beside this module.
What lives here is the part both tiers share: the ADR's named failure states,
and accessors that raise one of them rather than returning a default.

The package is named ``secrets`` after the domain, not the stdlib module. It is
a submodule of ``homeiq_ha``, so an absolute ``import secrets`` anywhere in this
package -- ``homeiq_ha.agent.onboarding`` does exactly that for
``token_urlsafe`` -- still resolves to the standard library.
"""

from __future__ import annotations

from homeiq_ha.secrets.states import (
    EXIT_CODES,
    FAILURE_STATES,
    SecretState,
    SecretStoreError,
    preflight_failure,
    require_dek,
    require_secret,
    store_unavailable,
)

__all__ = [
    "EXIT_CODES",
    "FAILURE_STATES",
    "SecretState",
    "SecretStoreError",
    "preflight_failure",
    "require_dek",
    "require_secret",
    "store_unavailable",
]
