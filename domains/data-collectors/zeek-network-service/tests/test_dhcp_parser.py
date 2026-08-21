"""Tests for the Zeek DHCP parser.

Covers the address-field fallback and the one-time rotated-log backfill —
the two behaviours that decide whether a device on the LAN is ever seen at
all. Fixtures use real MACs observed on the reference network.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.parsers.dhcp_parser import DhcpParser
from src.services.log_tracker import LogTracker
from src.services.oui_lookup import OUILookup

if TYPE_CHECKING:
    from pathlib import Path


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


def _dhcp_parser(fp_service: AsyncMock, log_tracker=None) -> DhcpParser:
    return DhcpParser(
        log_tracker=log_tracker or MagicMock(),
        fingerprint_service=fp_service,
        oui_lookup=OUILookup(),
        service=MagicMock(),
    )


class TestDhcpAddressFallback:
    """A record carrying only ``requested_addr`` must still be ingested.

    Zeek emits ``assigned_addr`` only when it sees the server's ACK. A sensor
    that is not inline with the DHCP server sees mostly client broadcasts, so
    ``requested_addr`` is the only address on 92% of records — and dropping
    them hid every Ring and Amazon device on the reference instance.
    """

    @pytest.mark.asyncio
    async def test_requested_addr_only_is_ingested(self):
        fp_service = AsyncMock()
        parser = _dhcp_parser(fp_service)

        await parser._parse_dhcp_line(
            json.dumps(
                {
                    "ts": 1787343812.0,
                    "mac": "40:f6:bc:00:00:55",
                    "requested_addr": "192.168.1.229",
                    "msg_types": ["REQUEST"],
                }
            )
        )

        fp_service.upsert_dhcp.assert_called_once()
        assert fp_service.upsert_dhcp.call_args.kwargs["ip_address"] == "192.168.1.229"
        assert fp_service.upsert_dhcp.call_args.kwargs["mac_address"] == "40:f6:bc:00:00:55"

    @pytest.mark.asyncio
    async def test_assigned_addr_wins_over_requested(self):
        """The server's grant outranks the client's ask when both are present."""
        fp_service = AsyncMock()
        parser = _dhcp_parser(fp_service)

        await parser._parse_dhcp_line(
            json.dumps(
                {
                    "ts": 1.0,
                    "mac": "9c:76:13:00:00:11",
                    "requested_addr": "192.168.1.99",
                    "client_addr": "192.168.1.55",
                    "assigned_addr": "192.168.1.40",
                }
            )
        )

        assert fp_service.upsert_dhcp.call_args.kwargs["ip_address"] == "192.168.1.40"

    @pytest.mark.asyncio
    async def test_failed_write_does_not_count_as_a_discovery(self):
        """A dead pool must not inflate ``devices_discovered``.

        ``upsert_dhcp`` returns False when the connection pool never opened.
        Counting that as a discovery is what let the service report thousands
        of upserts into an empty table.
        """
        fp_service = AsyncMock()
        fp_service.upsert_dhcp.return_value = False
        parser = _dhcp_parser(fp_service)

        await parser._parse_dhcp_line(
            json.dumps({"ts": 1.0, "mac": "9c:76:13:00:00:11", "requested_addr": "192.168.1.40"})
        )

        fp_service.upsert_dhcp.assert_called_once()
        assert parser.devices_discovered == 0

    @pytest.mark.asyncio
    async def test_no_address_at_all_is_skipped(self):
        fp_service = AsyncMock()
        parser = _dhcp_parser(fp_service)

        await parser._parse_dhcp_line(json.dumps({"ts": 1.0, "mac": "b0:09:da:00:00:33"}))

        fp_service.upsert_dhcp.assert_not_called()


class TestDhcpBackfill:
    """Rotated logs are read exactly once, so a quiet device is still found."""

    @pytest.mark.asyncio
    async def test_reads_rotated_logs_and_marks_done(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        state_dir = tmp_path / "state"
        log_dir.mkdir()
        state_dir.mkdir()
        (log_dir / "dhcp.2026-08-13-07-13-00.log").write_text(
            json.dumps({"ts": 1.0, "mac": "90:48:6c:00:00:22", "requested_addr": "192.168.1.201"})
            + "\n"
        )
        # The live file is the tail parser's job, not the backfill's.
        (log_dir / "dhcp.log").write_text(
            json.dumps({"ts": 2.0, "mac": "aa:bb:cc:dd:ee:ff", "requested_addr": "10.0.0.1"}) + "\n"
        )

        fp_service = AsyncMock()
        tracker = LogTracker(log_dir=str(log_dir), state_dir=str(state_dir))
        parser = _dhcp_parser(fp_service, log_tracker=tracker)

        assert await parser.backfill() == 1
        assert fp_service.upsert_dhcp.call_args.kwargs["mac_address"] == "90:48:6c:00:00:22"
        assert (state_dir / "dhcp-backfill.done").exists()

        # Second run is a no-op — the marker is the whole point.
        fp_service.upsert_dhcp.reset_mock()
        assert await parser.backfill() == 0
        fp_service.upsert_dhcp.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_rotated_logs_is_not_an_error(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        state_dir = tmp_path / "state"
        log_dir.mkdir()
        state_dir.mkdir()

        parser = _dhcp_parser(
            AsyncMock(), log_tracker=LogTracker(log_dir=str(log_dir), state_dir=str(state_dir))
        )

        assert await parser.backfill() == 0
