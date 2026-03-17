"""Tests for Epic 73 — Zeek Device Fingerprinting.

Covers DHCP parsing, TLS fingerprinting, SSH/software fingerprinting,
OUI vendor lookup, and fingerprint service operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.parsers.dhcp_parser import DhcpParser
from src.parsers.tls_parser import TlsParser
from src.parsers.ssh_parser import SshParser
from src.services.oui_lookup import OUILookup
from src.services.log_tracker import LogTracker


# ---------------------------------------------------------------------------
# OUI Vendor Lookup
# ---------------------------------------------------------------------------

class TestOUILookup:
    def test_known_espressif(self):
        oui = OUILookup()
        assert oui.lookup("24:6F:28:AA:BB:CC") == "Espressif"

    def test_known_raspberry_pi(self):
        oui = OUILookup()
        assert oui.lookup("B8:27:EB:11:22:33") == "Raspberry Pi"

    def test_known_philips_hue(self):
        oui = OUILookup()
        assert oui.lookup("00:17:88:AA:BB:CC") == "Philips Hue"

    def test_unknown_vendor(self):
        oui = OUILookup()
        assert oui.lookup("FF:FF:FF:AA:BB:CC") == "Unknown"

    def test_case_insensitive(self):
        oui = OUILookup()
        assert oui.lookup("24:6f:28:aa:bb:cc") == "Espressif"

    def test_dash_separator(self):
        oui = OUILookup()
        assert oui.lookup("24-6F-28-AA-BB-CC") == "Espressif"

    def test_tp_link(self):
        oui = OUILookup()
        assert oui.lookup("50:C7:BF:AA:BB:CC") == "TP-Link"

    def test_google(self):
        oui = OUILookup()
        assert oui.lookup("F4:F5:D8:AA:BB:CC") == "Google"

    def test_amazon(self):
        oui = OUILookup()
        assert oui.lookup("FC:65:DE:AA:BB:CC") == "Amazon"


# ---------------------------------------------------------------------------
# DHCP Parser
# ---------------------------------------------------------------------------

class TestDhcpParser:
    @pytest.mark.asyncio
    async def test_parse_dhcp_line(self, sample_dhcp_log_lines: list[str]):
        fp_service = AsyncMock()
        oui = OUILookup()
        parser = DhcpParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            oui_lookup=oui,
            service=MagicMock(),
        )

        await parser._parse_dhcp_line(sample_dhcp_log_lines[0])

        fp_service.upsert_dhcp.assert_called_once()
        call_kwargs = fp_service.upsert_dhcp.call_args
        assert call_kwargs.kwargs["mac_address"] == "24:6f:28:aa:bb:cc"
        assert call_kwargs.kwargs["ip_address"] == "192.168.1.42"
        assert call_kwargs.kwargs["hostname"] == "esp32-livingroom"
        assert call_kwargs.kwargs["vendor"] == "Espressif"

    @pytest.mark.asyncio
    async def test_parse_dhcp_line_no_mac(self):
        fp_service = AsyncMock()
        parser = DhcpParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            oui_lookup=OUILookup(),
            service=MagicMock(),
        )

        await parser._parse_dhcp_line(json.dumps({"ts": 1.0, "client_addr": "1.2.3.4"}))
        fp_service.upsert_dhcp.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_dhcpfp_line(self, sample_dhcpfp_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = DhcpParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            oui_lookup=OUILookup(),
            service=MagicMock(),
        )

        await parser._parse_dhcpfp_line(sample_dhcpfp_log_lines[0])

        fp_service.upsert_dhcp.assert_called_once()
        call_kwargs = fp_service.upsert_dhcp.call_args
        assert call_kwargs.kwargs["dhcp_fingerprint"] == "1,33,3,6,15,26,28,51,58,59"
        assert call_kwargs.kwargs["dhcp_vendor_class"] == "dhcpcd-6.7.1:Linux-5.4"

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self):
        fp_service = AsyncMock()
        parser = DhcpParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            oui_lookup=OUILookup(),
            service=MagicMock(),
        )

        await parser._parse_dhcp_line("not json")
        fp_service.upsert_dhcp.assert_not_called()

    @pytest.mark.asyncio
    async def test_devices_discovered_counter(self, sample_dhcp_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = DhcpParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            oui_lookup=OUILookup(),
            service=MagicMock(),
        )

        assert parser.devices_discovered == 0
        await parser._parse_dhcp_line(sample_dhcp_log_lines[0])
        assert parser.devices_discovered == 1
        await parser._parse_dhcp_line(sample_dhcp_log_lines[1])
        assert parser.devices_discovered == 2


# ---------------------------------------------------------------------------
# TLS Parser
# ---------------------------------------------------------------------------

class TestTlsParser:
    @pytest.mark.asyncio
    async def test_parse_ja3_line(self, sample_ja3_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_ja3_line(sample_ja3_log_lines[0])

        fp_service.update_tls_fingerprints.assert_called_once()
        call_kwargs = fp_service.update_tls_fingerprints.call_args
        assert call_kwargs.kwargs["ip_address"] == "192.168.1.42"
        assert call_kwargs.kwargs["ja3_hash"] == "e7d705a3286e19ea42f587b344ee6865"
        assert call_kwargs.kwargs["ja3s_hash"] == "ec74a5c51106f0419184d0dd08fb05bc"

    @pytest.mark.asyncio
    async def test_parse_ja4_line(self, sample_ja4_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_ja4_line(sample_ja4_log_lines[0])

        fp_service.update_tls_fingerprints.assert_called_once()
        call_kwargs = fp_service.update_tls_fingerprints.call_args
        assert call_kwargs.kwargs["ja4_hash"] == "t13d1516h2_8daaf6152771_b186095e22b6"

    @pytest.mark.asyncio
    async def test_parse_ja3_missing_ip(self):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_ja3_line(json.dumps({"ja3": "abc123"}))
        fp_service.update_tls_fingerprints.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_ja3_no_hashes(self):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_ja3_line(json.dumps({"id.orig_h": "192.168.1.42"}))
        fp_service.update_tls_fingerprints.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_ssl_line_with_embedded_ja3(self):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        line = json.dumps({
            "id.orig_h": "192.168.1.42",
            "ja3": "abc123",
            "ja4": "def456",
        })
        await parser._parse_ssl_line(line)

        fp_service.update_tls_fingerprints.assert_called_once()
        call_kwargs = fp_service.update_tls_fingerprints.call_args
        assert call_kwargs.kwargs["ja3_hash"] == "abc123"
        assert call_kwargs.kwargs["ja4_hash"] == "def456"

    @pytest.mark.asyncio
    async def test_tls_counter(self, sample_ja3_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        assert parser.tls_fingerprints_captured == 0
        await parser._parse_ja3_line(sample_ja3_log_lines[0])
        assert parser.tls_fingerprints_captured == 1


# ---------------------------------------------------------------------------
# SSH / Software Parser
# ---------------------------------------------------------------------------

class TestSshParser:
    @pytest.mark.asyncio
    async def test_parse_hassh_line(self, sample_hassh_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_hassh_line(sample_hassh_log_lines[0])

        fp_service.update_ssh_fingerprints.assert_called_once()
        call_kwargs = fp_service.update_ssh_fingerprints.call_args
        assert call_kwargs.kwargs["ip_address"] == "192.168.1.42"
        assert call_kwargs.kwargs["hassh_hash"] == "ec7378c1a92f5a8dde7e8b7a1ddf33d1"
        assert call_kwargs.kwargs["hassh_server"] == "b12d2871a1189eff20364cf5f4c3cc96"

    @pytest.mark.asyncio
    async def test_parse_hassh_missing_ip(self):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_hassh_line(json.dumps({"hassh": "abc"}))
        fp_service.update_ssh_fingerprints.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_software_browser(self, sample_software_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_software_line(sample_software_log_lines[0])

        fp_service.update_software.assert_called_once()
        call_kwargs = fp_service.update_software.call_args
        assert call_kwargs.kwargs["ip_address"] == "192.168.1.42"
        assert call_kwargs.kwargs["user_agent"] == "ESP32-HTTPClient 1.0"
        assert call_kwargs.kwargs["server_software"] is None

    @pytest.mark.asyncio
    async def test_parse_software_os(self, sample_software_log_lines: list[str]):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_software_line(sample_software_log_lines[1])

        fp_service.update_software.assert_called_once()
        call_kwargs = fp_service.update_software.call_args
        assert call_kwargs.kwargs["os_guess"] == "Linux 5.15"

    @pytest.mark.asyncio
    async def test_parse_software_no_host(self):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_software_line(json.dumps({"name": "test"}))
        fp_service.update_software.assert_not_called()

    @pytest.mark.asyncio
    async def test_counters(self, sample_hassh_log_lines, sample_software_log_lines):
        fp_service = AsyncMock()
        parser = SshParser(
            log_tracker=MagicMock(),
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        assert parser.ssh_fingerprints_captured == 0
        assert parser.software_entries_captured == 0

        await parser._parse_hassh_line(sample_hassh_log_lines[0])
        assert parser.ssh_fingerprints_captured == 1

        await parser._parse_software_line(sample_software_log_lines[0])
        assert parser.software_entries_captured == 1


# ---------------------------------------------------------------------------
# Log Tracker — new log files
# ---------------------------------------------------------------------------

class TestLogTrackerNewLogs:
    def test_dhcp_log_tracked(self, tmp_log_dir: Path):
        (tmp_log_dir / "dhcp.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        lines = tracker.read_new_lines("dhcp.log")
        assert len(lines) == 1

    def test_ja3_log_tracked(self, tmp_log_dir: Path):
        (tmp_log_dir / "ja3.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        lines = tracker.read_new_lines("ja3.log")
        assert len(lines) == 1

    def test_log_freshness_includes_dhcp(self, tmp_log_dir: Path):
        (tmp_log_dir / "dhcp.log").write_text('{"ts": 1.0}\n')
        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        freshness = tracker.get_log_freshness()
        assert freshness is not None
        assert freshness < 5


# ---------------------------------------------------------------------------
# DHCP parse cycle (integration-style with LogTracker)
# ---------------------------------------------------------------------------

class TestDhcpParseCycle:
    @pytest.mark.asyncio
    async def test_full_parse_cycle(self, tmp_log_dir: Path, sample_dhcp_log_lines: list[str]):
        """Test DHCP parser reads from log files and calls fingerprint service."""
        log_file = tmp_log_dir / "dhcp.log"
        log_file.write_text("\n".join(sample_dhcp_log_lines) + "\n")

        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        fp_service = AsyncMock()
        oui = OUILookup()
        parser = DhcpParser(
            log_tracker=tracker,
            fingerprint_service=fp_service,
            oui_lookup=oui,
            service=MagicMock(),
        )

        await parser._parse_cycle()

        assert fp_service.upsert_dhcp.call_count == 2
        assert parser.devices_discovered == 2

    @pytest.mark.asyncio
    async def test_no_duplicate_on_second_cycle(
        self, tmp_log_dir: Path, sample_dhcp_log_lines: list[str]
    ):
        """After reading all lines, second cycle should not re-process."""
        log_file = tmp_log_dir / "dhcp.log"
        log_file.write_text("\n".join(sample_dhcp_log_lines) + "\n")

        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        fp_service = AsyncMock()
        parser = DhcpParser(
            log_tracker=tracker,
            fingerprint_service=fp_service,
            oui_lookup=OUILookup(),
            service=MagicMock(),
        )

        await parser._parse_cycle()
        assert fp_service.upsert_dhcp.call_count == 2

        fp_service.reset_mock()
        await parser._parse_cycle()
        assert fp_service.upsert_dhcp.call_count == 0


# ---------------------------------------------------------------------------
# TLS parse cycle (integration-style)
# ---------------------------------------------------------------------------

class TestTlsParseCycle:
    @pytest.mark.asyncio
    async def test_full_tls_cycle(
        self,
        tmp_log_dir: Path,
        sample_ja3_log_lines: list[str],
        sample_ja4_log_lines: list[str],
    ):
        """Test TLS parser reads from ja3.log + ja4.log."""
        (tmp_log_dir / "ja3.log").write_text("\n".join(sample_ja3_log_lines) + "\n")
        (tmp_log_dir / "ja4.log").write_text("\n".join(sample_ja4_log_lines) + "\n")

        tracker = LogTracker(log_dir=str(tmp_log_dir), state_dir=str(tmp_log_dir))
        fp_service = AsyncMock()
        parser = TlsParser(
            log_tracker=tracker,
            fingerprint_service=fp_service,
            service=MagicMock(),
        )

        await parser._parse_cycle()

        # 1 from ja3.log + 1 from ja4.log = 2 calls
        assert fp_service.update_tls_fingerprints.call_count == 2
        assert parser.tls_fingerprints_captured == 2
