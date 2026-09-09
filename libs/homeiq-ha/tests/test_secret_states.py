"""The ADR's failure-state table, made executable (TAP-6573, VAL-063).

``docs/architecture/adr-appliance-secret-store.md:129-134`` names four
conditions and the state each one surfaces. The point of the table is that a
missing secret is *reported*, never replaced: a silent fallback to a shipped
value reintroduces exactly the constant-secret problem generating these values
exists to avoid, in the one place nobody would look for it.

These tests therefore assert on the mechanism -- that the accessors raise a
named state and that none of them even *accepts* a default -- rather than on an
observable that a fallback would satisfy just as well.
"""

from __future__ import annotations

import inspect
import secrets as stdlib_secrets

import pytest
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

#: The state names as the ADR table spells them, verbatim.
ADR_TABLE_STATES = (
    "preflight-failure",
    "SecretStoreUnsealed",
    "SecretStoreUnavailable",
    "SecretNotProvisioned",
)


def test_val063_every_adr_failure_state_is_a_named_constant() -> None:
    assert {state.value for state in FAILURE_STATES} == set(ADR_TABLE_STATES)


def test_val063_exit_codes_are_distinct_and_nonzero_for_every_failure_state() -> None:
    assert EXIT_CODES[SecretState.OK] == 0
    failures = [EXIT_CODES[state] for state in FAILURE_STATES]
    assert all(code != 0 for code in failures)
    assert len(set(failures)) == len(failures)


def test_val063_require_secret_raises_secret_not_provisioned_instead_of_defaulting() -> None:
    with pytest.raises(SecretStoreError) as absent:
        require_secret({}, "ha_token")
    assert absent.value.state is SecretState.SECRET_NOT_PROVISIONED
    assert absent.value.key == "ha_token"

    # An *empty* row is the same failure as an absent one: "" is not a value.
    with pytest.raises(SecretStoreError) as empty:
        require_secret({"ha_token": ""}, "ha_token")
    assert empty.value.state is SecretState.SECRET_NOT_PROVISIONED

    assert require_secret({"ha_token": "abc"}, "ha_token") == "abc"


def test_val063_require_dek_raises_secret_store_unsealed_when_the_dek_is_absent() -> None:
    with pytest.raises(SecretStoreError) as error:
        require_dek({}, tier2_rows_exist=True)
    assert error.value.state is SecretState.SECRET_STORE_UNSEALED
    assert error.value.key == "HOMEIQ_SECRET_DEK"


def test_val063_store_unavailable_and_preflight_failure_carry_their_named_states() -> None:
    unavailable = store_unavailable("connection refused")
    assert unavailable.state is SecretState.SECRET_STORE_UNAVAILABLE
    assert unavailable.retryable is True

    preflight = preflight_failure("POSTGRES_PASSWORD", "/var/lib/homeiq/.env")
    assert preflight.state is SecretState.PREFLIGHT_FAILURE
    assert preflight.key == "POSTGRES_PASSWORD"
    assert preflight.retryable is False


def test_val063_no_accessor_accepts_a_default_value() -> None:
    """The structural guard against the failure mode the ADR names.

    ``require_secret(rows, key, default="changeme")`` is the shape that would
    turn every named state above back into a silent fallback. There is no
    parameter through which one can be supplied.
    """
    for accessor in (require_secret, require_dek):
        params = inspect.signature(accessor).parameters
        assert "default" not in params
        assert "fallback" not in params
        for name, param in params.items():
            if name in {"values", "key"}:
                assert param.default is inspect.Parameter.empty, name


def test_val063_the_error_message_names_the_state_and_the_key() -> None:
    error = preflight_failure("INFLUXDB_TOKEN", "/var/lib/homeiq/.env")
    rendered = str(error)
    assert "preflight-failure" in rendered
    assert "INFLUXDB_TOKEN" in rendered


def test_the_secrets_subpackage_does_not_shadow_the_stdlib_secrets_module() -> None:
    """``homeiq_ha.agent.onboarding`` does ``import secrets`` for token_urlsafe."""
    assert hasattr(stdlib_secrets, "token_urlsafe")
    assert "homeiq_ha" not in (stdlib_secrets.__file__ or "")
