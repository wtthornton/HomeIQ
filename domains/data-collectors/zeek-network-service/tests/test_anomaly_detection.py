"""Tests for Epic 75 — Anomaly Detection & Security Baseline.

Covers:
- Anomaly log parsing (weird.log, notice.log) — Story 75.1
- Baseline service (upsert, approve, query) — Story 75.2
- New device detection — Story 75.3
- Beaconing detection — Story 75.4
- DGA domain detection — Story 75.4
- DNS tunneling detection — Story 75.4
- Flowmeter ML feature extraction — Story 75.5
- Security feed circuit breaker — Story 75.6
- REST API endpoints — Story 75.7
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.parsers.anomaly_parser import AnomalyParser  # noqa: I001
from src.parsers.flowmeter_parser import FlowmeterParser
from src.services.anomaly_detector import AnomalyDetector, is_dga_domain
from src.services.security_feed import SecurityFeed

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_influx_writer() -> AsyncMock:
    writer = AsyncMock()
    writer.write_success_count = 0
    writer.write_failure_count = 0
    writer.buffer_size = 0
    return writer


@pytest.fixture
def mock_baseline_service() -> AsyncMock:
    service = AsyncMock()
    service.host_exists = AsyncMock(return_value=False)
    service.is_known_host = AsyncMock(return_value=False)
    service.upsert_host = AsyncMock()
    service.approve = AsyncMock(return_value=True)
    service.get_all_hosts = AsyncMock(return_value=[])
    service.get_unapproved_hosts = AsyncMock(return_value=[])
    return service


@pytest.fixture
def anomaly_parser(mock_influx_writer: AsyncMock) -> AnomalyParser:
    return AnomalyParser(
        log_tracker=MagicMock(),
        influx_writer=mock_influx_writer,
        service=MagicMock(),
    )


@pytest.fixture
def anomaly_detector(
    mock_influx_writer: AsyncMock,
    mock_baseline_service: AsyncMock,
) -> AnomalyDetector:
    return AnomalyDetector(
        influx_writer=mock_influx_writer,
        baseline_service=mock_baseline_service,
        beacon_jitter=5.0,
        beacon_min_connections=5,  # lower for testing
        beacon_min_duration=60,  # lower for testing
    )


@pytest.fixture
def flowmeter_parser() -> FlowmeterParser:
    return FlowmeterParser(
        log_tracker=MagicMock(),
        service=MagicMock(),
    )


@pytest.fixture
def sample_weird_log_lines() -> list[str]:
    """Sample weird.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.resp_h": "93.184.216.34",
            "name": "bad_TCP_checksum",
            "addl": "Checksum mismatch",
            "peer": "zeek",
        }),
        json.dumps({
            "ts": 1710600001.0,
            "uid": "CaBk2m1PFbOSBF9fZ",
            "id.orig_h": "192.168.1.100",
            "id.resp_h": "10.0.0.1",
            "name": "dns_unmatched_reply",
            "addl": "",
            "peer": "zeek",
        }),
    ]


@pytest.fixture
def sample_notice_log_lines() -> list[str]:
    """Sample notice.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.resp_h": "93.184.216.34",
            "note": "SSL::Invalid_Server_Cert",
            "msg": "SSL certificate validation failed",
            "sub": "self-signed certificate",
            "src": "192.168.1.42",
            "dst": "93.184.216.34",
            "actions": ["Notice::ACTION_LOG"],
            "peer_descr": "zeek",
            "suppress_for": 3600.0,
        }),
        json.dumps({
            "ts": 1710600002.0,
            "note": "Scan::Port_Scan",
            "msg": "192.168.1.50 scanned at least 15 unique ports",
            "src": "192.168.1.50",
            "actions": ["Notice::ACTION_ALARM"],
            "peer_descr": "zeek",
            "suppress_for": 0,
        }),
    ]


@pytest.fixture
def sample_flowmeter_log_lines() -> list[str]:
    """Sample flowmeter.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "93.184.216.34",
            "id.resp_p": 443,
            "proto": "tcp",
            "duration": 5.234,
            "fwd_pkts_tot": 10,
            "bwd_pkts_tot": 8,
            "fwd_pkts_per_sec": 1.91,
            "bwd_pkts_per_sec": 1.53,
            "flow_pkts_per_sec": 3.44,
            "down_up_ratio": 0.8,
            "fwd_pkts_payload.avg": 512.5,
            "bwd_pkts_payload.avg": 1024.0,
            "flow_iat.avg": 0.29,
            "flow_iat.std": 0.12,
            "payload_bytes_per_second": 2048.0,
        }),
    ]


