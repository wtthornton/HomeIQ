"""Tests for Zeek log parsers — conn.log and dns.log."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.parsers.conn_parser import ConnLogParser, _classify_direction, _is_private, _safe_int, _safe_float
from src.parsers.dns_parser import DnsLogParser
from src.services.device_aggregator import DeviceAggregator
from src.services.log_tracker import LogTracker


# ---------------------------------------------------------------------------
# Direction classification
# ---------------------------------------------------------------------------

class TestDirectionClassification:
    def test_outbound(self):
        assert _classify_direction("192.168.1.42", "93.184.216.34") == "outbound"

    def test_inbound(self):
        assert _classify_direction("93.184.216.34", "192.168.1.42") == "inbound"

    def test_internal(self):
        assert _classify_direction("192.168.1.42", "192.168.1.1") == "internal"

    def test_private_ranges(self):
        assert _is_private("10.0.0.1") is True
        assert _is_private("172.16.0.1") is True
        assert _is_private("192.168.1.1") is True
        assert _is_private("8.8.8.8") is False
        assert _is_private("invalid") is False

    def test_ipv6_private(self):
        assert _is_private("::1") is True
        assert _is_private("fd00::1") is True
        assert _is_private("fe80::1") is True
        assert _is_private("2001:db8::1") is False


class TestSafeConversions:
    def test_safe_int_normal(self):
        assert _safe_int(42) == 42
        assert _safe_int("100") == 100

    def test_safe_int_zeek_dash(self):
        assert _safe_int("-") == 0
        assert _safe_int(None) == 0
        assert _safe_int("") == 0

    def test_safe_float_normal(self):
        assert _safe_float(1.5) == 1.5
        assert _safe_float("0.01") == 0.01

    def test_safe_float_zeek_dash(self):
        assert _safe_float("-") == 0.0
        assert _safe_float(None) == 0.0


# ---------------------------------------------------------------------------
# Log tracker
# ---------------------------------------------------------------------------

class TestLogTracker:
    def test_load_save_offsets(self, tmp_log_dir: Path):
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        tracker._offsets = {"conn.log": {"offset": 1234, "inode": 5678}}
        tracker.save_offsets()

        tracker2 = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        tracker2.load_offsets()
        assert tracker2._offsets["conn.log"]["offset"] == 1234

    def test_read_new_lines(self, tmp_log_dir: Path, sample_conn_log_lines: list[str]):
        log_file = tmp_log_dir / "conn.log"
        log_file.write_text("\n".join(sample_conn_log_lines) + "\n")

        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        lines = tracker.read_new_lines("conn.log")
        assert len(lines) == 3

        # Second read should return nothing (no new data)
        lines2 = tracker.read_new_lines("conn.log")
        assert len(lines2) == 0

    def test_read_after_rotation(self, tmp_log_dir: Path, sample_conn_log_lines: list[str]):
        log_file = tmp_log_dir / "conn.log"
        log_file.write_text("\n".join(sample_conn_log_lines) + "\n")

        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        tracker.read_new_lines("conn.log")

        # Simulate rotation: overwrite with smaller content
        log_file.write_text(sample_conn_log_lines[0] + "\n")
        lines = tracker.read_new_lines("conn.log")
        assert len(lines) == 1  # Reset to beginning due to size decrease

    def test_missing_log_file(self, tmp_log_dir: Path):
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        lines = tracker.read_new_lines("nonexistent.log")
        assert lines == []

    def test_log_freshness(self, tmp_log_dir: Path):
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        assert tracker.get_log_freshness() is None

        (tmp_log_dir / "conn.log").write_text("{}\n")
        freshness = tracker.get_log_freshness()
        assert freshness is not None
        assert freshness < 5  # Should be very recent


# ---------------------------------------------------------------------------
# conn.log parser
# ---------------------------------------------------------------------------

class TestConnLogParser:
    def test_parse_line_valid(self, sample_conn_log_lines: list[str]):
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = ConnLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        result = parser._parse_line(sample_conn_log_lines[0])
        assert result is not None
        point, parsed = result
        assert parsed["src_ip"] == "192.168.1.42"
        assert parsed["dst_ip"] == "93.184.216.34"
        assert parsed["orig_bytes"] == 1024
        assert parsed["resp_bytes"] == 4096
        assert parsed["duration"] == 1.234
        assert parsed["service"] == "ssl"

    def test_parse_line_invalid_json(self):
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = ConnLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        assert parser._parse_line("not json") is None

    def test_parse_line_missing_ips(self):
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = ConnLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        assert parser._parse_line(json.dumps({"ts": 1.0})) is None

    def test_docker_bridge_traffic_parsed(self, sample_conn_log_lines: list[str]):
        """Docker bridge traffic is parsed (BPF should exclude it, not the parser)."""
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = ConnLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        # Third entry is Docker bridge traffic (172.18.x.x)
        result = parser._parse_line(sample_conn_log_lines[2])
        assert result is not None
        _, parsed = result
        assert parsed["src_ip"] == "172.18.0.5"


# ---------------------------------------------------------------------------
# dns.log parser
# ---------------------------------------------------------------------------

class TestDnsLogParser:
    def test_parse_line_valid(self, sample_dns_log_lines: list[str]):
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = DnsLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        result = parser._parse_line(sample_dns_log_lines[0])
        assert result is not None
        point, device_ip, domain = result
        assert device_ip == "192.168.1.42"
        assert domain == "api.tuya.com"

    def test_parse_line_missing_query(self):
        aggregator = MagicMock(spec=DeviceAggregator)
        parser = DnsLogParser(
            log_tracker=MagicMock(),
            influx_writer=MagicMock(),
            aggregator=aggregator,
            service=MagicMock(),
        )
        line = json.dumps({"ts": 1.0, "id.orig_h": "192.168.1.42"})
        assert parser._parse_line(line) is None


# ---------------------------------------------------------------------------
# Device aggregator
# ---------------------------------------------------------------------------

class TestDeviceAggregator:
    def test_record_and_get_devices(self):
        aggregator = DeviceAggregator(influx_writer=MagicMock(), service=MagicMock())
        aggregator.record_connection(
            src_ip="192.168.1.42",
            dst_ip="93.184.216.34",
            orig_bytes=1024,
            resp_bytes=4096,
            duration=1.0,
            service="ssl",
        )
        aggregator.record_dns_query("192.168.1.42", "example.com")

        devices = aggregator.get_devices()
        assert len(devices) == 1
        assert devices[0]["ip"] == "192.168.1.42"
        assert devices[0]["bytes_sent_window"] == 1024

    def test_get_device_not_found(self):
        aggregator = DeviceAggregator(influx_writer=MagicMock(), service=MagicMock())
        assert aggregator.get_device("10.0.0.1") is None

    def test_get_device_detail(self):
        aggregator = DeviceAggregator(influx_writer=MagicMock(), service=MagicMock())
        aggregator.record_connection(
            "192.168.1.42", "93.184.216.34", 1024, 4096, 1.0, "ssl"
        )
        aggregator.record_connection(
            "192.168.1.42", "8.8.8.8", 64, 256, 0.01, "dns"
        )
        aggregator.record_dns_query("192.168.1.42", "example.com")
        aggregator.record_dns_query("192.168.1.42", "api.tuya.com")

        detail = aggregator.get_device("192.168.1.42")
        assert detail is not None
        assert detail["connections_window"] == 2
        assert detail["unique_destinations"] == 2
        assert detail["unique_domains"] == 2
        assert len(detail["active_services"]) == 2

    def test_current_stats(self):
        aggregator = DeviceAggregator(influx_writer=MagicMock(), service=MagicMock())
        aggregator.record_connection(
            "192.168.1.42", "93.184.216.34", 1024, 4096, 1.0, "ssl"
        )
        stats = aggregator.get_current_stats()
        assert stats["active_devices"] == 1
        assert stats["total_connections"] == 1
        assert stats["total_bytes"] == 5120
        assert len(stats["top_talkers"]) == 1


# ---------------------------------------------------------------------------
# Restart recovery (no duplicate writes)
# ---------------------------------------------------------------------------

class TestRestartRecovery:
    def test_offsets_persist_across_restarts(
        self, tmp_log_dir: Path, sample_conn_log_lines: list[str]
    ):
        log_file = tmp_log_dir / "conn.log"
        log_file.write_text("\n".join(sample_conn_log_lines) + "\n")

        # First "session" — read all lines
        tracker1 = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        lines1 = tracker1.read_new_lines("conn.log")
        assert len(lines1) == 3
        tracker1.save_offsets()

        # Second "session" — simulate restart, load offsets
        tracker2 = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        tracker2.load_offsets()
        lines2 = tracker2.read_new_lines("conn.log")
        assert len(lines2) == 0  # No duplicates
