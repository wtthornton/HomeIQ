"""Parser for Zeek dns.log — DNS query/response metadata.

Reads JSON lines from dns.log, converts to InfluxDB points, and writes
to the ``network_dns`` measurement.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import Point

if TYPE_CHECKING:
    from ..services.device_aggregator import DeviceAggregator
    from ..services.influx_writer import InfluxWriter
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-dns-parser")


def _safe_float(val: object) -> float:
    """Convert a Zeek field value to float, handling '-' and None."""
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


class DnsLogParser:
    """Parses Zeek dns.log and writes network_dns to InfluxDB."""

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
        """Background loop: parse dns.log every ``interval`` seconds."""
        logger.info("Starting dns.log parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("dns.log parser cancelled")
                raise
            except Exception as e:
                logger.error("dns.log parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from dns.log, write to InfluxDB, feed aggregator."""
        lines = self._log_tracker.read_new_lines("dns.log")
        if not lines:
            return

        points: list[Point] = []
        for line in lines:
            result = self._parse_line(line)
            if result:
                point, device_ip, domain = result
                points.append(point)
                self._aggregator.record_dns_query(device_ip, domain)

        if points:
            await self._influx_writer.write_points(points)
            self._service.dns_lines_parsed += len(points)
            logger.debug("Parsed %d dns.log entries", len(points))

        self._log_tracker.save_offsets()

    def _parse_line(self, line: str) -> tuple[Point, str, str] | None:
        """Parse a single dns.log JSON line.

        Returns:
            Tuple of (Point, device_ip, query_domain) or None if invalid.
        """
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON line in dns.log")
            return None

        device_ip = entry.get("id.orig_h", "")
        query_domain = entry.get("query", "")

        if not device_ip or not query_domain:
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

        # Answers count from the answers array
        answers = entry.get("answers", [])
        answers_count = len(answers) if isinstance(answers, list) else 0

        # TTL from first answer (Zeek stores as list of TTLs — key casing varies)
        ttls = entry.get("TTLs") or entry.get("ttls") or []
        ttl = _safe_float(ttls[0]) if ttls and isinstance(ttls, list) else 0.0

        # Rejected flag
        rejected = entry.get("rejected", False)

        point = (
            Point("network_dns")
            .tag("device_ip", device_ip)
            .tag("query_domain", query_domain)
            .tag("query_type", entry.get("qtype_name", "unknown"))
            .tag("rcode_name", entry.get("rcode_name", "unknown"))
            .field("rtt", _safe_float(entry.get("rtt")))
            .field("answers_count", answers_count)
            .field("ttl", ttl)
            .field("rejected", rejected)
            .time(timestamp)
        )

        return point, device_ip, query_domain
