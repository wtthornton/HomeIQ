"""TLS certificate tracker — manages network_tls_certificates in PostgreSQL.

Provides upsert operations keyed by certificate fingerprint and query
methods for the REST API. Detects expired certs and TLS < 1.2 negotiation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import asyncpg
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-cert-tracker")


class CertTracker:
    """Manages TLS certificate records in PostgreSQL."""

    def __init__(self, dsn: str, schema: str = "devices") -> None:
        self._dsn = dsn
        self._schema = schema
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Create the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            logger.info("CertTracker connected to PostgreSQL")
        except Exception as e:
            logger.error("CertTracker failed to connect to PostgreSQL: %s", e)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def upsert_certificate(
        self,
        fingerprint: str,
        subject: str | None = None,
        issuer: str | None = None,
        not_valid_before: datetime | None = None,
        not_valid_after: datetime | None = None,
        key_type: str | None = None,
        key_length: int | None = None,
        serial: str | None = None,
        self_signed: bool = False,
    ) -> None:
        """Insert or update a TLS certificate by fingerprint."""
        if not self._pool:
            return

        table = f"{self._schema}.network_tls_certificates"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            INSERT INTO {table}
                (fingerprint, subject, issuer, not_valid_before, not_valid_after,
                 key_type, key_length, serial, self_signed, first_seen, last_seen, times_seen)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10, 1)
            ON CONFLICT (fingerprint) DO UPDATE SET
                subject = COALESCE(EXCLUDED.subject, {table}.subject),
                issuer = COALESCE(EXCLUDED.issuer, {table}.issuer),
                not_valid_before = COALESCE(EXCLUDED.not_valid_before, {table}.not_valid_before),
                not_valid_after = COALESCE(EXCLUDED.not_valid_after, {table}.not_valid_after),
                key_type = COALESCE(EXCLUDED.key_type, {table}.key_type),
                key_length = COALESCE(EXCLUDED.key_length, {table}.key_length),
                serial = COALESCE(EXCLUDED.serial, {table}.serial),
                self_signed = EXCLUDED.self_signed,
                last_seen = EXCLUDED.last_seen,
                times_seen = {table}.times_seen + 1
            """,  # noqa: S608
            fingerprint,
            subject,
            issuer,
            not_valid_before,
            not_valid_after,
            key_type,
            key_length,
            serial,
            self_signed,
            now,
        )

    async def update_tls_metadata(
        self,
        fingerprint: str,
        tls_version: str | None = None,
        cipher_suite: str | None = None,
        server_name: str | None = None,
    ) -> None:
        """Update TLS negotiation metadata for a certificate."""
        if not self._pool:
            return

        table = f"{self._schema}.network_tls_certificates"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            UPDATE {table} SET
                tls_version = COALESCE($2, tls_version),
                cipher_suite = COALESCE($3, cipher_suite),
                server_name = COALESCE($4, server_name),
                last_seen = $5
            WHERE fingerprint = $1
            """,  # noqa: S608
            fingerprint,
            tls_version,
            cipher_suite,
            server_name,
            now,
        )

    async def get_all_certificates(self) -> list[dict[str, Any]]:
        """Get all tracked certificates with expiry status."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_tls_certificates"
        rows = await self._pool.fetch(
            f"""
            SELECT *,
                CASE
                    WHEN not_valid_after IS NOT NULL AND not_valid_after < NOW()
                    THEN TRUE ELSE FALSE
                END AS is_expired
            FROM {table}
            ORDER BY last_seen DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_expired_certificates(self) -> list[dict[str, Any]]:
        """Get certificates that have expired."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_tls_certificates"
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM {table}
            WHERE not_valid_after IS NOT NULL AND not_valid_after < NOW()
            ORDER BY not_valid_after ASC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_weak_tls(self) -> list[dict[str, Any]]:
        """Get certificates negotiated with TLS < 1.2."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_tls_certificates"
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM {table}
            WHERE tls_version IS NOT NULL
              AND tls_version NOT IN ('TLSv13', 'TLSv12', 'TLS 1.3', 'TLS 1.2')
            ORDER BY last_seen DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        """Get certificate by fingerprint."""
        if not self._pool:
            return None

        table = f"{self._schema}.network_tls_certificates"
        row = await self._pool.fetchrow(
            f"SELECT * FROM {table} WHERE fingerprint = $1",  # noqa: S608
            fingerprint,
        )
        return dict(row) if row else None
