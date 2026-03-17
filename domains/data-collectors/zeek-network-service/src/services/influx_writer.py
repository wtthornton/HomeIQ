"""InfluxDB writer with retry, DNS fallback, and in-memory buffering.

When InfluxDB is unavailable, points are buffered in memory for up to
5 minutes (configurable). On recovery, buffered points are flushed.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import InfluxDBClient3, Point

if TYPE_CHECKING:
    from ..config import Settings

logger = setup_logging("zeek-influx-writer")


class InfluxWriter:
    """Manages InfluxDB writes with retry, fallback, and buffering."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.client: InfluxDBClient3 | None = None
        self.working_url: str | None = None

        # Parse InfluxDB URLs with fallbacks
        self._urls = self._build_url_list(settings)

        # Stats
        self.write_success_count: int = 0
        self.write_failure_count: int = 0
        self.last_write_time: datetime | None = None
        self.last_write_error: str | None = None

        # In-memory buffer for InfluxDB outages
        self._buffer: list[Point] = []
        self._buffer_start_time: float | None = None
        self._buffer_max_seconds = settings.influx_buffer_max_seconds
        self._max_retries = settings.influxdb_write_retries

    @staticmethod
    def _build_url_list(settings: Settings) -> list[str]:
        """Build list of InfluxDB URLs from primary + fallback hosts."""
        primary = settings.influxdb_url
        urls = [primary]

        # Extract port from primary URL
        port = "8086"
        if "://" in primary:
            host_port = primary.split("://")[1].rstrip("/")
            if ":" in host_port:
                port = host_port.split(":")[1].split("/")[0]

        fallbacks = [
            h.strip()
            for h in settings.influxdb_fallback_hosts.split(",")
            if h.strip()
        ]
        for host in fallbacks:
            url = f"http://{host}:{port}"
            if url != primary:
                urls.append(url)

        return urls

    async def initialize(self) -> None:
        """Connect to InfluxDB, trying each URL in order."""
        token = (
            self._settings.influxdb_token.get_secret_value()
            if self._settings.influxdb_token
            else None
        )
        if not token:
            logger.error("INFLUXDB_TOKEN not set — writes will fail")
            return

        for url in self._urls:
            try:
                logger.info("Attempting InfluxDB connection at %s", url)
                client = InfluxDBClient3(
                    host=url,
                    token=token,
                    database=self._settings.influxdb_bucket,
                    org=self._settings.influxdb_org,
                )
                await asyncio.to_thread(client.query, "SELECT 1")
                self.client = client
                self.working_url = url
                logger.info("[OK] InfluxDB connected at %s", url)
                return
            except Exception as e:
                logger.warning("InfluxDB connection failed at %s: %s", url, e)

        logger.error("[FAIL] All InfluxDB URLs failed: %s", self._urls)

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    async def write_points(self, points: list[Point]) -> None:
        """Write multiple points as a batch, buffering on failure."""
        if not points:
            return

        if not self.client:
            for point in points:
                await self._buffer_point(point)
            return

        for attempt in range(1, self._max_retries + 1):
            try:
                await asyncio.to_thread(self.client.write, points)
                self.write_success_count += len(points)
                self.last_write_time = datetime.now(UTC)
                self.last_write_error = None

                if self._buffer:
                    await self._flush_buffer()

                return
            except Exception as e:
                error_str = str(e)
                self.last_write_error = error_str
                is_dns_error = (
                    "Name does not resolve" in error_str
                    or "Failed to resolve" in error_str
                )

                if is_dns_error:
                    logger.warning(
                        "DNS failure (attempt %d/%d), reconnecting...",
                        attempt,
                        self._max_retries,
                    )
                    await self._reconnect()
                    if not self.client:
                        break

                if attempt >= self._max_retries:
                    self.write_failure_count += len(points)
                    logger.error(
                        "InfluxDB batch write failed after %d attempts: %s",
                        attempt,
                        e,
                    )
                    for point in points:
                        await self._buffer_point(point)
                    return

                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "InfluxDB batch write failed (attempt %d/%d), retrying in %ds",
                    attempt,
                    self._max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)

    async def write_point(self, point: Point) -> None:
        """Write a single point with retry and buffer fallback."""
        if not self.client:
            await self._buffer_point(point)
            return

        for attempt in range(1, self._max_retries + 1):
            try:
                await asyncio.to_thread(self.client.write, point)
                self.write_success_count += 1
                self.last_write_time = datetime.now(UTC)
                self.last_write_error = None

                # Flush buffer on successful write
                if self._buffer:
                    await self._flush_buffer()

                return
            except Exception as e:
                error_str = str(e)
                self.last_write_error = error_str
                is_dns_error = (
                    "Name does not resolve" in error_str
                    or "Failed to resolve" in error_str
                )

                if is_dns_error:
                    logger.warning(
                        "DNS failure (attempt %d/%d), reconnecting...",
                        attempt,
                        self._max_retries,
                    )
                    await self._reconnect()
                    if not self.client:
                        break

                if attempt >= self._max_retries:
                    self.write_failure_count += 1
                    logger.error(
                        "InfluxDB write failed after %d attempts: %s", attempt, e
                    )
                    await self._buffer_point(point)
                    return

                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "InfluxDB write failed (attempt %d/%d), retrying in %ds",
                    attempt,
                    self._max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)

    async def _buffer_point(self, point: Point) -> None:
        """Add point to in-memory buffer, dropping oldest if expired."""
        now = time.time()

        if self._buffer_start_time is None:
            self._buffer_start_time = now

        # Drop buffer if it's been too long
        if now - self._buffer_start_time > self._buffer_max_seconds:
            dropped = len(self._buffer)
            self._buffer.clear()
            self._buffer_start_time = now
            if dropped:
                logger.warning(
                    "Dropped %d buffered points (exceeded %ds buffer window)",
                    dropped,
                    self._buffer_max_seconds,
                )

        self._buffer.append(point)
        if len(self._buffer) % 100 == 1:
            logger.info("Buffering points (count: %d)", len(self._buffer))

    async def _flush_buffer(self) -> None:
        """Flush buffered points to InfluxDB as a batch."""
        if not self._buffer or not self.client:
            return

        points = self._buffer.copy()
        self._buffer.clear()
        self._buffer_start_time = None

        try:
            await asyncio.to_thread(self.client.write, points)
            self.write_success_count += len(points)
            logger.info("Flushed %d buffered points", len(points))
        except Exception as e:
            self.write_failure_count += len(points)
            logger.error("Failed to flush %d buffered points: %s", len(points), e)

    async def _reconnect(self) -> None:
        """Attempt to reconnect to InfluxDB using fallback URLs."""
        old_client = self.client
        self.client = None
        await self.initialize()
        if self.client and self.client != old_client:
            logger.info("Reconnected to InfluxDB at %s", self.working_url)

    async def close(self) -> None:
        """Close the InfluxDB client."""
        if self.client:
            self.client.close()
            self.client = None
