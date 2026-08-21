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
    from pathlib import Path

    from ..services.fingerprint_service import FingerprintService
    from ..services.log_tracker import LogTracker
    from ..services.oui_lookup import OUILookup

logger = setup_logging("zeek-dhcp-parser")

#: Address fields in `dhcp.log`, most authoritative first.
#:
#: Zeek only emits ``assigned_addr`` when it observes the server's ACK, and
#: only emits ``client_addr`` when the client already held a lease. On a
#: network where the sensor is not inline with the DHCP server it sees mostly
#: client broadcasts, so ``requested_addr`` is the only address present.
#: Reading just the first two discarded 92% of records on the reference
#: instance (4247 of 4612 carried nothing but ``requested_addr``), and with
#: them every Ring and Amazon device on the LAN.
#:
#: ``requested_addr`` is the client's *ask*, not a server's grant, so the IP it
#: yields can be wrong if the server declines. That is tolerable: the MAC is
#: the identity here and the IP is a mutable address refreshed on every
#: observation.
_ADDRESS_FIELDS = ("assigned_addr", "client_addr", "requested_addr")


def _address_of(entry: dict) -> str:
    """Return the best available client address, or "" when none is present."""
    for field in _ADDRESS_FIELDS:
        value = entry.get(field)
        if value:
            return str(value)
    return ""


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
        self.backfilled_records: int = 0

    async def _ingest_rotated(self, path: Path) -> int:
        """Parse one rotated log. Returns the number of records read."""
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError as e:
            logger.warning("Skipping unreadable %s: %s", path.name, e)
            return 0
        for line in lines:
            await self._parse_dhcp_line(line)
        return len(lines)

    async def backfill(self) -> int:
        """Ingest Zeek's *rotated* DHCP logs once, then never again.

        :class:`LogTracker` follows only the live ``dhcp.log``; every rotated
        ``dhcp.<timestamp>.log`` is invisible to it. That is fine for a stream
        of connections, and wrong for DHCP: a device renews its lease on a
        multi-day timer, so a device that last spoke a week ago exists only in
        a rotated file. Without this, a fresh install reports an empty network
        until every device happens to renew — the same silence as having no
        sensor at all.

        The marker file makes this idempotent across restarts. Re-running it
        would be harmless (``upsert_dhcp`` is keyed on MAC) but pointlessly
        re-reads gigabytes.
        """
        marker = self._log_tracker.state_dir / "dhcp-backfill.done"
        if marker.exists():
            return 0

        rotated = sorted(self._log_tracker.log_dir.glob("dhcp.*.log"))
        if not rotated:
            logger.info("No rotated DHCP logs to backfill")
            return 0

        logger.info("Backfilling %d rotated DHCP log(s)", len(rotated))
        for path in rotated:
            self.backfilled_records += await self._ingest_rotated(path)

        try:
            marker.write_text("")
        except OSError as e:
            # Not fatal: the next start re-reads the same rotated logs and
            # upserts the same MACs. Loud, because it means wasted work.
            logger.warning("Could not write backfill marker %s: %s", marker, e)

        logger.info(
            "DHCP backfill complete: %d record(s) read, %d device upsert(s)",
            self.backfilled_records,
            self.devices_discovered,
        )
        return self.backfilled_records

    async def run(self, interval: int) -> None:
        """Background loop: parse DHCP logs every ``interval`` seconds."""
        logger.info("Starting DHCP parser (every %ds)", interval)
        try:
            await self.backfill()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("DHCP backfill failed; continuing with live tail")
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
        client_addr = _address_of(entry)

        if not mac or not client_addr:
            return

        hostname = entry.get("host_name")
        vendor = self._oui_lookup.lookup(mac)

        written = await self._fingerprint_service.upsert_dhcp(
            mac_address=mac,
            ip_address=client_addr,
            hostname=hostname,
            vendor=vendor,
        )
        if not written:
            return
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
        client_addr = _address_of(entry)

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
