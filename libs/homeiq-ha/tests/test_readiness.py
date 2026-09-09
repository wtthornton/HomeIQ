"""Authenticated readiness gate (TAP-6467).

The thing that would silently give a wrong result: a check that is satisfied
by ``/manifest.json`` returning 200. Every fake probe here answers on
whatever path it is given, so a gate that accidentally hits an unauthenticated
path instead of :data:`READINESS_PATH` would still need a passing fake to
prove it -- ``test_manifest_200_but_api_401_is_not_ready`` is that proof: the
fake serves 200 on ``/manifest.json`` and 401 on the authenticated path, and
the gate must land on ``credential-rejected``, not ``ready``.
"""

from __future__ import annotations

import asyncio

import pytest
from homeiq_ha.agent.readiness import (
    READINESS_PATH,
    HttpProbe,
    ReadinessState,
    check_readiness,
    poll_until_ready,
)
from homeiq_ha.secrets.states import SecretState, SecretStoreError


class _FixedStatusProbe:
    """Answers every GET with a fixed status code, whatever the path."""

    def __init__(self, status: int) -> None:
        self.status = status
        self.calls: list[tuple[str, dict[str, str], float]] = []

    async def get(self, url: str, *, headers: dict[str, str], timeout: float) -> int:
        self.calls.append((url, headers, timeout))
        return self.status


class _PathAwareProbe:
    """Serves 200 on manifest.json and a different status on the readiness path."""

    def __init__(self, readiness_status: int) -> None:
        self.readiness_status = readiness_status

    async def get(self, url: str, **_kwargs: object) -> int:
        if url.endswith("/manifest.json"):
            return 200
        assert url.endswith(READINESS_PATH)
        return self.readiness_status


class _RaisingProbe:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def get(self, _url: str, **_kwargs: object) -> int:
        raise self.exc


class _HangingProbe:
    """Never returns within the bound -- proves the timeout, not just accepts it."""

    async def get(self, _url: str, *, timeout: float, **_kwargs: object) -> int:
        await asyncio.sleep(timeout + 5)
        return 200


class _SequenceProbe:
    """Returns each status in order, once per call -- the cold-start race."""

    def __init__(self, statuses: list[int]) -> None:
        self._statuses = list(statuses)

    async def get(self, _url: str, **_kwargs: object) -> int:
        return self._statuses.pop(0)


@pytest.mark.asyncio
async def test_manifest_200_but_api_401_is_not_ready() -> None:
    """A liveness 200 on /manifest.json must never read as readiness."""
    result = await check_readiness("http://ha.local:8123", token="tok", probe=_PathAwareProbe(401))
    assert result.state is ReadinessState.CREDENTIAL_REJECTED
    assert not result.ready


@pytest.mark.asyncio
async def test_authenticated_200_is_ready() -> None:
    probe = _FixedStatusProbe(200)
    result = await check_readiness("http://ha.local:8123", token="tok", probe=probe)
    assert result.ready
    assert result.named == "ready"
    (url, headers, _timeout) = probe.calls[0]
    assert url == f"http://ha.local:8123{READINESS_PATH}"
    assert headers["Authorization"] == "Bearer tok"


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.asyncio
async def test_401_and_403_are_credential_rejected_distinct_from_unreachable(
    status: int,
) -> None:
    result = await check_readiness(
        "http://ha.local:8123", token="tok", probe=_FixedStatusProbe(status)
    )
    assert result.state is ReadinessState.CREDENTIAL_REJECTED
    assert result.state is not ReadinessState.UNREACHABLE
    assert result.named == "credential-rejected"


@pytest.mark.asyncio
async def test_non_2xx_non_auth_status_is_not_ready_with_reason() -> None:
    """A port that accepts connections but returns no valid API response
    (e.g. 500 while the config layer is still loading) is not-ready, not ready."""
    result = await check_readiness(
        "http://ha.local:8123", token="tok", probe=_FixedStatusProbe(500)
    )
    assert result.state is ReadinessState.NOT_READY
    assert result.named == "not-ready:http-500"


@pytest.mark.asyncio
async def test_connection_refused_is_unreachable() -> None:
    result = await check_readiness(
        "http://ha.local:8123",
        token="tok",
        probe=_RaisingProbe(ConnectionRefusedError("refused")),
    )
    assert result.state is ReadinessState.UNREACHABLE


@pytest.mark.asyncio
async def test_a_hung_probe_is_bounded_by_the_timeout_not_assumed_ready() -> None:
    result = await check_readiness(
        "http://ha.local:8123", token="tok", probe=_HangingProbe(), timeout=0.05
    )
    assert result.state is ReadinessState.UNREACHABLE
    assert result.named == "unreachable"
    assert result.reason == "timeout"


@pytest.mark.asyncio
async def test_missing_credential_is_not_ready_never_a_crash(monkeypatch) -> None:
    """Pre-onboarding, the store has no row -- SecretNotProvisioned -- and the
    gate must report that as standby, never raise and never read HA_TOKEN."""
    from homeiq_ha.agent import readiness as readiness_module

    def _raise_not_provisioned(**_kwargs: object) -> str:
        raise SecretStoreError(SecretState.SECRET_NOT_PROVISIONED, key="ha_token")

    monkeypatch.setattr(readiness_module, "load_ha_token", _raise_not_provisioned)
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HOME_ASSISTANT_TOKEN", raising=False)

    result = await check_readiness("http://ha.local:8123", probe=_FixedStatusProbe(200))

    assert result.state is ReadinessState.NOT_READY
    assert result.named == "not-ready:no-credential"


@pytest.mark.asyncio
async def test_unsealed_store_is_not_ready_with_a_distinct_reason(monkeypatch) -> None:
    from homeiq_ha.agent import readiness as readiness_module

    def _raise_unsealed(**_kwargs: object) -> str:
        raise SecretStoreError(SecretState.SECRET_STORE_UNSEALED, key="ha_token")

    monkeypatch.setattr(readiness_module, "load_ha_token", _raise_unsealed)

    result = await check_readiness("http://ha.local:8123", probe=_FixedStatusProbe(200))

    assert result.named == "not-ready:secret-store-unsealed"


@pytest.mark.asyncio
async def test_poll_until_ready_flips_from_not_ready_to_ready() -> None:
    """The cold-start race: HA answers not-ready, then ready, between polls."""
    probe = _SequenceProbe([500, 500, 200])
    result = await poll_until_ready(
        "http://ha.local:8123",
        token="tok",
        probe=probe,
        timeout=1.0,
        interval=0.0,
        deadline=5.0,
    )
    assert result.ready


@pytest.mark.asyncio
async def test_poll_until_ready_gives_up_at_the_deadline_never_unbounded() -> None:
    probe = _FixedStatusProbe(500)
    result = await poll_until_ready(
        "http://ha.local:8123", token="tok", probe=probe, timeout=0.05, interval=0.01, deadline=0.1
    )
    assert not result.ready
    assert result.state is ReadinessState.NOT_READY


@pytest.mark.asyncio
async def test_poll_until_ready_does_not_retry_a_rejected_credential() -> None:
    """Retrying a bad credential cannot change the outcome -- return immediately."""
    probe = _FixedStatusProbe(401)
    result = await poll_until_ready(
        "http://ha.local:8123", token="tok", probe=probe, timeout=1.0, interval=10.0, deadline=0.05
    )
    assert result.state is ReadinessState.CREDENTIAL_REJECTED
    assert len(probe.calls) == 1


def test_a_fake_implementing_get_satisfies_the_http_probe_shape() -> None:
    probe: HttpProbe = _FixedStatusProbe(200)
    assert callable(probe.get)
