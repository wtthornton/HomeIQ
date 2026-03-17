"""Fingerprint service — manages network_device_fingerprints in PostgreSQL.

Provides upsert operations (MAC is primary key) and query methods for
the REST API. All database access goes through asyncpg for async I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import asyncpg
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-fingerprint-service")


class FingerprintService:
    """Manages device fingerprint records in PostgreSQL."""

    def __init__(self, dsn: str, schema: str = "devices") -> None:
        self._dsn = dsn
        self._schema = schema
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Create the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            logger.info("Fingerprint service connected to PostgreSQL")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL: %s", e)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def upsert_dhcp(
        self,
        mac_address: str,
        ip_address: str,
        hostname: str | None = None,
        vendor: str | None = None,
        dhcp_fingerprint: str | None = None,
        dhcp_vendor_class: str | None = None,
    ) -> None:
        """Insert or update a device from DHCP discovery.

        MAC is the primary key. On conflict, update IP, hostname, vendor,
        DHCP fields, increment times_seen, and refresh last_seen.
        """
        if not self._pool:
            return

        table = f"{self._schema}.network_device_fingerprints"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            INSERT INTO {table}
                (mac_address, ip_address, hostname, vendor,
                 dhcp_fingerprint, dhcp_vendor_class, first_seen, last_seen, times_seen)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7, 1)
            ON CONFLICT (mac_address) DO UPDATE SET
                ip_address = EXCLUDED.ip_address,
                hostname = COALESCE(EXCLUDED.hostname, {table}.hostname),
                vendor = COALESCE(EXCLUDED.vendor, {table}.vendor),
                dhcp_fingerprint = COALESCE(EXCLUDED.dhcp_fingerprint, {table}.dhcp_fingerprint),
                dhcp_vendor_class = COALESCE(EXCLUDED.dhcp_vendor_class, {table}.dhcp_vendor_class),
                last_seen = EXCLUDED.last_seen,
                times_seen = {table}.times_seen + 1,
                is_active = TRUE
            """,  # noqa: S608
            mac_address.upper(),
            ip_address,
            hostname,
            vendor,
            dhcp_fingerprint,
            dhcp_vendor_class,
            now,
        )

    async def update_tls_fingerprints(
        self,
        ip_address: str,
        ja3_hash: str | None = None,
        ja3s_hash: str | None = None,
        ja4_hash: str | None = None,
    ) -> None:
        """Update TLS fingerprints for a device identified by IP.

        Only updates fields that are non-None (COALESCE preserves existing).
        """
        if not self._pool:
            return

        table = f"{self._schema}.network_device_fingerprints"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            UPDATE {table} SET
                ja3_hash = COALESCE($2, ja3_hash),
                ja3s_hash = COALESCE($3, ja3s_hash),
                ja4_hash = COALESCE($4, ja4_hash),
                last_seen = $5
            WHERE ip_address = $1::inet
            """,  # noqa: S608
            ip_address,
            ja3_hash,
            ja3s_hash,
            ja4_hash,
            now,
        )

    async def update_ssh_fingerprints(
        self,
        ip_address: str,
        hassh_hash: str | None = None,
        hassh_server: str | None = None,
    ) -> None:
        """Update SSH fingerprints for a device identified by IP."""
        if not self._pool:
            return

        table = f"{self._schema}.network_device_fingerprints"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            UPDATE {table} SET
                hassh_hash = COALESCE($2, hassh_hash),
                hassh_server = COALESCE($3, hassh_server),
                last_seen = $4
            WHERE ip_address = $1::inet
            """,  # noqa: S608
            ip_address,
            hassh_hash,
            hassh_server,
            now,
        )

    async def update_software(
        self,
        ip_address: str,
        user_agent: str | None = None,
        server_software: str | None = None,
        os_guess: str | None = None,
    ) -> None:
        """Update software detection fields for a device identified by IP."""
        if not self._pool:
            return

        table = f"{self._schema}.network_device_fingerprints"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            UPDATE {table} SET
                user_agent = COALESCE($2, user_agent),
                server_software = COALESCE($3, server_software),
                os_guess = COALESCE($4, os_guess),
                last_seen = $5
            WHERE ip_address = $1::inet
            """,  # noqa: S608
            ip_address,
            user_agent,
            server_software,
            os_guess,
            now,
        )

    async def get_by_ip(self, ip_address: str) -> dict[str, Any] | None:
        """Get fingerprint record by IP address."""
        if not self._pool:
            return None

        table = f"{self._schema}.network_device_fingerprints"
        row = await self._pool.fetchrow(
            f"SELECT * FROM {table} WHERE ip_address = $1::inet",  # noqa: S608
            ip_address,
        )
        return dict(row) if row else None

    async def get_by_mac(self, mac_address: str) -> dict[str, Any] | None:
        """Get fingerprint record by MAC address."""
        if not self._pool:
            return None

        table = f"{self._schema}.network_device_fingerprints"
        row = await self._pool.fetchrow(
            f"SELECT * FROM {table} WHERE mac_address = $1",  # noqa: S608
            mac_address.upper(),
        )
        return dict(row) if row else None

    async def get_discovered(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get devices discovered within the last N hours."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_device_fingerprints"
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM {table}
            WHERE last_seen > NOW() - INTERVAL '{hours} hours'
            ORDER BY last_seen DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_new_devices(self) -> list[dict[str, Any]]:
        """Get devices not yet in the baseline (first_seen == last_seen or times_seen == 1)."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_device_fingerprints"
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM {table}
            WHERE times_seen = 1
            ORDER BY first_seen DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_all_active(self) -> list[dict[str, Any]]:
        """Get all active fingerprint records."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_device_fingerprints"
        rows = await self._pool.fetch(
            f"SELECT * FROM {table} WHERE is_active = TRUE ORDER BY last_seen DESC",  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def ip_to_mac(self, ip_address: str) -> str | None:
        """Resolve an IP address to a MAC address from known devices."""
        if not self._pool:
            return None

        table = f"{self._schema}.network_device_fingerprints"
        row = await self._pool.fetchrow(
            f"SELECT mac_address FROM {table} WHERE ip_address = $1::inet",  # noqa: S608
            ip_address,
        )
        return row["mac_address"] if row else None
