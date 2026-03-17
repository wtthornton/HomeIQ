"""Parser for Zeek weird.log + notice.log — anomaly detection.

Reads JSON lines from weird.log (protocol violations) and notice.log
(Zeek-generated alerts), writes to InfluxDB ``network_anomalies``
measurement. On-occurrence writes (not batched) for real-time alerting.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client import Point

if TYPE_CHECKING:
    from ..services.influx_writer import InfluxWriter
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-anomaly-parser")

# Severity mapping for Zeek notice actions
_NOTICE_SEVERITY: dict[str, str] = {
    "Notice::ACTION_LOG": "info",
    "Notice::ACTION_EMAIL": "warning",
    "Notice::ACTION_ALARM": "critical",
    "Notice::ACTION_DROP": "critical",
}

# Severity mapping for common weird names
_WEIRD_SEVERITY: dict[str, str] = {
    "dns_unmatched_reply": "info",
    "above_hole_data_without_any_acks": "info",
    "possible_split_routing": "info",
    "data_before_established": "warning",
    "bad_TCP_checksum": "warning",
    "connection_originator_SYN_ack": "warning",
    "truncated_header": "warning",
    "SYN_after_close": "warning",
    "TCP_ack_underflow_or_misorder": "info",
    "window_recision": "info",
}


class AnomalyParser:
    """Parses Zeek weird.log and notice.log for anomaly detection."""

    def __init__(
        self,
        log_tracker: LogTracker,
        influx_writer: InfluxWriter,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._influx_writer = influx_writer
        self._service = service

        # Stats
        self.weird_lines_parsed: int = 0
        self.notice_lines_parsed: int = 0
        self.anomalies_detected: int = 0

    async def run(self, interval: int) -> None:
        """Background loop: parse weird/notice logs every ``interval`` seconds."""
        logger.info("Starting anomaly parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("Anomaly parser cancelled")
                raise
            except Exception as e:
                logger.error("Anomaly parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from weird.log + notice.log and write anomalies."""
        updated = False

        for line in self._log_tracker.read_new_lines("weird.log"):
            point = self._parse_weird_line(line)
            if point:
                await self._influx_writer.write_points([point])
                self.anomalies_detected += 1
            self.weird_lines_parsed += 1
            updated = True

        for line in self._log_tracker.read_new_lines("notice.log"):
            point = self._parse_notice_line(line)
            if point:
                await self._influx_writer.write_points([point])
                self.anomalies_detected += 1
            self.notice_lines_parsed += 1
            updated = True

        if updated:
            self._log_tracker.save_offsets()

    def _parse_weird_line(self, line: str) -> Point | None:
        """Parse weird.log JSON — protocol violations and anomalies."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        name = entry.get("name", "")
        if not name:
            return None

        ts_value = entry.get("ts")
        timestamp = (
            datetime.fromtimestamp(float(ts_value), tz=UTC)
            if ts_value
            else datetime.now(UTC)
        )

        source_ip = entry.get("id.orig_h", "")
        dest_ip = entry.get("id.resp_h", "")
        peer = entry.get("peer", "")
        notice_msg = entry.get("addl", "")
        severity = _WEIRD_SEVERITY.get(name, "warning")

        point = (
            Point("network_anomalies")
            .tag("source_ip", source_ip)
            .tag("dest_ip", dest_ip)
            .tag("anomaly_type", "protocol_violation")
            .tag("severity", severity)
            .tag("source_log", "weird")
            .field("name", name)
            .field("message", notice_msg)
            .field("peer", peer)
            .field("suppress_for", int(entry.get("suppress_for", 0)))
            .time(timestamp)
        )
        return point

    def _parse_notice_line(self, line: str) -> Point | None:
        """Parse notice.log JSON — Zeek-generated alerts."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        note = entry.get("note", "")
        if not note:
            return None

        ts_value = entry.get("ts")
        timestamp = (
            datetime.fromtimestamp(float(ts_value), tz=UTC)
            if ts_value
            else datetime.now(UTC)
        )

        source_ip = entry.get("id.orig_h", entry.get("src", ""))
        dest_ip = entry.get("id.resp_h", entry.get("dst", ""))
        msg = entry.get("msg", "")
        sub_msg = entry.get("sub", "")
        peer = entry.get("peer_descr", "")
        suppress_for = entry.get("suppress_for", 0)

        # Map action to severity
        actions = entry.get("actions", [])
        severity = "info"
        for action in actions if isinstance(actions, list) else []:
            mapped = _NOTICE_SEVERITY.get(action)
            if mapped:
                severity = mapped
                break

        point = (
            Point("network_anomalies")
            .tag("source_ip", source_ip)
            .tag("dest_ip", dest_ip)
            .tag("anomaly_type", note)
            .tag("severity", severity)
            .tag("source_log", "notice")
            .field("name", note)
            .field("message", msg)
            .field("sub_message", sub_msg)
            .field("peer", peer)
            .field("suppress_for", int(suppress_for) if suppress_for else 0)
            .time(timestamp)
        )
        return point

    def get_recent_anomalies(self) -> dict:
        """Return anomaly parser statistics."""
        return {
            "weird_lines_parsed": self.weird_lines_parsed,
            "notice_lines_parsed": self.notice_lines_parsed,
            "anomalies_detected": self.anomalies_detected,
        }
