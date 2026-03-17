"""Parser for Zeek conn.log — connection metadata.

Reads JSON lines from conn.log, converts to InfluxDB points, and writes
to the ``network_connections`` measurement.
"""

from __future__ import annotations

import asyncio
import json
import ipaddress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import Point

if TYPE_CHECKING:
    from ..services.device_aggregator import DeviceAggregator
    from ..services.influx_writer import InfluxWriter
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-conn-parser")

# RFC1918 + IPv6 ULA/loopback ranges for direction classification
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),   # IPv6 ULA
    ipaddress.ip_network("::1/128"),    # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def _safe_int(val: object) -> int:
    """Convert a Zeek field value to int, handling '-' and None."""
    try:
        return int(val or 0)
    except (ValueError, TypeError):
        return 0


def _safe_float(val: object) -> float:
    """Convert a Zeek field value to float, handling '-' and None."""
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _is_private(ip_str: str) -> bool:
    """Check if an IP address is in a private range."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        return False


def _classify_direction(src_ip: str, dst_ip: str) -> str:
    """Classify connection direction: internal, outbound, or inbound."""
    src_private = _is_private(src_ip)
    dst_private = _is_private(dst_ip)
    if src_private and dst_private:
        return "internal"
    if src_private and not dst_private:
        return "outbound"
    return "inbound"


class ConnLogParser:
    """Parses Zeek conn.log and writes network_connections to InfluxDB."""

    def __init__(
        self,
        log_tracker: LogTracker,
        influx_writer: InfluxWriter,
        aggregator: DeviceAggregator,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._influx_writer = influx_writer
        self._aggregator = aggregator
        self._service = service

    async def run(self, interval: int) -> None:
        """Background loop: parse conn.log every ``interval`` seconds."""
        logger.info("Starting conn.log parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("conn.log parser cancelled")
                raise
            except Exception as e:
                logger.error("conn.log parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from conn.log, write to InfluxDB, feed aggregator."""
        lines = self._log_tracker.read_new_lines("conn.log")
        if not lines:
            return

        points: list[Point] = []
        for line in lines:
            result = self._parse_line(line)
            if result:
                point, parsed = result
                points.append(point)
                # Feed the device aggregator
                self._aggregator.record_connection(
                    src_ip=parsed["src_ip"],
                    dst_ip=parsed["dst_ip"],
                    orig_bytes=parsed["orig_bytes"],
                    resp_bytes=parsed["resp_bytes"],
                    duration=parsed["duration"],
                    service=parsed["service"],
                )

        if points:
            await self._influx_writer.write_points(points)
            self._service.conn_lines_parsed += len(points)
            logger.debug("Parsed %d conn.log entries", len(points))

        self._log_tracker.save_offsets()

    def _parse_line(self, line: str) -> tuple[Point, dict] | None:
        """Parse a single conn.log JSON line into an InfluxDB Point and raw fields.

        Returns:
            Tuple of (Point, parsed_fields_dict) or None if line is invalid.
        """
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON line in conn.log")
            return None

        src_ip = entry.get("id.orig_h", "")
        dst_ip = entry.get("id.resp_h", "")

        if not src_ip or not dst_ip:
            return None

        # Extract timestamp
        ts_value = entry.get("ts")
        if ts_value:
            try:
                timestamp = datetime.fromtimestamp(float(ts_value), tz=UTC)
            except (ValueError, TypeError, OSError):
                timestamp = datetime.now(UTC)
        else:
            timestamp = datetime.now(UTC)

        direction = _classify_direction(src_ip, dst_ip)
        service = entry.get("service", "unknown") or "unknown"
        duration = _safe_float(entry.get("duration"))
        orig_bytes = _safe_int(entry.get("orig_bytes"))
        resp_bytes = _safe_int(entry.get("resp_bytes"))

        point = (
            Point("network_connections")
            .tag("src_ip", src_ip)
            .tag("dst_ip", dst_ip)
            .tag("proto", entry.get("proto", "unknown"))
            .tag("service", service)
            .tag("conn_state", entry.get("conn_state", ""))
            .tag("direction", direction)
            .field("duration", duration)
            .field("orig_bytes", orig_bytes)
            .field("resp_bytes", resp_bytes)
            .field("orig_pkts", _safe_int(entry.get("orig_pkts")))
            .field("resp_pkts", _safe_int(entry.get("resp_pkts")))
            .field("missed_bytes", _safe_int(entry.get("missed_bytes")))
            .time(timestamp)
        )

        parsed = {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "orig_bytes": orig_bytes,
            "resp_bytes": resp_bytes,
            "duration": duration,
            "service": service,
        }

        return point, parsed
