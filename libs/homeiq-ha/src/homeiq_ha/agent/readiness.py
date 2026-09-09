"""Authenticated readiness gate for the appliance's own Home Assistant (TAP-6467).

``GET /manifest.json`` needs no auth and answers 200 the instant the HTTP
listener is up -- long before Home Assistant's config layer, which the stored
credential authenticates against, exists. That makes it a liveness probe, not a
readiness one: a port that accepts connections and serves ``/manifest.json``
while still booting has, on every observed HA start, returned no valid response
from an authenticated endpoint yet. So this gate never touches
``/manifest.json``; it makes one authenticated call to :data:`READINESS_PATH`
with the stored owner credential and classifies the result:

- ``200`` -- the instance is up *and* the credential is accepted: ``ready``.
- ``401``/``403`` -- the instance is up but the credential is rejected: a
  distinct ``credential-rejected``, never folded into ``not-ready`` or
  ``unreachable``.
- anything else (a non-2xx status, a connection refusal, a timeout) --
  ``not-ready`` or ``unreachable``, never assumed ready.

The credential itself comes from the tier-2 secret store
(:func:`homeiq_ha.secrets.store.load_ha_token`) by default -- never
``HA_TOKEN``/``HOME_ASSISTANT_TOKEN`` read from the host environment, and never
persisted here. Before onboarding, the store simply has no row yet
(``SecretNotProvisioned``), which this module reports as
``not-ready:no-credential`` rather than raising.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import aiohttp

from homeiq_ha.secrets.states import SecretState, SecretStoreError
from homeiq_ha.secrets.store import load_ha_token

logger = logging.getLogger(__name__)

#: The authenticated endpoint the gate probes. Any endpoint under ``/api/``
#: requires a valid bearer token; this one is cheap and side-effect-free.
READINESS_PATH = "/api/config"

#: Per-attempt bound. A probe that neither succeeds nor fails within this many
#: seconds is treated as unreachable rather than hung forever.
DEFAULT_READINESS_TIMEOUT = 5.0

#: Default bound for :func:`poll_until_ready`. Startup is polled, never assumed.
DEFAULT_POLL_DEADLINE = 30.0
DEFAULT_POLL_INTERVAL = 1.0


class ReadinessState(StrEnum):
    """Named outcomes of one readiness probe."""

    READY = "ready"
    NOT_READY = "not-ready"
    CREDENTIAL_REJECTED = "credential-rejected"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """The outcome of one probe, plus why for anything short of ``ready``."""

    state: ReadinessState
    reason: str = ""

    @property
    def ready(self) -> bool:
        return self.state is ReadinessState.READY

    @property
    def named(self) -> str:
        """The wire-level name: ``ready`` / ``credential-rejected`` /
        ``unreachable`` / ``not-ready:<reason>``."""
        if self.state is ReadinessState.NOT_READY and self.reason:
            return f"not-ready:{self.reason}"
        return self.state.value


class HttpProbe(Protocol):
    """What the gate needs from an HTTP client.

    Production uses :class:`AiohttpProbe`; tests inject a fake that returns a
    fixed status or raises, so the gate is exercised against an in-process
    double rather than a real socket.
    """

    async def get(self, url: str, *, headers: dict[str, str], timeout: float) -> int:
        """Return the response status code. Raise on connection failure."""
        ...


class AiohttpProbe:
    """The real probe: one GET, its own bounded ``ClientTimeout``."""

    async def get(self, url: str, *, headers: dict[str, str], timeout: float) -> int:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with (
            aiohttp.ClientSession(timeout=client_timeout) as session,
            session.get(url, headers=headers) as response,
        ):
            return response.status


def _reason_for_secret_error(exc: SecretStoreError) -> str:
    if exc.state is SecretState.SECRET_NOT_PROVISIONED:
        return "no-credential"
    return "secret-store-unsealed"


async def check_readiness(
    base_url: str,
    *,
    token: str | None = None,
    probe: HttpProbe | None = None,
    timeout: float = DEFAULT_READINESS_TIMEOUT,
) -> ReadinessResult:
    """One authenticated readiness probe against THIS appliance's Home Assistant.

    Args:
        base_url: The appliance's own HA HTTP base URL (e.g. ``HA_URL``). Never
            a customer-supplied value persisted anywhere -- it is read at the
            call site and used once.
        token: Overrides the stored credential -- tests only. Production
            callers omit it, so the gate reads
            :func:`homeiq_ha.secrets.store.load_ha_token` and never
            ``HA_TOKEN``/``HOME_ASSISTANT_TOKEN`` from the process
            environment.
        probe: Overrides the HTTP transport -- tests only.
        timeout: Bound on the single attempt, in seconds. Startup is polled
            (see :func:`poll_until_ready`), never assumed instantaneous.
    """
    if token is None:
        try:
            token = load_ha_token()
        except SecretStoreError as exc:
            return ReadinessResult(ReadinessState.NOT_READY, _reason_for_secret_error(exc))

    prober = probe or AiohttpProbe()
    url = f"{base_url.rstrip('/')}{READINESS_PATH}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        status = await asyncio.wait_for(
            prober.get(url, headers=headers, timeout=timeout), timeout=timeout
        )
    except TimeoutError:
        return ReadinessResult(ReadinessState.UNREACHABLE, "timeout")
    except (aiohttp.ClientError, OSError) as exc:
        return ReadinessResult(ReadinessState.UNREACHABLE, type(exc).__name__)

    if status in (401, 403):
        return ReadinessResult(ReadinessState.CREDENTIAL_REJECTED, f"http-{status}")
    if status == 200:
        return ReadinessResult(ReadinessState.READY)
    return ReadinessResult(ReadinessState.NOT_READY, f"http-{status}")


async def poll_until_ready(
    base_url: str,
    *,
    token: str | None = None,
    probe: HttpProbe | None = None,
    timeout: float = DEFAULT_READINESS_TIMEOUT,
    interval: float = DEFAULT_POLL_INTERVAL,
    deadline: float = DEFAULT_POLL_DEADLINE,
) -> ReadinessResult:
    """Poll :func:`check_readiness` until ``ready`` or ``deadline`` elapses.

    Bounded by construction: the loop's own clock, not the probe's timeout,
    caps total wall time, so a probe that always answers quickly but never
    ``ready`` still returns by ``deadline``. A rejected credential is not a
    transient boot condition -- retrying it cannot change the outcome -- so
    that state returns immediately instead of being polled to the deadline.
    """
    loop = asyncio.get_running_loop()
    start = loop.time()
    result = await check_readiness(base_url, token=token, probe=probe, timeout=timeout)
    while (
        not result.ready
        and result.state is not ReadinessState.CREDENTIAL_REJECTED
        and loop.time() - start < deadline
    ):
        await asyncio.sleep(interval)
        result = await check_readiness(base_url, token=token, probe=probe, timeout=timeout)
    return result


__all__ = [
    "DEFAULT_POLL_DEADLINE",
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_READINESS_TIMEOUT",
    "READINESS_PATH",
    "AiohttpProbe",
    "HttpProbe",
    "ReadinessResult",
    "ReadinessState",
    "check_readiness",
    "poll_until_ready",
]
