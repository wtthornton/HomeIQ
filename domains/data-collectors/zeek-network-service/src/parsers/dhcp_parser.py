"""Parser for Zeek dhcp.log + dhcpfp.log — DHCP device discovery.

Reads JSON lines from DHCP logs, extracts MAC/IP/hostname, performs
OUI vendor lookup, and upserts into network_device_fingerprints via
FingerprintService.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging

if TYPE_CHECKING:
    from ..services.fingerprint_service import FingerprintService
    from ..services.log_tracker import LogTracker
    from ..services.oui_lookup import OUILookup

logger = setup_logging("zeek-dhcp-parser")


class DhcpParser:
    """Parses Zeek dhcp.log and dhcpfp.log to discover network devices."""

    def __init__(
        self,
        log_tracker: LogTracker,
        fingerprint_service: FingerprintService,
        oui_lookup: OUILookup,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._fingerprint_service = fingerprint_service
        self._oui_lookup = oui_lookup
        self._service = service
        self.devices_discovered: int = 0

    async def run(self, interval: int) -> None:
        """Background loop: parse DHCP logs every ``interval`` seconds."""
        logger.info("Starting DHCP parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("DHCP parser cancelled")
                raise
            except Exception as e:
                logger.error("DHCP parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from dhcp.log + dhcpfp.log, upsert devices."""
        # Parse dhcp.log for MAC/IP/hostname
        dhcp_lines = self._log_tracker.read_new_lines("dhcp.log")
        for line in dhcp_lines:
            await self._parse_dhcp_line(line)

        # Parse dhcpfp.log for DHCP fingerprints (from KYD package)
        dhcpfp_lines = self._log_tracker.read_new_lines("dhcpfp.log")
        for line in dhcpfp_lines:
            await self._parse_dhcpfp_line(line)

        if dhcp_lines or dhcpfp_lines:
            self._log_tracker.save_offsets()

    async def _parse_dhcp_line(self, line: str) -> None:
        """Parse a dhcp.log JSON line and upsert the device."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        mac = entry.get("mac", "")
        client_addr = entry.get("assigned_addr") or entry.get("client_addr", "")

        if not mac or not client_addr:
            return

        hostname = entry.get("host_name")
        vendor = self._oui_lookup.lookup(mac)

        await self._fingerprint_service.upsert_dhcp(
            mac_address=mac,
            ip_address=client_addr,
            hostname=hostname,
            vendor=vendor,
        )
        self.devices_discovered += 1
        logger.debug("DHCP discovery: %s → %s (%s)", mac, client_addr, hostname or "no hostname")

    async def _parse_dhcpfp_line(self, line: str) -> None:
        """Parse a dhcpfp.log (KYD) JSON line and update fingerprint fields."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        mac = entry.get("mac", "")
        if not mac:
            return

        fingerprint = entry.get("fingerprint", "")
        vendor_class = entry.get("vendor_class", "")
        client_addr = entry.get("client_addr") or entry.get("assigned_addr", "")

        if not client_addr:
            return

        vendor = self._oui_lookup.lookup(mac)

        await self._fingerprint_service.upsert_dhcp(
            mac_address=mac,
            ip_address=client_addr,
            vendor=vendor,
            dhcp_fingerprint=fingerprint or None,
            dhcp_vendor_class=vendor_class or None,
        )
