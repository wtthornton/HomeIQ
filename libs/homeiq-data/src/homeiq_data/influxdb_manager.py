"""Managed InfluxDB client for HomeIQ services.

Consolidates 3 duplicate InfluxDB client implementations into a single
lifecycle manager, following the same pattern as ``DatabaseManager``.

Handles connection lifecycle, batch writes, queries, health checks,
and graceful shutdown.

Usage::

    from homeiq_data import InfluxDBManager

    influx = InfluxDBManager(
        url="http://influxdb:8086",
        token="my-token",
        org="homeiq",
        bucket="home_assistant_events",
    )

    # In lifespan:
    await influx.connect()

    # Write points:
    from influxdb_client import Point
    point = Point("temperature").tag("room", "living").field("value", 21.5)
    await influx.write_points([point])

    # Query:
    results = await influx.query(
        'from(bucket: "home_assistant_events") |> range(start: -1h)'
    )

    # Cleanup:
    await influx.close()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from influxdb_client import Point

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency when influxdb_client is not installed
_influxdb_module: Any = None


def _get_influxdb() -> Any:
    """Lazily import the influxdb_client module."""
    global _influxdb_module  # noqa: PLW0603
    if _influxdb_module is None:
        try:
            import influxdb_client

            _influxdb_module = influxdb_client
        except ImportError as exc:
            raise ImportError(
                "influxdb-client package is required. "
                "Install with: pip install influxdb-client"
            ) from exc
    return _influxdb_module


class InfluxDBManager:
    """Managed InfluxDB client with lifecycle, batch writes, and queries.

    Follows the same lifecycle pattern as ``DatabaseManager``:
    ``connect()`` on startup, ``close()`` on shutdown, with a
    ``check_health()`` method for health endpoints.

    Parameters
    ----------
    url:
        InfluxDB server URL (e.g. ``http://influxdb:8086``).
    token:
        InfluxDB authentication token.
    org:
        InfluxDB organization name.
    bucket:
        Default bucket for writes and queries.
    timeout:
        Connection/request timeout in seconds (default 30).
    write_retries:
        Number of retry attempts for write operations (default 3).
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        *,
        timeout: int = 30,
        write_retries: int = 3,
    ) -> None:
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._timeout = timeout
        self._write_retries = write_retries

        self._client: Any = None
        self._write_api: Any = None
        self._query_api: Any = None
        self._available = False

        # Statistics
        self._write_count = 0
        self._write_errors = 0
        self._query_count = 0
        self._query_errors = 0
        self._last_write: datetime | None = None
        self._last_error: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to InfluxDB and initialize write/query APIs.

        Never raises -- returns ``False`` on failure so services can
        start in degraded mode.

        Returns
        -------
        bool
            ``True`` if connection succeeded, ``False`` otherwise.
        """
        influxdb_client = _get_influxdb()
        try:
            self._client = influxdb_client.InfluxDBClient(
                url=self._url,
                token=self._token,
                org=self._org,
                timeout=self._timeout * 1000,
            )

            # Verify connectivity via the /health endpoint
            await self._ping()

            self._write_api = self._client.write_api(
                write_options=influxdb_client.client.write_api.SYNCHRONOUS,
            )
            self._query_api = self._client.query_api()
            self._available = True

            logger.info(
                "InfluxDBManager connected: url=%s org=%s bucket=%s",
                self._url,
                self._org,
                self._bucket,
            )
            return True

        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.error("InfluxDBManager connection failed: %s", exc)
            return False

    async def close(self) -> None:
        """Close the InfluxDB client and release resources."""
        try:
            if self._write_api is not None:
                self._write_api.close()
                self._write_api = None

            if self._client is not None:
                self._client.close()
                self._client = None

            self._query_api = None
            self._available = False
            logger.info("InfluxDBManager connections closed")

        except Exception as exc:
            logger.error("Error closing InfluxDBManager: %s", exc)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def write_points(
        self,
        points: list[Point],
        *,
        bucket: str | None = None,
    ) -> bool:
        """Write a list of Points to InfluxDB with retry.

        Parameters
        ----------
        points:
            List of ``influxdb_client.Point`` objects.
        bucket:
            Target bucket override (defaults to constructor bucket).

        Returns
        -------
        bool
            ``True`` if the write succeeded, ``False`` otherwise.
        """
        if not self._available or self._write_api is None:
            logger.error("InfluxDBManager not connected; cannot write")
            return False

        if not points:
            return True

        target_bucket = bucket or self._bucket

        for attempt in range(1, self._write_retries + 1):
            try:
                await asyncio.to_thread(
                    self._write_api.write,
                    bucket=target_bucket,
                    org=self._org,
                    record=points,
                )
                self._write_count += len(points)
                self._last_write = datetime.now(UTC)
                self._last_error = None
                logger.debug(
                    "Wrote %d points to bucket=%s",
                    len(points),
                    target_bucket,
                )
                return True

            except Exception as exc:
                self._last_error = str(exc)
                if attempt >= self._write_retries:
                    self._write_errors += len(points)
                    logger.error(
                        "InfluxDB write failed after %d attempts: %s",
                        attempt,
                        exc,
                    )
                    return False

                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "InfluxDB write failed (attempt %d/%d), retrying in %ds",
                    attempt,
                    self._write_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)

        return False  # pragma: no cover

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    async def query(
        self,
        flux_query: str,
        *,
        org: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Flux query and return results as dicts.

        Parameters
        ----------
        flux_query:
            Flux query string.
        org:
            Organization override (defaults to constructor org).

        Returns
        -------
        list[dict]
            List of record value dictionaries.
        """
        if not self._available or self._query_api is None:
            logger.error("InfluxDBManager not connected; cannot query")
            return []

        try:
            result = await asyncio.to_thread(
                self._query_api.query,
                query=flux_query,
                org=org or self._org,
            )

            data: list[dict[str, Any]] = []
            for table in result:
                for record in table.records:
                    data.append(record.values)

            self._query_count += 1
            logger.debug("Query returned %d records", len(data))
            return data

        except Exception as exc:
            self._query_errors += 1
            self._last_error = str(exc)
            logger.error("InfluxDB query failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Health & diagnostics
    # ------------------------------------------------------------------

    async def check_health(self) -> dict[str, Any]:
        """Check InfluxDB connectivity and return status dict.

        Always returns an HTTP-200-safe status. Never raises.
        """
        if not self._available or self._client is None:
            return {
                "status": "unavailable",
                "backend": "influxdb",
                "url": self._url,
                "bucket": self._bucket,
                "connection": "not initialized",
            }

        try:
            await self._ping()
            return {
                "status": "healthy",
                "backend": "influxdb",
                "url": self._url,
                "bucket": self._bucket,
                "connection": "ok",
                "write_count": self._write_count,
                "write_errors": self._write_errors,
                "query_count": self._query_count,
                "query_errors": self._query_errors,
                "last_write": (
                    self._last_write.isoformat() if self._last_write else None
                ),
            }

        except Exception as exc:
            logger.error("InfluxDBManager health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "backend": "influxdb",
                "url": self._url,
                "bucket": self._bucket,
                "connection": str(exc),
            }

    @property
    def available(self) -> bool:
        """Whether the client is connected and available."""
        return self._available

    @property
    def url(self) -> str:
        """The configured InfluxDB URL."""
        return self._url

    @property
    def bucket(self) -> str:
        """The default bucket name."""
        return self._bucket

    def get_stats(self) -> dict[str, Any]:
        """Return accumulated write/query statistics."""
        return {
            "write_count": self._write_count,
            "write_errors": self._write_errors,
            "query_count": self._query_count,
            "query_errors": self._query_errors,
            "last_write": (
                self._last_write.isoformat() if self._last_write else None
            ),
            "last_error": self._last_error,
            "available": self._available,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ping(self) -> None:
        """Verify InfluxDB is reachable via the /health endpoint."""
        import aiohttp

        async with aiohttp.ClientSession() as session, session.get(
            f"{self._url}/health",
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        ) as response:
            if response.status != 200:
                msg = f"InfluxDB health check failed: HTTP {response.status}"
                raise ConnectionError(msg)
