"""Zeek Network Intelligence Service.

Parses Zeek JSON logs from a shared volume, writes time-series metrics to
InfluxDB, stores device metadata in PostgreSQL, and exposes a REST API for
network intelligence data. Follows the HomeIQ data-collector pattern.
"""

from __future__ import annotations

import asyncio
import ipaddress
from contextlib import suppress
from datetime import UTC, datetime

from fastapi import HTTPException, Path, Query
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .config import settings
from .parsers.anomaly_parser import AnomalyParser
from .parsers.conn_parser import ConnLogParser
from .parsers.dhcp_parser import DhcpParser
from .parsers.dns_parser import DnsLogParser
from .parsers.flowmeter_parser import FlowmeterParser
from .parsers.mqtt_parser import MqttParser
from .parsers.ssh_parser import SshParser
from .parsers.tls_parser import TlsParser
from .parsers.x509_parser import X509Parser
from .services.anomaly_detector import AnomalyDetector
from .services.baseline_service import BaselineService
from .services.cert_tracker import CertTracker
from .services.device_aggregator import DeviceAggregator
from .services.dns_profiler import DnsProfiler
from .services.fingerprint_service import FingerprintService
from .services.influx_writer import InfluxWriter
from .services.log_tracker import LogTracker
from .services.oui_lookup import OUILookup
from .services.security_feed import SecurityFeed

SERVICE_NAME = settings.service_name
SERVICE_VERSION = __version__

logger = setup_logging(SERVICE_NAME)


