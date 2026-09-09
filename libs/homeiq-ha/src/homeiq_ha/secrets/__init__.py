"""Appliance secret-store states and no-fallback accessors (TAP-6573).

``states`` is the part both tiers share: the ADR's named failure states, and
accessors that raise one of them rather than returning a default. ``store`` is
tier 2 itself (TAP-6572) -- AES-GCM rows under the tier-1 DEK, behind a backend
interface with the ADR's mandated Postgres adapter and the file adapter the
appliance first-boot path uses. :func:`load_ha_token` is the entry point a
HomeIQ service or the AgentForge publish step calls to obtain the Home Assistant
credential; it raises ``SecretNotProvisioned`` before onboarding rather than
handing back an empty token.

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
from homeiq_ha.secrets.store import (
    HA_TOKEN_KEY,
    SECRET_TABLE,
    ApplianceSecretStore,
    FileSecretBackend,
    PostgresSecretBackend,
    SecretBackend,
    SecretRow,
    load_dek,
    load_ha_token,
    read_tier1_env,
    resolve_state_dir,
)

__all__ = [
    "EXIT_CODES",
    "FAILURE_STATES",
    "HA_TOKEN_KEY",
    "SECRET_TABLE",
    "ApplianceSecretStore",
    "FileSecretBackend",
    "PostgresSecretBackend",
    "SecretBackend",
    "SecretRow",
    "SecretState",
    "SecretStoreError",
    "load_dek",
    "load_ha_token",
    "preflight_failure",
    "read_tier1_env",
    "require_dek",
    "require_secret",
    "resolve_state_dir",
    "store_unavailable",
]