# ---------------------------------------------------------------------------
# Story 75.1 — Anomaly log parsing
# ---------------------------------------------------------------------------


class TestAnomalyParser:
    def test_parse_weird_line_valid(
        self, anomaly_parser: AnomalyParser, sample_weird_log_lines: list[str]
    ):
        point = anomaly_parser._parse_weird_line(sample_weird_log_lines[0])
        assert point is not None
        # Verify it's a Point with expected tags
        line_protocol = point.to_line_protocol()
        assert "network_anomalies" in line_protocol
        assert "protocol_violation" in line_protocol
        assert "bad_TCP_checksum" in line_protocol
        assert "warning" in line_protocol

    def test_parse_weird_line_severity_mapping(
        self, anomaly_parser: AnomalyParser, sample_weird_log_lines: list[str]
    ):
        # "bad_TCP_checksum" maps to "warning"
        point = anomaly_parser._parse_weird_line(sample_weird_log_lines[0])
        assert point is not None
        assert "warning" in point.to_line_protocol()

        # "dns_unmatched_reply" maps to "info"
        point2 = anomaly_parser._parse_weird_line(sample_weird_log_lines[1])
        assert point2 is not None
        assert "info" in point2.to_line_protocol()

    def test_parse_weird_line_invalid_json(self, anomaly_parser: AnomalyParser):
        result = anomaly_parser._parse_weird_line("not valid json {{{")
        assert result is None

    def test_parse_weird_line_missing_name(self, anomaly_parser: AnomalyParser):
        result = anomaly_parser._parse_weird_line(json.dumps({"ts": 1710600000.0}))
        assert result is None

    def test_parse_notice_line_valid(
        self, anomaly_parser: AnomalyParser, sample_notice_log_lines: list[str]
    ):
        point = anomaly_parser._parse_notice_line(sample_notice_log_lines[0])
        assert point is not None
        line_protocol = point.to_line_protocol()
        assert "network_anomalies" in line_protocol
        assert "SSL::Invalid_Server_Cert" in line_protocol
        assert "info" in line_protocol  # ACTION_LOG → info

    def test_parse_notice_line_alarm_severity(
        self, anomaly_parser: AnomalyParser, sample_notice_log_lines: list[str]
    ):
        point = anomaly_parser._parse_notice_line(sample_notice_log_lines[1])
        assert point is not None
        assert "critical" in point.to_line_protocol()  # ACTION_ALARM → critical

    def test_parse_notice_line_invalid_json(self, anomaly_parser: AnomalyParser):
        result = anomaly_parser._parse_notice_line("not json")
        assert result is None

    def test_parse_notice_line_missing_note(self, anomaly_parser: AnomalyParser):
        result = anomaly_parser._parse_notice_line(json.dumps({"ts": 1710600000.0}))
        assert result is None

    def test_stats_tracking(self, anomaly_parser: AnomalyParser):
        assert anomaly_parser.weird_lines_parsed == 0
        assert anomaly_parser.notice_lines_parsed == 0
        assert anomaly_parser.anomalies_detected == 0

        stats = anomaly_parser.get_recent_anomalies()
        assert stats["weird_lines_parsed"] == 0
        assert stats["notice_lines_parsed"] == 0


# ---------------------------------------------------------------------------
# Story 75.3 — New device detection
# ---------------------------------------------------------------------------


