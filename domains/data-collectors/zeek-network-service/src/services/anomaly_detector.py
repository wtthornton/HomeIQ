"""Anomaly detection engine — new device alerts, beaconing, DGA detection.

Combines baseline knowledge with network telemetry to detect:
- New/unknown devices (Story 75.3)
- C2 beaconing patterns (Story 75.4)
- DGA domains and DNS tunneling (Story 75.4)

Feeds anomalies to InfluxDB ``network_anomalies`` measurement and
cross-service consumers (proactive-agent, ai-pattern-service).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from influxdb_client import Point

if TYPE_CHECKING:
    from .baseline_service import BaselineService
    from .influx_writer import InfluxWriter

logger = setup_logging("zeek-anomaly-detector")

# ---------------------------------------------------------------------------
# DGA detection constants
# ---------------------------------------------------------------------------
# Consonant clusters unlikely in legitimate domains
_CONSONANT_CLUSTER = re.compile(r"[bcdfghjklmnpqrstvwxyz]{5,}", re.IGNORECASE)
# Minimum length for DGA consideration
_DGA_MIN_LENGTH = 12
# Shannon entropy threshold (DGA domains typically > 3.5)
_DGA_ENTROPY_THRESHOLD = 3.5
# DNS tunneling: large TXT records
_DNS_TUNNEL_MIN_TXT_SIZE = 200

# Beaconing defaults (overridable via env)
_BEACON_MIN_CONNECTIONS = 20
_BEACON_JITTER_THRESHOLD = 5.0  # seconds
_BEACON_MIN_DURATION = 3600  # 1 hour


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0
    freq: dict[str, int] = defaultdict(int)
    for c in s:
        freq[c] += 1
    length = len(s)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )


def is_dga_domain(domain: str) -> bool:
    """Heuristic check for DGA-generated domain names.

    Checks:
    1. High Shannon entropy (> 3.5)
    2. Long label length (> 12 chars)
    3. Consonant clusters (5+ consecutive consonants)
    """
    if not domain:
        return False

    # Extract the second-level domain label
    parts = domain.rstrip(".").split(".")
    if len(parts) < 2:
        return False
    label = parts[-2]  # second-level domain

    if len(label) < _DGA_MIN_LENGTH:
        return False

    entropy = _shannon_entropy(label)
    if entropy > _DGA_ENTROPY_THRESHOLD:
        return True

    return bool(_CONSONANT_CLUSTER.search(label))


class AnomalyDetector:
    """Stateful anomaly detection engine.

    Tracks connection patterns (beaconing) and DNS queries (DGA/tunneling)
    in memory, flushing alerts to InfluxDB when anomalies are detected.
    """

    def __init__(
        self,
        influx_writer: InfluxWriter,
        baseline_service: BaselineService,
        *,
        beacon_jitter: float = _BEACON_JITTER_THRESHOLD,
        beacon_min_connections: int = _BEACON_MIN_CONNECTIONS,
        beacon_min_duration: int = _BEACON_MIN_DURATION,
    ) -> None:
        self._influx_writer = influx_writer
        self._baseline_service = baseline_service

        # Beaconing config
        self._beacon_jitter = beacon_jitter
        self._beacon_min_connections = beacon_min_connections
        self._beacon_min_duration = beacon_min_duration

        # In-memory state for beaconing detection
        # Key: (src_ip, dst_ip) → list of connection timestamps
        self._connection_times: dict[tuple[str, str], list[datetime]] = defaultdict(list)

        # Stats
        self.new_devices_detected: int = 0
        self.beacons_detected: int = 0
        self.dga_domains_detected: int = 0
        self.dns_tunnels_detected: int = 0

        # Recent alerts (for API endpoint, capped at 1000)
        self._recent_alerts: list[dict] = []
        self._max_recent = 1000

    async def check_new_device(
        self,
        ip_address: str,
        mac_address: str | None = None,
        hostname: str | None = None,
    ) -> None:
        """Check if a device is new to the network and generate alert if so.

        Called by DHCP parser or conn parser when a new IP is seen.
        """
        # Check if already in baseline
        if await self._baseline_service.host_exists(ip_address):
            # Device is known, check if baseline-approved
            if await self._baseline_service.is_known_host(ip_address):
                return  # Approved, no alert
            return  # Already seen but not approved — don't re-alert

        # New device: register and alert
        await self._baseline_service.upsert_host(
            ip_address=ip_address,
            mac_address=mac_address,
            hostname=hostname,
        )

        point = (
            Point("network_anomalies")
            .tag("source_ip", ip_address)
            .tag("anomaly_type", "new_device")
            .tag("severity", "warning")
            .tag("source_log", "detector")
            .field("name", "new_device")
            .field("message", f"New device detected: {ip_address} (MAC: {mac_address or 'unknown'})")
            .field("mac_address", mac_address or "")
            .field("hostname", hostname or "")
            .time(datetime.now(UTC))
        )
        await self._influx_writer.write_points([point])
        self.new_devices_detected += 1

        alert = {
            "type": "new_device",
            "severity": "warning",
            "ip": ip_address,
            "mac": mac_address,
            "hostname": hostname,
            "detected_at": datetime.now(UTC).isoformat(),
        }
        self._add_alert(alert)
        logger.warning("New device detected: %s (MAC: %s)", ip_address, mac_address)

    def record_connection(
        self,
        src_ip: str,
        dst_ip: str,
        timestamp: datetime,
    ) -> None:
        """Record a connection for beaconing analysis.

        Called by conn parser for connections to external IPs.
        """
        key = (src_ip, dst_ip)
        times = self._connection_times[key]
        times.append(timestamp)

        # Keep only last 2 hours of data to bound memory
        cutoff = datetime.now(UTC) - timedelta(hours=2)
        self._connection_times[key] = [t for t in times if t > cutoff]

    async def check_beaconing(self) -> list[dict]:
        """Analyze connection patterns for beaconing behavior.

        Returns list of detected beacons with details.
        """
        beacons: list[dict] = []
        now = datetime.now(UTC)

        for (src_ip, dst_ip), times in list(self._connection_times.items()):
            if len(times) < self._beacon_min_connections:
                continue

            # Check time span
            times_sorted = sorted(times)
            duration = (times_sorted[-1] - times_sorted[0]).total_seconds()
            if duration < self._beacon_min_duration:
                continue

            # Calculate intervals between connections
            intervals = [
                (times_sorted[i + 1] - times_sorted[i]).total_seconds()
                for i in range(len(times_sorted) - 1)
            ]
            if not intervals:
                continue

            # Check for regularity (low jitter)
            mean_interval = sum(intervals) / len(intervals)
            if mean_interval <= 0:
                continue

            variance = sum((i - mean_interval) ** 2 for i in intervals) / len(intervals)
            std_dev = variance ** 0.5

            if std_dev <= self._beacon_jitter:
                beacon = {
                    "type": "beaconing",
                    "severity": "critical",
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "connection_count": len(times),
                    "mean_interval_seconds": round(mean_interval, 2),
                    "jitter_seconds": round(std_dev, 2),
                    "duration_seconds": round(duration, 0),
                    "detected_at": now.isoformat(),
                }
                beacons.append(beacon)

                point = (
                    Point("network_anomalies")
                    .tag("source_ip", src_ip)
                    .tag("dest_ip", dst_ip)
                    .tag("anomaly_type", "beaconing")
                    .tag("severity", "critical")
                    .tag("source_log", "detector")
                    .field("name", "beaconing")
                    .field(
                        "message",
                        f"Beaconing detected: {src_ip} → {dst_ip} every {mean_interval:.0f}s",
                    )
                    .field("mean_interval", mean_interval)
                    .field("jitter", std_dev)
                    .field("connection_count", len(times))
                    .time(now)
                )
                await self._influx_writer.write_points([point])
                self.beacons_detected += 1
                self._add_alert(beacon)

        return beacons

    async def check_dns_anomaly(
        self,
        source_ip: str,
        query_domain: str,
        query_type: str = "",
        answer_size: int = 0,
    ) -> None:
        """Check a DNS query for DGA patterns or tunneling indicators.

        Called by DNS parser for each resolved query.
        """
        # DGA detection
        if is_dga_domain(query_domain):
            point = (
                Point("network_anomalies")
                .tag("source_ip", source_ip)
                .tag("anomaly_type", "dga_domain")
                .tag("severity", "critical")
                .tag("source_log", "detector")
                .field("name", "dga_domain")
                .field("message", f"Possible DGA domain: {query_domain}")
                .field("domain", query_domain)
                .time(datetime.now(UTC))
            )
            await self._influx_writer.write_points([point])
            self.dga_domains_detected += 1

            alert = {
                "type": "dga_domain",
                "severity": "critical",
                "source_ip": source_ip,
                "domain": query_domain,
                "detected_at": datetime.now(UTC).isoformat(),
            }
            self._add_alert(alert)
            logger.warning("Possible DGA domain from %s: %s", source_ip, query_domain)

        # DNS tunneling: large TXT records
        if query_type == "TXT" and answer_size >= _DNS_TUNNEL_MIN_TXT_SIZE:
            point = (
                Point("network_anomalies")
                .tag("source_ip", source_ip)
                .tag("anomaly_type", "dns_tunneling")
                .tag("severity", "critical")
                .tag("source_log", "detector")
                .field("name", "dns_tunneling")
                .field(
                    "message",
                    f"Possible DNS tunneling: TXT record {answer_size}B to {query_domain}",
                )
                .field("domain", query_domain)
                .field("answer_size", answer_size)
                .time(datetime.now(UTC))
            )
            await self._influx_writer.write_points([point])
            self.dns_tunnels_detected += 1

            alert = {
                "type": "dns_tunneling",
                "severity": "critical",
                "source_ip": source_ip,
                "domain": query_domain,
                "answer_size": answer_size,
                "detected_at": datetime.now(UTC).isoformat(),
            }
            self._add_alert(alert)
            logger.warning(
                "Possible DNS tunneling from %s: TXT %dB to %s",
                source_ip,
                answer_size,
                query_domain,
            )

    def get_alerts(
        self,
        severity: str | None = None,
        anomaly_type: str | None = None,
    ) -> list[dict]:
        """Get recent alerts, optionally filtered."""
        alerts = self._recent_alerts
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        if anomaly_type:
            alerts = [a for a in alerts if a.get("type") == anomaly_type]
        return alerts

    def get_stats(self) -> dict:
        """Return anomaly detection statistics."""
        return {
            "new_devices_detected": self.new_devices_detected,
            "beacons_detected": self.beacons_detected,
            "dga_domains_detected": self.dga_domains_detected,
            "dns_tunnels_detected": self.dns_tunnels_detected,
            "active_alerts": len(self._recent_alerts),
            "tracked_connections": len(self._connection_times),
        }

    def _add_alert(self, alert: dict) -> None:
        """Add an alert to the recent alerts list (bounded)."""
        self._recent_alerts.append(alert)
        if len(self._recent_alerts) > self._max_recent:
            self._recent_alerts = self._recent_alerts[-self._max_recent :]
