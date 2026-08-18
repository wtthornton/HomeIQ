"""Config-checked Home Assistant core restart, polled back to life.

Shared by every recipe whose change only lands after a full restart: a custom
component dropped into ``custom_components/`` (:mod:`.powercalc`) and the
``http:`` / ``recorder:`` blocks of ``configuration.yaml``
(:mod:`.config_yaml`) — none of which HA can reload in place.

Two live behaviours are encoded here rather than rediscovered per caller
(observed 2026-08-13 on HA 2026.8.1):

1. HA drops the HTTP connection as it shuts down, so the restart service call
   raises ``aiohttp.ServerDisconnectedError`` — a ``ClientError``, which is
   neither ``OSError`` nor ``HAClientError``, and
   :meth:`~homeiq_ha.client.rest.HARestClient.request` does not wrap transport
   errors. The service call is therefore never the proof that a restart
   happened; the poll below is, and a poll that never succeeds raises.
2. Polling immediately sees the *old* instance still ``RUNNING`` and would
   report success before it has even exited, so the wait starts with a
   deliberate floor.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import aiohttp

from homeiq_ha.client.errors import HAClientError

#: How long to wait for the core to come back before giving up.
RESTART_TIMEOUT = 240.0
#: Gap between ``/api/config`` polls while the core is down.
RESTART_POLL_INTERVAL = 5.0
#: Floor before the first poll, so a still-running old instance is not
#: mistaken for a restarted new one.
RESTART_MIN_WAIT = 15.0


async def restart_core(
    ha: Any,
    *,
    timeout: float = RESTART_TIMEOUT,
    poll_interval: float = RESTART_POLL_INTERVAL,
    min_wait: float = RESTART_MIN_WAIT,
) -> None:
    """Restart Home Assistant core and wait until it reports ``RUNNING``.

    The configuration is validated first: restarting into a broken
    ``configuration.yaml`` leaves an instance that will not boot, which no
    caller can undo remotely.

    Args:
        ha: The client. Must be the unguarded one — this writes.
        timeout: Seconds to wait for ``state == "RUNNING"`` after the restart.
        poll_interval: Gap between polls.
        min_wait: Floor before the first poll.

    Raises:
        HAClientError: the config check did not return ``valid``, or the core
            did not come back within ``timeout``.
    """
    check = await ha.rest.check_config()
    if (check or {}).get("result") != "valid":
        raise HAClientError(f"refusing to restart: config check returned {check!r}")

    with contextlib.suppress(HAClientError, OSError, aiohttp.ClientError):
        await ha.rest.call_service("homeassistant", "restart")

    await asyncio.sleep(min_wait)
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            config = await ha.rest.request("GET", "/api/config")
            if (config or {}).get("state") == "RUNNING":
                break
        except (HAClientError, OSError, aiohttp.ClientError):
            pass  # still rebooting; the deadline below bounds the wait
        if asyncio.get_running_loop().time() > deadline:
            raise HAClientError(f"HA did not reach state RUNNING within {timeout}s of the restart")
        await asyncio.sleep(poll_interval)

    # The restart killed the WebSocket; reconnect it for the reads that follow
    # (the client has no auto-reconnect on this path).
    await ha.ws.close()
    await ha.ws.connect()


__all__ = [
    "RESTART_MIN_WAIT",
    "RESTART_POLL_INTERVAL",
    "RESTART_TIMEOUT",
    "restart_core",
]