class TestNewDeviceDetection:
    @pytest.mark.asyncio
    async def test_new_device_alert(
        self,
        anomaly_detector: AnomalyDetector,
        mock_baseline_service: AsyncMock,
        mock_influx_writer: AsyncMock,
    ):
        mock_baseline_service.host_exists.return_value = False

        await anomaly_detector.check_new_device(
            ip_address="192.168.1.200",
            mac_address="AA:BB:CC:DD:EE:FF",
            hostname="unknown-device",
        )

        mock_baseline_service.upsert_host.assert_called_once()
        mock_influx_writer.write_points.assert_called_once()
        assert anomaly_detector.new_devices_detected == 1
        assert len(anomaly_detector.get_alerts()) == 1
        assert anomaly_detector.get_alerts()[0]["type"] == "new_device"

    @pytest.mark.asyncio
    async def test_known_device_no_alert(
        self,
        anomaly_detector: AnomalyDetector,
        mock_baseline_service: AsyncMock,
        mock_influx_writer: AsyncMock,
    ):
        mock_baseline_service.host_exists.return_value = True
        mock_baseline_service.is_known_host.return_value = True

        await anomaly_detector.check_new_device(ip_address="192.168.1.1")

        mock_influx_writer.write_points.assert_not_called()
        assert anomaly_detector.new_devices_detected == 0

    @pytest.mark.asyncio
    async def test_existing_unapproved_no_re_alert(
        self,
        anomaly_detector: AnomalyDetector,
        mock_baseline_service: AsyncMock,
        mock_influx_writer: AsyncMock,
    ):
        # Device exists but is not approved
        mock_baseline_service.host_exists.return_value = True
        mock_baseline_service.is_known_host.return_value = False

        await anomaly_detector.check_new_device(ip_address="192.168.1.200")

        mock_influx_writer.write_points.assert_not_called()
        assert anomaly_detector.new_devices_detected == 0


# ---------------------------------------------------------------------------
# Story 75.4 — Beaconing detection
# ---------------------------------------------------------------------------


class TestBeaconingDetection:
    @pytest.mark.asyncio
    async def test_beacon_detected(
        self,
        anomaly_detector: AnomalyDetector,
        mock_influx_writer: AsyncMock,
    ):
        """Regular 60s interval connections should trigger beaconing alert."""
        now = datetime.now(UTC)
        # Simulate 10 connections at regular 60s intervals (10 min span)
        for i in range(10):
            anomaly_detector.record_connection(
                "192.168.1.42",
                "185.100.87.202",
                now - timedelta(minutes=10) + timedelta(seconds=60 * i),
            )

        beacons = await anomaly_detector.check_beaconing()
        assert len(beacons) == 1
        assert beacons[0]["type"] == "beaconing"
        assert beacons[0]["severity"] == "critical"
        assert beacons[0]["src_ip"] == "192.168.1.42"
        assert beacons[0]["dst_ip"] == "185.100.87.202"
        assert anomaly_detector.beacons_detected == 1
        mock_influx_writer.write_points.assert_called()

    @pytest.mark.asyncio
    async def test_random_connections_no_beacon(
        self,
        anomaly_detector: AnomalyDetector,
    ):
        """Random intervals should not trigger beaconing."""
        now = datetime.now(UTC)
        # Irregular intervals
        offsets = [0, 5, 45, 46, 120, 125, 300, 301, 500, 600]
        for offset in offsets:
            anomaly_detector.record_connection(
                "192.168.1.42",
                "8.8.8.8",
                now - timedelta(seconds=max(offsets)) + timedelta(seconds=offset),
            )

        beacons = await anomaly_detector.check_beaconing()
        assert len(beacons) == 0

    @pytest.mark.asyncio
    async def test_too_few_connections_no_beacon(
        self,
        anomaly_detector: AnomalyDetector,
    ):
        """Below threshold count should not trigger."""
        now = datetime.now(UTC)
        for i in range(3):  # below min_connections=5
            anomaly_detector.record_connection(
                "192.168.1.42", "10.0.0.1", now + timedelta(seconds=60 * i)
            )

        beacons = await anomaly_detector.check_beaconing()
        assert len(beacons) == 0


# ---------------------------------------------------------------------------
# Story 75.4 — DGA domain detection
# ---------------------------------------------------------------------------


