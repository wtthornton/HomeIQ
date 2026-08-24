"""Tests for Epic 73 — Zeek Device Fingerprinting.

Covers DHCP parsing, TLS fingerprinting, SSH/software fingerprinting,
OUI vendor lookup, and fingerprint service operations.
"""

from __future__ import annotations

import gzip
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.parsers.dhcp_parser import DhcpParser
from src.parsers.ssh_parser import SshParser
from src.parsers.tls_parser import TlsParser
from src.services.log_tracker import LogTracker
from src.services.oui_lookup import OUILookup

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# OUI Vendor Lookup
# ---------------------------------------------------------------------------


def _oui_dataset(tmp_path: Path, rows: dict[str, str]) -> Path:
    path = tmp_path / "ieee-oui.tsv.gz"
    payload = "\n".join(f"{a}\t{o}" for a, o in rows.items()).encode()
    path.write_bytes(gzip.compress(payload))
    return path


class TestOUIDataset:
    """The IEEE dataset, and the sub-assignment rule that makes it necessary."""

    def test_longest_prefix_wins(self, tmp_path: Path):
        """A 36-bit MA-S assignee outranks the 24-bit block holder.

        IEEE subdivides MA-L blocks; the sub-assignee is a different company.
        Reading only 3 octets names the block holder, which is the wrong vendor.
        """
        dataset = _oui_dataset(
            tmp_path,
            {
                "8CF681": "Block Holder Inc",
                "8CF6810": "Mid Assignee Ltd",
                "8CF681012": "Actual Vendor GmbH",
            },
        )
        oui = OUILookup(dataset_path=dataset)

        assert oui.source == "ieee"
        assert oui.lookup("8C:F6:81:01:23:45") == "Actual Vendor GmbH"
        assert oui.lookup("8C:F6:81:0F:FF:FF") == "Mid Assignee Ltd"
        assert oui.lookup("8C:F6:81:FF:FF:FF") == "Block Holder Inc"

    def test_real_ring_and_amazon_prefixes(self, tmp_path: Path):
        """The prefixes the curated list missed on the reference network."""
        dataset = _oui_dataset(
            tmp_path,
            {"9C7613": "Ring LLC", "90486C": "Ring LLC", "C08D51": "Amazon Technologies Inc."},
        )
        oui = OUILookup(dataset_path=dataset)

        assert oui.lookup("9C:76:13:00:00:11") == "Ring LLC"
        assert oui.lookup("90:48:6C:00:00:22") == "Ring LLC"
        assert oui.lookup("C0:8D:51:00:00:44") == "Amazon Technologies Inc."

    def test_missing_dataset_falls_back_and_says_so(self, tmp_path: Path):
        """A missing dataset degrades loudly rather than resolving everything to Unknown."""
        oui = OUILookup(dataset_path=tmp_path / "absent.tsv.gz")

        assert oui.source == "curated-fallback"
        assert oui.lookup("24:6F:28:AA:BB:CC") == "Espressif"


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

        line = json.dumps(
            {
                "id.orig_h": "192.168.1.42",
                "ja3": "abc123",
                "ja4": "def456",
            }
        )
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
