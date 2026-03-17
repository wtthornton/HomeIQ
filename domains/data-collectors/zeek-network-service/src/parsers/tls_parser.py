"""Parser for Zeek ssl.log + ja3.log + ja4.log — TLS fingerprinting.

Reads JSON lines from TLS-related logs and updates the
network_device_fingerprints table with JA3/JA3S/JA4 hashes,
correlating by source IP to existing MAC-based records.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging

if TYPE_CHECKING:
    from ..services.fingerprint_service import FingerprintService
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-tls-parser")


class TlsParser:
    """Parses Zeek TLS logs and updates fingerprint records."""

    def __init__(
        self,
        log_tracker: LogTracker,
        fingerprint_service: FingerprintService,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._fingerprint_service = fingerprint_service
        self._service = service
        self.tls_fingerprints_captured: int = 0

    async def run(self, interval: int) -> None:
        """Background loop: parse TLS logs every ``interval`` seconds."""
        logger.info("Starting TLS parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("TLS parser cancelled")
                raise
            except Exception as e:
                logger.error("TLS parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from ssl.log, ja3.log, ja4.log and update fingerprints."""
        updated = False

        # JA3 log — has ja3 (client) and ja3s (server) hashes
        for line in self._log_tracker.read_new_lines("ja3.log"):
            await self._parse_ja3_line(line)
            updated = True

        # JA4 log — has ja4 fingerprint string
        for line in self._log_tracker.read_new_lines("ja4.log"):
            await self._parse_ja4_line(line)
            updated = True

        # ssl.log — fallback for JA3/JA4 if they're embedded in ssl.log fields
        for line in self._log_tracker.read_new_lines("ssl.log"):
            await self._parse_ssl_line(line)
            updated = True

        if updated:
            self._log_tracker.save_offsets()

    async def _parse_ja3_line(self, line: str) -> None:
        """Parse a ja3.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        src_ip = entry.get("id.orig_h", "")
        if not src_ip:
            return

        ja3_hash = entry.get("ja3", "")
        ja3s_hash = entry.get("ja3s", "")

        if not ja3_hash and not ja3s_hash:
            return

        await self._fingerprint_service.update_tls_fingerprints(
            ip_address=src_ip,
            ja3_hash=ja3_hash or None,
            ja3s_hash=ja3s_hash or None,
        )
        self.tls_fingerprints_captured += 1

    async def _parse_ja4_line(self, line: str) -> None:
        """Parse a ja4.log JSON line."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        src_ip = entry.get("id.orig_h", "")
        if not src_ip:
            return

        ja4_hash = entry.get("ja4", "")
        if not ja4_hash:
            return

        await self._fingerprint_service.update_tls_fingerprints(
            ip_address=src_ip,
            ja4_hash=ja4_hash,
        )
        self.tls_fingerprints_captured += 1

    async def _parse_ssl_line(self, line: str) -> None:
        """Parse ssl.log — extract JA3/JA4 if embedded as fields."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        src_ip = entry.get("id.orig_h", "")
        if not src_ip:
            return

        # Some Zeek configs embed ja3/ja4 directly in ssl.log
        ja3 = entry.get("ja3")
        ja3s = entry.get("ja3s")
        ja4 = entry.get("ja4")

        if not any([ja3, ja3s, ja4]):
            return

        await self._fingerprint_service.update_tls_fingerprints(
            ip_address=src_ip,
            ja3_hash=ja3 or None,
            ja3s_hash=ja3s or None,
            ja4_hash=ja4 or None,
        )
        self.tls_fingerprints_captured += 1