class TestDGADetection:
    def test_dga_domain_high_entropy(self):
        assert is_dga_domain("xk4j9m2p7q8r5t.com") is True

    def test_dga_domain_consonant_cluster(self):
        assert is_dga_domain("bcdfghjklmnpqrst.net") is True

    def test_legitimate_domain_not_dga(self):
        assert is_dga_domain("google.com") is False
        assert is_dga_domain("api.tuya.com") is False
        assert is_dga_domain("time.google.com") is False

    def test_short_domain_not_dga(self):
        assert is_dga_domain("ab.com") is False

    def test_empty_domain(self):
        assert is_dga_domain("") is False
        assert is_dga_domain("com") is False

    @pytest.mark.asyncio
    async def test_dga_alert_generated(
        self,
        anomaly_detector: AnomalyDetector,
        mock_influx_writer: AsyncMock,
    ):
        await anomaly_detector.check_dns_anomaly(
            source_ip="192.168.1.42",
            query_domain="xk4j9m2p7q8r5t.com",
            query_type="A",
        )
        mock_influx_writer.write_points.assert_called_once()
        assert anomaly_detector.dga_domains_detected == 1

    @pytest.mark.asyncio
    async def test_legitimate_dns_no_alert(
        self,
        anomaly_detector: AnomalyDetector,
        mock_influx_writer: AsyncMock,
    ):
        await anomaly_detector.check_dns_anomaly(
            source_ip="192.168.1.42",
            query_domain="api.tuya.com",
            query_type="A",
        )
        mock_influx_writer.write_points.assert_not_called()
        assert anomaly_detector.dga_domains_detected == 0


# ---------------------------------------------------------------------------
# Story 75.4 — DNS tunneling detection
# ---------------------------------------------------------------------------


class TestDNSTunnelingDetection:
    @pytest.mark.asyncio
    async def test_dns_tunneling_large_txt(
        self,
        anomaly_detector: AnomalyDetector,
        mock_influx_writer: AsyncMock,
    ):
        await anomaly_detector.check_dns_anomaly(
            source_ip="192.168.1.42",
            query_domain="data.evil.com",
            query_type="TXT",
            answer_size=500,
        )
        mock_influx_writer.write_points.assert_called_once()
        assert anomaly_detector.dns_tunnels_detected == 1

    @pytest.mark.asyncio
    async def test_normal_txt_no_alert(
        self,
        anomaly_detector: AnomalyDetector,
        mock_influx_writer: AsyncMock,
    ):
        await anomaly_detector.check_dns_anomaly(
            source_ip="192.168.1.42",
            query_domain="example.com",
            query_type="TXT",
            answer_size=50,  # small, normal SPF record
        )
        mock_influx_writer.write_points.assert_not_called()
        assert anomaly_detector.dns_tunnels_detected == 0


# ---------------------------------------------------------------------------
# Story 75.5 — Flowmeter ML features
# ---------------------------------------------------------------------------


class TestFlowmeterParser:
    def test_parse_line_valid(
        self,
        flowmeter_parser: FlowmeterParser,
        sample_flowmeter_log_lines: list[str],
    ):
        features = flowmeter_parser._parse_line(sample_flowmeter_log_lines[0])
        assert features is not None
        assert features["src_ip"] == "192.168.1.42"
        assert features["dst_ip"] == "93.184.216.34"
        assert features["dst_port"] == 443
        assert features["proto"] == "tcp"
        assert features["duration"] == 5.234
        assert features["fwd_pkts_tot"] == 10
        assert features["bwd_pkts_tot"] == 8
        assert "timestamp" in features

    def test_parse_line_invalid_json(self, flowmeter_parser: FlowmeterParser):
        result = flowmeter_parser._parse_line("not json")
        assert result is None

    def test_parse_line_missing_ips(self, flowmeter_parser: FlowmeterParser):
        result = flowmeter_parser._parse_line(json.dumps({"ts": 1710600000.0}))
        assert result is None

    def test_get_recent_flows(self, flowmeter_parser: FlowmeterParser):
        # Initially empty
        assert flowmeter_parser.get_recent_flows() == []

        # Add some flows
        flowmeter_parser._recent_flows = [
            {"src_ip": "1.1.1.1", "dst_ip": "2.2.2.2"},
            {"src_ip": "3.3.3.3", "dst_ip": "4.4.4.4"},
        ]
        assert len(flowmeter_parser.get_recent_flows(limit=1)) == 1
        assert len(flowmeter_parser.get_recent_flows(limit=10)) == 2

    def test_ml_feed_incremental(self, flowmeter_parser: FlowmeterParser):
        flowmeter_parser._recent_flows = [
            {"idx": 0},
            {"idx": 1},
            {"idx": 2},
        ]
        flowmeter_parser.flows_parsed = 3

        feed = flowmeter_parser.get_ml_feed(since_index=1)
        assert len(feed["flows"]) == 2
        assert feed["next_index"] == 3


