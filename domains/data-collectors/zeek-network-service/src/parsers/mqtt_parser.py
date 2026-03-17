"""Parser for Zeek MQTT logs — mqtt_connect, mqtt_publish, mqtt_subscribe.

Reads JSON lines from MQTT-related logs, converts to InfluxDB points,
and writes to the ``network_mqtt`` measurement. 30s batch writes.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import Point

if TYPE_CHECKING:
    from ..services.influx_writer import InfluxWriter
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-mqtt-parser")


def _safe_int(val: object) -> int:
    """Convert a Zeek field value to int, handling '-' and None."""
    try:
        return int(val or 0)
    except (ValueError, TypeError):
        return 0


class MqttParser:
    """Parses Zeek MQTT logs and writes network_mqtt to InfluxDB."""

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
        self.mqtt_lines_parsed: int = 0

        # In-memory tracking for API queries
        self._known_clients: dict[str, dict] = {}
        self._topic_counts: dict[str, int] = {}

    async def run(self, interval: int) -> None:
        """Background loop: parse MQTT logs every ``interval`` seconds."""
        logger.info("Starting MQTT parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("MQTT parser cancelled")
                raise
            except Exception as e:
                logger.error("MQTT parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from MQTT logs, write to InfluxDB."""
        points: list[Point] = []

        for line in self._log_tracker.read_new_lines("mqtt_connect.log"):
            point = self._parse_connect_line(line)
            if point:
                points.append(point)

        for line in self._log_tracker.read_new_lines("mqtt_publish.log"):
            point = self._parse_publish_line(line)
            if point:
                points.append(point)

        for line in self._log_tracker.read_new_lines("mqtt_subscribe.log"):
            point = self._parse_subscribe_line(line)
            if point:
                points.append(point)

        if points:
            await self._influx_writer.write_points(points)
            self.mqtt_lines_parsed += len(points)
            logger.debug("Parsed %d MQTT log entries", len(points))
            self._log_tracker.save_offsets()

    def _extract_timestamp(self, entry: dict) -> datetime:
        """Extract and convert Zeek timestamp."""
        ts_value = entry.get("ts")
        if ts_value:
            try:
                return datetime.fromtimestamp(float(ts_value), tz=UTC)
            except (ValueError, TypeError, OSError):
                pass
        return datetime.now(UTC)

    def _parse_connect_line(self, line: str) -> Point | None:
        """Parse mqtt_connect.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        client_ip = entry.get("id.orig_h", "")
        if not client_ip:
            return None

        client_id = entry.get("client_id", "unknown")
        connect_ok = entry.get("connect_status", "") == "0"
        proto_version = _safe_int(entry.get("proto_version"))

        # Track known clients
        self._known_clients[client_id] = {
            "client_ip": client_ip,
            "proto_version": proto_version,
            "connect_ok": connect_ok,
            "last_seen": self._extract_timestamp(entry).isoformat(),
        }

        return (
            Point("network_mqtt")
            .tag("client_id", client_id)
            .tag("client_ip", client_ip)
            .tag("action", "connect")
            .tag("topic", "")
            .tag("qos", "")
            .field("payload_size", 0)
            .field("retain", False)
            .field("connect_ok", connect_ok)
            .field("proto_version", proto_version)
            .time(self._extract_timestamp(entry))
        )

    def _parse_publish_line(self, line: str) -> Point | None:
        """Parse mqtt_publish.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        client_ip = entry.get("id.orig_h", "")
        if not client_ip:
            return None

        topic = entry.get("topic", "unknown")
        qos = str(entry.get("qos", 0))
        payload_len = _safe_int(entry.get("payload_len"))
        retain = bool(entry.get("retain", False))

        # Track topic counts
        self._topic_counts[topic] = self._topic_counts.get(topic, 0) + 1

        return (
            Point("network_mqtt")
            .tag("client_id", entry.get("client_id", "unknown"))
            .tag("client_ip", client_ip)
            .tag("action", "publish")
            .tag("topic", topic)
            .tag("qos", qos)
            .field("payload_size", payload_len)
            .field("retain", retain)
            .field("connect_ok", True)
            .field("proto_version", 0)
            .time(self._extract_timestamp(entry))
        )

    def _parse_subscribe_line(self, line: str) -> Point | None:
        """Parse mqtt_subscribe.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        client_ip = entry.get("id.orig_h", "")
        if not client_ip:
            return None

        topic = entry.get("topic", "unknown")
        qos = str(entry.get("qos", 0))

        # Track topic counts
        self._topic_counts[topic] = self._topic_counts.get(topic, 0) + 1

        return (
            Point("network_mqtt")
            .tag("client_id", entry.get("client_id", "unknown"))
            .tag("client_ip", client_ip)
            .tag("action", "subscribe")
            .tag("topic", topic)
            .tag("qos", qos)
            .field("payload_size", 0)
            .field("retain", False)
            .field("connect_ok", True)
            .field("proto_version", 0)
            .time(self._extract_timestamp(entry))
        )

    def get_topics(self) -> list[dict]:
        """Return active topics with message counts."""
        return [
            {"topic": topic, "message_count": count}
            for topic, count in sorted(
                self._topic_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

    def get_clients(self) -> list[dict]:
        """Return connected MQTT clients."""
        return [
            {"client_id": cid, **info}
            for cid, info in self._known_clients.items()
        ]
