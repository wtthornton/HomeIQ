"""Tests for Epic 74 — Zeek MQTT & Protocol Intelligence.

Covers MQTT parsing, X.509 certificate tracking, DNS behavior profiling,
alerting logic, and protocol intelligence REST API endpoints.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.parsers.mqtt_parser import MqttParser
from src.parsers.x509_parser import X509Parser
from src.services.dns_profiler import classify_domain
from src.services.log_tracker import LogTracker

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Domain Classification
# ---------------------------------------------------------------------------


class TestDomainClassification:
    def test_cloud_api_tuya(self):
        suffix, category = classify_domain("api.tuya.com")
        assert category == "cloud_api"
        assert suffix == "tuya.com"

    def test_ntp_google(self):
        suffix, category = classify_domain("time.google.com")
        assert category == "ntp"

    def test_update_check_github(self):
        suffix, category = classify_domain("api.github.com")
        assert category == "update_check"

    def test_ad_tracker_doubleclick(self):
        suffix, category = classify_domain("ad.doubleclick.net")
        assert category == "ad_tracker"

    def test_social_media_youtube(self):
        suffix, category = classify_domain("www.youtube.com")
        assert category == "social_media"

    def test_unknown_domain(self):
        suffix, category = classify_domain("mydevice.local")
        assert category == "unknown"
        assert suffix == "mydevice.local"

    def test_trailing_dot_stripped(self):
        suffix, category = classify_domain("api.tuya.com.")
        assert category == "cloud_api"

    def test_case_insensitive(self):
        suffix, category = classify_domain("API.TUYA.COM")
        assert category == "cloud_api"

    def test_amazonaws(self):
        suffix, category = classify_domain("s3.us-east-1.amazonaws.com")
        assert category == "cloud_api"


# ---------------------------------------------------------------------------
# MQTT Parser
# ---------------------------------------------------------------------------


class TestMqttParser:
    @pytest.fixture
    def parser(self):
        return MqttParser(
            log_tracker=MagicMock(),
            influx_writer=AsyncMock(),
            service=MagicMock(),
        )

    def test_parse_connect_line(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.50",
            "id.resp_h": "192.168.1.1",
            "id.resp_p": 1883,
            "client_id": "zigbee2mqtt_bridge",
            "connect_status": "0",
            "proto_version": 4,
        })
        point = parser._parse_connect_line(line)
        assert point is not None

    def test_parse_connect_missing_ip(self, parser):
        line = json.dumps({"client_id": "test"})
        assert parser._parse_connect_line(line) is None

    def test_parse_publish_line(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.50",
            "client_id": "zigbee2mqtt_bridge",
            "topic": "homeassistant/sensor/temperature",
            "qos": 1,
            "payload_len": 128,
            "retain": True,
        })
        point = parser._parse_publish_line(line)
        assert point is not None

    def test_parse_publish_missing_ip(self, parser):
        line = json.dumps({"topic": "test"})
        assert parser._parse_publish_line(line) is None

    def test_parse_subscribe_line(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.42",
            "client_id": "esphome_living_room",
            "topic": "homeassistant/switch/#",
            "qos": 0,
        })
        point = parser._parse_subscribe_line(line)
        assert point is not None

    def test_parse_subscribe_missing_ip(self, parser):
        line = json.dumps({"topic": "test"})
        assert parser._parse_subscribe_line(line) is None

    def test_parse_invalid_json(self, parser):
        assert parser._parse_connect_line("not json") is None
        assert parser._parse_publish_line("not json") is None
        assert parser._parse_subscribe_line("not json") is None

    def test_client_tracking(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.50",
            "client_id": "zigbee2mqtt_bridge",
            "connect_status": "0",
            "proto_version": 4,
        })
        parser._parse_connect_line(line)
        clients = parser.get_clients()
        assert len(clients) == 1
        assert clients[0]["client_id"] == "zigbee2mqtt_bridge"

    def test_topic_tracking(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.50",
            "client_id": "test",
            "topic": "homeassistant/sensor/temp",
            "qos": 0,
            "payload_len": 64,
        })
        parser._parse_publish_line(line)
        parser._parse_publish_line(line)
        topics = parser.get_topics()
        assert len(topics) == 1
        assert topics[0]["message_count"] == 2

    def test_mqtt_lines_counter(self, parser):
        assert parser.mqtt_lines_parsed == 0

    @pytest.mark.asyncio
    async def test_parse_cycle_with_data(self, tmp_path: Path):
        """Test MQTT parser full cycle reads logs and writes to InfluxDB."""
        log_dir = tmp_path
        (log_dir / "mqtt_connect.log").write_text(json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.50",
            "client_id": "test_client",
            "connect_status": "0",
            "proto_version": 4,
        }) + "\n")

        tracker = LogTracker(log_dir=str(log_dir), state_dir=str(log_dir))
        influx = AsyncMock()
        parser = MqttParser(
            log_tracker=tracker,
            influx_writer=influx,
            service=MagicMock(),
        )

        await parser._parse_cycle()

        influx.write_points.assert_called_once()
        assert parser.mqtt_lines_parsed == 1

    @pytest.mark.asyncio
    async def test_no_duplicate_on_second_cycle(self, tmp_path: Path):
        """Second cycle should not re-process same lines."""
        (tmp_path / "mqtt_connect.log").write_text(json.dumps({
            "ts": 1.0, "id.orig_h": "1.2.3.4", "client_id": "c1",
            "connect_status": "0",
        }) + "\n")

        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        influx = AsyncMock()
        parser = MqttParser(log_tracker=tracker, influx_writer=influx, service=MagicMock())

        await parser._parse_cycle()
        assert influx.write_points.call_count == 1

        influx.reset_mock()
        await parser._parse_cycle()
        influx.write_points.assert_not_called()


# ---------------------------------------------------------------------------
# X.509 Parser
# ---------------------------------------------------------------------------


class TestX509Parser:
    @pytest.fixture
    def parser(self):
        return X509Parser(
            log_tracker=MagicMock(),
            cert_tracker=AsyncMock(),
            service=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_parse_x509_line(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "fingerprint": "sha256:abc123def456",
            "certificate.subject": "CN=example.com",
            "certificate.issuer": "CN=Let's Encrypt Authority X3",
            "certificate.not_valid_before": 1700000000.0,
            "certificate.not_valid_after": 1730000000.0,
            "certificate.key_type": "rsa",
            "certificate.key_length": 2048,
            "certificate.serial": "0123456789ABCDEF",
        })
        await parser._parse_x509_line(line)

        parser._cert_tracker.upsert_certificate.assert_called_once()
        call_kwargs = parser._cert_tracker.upsert_certificate.call_args.kwargs
        assert call_kwargs["fingerprint"] == "sha256:abc123def456"
        assert call_kwargs["subject"] == "CN=example.com"
        assert call_kwargs["self_signed"] is False
        assert parser.certs_tracked == 1

    @pytest.mark.asyncio
    async def test_parse_x509_self_signed(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "fingerprint": "sha256:self_signed_fp",
            "certificate.subject": "CN=my.local",
            "certificate.issuer": "CN=my.local",
        })
        await parser._parse_x509_line(line)

        call_kwargs = parser._cert_tracker.upsert_certificate.call_args.kwargs
        assert call_kwargs["self_signed"] is True

    @pytest.mark.asyncio
    async def test_parse_x509_no_fingerprint(self, parser):
        line = json.dumps({"ts": 1.0, "certificate.subject": "CN=test"})
        await parser._parse_x509_line(line)
        parser._cert_tracker.upsert_certificate.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_x509_invalid_json(self, parser):
        await parser._parse_x509_line("not json")
        parser._cert_tracker.upsert_certificate.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_ssl_line(self, parser):
        line = json.dumps({
            "ts": 1710600000.0,
            "id.orig_h": "192.168.1.42",
            "id.resp_h": "93.184.216.34",
            "version": "TLSv12",
            "cipher": "TLS_AES_256_GCM_SHA384",
            "server_name": "example.com",
            "cert_chain_fps": ["sha256:abc123def456"],
        })
        await parser._parse_ssl_line(line)

        parser._cert_tracker.update_tls_metadata.assert_called_once()
        call_kwargs = parser._cert_tracker.update_tls_metadata.call_args.kwargs
        assert call_kwargs["tls_version"] == "TLSv12"
        assert call_kwargs["server_name"] == "example.com"

    @pytest.mark.asyncio
    async def test_parse_ssl_no_cert_chain(self, parser):
        line = json.dumps({"ts": 1.0, "version": "TLSv12"})
        await parser._parse_ssl_line(line)
        parser._cert_tracker.update_tls_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_ssl_invalid_json(self, parser):
        await parser._parse_ssl_line("not json")
        parser._cert_tracker.update_tls_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_parse_cycle(self, tmp_path: Path):
        (tmp_path / "x509.log").write_text(json.dumps({
            "ts": 1.0,
            "fingerprint": "fp1",
            "certificate.subject": "CN=test",
            "certificate.issuer": "CN=CA",
        }) + "\n")

        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        cert_tracker = AsyncMock()
        parser = X509Parser(log_tracker=tracker, cert_tracker=cert_tracker, service=MagicMock())

        await parser._parse_cycle()

        cert_tracker.upsert_certificate.assert_called_once()
        assert parser.certs_tracked == 1


# ---------------------------------------------------------------------------
# Log Tracker — Phase 3 log files
# ---------------------------------------------------------------------------


class TestLogTrackerPhase3:
    def test_mqtt_connect_log_tracked(self, tmp_path: Path):
        (tmp_path / "mqtt_connect.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        lines = tracker.read_new_lines("mqtt_connect.log")
        assert len(lines) == 1

    def test_mqtt_publish_log_tracked(self, tmp_path: Path):
        (tmp_path / "mqtt_publish.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        lines = tracker.read_new_lines("mqtt_publish.log")
        assert len(lines) == 1

    def test_mqtt_subscribe_log_tracked(self, tmp_path: Path):
        (tmp_path / "mqtt_subscribe.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        lines = tracker.read_new_lines("mqtt_subscribe.log")
        assert len(lines) == 1

    def test_x509_log_tracked(self, tmp_path: Path):
        (tmp_path / "x509.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        lines = tracker.read_new_lines("x509.log")
        assert len(lines) == 1

    def test_log_freshness_includes_mqtt(self, tmp_path: Path):
        (tmp_path / "mqtt_connect.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_path), state_dir=str(tmp_path))
        freshness = tracker.get_log_freshness()
        assert freshness is not None
        assert freshness < 5


# ---------------------------------------------------------------------------
# Security Alerts (Story 74.5)
# ---------------------------------------------------------------------------


class TestSecurityAlerts:
    def test_rogue_client_detection(self):
        """Unknown MQTT client IDs should be flagged."""
        parser = MqttParser(
            log_tracker=MagicMock(),
            influx_writer=AsyncMock(),
            service=MagicMock(),
        )

        # Add a known client
        parser._parse_connect_line(json.dumps({
            "ts": 1.0,
            "id.orig_h": "192.168.1.50",
            "client_id": "homeassistant_core",
            "connect_status": "0",
        }))

        # Add an unknown client
        parser._parse_connect_line(json.dumps({
            "ts": 1.0,
            "id.orig_h": "192.168.1.99",
            "client_id": "rogue_device_42",
            "connect_status": "0",
        }))

        clients = parser.get_clients()
        known_prefixes = {"homeassistant", "mosquitto", "zigbee2mqtt", "zwavejs", "esphome"}
        rogue = [
            c for c in clients
            if not any(c["client_id"].lower().startswith(p) for p in known_prefixes)
        ]
        assert len(rogue) == 1
        assert rogue[0]["client_id"] == "rogue_device_42"

    def test_known_client_not_flagged(self):
        """Known MQTT client prefixes should not be flagged."""
        parser = MqttParser(
            log_tracker=MagicMock(),
            influx_writer=AsyncMock(),
            service=MagicMock(),
        )

        for cid in ["homeassistant_core", "zigbee2mqtt_bridge", "esphome_living"]:
            parser._parse_connect_line(json.dumps({
                "ts": 1.0, "id.orig_h": "192.168.1.1",
                "client_id": cid, "connect_status": "0",
            }))

        known_prefixes = {"homeassistant", "mosquitto", "zigbee2mqtt", "zwavejs", "esphome"}
        rogue = [
            c for c in parser.get_clients()
            if not any(c["client_id"].lower().startswith(p) for p in known_prefixes)
        ]
        assert len(rogue) == 0


# ---------------------------------------------------------------------------
# X509 Parser — timestamp parsing
# ---------------------------------------------------------------------------


class TestX509TimestampParsing:
    def test_valid_timestamp(self):
        result = X509Parser._parse_zeek_ts(1700000000.0)
        assert result is not None
        assert result.year == 2023

    def test_none_timestamp(self):
        assert X509Parser._parse_zeek_ts(None) is None

    def test_invalid_timestamp(self):
        assert X509Parser._parse_zeek_ts("not a number") is None
