"""Per-device metric aggregation from parsed connection data.

Computes ``network_device_metrics`` InfluxDB measurement every 60 seconds
from in-memory connection state accumulated by conn_parser.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import Point

if TYPE_CHECKING:
    from .influx_writer import InfluxWriter

logger = setup_logging("zeek-device-aggregator")


class _DeviceWindow:
    """Accumulates connection metrics for a single device within an aggregation window."""

    __slots__ = (
        "bytes_sent",
        "bytes_recv",
        "connection_count",
        "destinations",
        "domains",
        "conn_durations",
        "services",
        "last_seen",
    )

    def __init__(self) -> None:
        self.bytes_sent: int = 0
        self.bytes_recv: int = 0
        self.connection_count: int = 0
        self.destinations: set[str] = set()
        self.domains: set[str] = set()
        self.conn_durations: list[float] = []
        self.services: set[str] = set()
        self.last_seen: datetime = datetime.now(UTC)

    def add_connection(
        self,
        dst_ip: str,
        orig_bytes: int,
        resp_bytes: int,
        duration: float,
        service: str,
    ) -> None:
        self.bytes_sent += orig_bytes
        self.bytes_recv += resp_bytes
        self.connection_count += 1
        self.destinations.add(dst_ip)
        if duration > 0:
            self.conn_durations.append(duration)
        if service and service != "unknown":
            self.services.add(service)
        self.last_seen = datetime.now(UTC)

    def add_dns_query(self, domain: str) -> None:
        self.domains.add(domain)

    @property
    def avg_conn_duration(self) -> float:
        if not self.conn_durations:
            return 0.0
        return sum(self.conn_durations) / len(self.conn_durations)


class DeviceAggregator:
    """Aggregates per-device network metrics and writes to InfluxDB.

    Uses a double-buffer pattern: ``_active`` accumulates new records from
    parsers, while ``_snapshot`` holds the last completed window for read
    endpoints. The swap is atomic (single assignment under GIL) so no lock
    is needed for the record path. Read endpoints iterate ``_snapshot``
    (immutable between swaps) for thread-safe iteration.
    """

    def __init__(self, influx_writer: InfluxWriter, service: object) -> None:
        self._influx_writer = influx_writer
        self._service = service
        self._active: dict[str, _DeviceWindow] = defaultdict(_DeviceWindow)
        self._snapshot: dict[str, _DeviceWindow] = {}

    async def run(self, interval: int) -> None:
        """Background loop: aggregate and write device metrics every ``interval`` seconds."""
        logger.info("Starting device aggregation (every %ds)", interval)
        while True:
            try:
                await asyncio.sleep(interval)
                await self._aggregate_and_write()
            except asyncio.CancelledError:
                logger.info("Device aggregator cancelled")
                raise
            except Exception as e:
                logger.error("Device aggregation error: %s", e)

    def record_connection(
        self,
        src_ip: str,
        dst_ip: str,
        orig_bytes: int,
        resp_bytes: int,
        duration: float,
        service: str,
    ) -> None:
        """Record a connection for aggregation (called by conn_parser)."""
        self._active[src_ip].add_connection(
            dst_ip, orig_bytes, resp_bytes, duration, service
        )

    def record_dns_query(self, device_ip: str, domain: str) -> None:
        """Record a DNS query for aggregation (called by dns_parser)."""
        self._active[device_ip].add_dns_query(domain)

    async def _aggregate_and_write(self) -> None:
        """Swap active buffer to snapshot, write to InfluxDB."""
        if not self._active:
            return

        # Atomic swap: parsers immediately start writing to new empty dict
        snapshot = self._active
        self._active = defaultdict(_DeviceWindow)
        # Expose completed window to read endpoints
        self._snapshot = snapshot

        now = datetime.now(UTC)
        points: list[Point] = []

        for device_ip, window in snapshot.items():
            point = (
                Point("network_device_metrics")
                .tag("device_ip", device_ip)
                .field("total_bytes_sent", window.bytes_sent)
                .field("total_bytes_recv", window.bytes_recv)
                .field("connection_count", window.connection_count)
                .field("unique_destinations", len(window.destinations))
                .field("unique_domains", len(window.domains))
                .field("avg_conn_duration", window.avg_conn_duration)
                .field("active_services", len(window.services))
                .time(now)
            )
            points.append(point)

        if points:
            await self._influx_writer.write_points(points)
            logger.debug("Wrote device metrics for %d devices", len(points))

    def _merged_devices(self) -> dict[str, _DeviceWindow]:
        """Merge snapshot and active windows for read endpoints."""
        merged = dict(self._snapshot)
        for ip, window in self._active.items():
            if ip in merged:
                # Active window has newer data — prefer it
                merged[ip] = window
            else:
                merged[ip] = window
        return merged

    def get_devices(self) -> list[dict[str, Any]]:
        """Return all discovered devices with latest metrics."""
        devices = []
        for ip, window in self._merged_devices().items():
            devices.append(
                {
                    "ip": ip,
                    "last_seen": window.last_seen.isoformat(),
                    "connections_window": window.connection_count,
                    "bytes_sent_window": window.bytes_sent,
                    "bytes_recv_window": window.bytes_recv,
                    "unique_destinations": len(window.destinations),
                    "unique_domains": len(window.domains),
                    "active_services": list(window.services),
                }
            )
        return sorted(devices, key=lambda d: d["bytes_sent_window"], reverse=True)

    def get_device(self, ip: str) -> dict[str, Any] | None:
        """Return detail for a single device, or None."""
        merged = self._merged_devices()
        window = merged.get(ip)
        if not window:
            return None
        return {
            "ip": ip,
            "last_seen": window.last_seen.isoformat(),
            "connections_window": window.connection_count,
            "bytes_sent_window": window.bytes_sent,
            "bytes_recv_window": window.bytes_recv,
            "unique_destinations": len(window.destinations),
            "unique_domains": len(window.domains),
            "top_destinations": sorted(window.destinations)[:10],
            "top_domains": sorted(window.domains)[:10],
            "active_services": list(window.services),
            "avg_conn_duration": window.avg_conn_duration,
        }

    def get_current_stats(self) -> dict[str, Any]:
        """Return current network stats: connections/min, bytes/min, top talkers."""
        merged = self._merged_devices()
        total_conns = sum(d.connection_count for d in merged.values())
        total_bytes = sum(
            d.bytes_sent + d.bytes_recv for d in merged.values()
        )

        # Top 5 talkers by total bytes
        top_talkers = sorted(
            [
                {
                    "ip": ip,
                    "total_bytes": w.bytes_sent + w.bytes_recv,
                    "connections": w.connection_count,
                }
                for ip, w in merged.items()
            ],
            key=lambda x: x["total_bytes"],
            reverse=True,
        )[:5]

        return {
            "active_devices": len(merged),
            "total_connections": total_conns,
            "total_bytes": total_bytes,
            "top_talkers": top_talkers,
        }
