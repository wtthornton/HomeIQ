"""Tests for first-boot HA onboarding and credential minting (TAP-6484).

The live flow is verified against a real `homeiq/home-assistant:2026.8.3`
container; these cover the parts that must hold without one — the generators,
the idempotency gate, and every named failure state. Each mocked dependency has
a failing counterpart, because a success-only mock tests that the happy path
compiles, not that the integration works.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from homeiq_ha.agent.onboarding import (
    HAOnboarder,
    OnboardingError,
    OnboardingState,
    OwnerCredential,
    generate_deployment_secrets,
    generate_password,
    generate_secret,
)

# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------


def test_generated_passwords_are_distinct() -> None:
    """Constant-across-installs is the exact bug this story exists to prevent."""
    assert len({generate_password() for _ in range(200)}) == 200


def test_password_honours_requested_length() -> None:
    assert len(generate_password(48)) == 48


def test_password_below_the_floor_is_refused() -> None:
    with pytest.raises(ValueError, match="below the 16-character floor"):
        generate_password(8)


def test_password_is_shell_and_url_safe() -> None:
    """These land in env files and compose interpolation; a `$` or quote there
    turns a valid secret into a parse error or a silently truncated value."""
    password = generate_password(256)
    assert password.isalnum()


def test_secret_below_the_floor_is_refused() -> None:
    with pytest.raises(ValueError, match="below the 16-byte floor"):
        generate_secret(8)


def test_deployment_secrets_are_distinct_per_key() -> None:
    """Reusing one value across keys would make a single leak total."""
    keys = ["POSTGRES_PASSWORD", "API_KEY", "JWT_SECRET_KEY", "INFLUXDB_TOKEN"]
    secrets_map = generate_deployment_secrets(keys)
    assert sorted(secrets_map) == sorted(keys)
    assert len(set(secrets_map.values())) == len(keys)


def test_deployment_secrets_of_no_keys_is_empty() -> None:
    assert generate_deployment_secrets([]) == {}


# --------------------------------------------------------------------------
# Credential redaction
# --------------------------------------------------------------------------


def test_credential_repr_hides_token_and_password() -> None:
    """repr lands in logs and tracebacks; leaking there defeats generation."""
    cred = OwnerCredential(token="t" * 183, username="homeiq", password="hunter2hunter2xy")
    rendered = repr(cred)
    assert "t" * 183 not in rendered
    assert "hunter2hunter2xy" not in rendered
    assert "redacted" in rendered
    assert "homeiq" in rendered


# --------------------------------------------------------------------------
# Idempotency and failure states
# --------------------------------------------------------------------------


class _FakeOnboarder(HAOnboarder):
    """Overrides only the network edges, so the real control flow is exercised."""

    def __init__(self, steps: dict[str, bool], **overrides: Any) -> None:
        super().__init__(base_url="http://ha.invalid")
        self._steps = steps
        self._overrides = overrides
        #: Every argument the real flow hands each edge, so tests can assert the
        #: generated password actually reaches HA rather than being dropped.
        self.calls: dict[str, dict[str, Any]] = {}

    async def onboarding_steps(self) -> dict[str, bool]:
        return self._steps

    async def _create_owner(self, username: str, password: str) -> str:
        self.calls["create"] = {"username": username, "password": password}
        if "create" in self._overrides:
            raise self._overrides["create"]
        return "auth-code"

    async def _exchange_code(self, auth_code: str) -> str:
        self.calls["exchange"] = {"auth_code": auth_code}
        if "exchange" in self._overrides:
            raise self._overrides["exchange"]
        return "short-lived"

    async def _mint_long_lived(self, access_token: str, lifespan_days: int) -> str:
        self.calls["mint"] = {"access_token": access_token, "lifespan_days": lifespan_days}
        if "mint" in self._overrides:
            raise self._overrides["mint"]
        return "long-lived-token"


def test_second_boot_does_not_reonboard() -> None:
    """A second boot must reuse the stored credential, never mint a second owner."""
    onboarder = _FakeOnboarder({"user": True, "core_config": False})
    with pytest.raises(OnboardingError) as excinfo:
        asyncio.run(onboarder.onboard())
    assert excinfo.value.state is OnboardingState.ALREADY_ONBOARDED


def test_first_boot_mints_a_credential() -> None:
    onboarder = _FakeOnboarder({"user": False})
    cred = asyncio.run(onboarder.onboard())
    assert cred.token == "long-lived-token"
    assert cred.state is OnboardingState.COMPLETED
    assert len(cred.password) == 32


def test_generated_password_reaches_ha_and_the_code_is_threaded_through() -> None:
    """The returned credential must be the one actually sent, and each step must
    consume the previous step's output — a plausible-looking token that was never
    plumbed through is the failure this asserts against."""
    onboarder = _FakeOnboarder({"user": False})
    cred = asyncio.run(onboarder.onboard(lifespan_days=99))
    assert onboarder.calls["create"]["password"] == cred.password
    assert onboarder.calls["create"]["username"] == cred.username
    assert onboarder.calls["exchange"]["auth_code"] == "auth-code"
    assert onboarder.calls["mint"]["access_token"] == "short-lived"
    assert onboarder.calls["mint"]["lifespan_days"] == 99


def test_caller_supplied_password_is_used() -> None:
    onboarder = _FakeOnboarder({"user": False})
    cred = asyncio.run(onboarder.onboard(password="supplied-password-value"))
    assert cred.password == "supplied-password-value"


@pytest.mark.parametrize(
    ("failing_step", "expected"),
    [
        ("create", OnboardingState.USER_STEP_REJECTED),
        ("exchange", OnboardingState.TOKEN_EXCHANGE_FAILED),
        ("mint", OnboardingState.LONG_LIVED_MINT_FAILED),
    ],
)
def test_each_step_failure_surfaces_its_named_state(
    failing_step: str, expected: OnboardingState
) -> None:
    """Never a silent fallback to a default credential — that would reintroduce
    the constant-secret problem generation exists to avoid."""
    error = OnboardingError(expected, "boom")
    onboarder = _FakeOnboarder({"user": False}, **{failing_step: error})
    with pytest.raises(OnboardingError) as excinfo:
        asyncio.run(onboarder.onboard())
    assert excinfo.value.state is expected


def test_onboarding_error_message_names_the_state() -> None:
    error = OnboardingError(OnboardingState.UNREACHABLE, "connection refused")
    assert "unreachable" in str(error)
    assert "connection refused" in str(error)


def test_client_id_is_a_url_with_trailing_slash() -> None:
    """HA validates client_id as a URL matching the request origin."""
    assert HAOnboarder("http://localhost:8123")._client_id == "http://localhost:8123/"
    assert HAOnboarder("http://localhost:8123/")._client_id == "http://localhost:8123/"