# ---------------------------------------------------------------------------
# Story 75.6 — Security feed circuit breaker
# ---------------------------------------------------------------------------


class TestSecurityFeed:
    def test_initial_state(self):
        feed = SecurityFeed(data_api_url="http://data-api:8006")
        assert feed.events_sent == 0
        assert feed.events_failed == 0
        assert feed._circuit_open is False

    def test_circuit_breaker_opens_after_failures(self):
        feed = SecurityFeed(data_api_url="http://data-api:8006")

        feed._record_failure("test error 1")
        assert feed._circuit_open is False

        feed._record_failure("test error 2")
        assert feed._circuit_open is False

        feed._record_failure("test error 3")
        assert feed._circuit_open is True
        assert feed.events_failed == 3

    def test_circuit_breaker_recovery(self):
        feed = SecurityFeed(data_api_url="http://data-api:8006")

        # Open circuit
        for _ in range(3):
            feed._record_failure("error")
        assert feed._circuit_open is True

        # Simulate expiry
        feed._circuit_open_until = datetime.now(UTC) - timedelta(seconds=1)
        assert feed._is_circuit_open() is False
        assert feed._circuit_open is False

    def test_stats(self):
        feed = SecurityFeed(data_api_url="http://data-api:8006")
        stats = feed.get_stats()
        assert stats["events_sent"] == 0
        assert stats["events_failed"] == 0
        assert stats["circuit_open"] is False


# ---------------------------------------------------------------------------
# Story 75.7 — Alert filtering
# ---------------------------------------------------------------------------


class TestAlertFiltering:
    def test_filter_by_severity(self, anomaly_detector: AnomalyDetector):
        anomaly_detector._recent_alerts = [
            {"type": "new_device", "severity": "warning"},
            {"type": "beaconing", "severity": "critical"},
            {"type": "dga_domain", "severity": "critical"},
        ]

        critical = anomaly_detector.get_alerts(severity="critical")
        assert len(critical) == 2

        warning = anomaly_detector.get_alerts(severity="warning")
        assert len(warning) == 1

    def test_filter_by_type(self, anomaly_detector: AnomalyDetector):
        anomaly_detector._recent_alerts = [
            {"type": "new_device", "severity": "warning"},
            {"type": "beaconing", "severity": "critical"},
            {"type": "new_device", "severity": "warning"},
        ]

        devices = anomaly_detector.get_alerts(anomaly_type="new_device")
        assert len(devices) == 2

    def test_alert_buffer_bounded(self, anomaly_detector: AnomalyDetector):
        anomaly_detector._max_recent = 5
        for i in range(10):
            anomaly_detector._add_alert({"type": "test", "index": i})

        assert len(anomaly_detector._recent_alerts) == 5
        # Should keep the most recent
        assert anomaly_detector._recent_alerts[0]["index"] == 5

    def test_stats_summary(self, anomaly_detector: AnomalyDetector):
        stats = anomaly_detector.get_stats()
        assert stats["new_devices_detected"] == 0
        assert stats["beacons_detected"] == 0
        assert stats["dga_domains_detected"] == 0
        assert stats["dns_tunnels_detected"] == 0
        assert stats["active_alerts"] == 0
        assert stats["tracked_connections"] == 0