class ZeekNetworkService:
    """Core service coordinating Zeek log parsing, InfluxDB writes, and metrics."""

    def __init__(self) -> None:
        self.log_tracker = LogTracker(
            log_dir=settings.zeek_log_dir,
            state_dir=settings.state_dir,
        )
        self.influx_writer = InfluxWriter(settings)
        self.oui_lookup = OUILookup()

        # Background task handles — Phase 1
        self.conn_parser_task: asyncio.Task | None = None
        self.dns_parser_task: asyncio.Task | None = None
        self.aggregator_task: asyncio.Task | None = None
        # Phase 2
        self.dhcp_parser_task: asyncio.Task | None = None
        self.tls_parser_task: asyncio.Task | None = None
        self.ssh_parser_task: asyncio.Task | None = None
        # Phase 3
        self.mqtt_parser_task: asyncio.Task | None = None
        self.x509_parser_task: asyncio.Task | None = None
        # Phase 4
        self.anomaly_parser_task: asyncio.Task | None = None
        self.flowmeter_parser_task: asyncio.Task | None = None
        self.beaconing_task: asyncio.Task | None = None

        # Stats
        self.conn_lines_parsed: int = 0
        self.dns_lines_parsed: int = 0
        self.start_time: datetime | None = None

        # Eagerly create sub-components so endpoints never hit AttributeError
        self.device_aggregator = DeviceAggregator(
            influx_writer=self.influx_writer,
            service=self,
        )
        self.fingerprint_service = FingerprintService(
            dsn=settings.effective_database_url,
            schema=settings.database_schema,
        )
        self.cert_tracker = CertTracker(
            dsn=settings.effective_database_url,
            schema=settings.database_schema,
        )
        self.dns_profiler = DnsProfiler(
            dsn=settings.effective_database_url,
            schema=settings.database_schema,
        )
        self.baseline_service = BaselineService(
            dsn=settings.effective_database_url,
            schema=settings.database_schema,
        )
        self.security_feed = SecurityFeed(
            data_api_url=settings.data_api_url,
            api_key=settings.data_api_key.get_secret_value() if settings.data_api_key else None,
            proactive_agent_url=settings.proactive_agent_url,
            ai_pattern_url=settings.ai_pattern_url,
        )
        self.anomaly_detector: AnomalyDetector | None = None

        # Phase 1+2 parsers (set during startup)
        self.conn_parser: ConnLogParser | None = None
        self.dns_parser: DnsLogParser | None = None
        self.dhcp_parser: DhcpParser | None = None
        self.tls_parser: TlsParser | None = None
        self.ssh_parser: SshParser | None = None
        # Phase 3 parsers
        self.mqtt_parser: MqttParser | None = None
        self.x509_parser: X509Parser | None = None
        # Phase 4 parsers
        self.anomaly_parser: AnomalyParser | None = None
        self.flowmeter_parser: FlowmeterParser | None = None

    async def startup(self) -> None:
        """Initialize connections and start background tasks."""
        logger.info("Initializing Zeek Network Intelligence Service...")
        self.start_time = datetime.now(UTC)

        await self.influx_writer.initialize()
        await self.fingerprint_service.initialize()
        await self.cert_tracker.initialize()
        await self.dns_profiler.initialize()
        await self.baseline_service.initialize()
        await self.security_feed.initialize()
        self.log_tracker.load_offsets()

        # Phase 4 anomaly detector (needs baseline_service)
        self.anomaly_detector = AnomalyDetector(
            influx_writer=self.influx_writer,
            baseline_service=self.baseline_service,
            beacon_jitter=settings.beacon_jitter_threshold,
            beacon_min_connections=settings.beacon_min_connections,
            beacon_min_duration=settings.beacon_min_duration,
        )

        # Phase 1 parsers
        self.conn_parser = ConnLogParser(
            log_tracker=self.log_tracker,
            influx_writer=self.influx_writer,
            aggregator=self.device_aggregator,
            service=self,
        )
        self.dns_parser = DnsLogParser(
            log_tracker=self.log_tracker,
            influx_writer=self.influx_writer,
            aggregator=self.device_aggregator,
            service=self,
        )

        # Phase 2 parsers (fingerprinting)
        self.dhcp_parser = DhcpParser(
            log_tracker=self.log_tracker,
            fingerprint_service=self.fingerprint_service,
            oui_lookup=self.oui_lookup,
            service=self,
        )
        self.tls_parser = TlsParser(
            log_tracker=self.log_tracker,
            fingerprint_service=self.fingerprint_service,
            service=self,
        )
        self.ssh_parser = SshParser(
            log_tracker=self.log_tracker,
            fingerprint_service=self.fingerprint_service,
            service=self,
        )

        # Phase 3 parsers (MQTT & Protocol Intelligence)
        self.mqtt_parser = MqttParser(
            log_tracker=self.log_tracker,
            influx_writer=self.influx_writer,
            service=self,
        )
        self.x509_parser = X509Parser(
            log_tracker=self.log_tracker,
            cert_tracker=self.cert_tracker,
            service=self,
        )

        # Phase 4 parsers (Anomaly Detection)
        self.anomaly_parser = AnomalyParser(
            log_tracker=self.log_tracker,
            influx_writer=self.influx_writer,
            service=self,
        )
        self.flowmeter_parser = FlowmeterParser(
            log_tracker=self.log_tracker,
            service=self,
        )

        # Start background tasks
        self.conn_parser_task = asyncio.create_task(
            self.conn_parser.run(settings.poll_interval_seconds),
            name="conn-log-parser",
        )
        self.dns_parser_task = asyncio.create_task(
            self.dns_parser.run(settings.poll_interval_seconds),
            name="dns-log-parser",
        )
        self.aggregator_task = asyncio.create_task(
            self.device_aggregator.run(settings.device_metrics_interval_seconds),
            name="device-aggregator",
        )
        self.dhcp_parser_task = asyncio.create_task(
            self.dhcp_parser.run(settings.poll_interval_seconds),
            name="dhcp-parser",
        )
        self.tls_parser_task = asyncio.create_task(
            self.tls_parser.run(settings.poll_interval_seconds),
            name="tls-parser",
        )
        self.ssh_parser_task = asyncio.create_task(
            self.ssh_parser.run(settings.poll_interval_seconds),
            name="ssh-parser",
        )
        self.mqtt_parser_task = asyncio.create_task(
            self.mqtt_parser.run(settings.poll_interval_seconds),
            name="mqtt-parser",
        )
        self.x509_parser_task = asyncio.create_task(
            self.x509_parser.run(settings.poll_interval_seconds),
            name="x509-parser",
        )
        self.anomaly_parser_task = asyncio.create_task(
            self.anomaly_parser.run(settings.poll_interval_seconds),
            name="anomaly-parser",
        )
        self.flowmeter_parser_task = asyncio.create_task(
            self.flowmeter_parser.run(settings.poll_interval_seconds),
            name="flowmeter-parser",
        )
        self.beaconing_task = asyncio.create_task(
            self._beaconing_loop(settings.beaconing_check_interval_seconds),
            name="beaconing-check",
        )

        logger.info("Zeek Network Intelligence Service initialized")

    async def _beaconing_loop(self, interval: int) -> None:
        """Periodic beaconing analysis."""
        logger.info("Starting beaconing detection (every %ds)", interval)
        while True:
            try:
                if self.anomaly_detector:
                    beacons = await self.anomaly_detector.check_beaconing()
                    for beacon in beacons:
                        await self.security_feed.send_security_event(beacon)
            except asyncio.CancelledError:
                logger.info("Beaconing detection cancelled")
                raise
            except Exception as e:
                logger.error("Beaconing detection error: %s", e)
            await asyncio.sleep(interval)

    async def shutdown(self) -> None:
        """Stop background tasks and close connections."""
        logger.info("Shutting down Zeek Network Intelligence Service...")

        tasks = [
            self.conn_parser_task,
            self.dns_parser_task,
            self.aggregator_task,
            self.dhcp_parser_task,
            self.tls_parser_task,
            self.ssh_parser_task,
            self.mqtt_parser_task,
            self.x509_parser_task,
            self.anomaly_parser_task,
            self.flowmeter_parser_task,
            self.beaconing_task,
        ]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

        self.log_tracker.save_offsets()
        await self.influx_writer.close()
        await self.fingerprint_service.close()
        await self.cert_tracker.close()
        await self.dns_profiler.close()
        await self.baseline_service.close()
        await self.security_feed.close()

    def get_zeek_health(self) -> dict:
        """Check Zeek container health by log freshness."""
        freshness = self.log_tracker.get_log_freshness()
        zeek_running = freshness is not None and freshness < 60
        return {
            "zeek_process_running": zeek_running,
            "log_freshness_seconds": freshness,
        }

    def get_stats(self) -> dict:
        """Return current service statistics."""
        fingerprint_stats = {}
        if self.dhcp_parser:
            fingerprint_stats["dhcp_devices_discovered"] = self.dhcp_parser.devices_discovered
        if self.tls_parser:
            fingerprint_stats["tls_fingerprints_captured"] = self.tls_parser.tls_fingerprints_captured
        if self.ssh_parser:
            fingerprint_stats["ssh_fingerprints_captured"] = self.ssh_parser.ssh_fingerprints_captured
            fingerprint_stats["software_entries_captured"] = self.ssh_parser.software_entries_captured

        # Phase 3 stats
        protocol_stats = {}
        if self.mqtt_parser:
            protocol_stats["mqtt_lines_parsed"] = self.mqtt_parser.mqtt_lines_parsed
        if self.x509_parser:
            protocol_stats["certs_tracked"] = self.x509_parser.certs_tracked

        # Phase 4 stats
        anomaly_stats = {}
        if self.anomaly_parser:
            anomaly_stats.update(self.anomaly_parser.get_recent_anomalies())
        if self.anomaly_detector:
            anomaly_stats.update(self.anomaly_detector.get_stats())
        if self.flowmeter_parser:
            anomaly_stats["flowmeter_flows_parsed"] = self.flowmeter_parser.flows_parsed
        anomaly_stats.update(self.security_feed.get_stats())

        return {
            "conn_lines_parsed": self.conn_lines_parsed,
            "dns_lines_parsed": self.dns_lines_parsed,
            "influxdb_writes_total": self.influx_writer.write_success_count,
            "influxdb_writes_failed": self.influx_writer.write_failure_count,
            "influxdb_buffer_size": self.influx_writer.buffer_size,
            "uptime_seconds": (
                (datetime.now(UTC) - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            **fingerprint_stats,
            **protocol_stats,
            **anomaly_stats,
        }


# ---------------------------------------------------------------------------
# Global service instance
# ---------------------------------------------------------------------------
zeek_service: ZeekNetworkService | None = None


async def _startup() -> None:
    global zeek_service
    zeek_service = ZeekNetworkService()
    await zeek_service.startup()


async def _shutdown() -> None:
    global zeek_service
    if zeek_service:
        await zeek_service.shutdown()
        zeek_service = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
_lifespan = ServiceLifespan(settings.service_name)
_lifespan.on_startup(_startup, name="zeek-network")
_lifespan.on_shutdown(_shutdown, name="zeek-network")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
_health = StandardHealthCheck(
    service_name=settings.service_name,
    version=SERVICE_VERSION,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = create_app(
    title="Zeek Network Intelligence Service",
    version=SERVICE_VERSION,
    description="Passive network monitoring for IoT devices via Zeek",
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=settings.get_cors_origins_list(),
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": [
            "/health",
            "/metrics",
            "/current-stats",
            "/devices",
            "/devices/{ip}",
            "/devices/{ip}/fingerprint",
            "/devices/discovered",
            "/devices/new",
            "/mqtt/topics",
            "/mqtt/clients",
            "/tls/certificates",
            "/dns/profiles/{ip}",
            "/security/alerts",
            "/anomalies",
            "/baseline/devices",
            "/baseline/approve/{ip}",
            "/flowmeter/features",
            "/cache/stats",
        ],
    }


@app.get("/metrics")
async def metrics():
    """Lightweight numeric metrics endpoint (JSON)."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    stats = zeek_service.get_stats()
    return stats


@app.get("/current-stats")
async def current_stats():
    """Current network statistics — connections/min, bytes/min, top talkers."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return zeek_service.device_aggregator.get_current_stats()


@app.get("/devices")
async def list_devices():
    """All discovered devices with latest metrics."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return zeek_service.device_aggregator.get_devices()


@app.get("/devices/discovered")
async def discovered_devices(hours: int = Query(default=24, ge=1, le=720)):
    """Devices discovered via DHCP within the last N hours."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await zeek_service.fingerprint_service.get_discovered(hours=hours)


@app.get("/devices/new")
async def new_devices():
    """Devices not yet in the baseline (seen only once)."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await zeek_service.fingerprint_service.get_new_devices()


@app.get("/devices/{ip}")
async def get_device(ip: str = Path(description="Device IP address")):
    """Device detail — connections, DNS, bandwidth."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid IP address: {ip}") from None

    device = zeek_service.device_aggregator.get_device(ip)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {ip} not found")

    return device


@app.get("/devices/{ip}/fingerprint")
async def get_device_fingerprint(ip: str = Path(description="Device IP address")):
    """Device fingerprint — DHCP, TLS (JA3/JA4), SSH (HASSH), software."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid IP address: {ip}") from None

    fingerprint = await zeek_service.fingerprint_service.get_by_ip(ip)
    if not fingerprint:
        raise HTTPException(status_code=404, detail=f"No fingerprint data for {ip}")

    return fingerprint


# ---------------------------------------------------------------------------
# Phase 3 — Protocol Intelligence endpoints
# ---------------------------------------------------------------------------


@app.get("/mqtt/topics")
async def mqtt_topics():
    """Active MQTT topics with message counts."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not zeek_service.mqtt_parser:
        return []

    return zeek_service.mqtt_parser.get_topics()


@app.get("/mqtt/clients")
async def mqtt_clients():
    """Connected MQTT clients."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not zeek_service.mqtt_parser:
        return []

    return zeek_service.mqtt_parser.get_clients()


@app.get("/tls/certificates")
async def tls_certificates():
    """Tracked TLS certificates with expiry status."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await zeek_service.cert_tracker.get_all_certificates()


@app.get("/dns/profiles/{ip}")
async def dns_profile(ip: str = Path(description="Device IP address")):
    """Per-device DNS query profile with domain categorization."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid IP address: {ip}") from None

    profile = await zeek_service.dns_profiler.get_device_profile(ip)
    summary = await zeek_service.dns_profiler.get_category_summary(ip)

    return {
        "device_ip": ip,
        "category_summary": summary,
        "domains": profile,
    }


@app.get("/security/alerts")
async def security_alerts():
    """Active security alerts — expired certs, weak TLS, rogue MQTT clients.

    Story 74.5: Alerting on rogue MQTT clients (unknown client_id),
    expired TLS certificates, and TLS < 1.2 negotiation.
    """
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    alerts: list[dict] = []

    # Expired TLS certificates
    expired = await zeek_service.cert_tracker.get_expired_certificates()
    for cert in expired:
        alerts.append({
            "type": "expired_certificate",
            "severity": "warning",
            "detail": f"Certificate {cert.get('fingerprint', '')[:16]}... expired",
            "subject": cert.get("subject"),
            "server_name": cert.get("server_name"),
            "expired_at": str(cert.get("not_valid_after", "")),
        })

    # Weak TLS (< 1.2)
    weak = await zeek_service.cert_tracker.get_weak_tls()
    for cert in weak:
        alerts.append({
            "type": "weak_tls",
            "severity": "warning",
            "detail": f"TLS {cert.get('tls_version', '')} negotiated (< 1.2)",
            "server_name": cert.get("server_name"),
            "tls_version": cert.get("tls_version"),
            "cipher_suite": cert.get("cipher_suite"),
        })

    # Rogue MQTT clients (unknown client_id — heuristic: no known mapping)
    if zeek_service.mqtt_parser:
        known_prefixes = {"homeassistant", "mosquitto", "zigbee2mqtt", "zwavejs", "esphome"}
        for client in zeek_service.mqtt_parser.get_clients():
            cid = client.get("client_id", "")
            is_known = any(cid.lower().startswith(prefix) for prefix in known_prefixes)
            if not is_known and cid and cid != "unknown":
                alerts.append({
                    "type": "rogue_mqtt_client",
                    "severity": "info",
                    "detail": f"Unknown MQTT client: {cid}",
                    "client_id": cid,
                    "client_ip": client.get("client_ip"),
                })

    # Phase 4 anomaly alerts (new devices, beaconing, DGA, DNS tunneling)
    if zeek_service.anomaly_detector:
        for anomaly in zeek_service.anomaly_detector.get_alerts():
            alerts.append({
                "type": anomaly.get("type", "unknown"),
                "severity": anomaly.get("severity", "info"),
                "detail": anomaly.get("message", str(anomaly)),
                **{k: v for k, v in anomaly.items() if k not in ("type", "severity", "message")},
            })

    return {"alerts": alerts, "total": len(alerts)}


# ---------------------------------------------------------------------------
# Phase 4 — Anomaly Detection & Security Baseline endpoints
# ---------------------------------------------------------------------------


@app.get("/anomalies")
async def list_anomalies(
    severity: str | None = Query(default=None, description="Filter by severity"),
    anomaly_type: str | None = Query(default=None, description="Filter by anomaly type"),
):
    """Recent anomaly events — filterable by type and severity."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not zeek_service.anomaly_detector:
        return {"anomalies": [], "total": 0}

    alerts = zeek_service.anomaly_detector.get_alerts(
        severity=severity,
        anomaly_type=anomaly_type,
    )
    return {"anomalies": alerts, "total": len(alerts)}


@app.get("/baseline/devices")
async def baseline_devices():
    """Network baseline device list — all known hosts with approval status."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    hosts = await zeek_service.baseline_service.get_all_hosts()
    return {"devices": hosts, "total": len(hosts)}


@app.post("/baseline/approve/{ip}")
async def approve_baseline(
    ip: str = Path(description="Device IP address to approve"),
    approved_by: str = Query(default="admin", description="Who approved"),
):
    """Approve a device into the network baseline (suppress new_device alerts)."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid IP address: {ip}") from None

    success = await zeek_service.baseline_service.approve(ip, approved_by=approved_by)
    if not success:
        raise HTTPException(status_code=404, detail=f"Device {ip} not found in baseline")

    return {"status": "approved", "ip": ip, "approved_by": approved_by}


@app.get("/flowmeter/features")
async def flowmeter_features(
    limit: int = Query(default=100, ge=1, le=5000, description="Max features to return"),
    since_index: int = Query(default=0, ge=0, description="Incremental fetch index"),
):
    """ML-ready traffic features from zeek-flowmeter for ml-service consumption."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not zeek_service.flowmeter_parser:
        return {"flows": [], "next_index": 0, "total_parsed": 0}

    if since_index > 0:
        return zeek_service.flowmeter_parser.get_ml_feed(since_index=since_index)

    return {
        "flows": zeek_service.flowmeter_parser.get_recent_flows(limit=limit),
        "next_index": zeek_service.flowmeter_parser.flows_parsed,
        "total_parsed": zeek_service.flowmeter_parser.flows_parsed,
    }


@app.get("/cache/stats")
async def cache_stats():
    """Cache and buffer statistics."""
    if not zeek_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    stats = zeek_service.get_stats()
    zeek_health = zeek_service.get_zeek_health()

    return {
        **stats,
        **zeek_health,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
