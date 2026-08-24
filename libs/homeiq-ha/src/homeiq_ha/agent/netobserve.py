"""Passive LAN observation for the init agent.

The init agent's container sits on a docker bridge and cannot see LAN layer 2,
so it does not scan anything. ``zeek-network-service`` owns observation: a
host-network Zeek sensor writes ``dhcp.log``, the service parses it and
resolves each MAC against the IEEE registry, and this module reads the result.

Kept separate from :mod:`.unclaimed` so the recipe depends on the
:class:`NetworkObserver` protocol rather than on HTTP.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import aiohttp


@dataclass(frozen=True)
class ObservedHost:
    """One device seen on the local network by a passive sensor.

    ``mac`` is the identity. ``ip`` is a mutable address and ``hostname`` is a
    name; neither is used as a key.
    """

    mac: str
    ip: str | None = None
    hostname: str | None = None
    vendor: str | None = None

    @property
    def mac_digits(self) -> str:
        return self.mac.upper().replace(":", "").replace("-", "").replace(".", "")


@runtime_checkable
class NetworkObserver(Protocol):
    """Source of passively observed LAN hosts.

    Injected rather than constructed so the recipe can report
    ``NOT_APPLICABLE`` when no sensor is deployed, instead of claiming a clean
    network it never looked at.
    """

    async def observed_hosts(self) -> list[ObservedHost]: ...


class ZeekNetworkObserver:
    """Reads observed hosts from zeek-network-service's fingerprint store.

    That service is the upstream owner of LAN observation: it runs beside a
    host-network Zeek sensor, parses ``dhcp.log``, and resolves each MAC
    against the IEEE registry. This recipe consumes its output rather than
    scanning the network itself — the init agent's container sits on a docker
    bridge and cannot see LAN layer 2 at all.

    Note the coverage boundary this inherits: a device that never renewed a
    DHCP lease inside the capture window is not in the store, so an empty
    result means "nothing observed", never "nothing present".
    """

    #: Only DHCP records seen in this window are returned. 720 h is the
    #: service's maximum and matches how slowly IoT leases turn over.
    DEFAULT_WINDOW_HOURS = 720

    def __init__(self, base_url: str, *, hours: int = DEFAULT_WINDOW_HOURS, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._hours = hours
        self._timeout = timeout

    async def observed_hosts(self) -> list[ObservedHost]:
        url = f"{self._base_url}/devices/discovered"
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(url, params={"hours": self._hours}) as response,
        ):
            # A 503 means the fingerprint schema is not at head. Surfacing it
            # beats treating an unavailable store as an empty network.
            response.raise_for_status()
            rows = await response.json()

        return [
            ObservedHost(
                mac=row["mac_address"],
                ip=row.get("ip_address"),
                hostname=row.get("hostname"),
                vendor=row.get("vendor"),
            )
            for row in rows or []
            if row.get("mac_address")
        ]


def observer_from_env() -> NetworkObserver | None:
    """Build the observer from ``HOMEIQ_NETWORK_OBSERVER_URL``, or ``None``.

    Returning ``None`` is meaningful: the recipe then reports
    ``NOT_APPLICABLE`` rather than ``SATISFIED``, so an unconfigured sensor
    never reads as a network with nothing on it.
    """
    url = os.environ.get("HOMEIQ_NETWORK_OBSERVER_URL", "").strip()
    return ZeekNetworkObserver(url) if url else None


__all__ = [
    "NetworkObserver",
    "ObservedHost",
    "ZeekNetworkObserver",
    "observer_from_env",
]
