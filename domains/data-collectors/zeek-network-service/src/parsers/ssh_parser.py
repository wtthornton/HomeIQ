"""Parser for Zeek hassh.log + software.log — SSH and software fingerprinting.

Reads JSON lines from hassh.log and software.log, updates the
network_device_fingerprints table with HASSH hashes, user-agent
strings, server software, and OS guesses.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging

if TYPE_CHECKING:
    from ..services.fingerprint_service import FingerprintService
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-ssh-parser")


class SshParser:
    """Parses Zeek hassh.log and software.log for device fingerprinting."""

    def __init__(
        self,
        log_tracker: LogTracker,
        fingerprint_service: FingerprintService,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._fingerprint_service = fingerprint_service
        self._service = service
        self.ssh_fingerprints_captured: int = 0
        self.software_entries_captured: int = 0

    async def run(self, interval: int) -> None:
        """Background loop: parse SSH/software logs every ``interval`` seconds."""
        logger.info("Starting SSH/software parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("SSH/software parser cancelled")
                raise
            except Exception as e:
                logger.error("SSH/software parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from hassh.log + software.log and update fingerprints."""
        updated = False

        for line in self._log_tracker.read_new_lines("hassh.log"):
            await self._parse_hassh_line(line)
            updated = True

        for line in self._log_tracker.read_new_lines("software.log"):
            await self._parse_software_line(line)
            updated = True

        if updated:
            self._log_tracker.save_offsets()

    async def _parse_hassh_line(self, line: str) -> None:
        """Parse a hassh.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        src_ip = entry.get("id.orig_h", "")
        if not src_ip:
            return

        hassh = entry.get("hassh", "")
        hassh_server = entry.get("hasshServer", "")

        if not hassh and not hassh_server:
            return

        await self._fingerprint_service.update_ssh_fingerprints(
            ip_address=src_ip,
            hassh_hash=hassh or None,
            hassh_server=hassh_server or None,
        )
        self.ssh_fingerprints_captured += 1

    async def _parse_software_line(self, line: str) -> None:
        """Parse a software.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        host = entry.get("host", "")
        if not host:
            return

        software_type = entry.get("software_type", "")
        name = entry.get("name", "")
        version_major = entry.get("version.major", "")
        version_minor = entry.get("version.minor", "")

        version_str = ""
        if version_major is not None and version_major != "":
            version_str = str(version_major)
            if version_minor is not None and version_minor != "":
                version_str += f".{version_minor}"

        software_name = f"{name} {version_str}".strip() if name else ""
        if not software_name:
            return

        # Determine which field to update based on software_type
        user_agent = None
        server_software = None
        os_guess = None

        if software_type in ("HTTP::BROWSER", "HTTP::USER_AGENT"):
            user_agent = software_name
        elif software_type in ("HTTP::SERVER", "HTTP::APPSERVER"):
            server_software = software_name
        elif software_type == "OS":
            os_guess = software_name
        else:
            # Generic — store as user_agent
            user_agent = software_name

        await self._fingerprint_service.update_software(
            ip_address=host,
            user_agent=user_agent,
            server_software=server_software,
            os_guess=os_guess,
        )
        self.software_entries_captured += 1
