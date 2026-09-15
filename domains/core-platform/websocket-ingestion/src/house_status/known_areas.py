"""The known-area set for the rooms roll-up, sourced from data-api (TAP-7587).

``HouseStatusAggregator`` only ever learns about an area once a presence
sensor reports for it (see ``aggregator.py``'s ``_room_occupancy`` cache), and
the discovery service does not retain its own copy of HA's area registry
after syncing it to data-api (``discovery_service.discover_areas`` returns a
list without caching it on ``self``). So the only place a zero-sensor area
can be found is data-api's ``areas`` table, via the internal, inter-service
``/internal/areas/list`` endpoint it already exposes for this purpose.
"""

from __future__ import annotations

import logging
import time

import aiohttp

logger = logging.getLogger(__name__)


class KnownAreasUnavailable(RuntimeError):
    """Raised when data-api's known-area set cannot be fetched."""


async def fetch_known_area_ids(
    data_api_url: str, api_key: str | None, timeout: float = 5.0
) -> list[str]:
    """Return every area_id known to data-api's areas table.

    Raises ``KnownAreasUnavailable`` on any network or non-200 response so
    the caller can fail closed rather than silently reporting an incomplete
    room list.
    """
    url = f"{data_api_url}/internal/areas/list"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response,
        ):
            if response.status != 200:
                raise KnownAreasUnavailable(f"data-api returned HTTP {response.status} for {url}")
            payload = await response.json()
    except aiohttp.ClientError as exc:
        raise KnownAreasUnavailable(f"data-api unreachable at {url}: {exc}") from exc

    return [area["area_id"] for area in payload.get("areas", []) if area.get("area_id")]


class KnownAreaCache:
    """In-process, TTL-bounded cache of the known-area set.

    The REST rooms route refreshes this on a cache miss; the WebSocket
    rooms section only ever reads it (never triggers a fetch) so a
    data-api outage degrades the live push to sensor-observed areas only
    instead of blocking or failing the WebSocket handshake.
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._area_ids: list[str] = []
        self._fetched_at: float = 0.0

    def get_cached(self) -> list[str]:
        """Return the last known-area set fetched, or ``[]`` if never warmed."""
        return list(self._area_ids)

    def is_stale(self) -> bool:
        """Return True if the cache has never been fetched or is past TTL."""
        return self._fetched_at == 0.0 or (time.monotonic() - self._fetched_at) >= (
            self._ttl_seconds
        )

    def update(self, area_ids: list[str]) -> None:
        """Replace the cached area-id set and reset the TTL clock."""
        self._area_ids = list(area_ids)
        self._fetched_at = time.monotonic()
