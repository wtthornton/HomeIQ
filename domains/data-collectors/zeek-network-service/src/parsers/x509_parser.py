"""Parser for Zeek x509.log + ssl.log — TLS certificate tracking.

Reads JSON lines from x509.log and ssl.log, extracts certificate
metadata, and stores in PostgreSQL via CertTracker service.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging

if TYPE_CHECKING:
    from ..services.cert_tracker import CertTracker
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-x509-parser")


class X509Parser:
    """Parses Zeek x509.log and ssl.log to track TLS certificates."""

    def __init__(
        self,
        log_tracker: LogTracker,
        cert_tracker: CertTracker,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._cert_tracker = cert_tracker
        self._service = service

        # Stats
        self.certs_tracked: int = 0

    async def run(self, interval: int) -> None:
        """Background loop: parse x509/ssl logs every ``interval`` seconds."""
        logger.info("Starting X.509 parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("X.509 parser cancelled")
                raise
            except Exception as e:
                logger.error("X.509 parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from x509.log + ssl.log and track certs."""
        updated = False

        for line in self._log_tracker.read_new_lines("x509.log"):
            await self._parse_x509_line(line)
            updated = True

        for line in self._log_tracker.read_new_lines("ssl.log"):
            await self._parse_ssl_line(line)
            updated = True

        if updated:
            self._log_tracker.save_offsets()

    async def _parse_x509_line(self, line: str) -> None:
        """Parse x509.log JSON — full certificate metadata."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        fingerprint = entry.get("fingerprint", "")
        if not fingerprint:
            return

        # Extract certificate fields
        subject = entry.get("certificate.subject", "")
        issuer = entry.get("certificate.issuer", "")

        # Validity dates
        not_valid_before = self._parse_zeek_ts(entry.get("certificate.not_valid_before"))
        not_valid_after = self._parse_zeek_ts(entry.get("certificate.not_valid_after"))

        key_type = entry.get("certificate.key_type", "")
        key_length = entry.get("certificate.key_length")
        serial = entry.get("certificate.serial", "")

        # Detect self-signed
        self_signed = subject == issuer if subject and issuer else False

        await self._cert_tracker.upsert_certificate(
            fingerprint=fingerprint,
            subject=subject or None,
            issuer=issuer or None,
            not_valid_before=not_valid_before,
            not_valid_after=not_valid_after,
            key_type=key_type or None,
            key_length=int(key_length) if key_length else None,
            serial=serial or None,
            self_signed=self_signed,
        )
        self.certs_tracked += 1

    async def _parse_ssl_line(self, line: str) -> None:
        """Parse ssl.log JSON — extract TLS version, cipher, and server name."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        # ssl.log links to x509.log via cert_chain_fps
        cert_fps = entry.get("cert_chain_fps", [])
        if not cert_fps or not isinstance(cert_fps, list):
            return

        fingerprint = cert_fps[0] if cert_fps else ""
        if not fingerprint:
            return

        tls_version = entry.get("version", "")
        cipher = entry.get("cipher", "")
        server_name = entry.get("server_name", "")

        await self._cert_tracker.update_tls_metadata(
            fingerprint=fingerprint,
            tls_version=tls_version or None,
            cipher_suite=cipher or None,
            server_name=server_name or None,
        )

    @staticmethod
    def _parse_zeek_ts(val: object) -> datetime | None:
        """Parse a Zeek timestamp (epoch float) into datetime."""
        if val is None:
            return None
        try:
            return datetime.fromtimestamp(float(val), tz=UTC)
        except (ValueError, TypeError, OSError):
            return None
