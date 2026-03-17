"""Network baseline service — manages network_baseline_hosts in PostgreSQL.

Provides upsert for known hosts/services from Zeek logs, baseline
approval workflow, and queries for the REST API.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import asyncpg
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-baseline-service")


class BaselineService:
    """Manages network baseline host records in PostgreSQL."""

    def __init__(self, dsn: str, schema: str = "devices") -> None:
        self._dsn = dsn
        self._schema = schema
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Create the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            logger.info("BaselineService connected to PostgreSQL")
        except Exception as e:
            logger.error("BaselineService failed to connect to PostgreSQL: %s", e)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def upsert_host(
        self,
        ip_address: str,
        mac_address: str | None = None,
        hostname: str | None = None,
        services: list[dict] | None = None,
    ) -> None:
        """Insert or update a known host in the baseline table."""
        if not self._pool:
            return

        table = f"{self._schema}.network_baseline_hosts"
        now = datetime.now(UTC)
        services_json = json.dumps(services) if services else None

        await self._pool.execute(
            f"""
            INSERT INTO {table}
                (ip_address, mac_address, hostname, services, first_seen, last_seen, times_seen)
            VALUES ($1, $2, $3, $4::jsonb, $5, $5, 1)
            ON CONFLICT (ip_address) DO UPDATE SET
                mac_address = COALESCE(EXCLUDED.mac_address, {table}.mac_address),
                hostname = COALESCE(EXCLUDED.hostname, {table}.hostname),
                services = COALESCE(EXCLUDED.services, {table}.services),
                last_seen = EXCLUDED.last_seen,
                times_seen = {table}.times_seen + 1
            """,  # noqa: S608
            ip_address,
            mac_address,
            hostname,
            services_json,
            now,
        )

    async def approve(self, ip_address: str, approved_by: str = "admin") -> bool:
        """Approve a device into the baseline (suppress new_device alerts)."""
        if not self._pool:
            return False

        table = f"{self._schema}.network_baseline_hosts"
        now = datetime.now(UTC)

        result = await self._pool.execute(
            f"""
            UPDATE {table} SET
                is_baseline = TRUE,
                approved_by = $2,
                approved_at = $3
            WHERE ip_address = $1
            """,  # noqa: S608
            ip_address,
            approved_by,
            now,
        )
        return result != "UPDATE 0"

    async def is_known_host(self, ip_address: str) -> bool:
        """Check if an IP is in the baseline (approved)."""
        if not self._pool:
            return False

        table = f"{self._schema}.network_baseline_hosts"
        row = await self._pool.fetchrow(
            f"SELECT is_baseline FROM {table} WHERE ip_address = $1",  # noqa: S608
            ip_address,
        )
        return bool(row and row["is_baseline"])

    async def host_exists(self, ip_address: str) -> bool:
        """Check if an IP has been seen at all (baseline or not)."""
        if not self._pool:
            return False

        table = f"{self._schema}.network_baseline_hosts"
        row = await self._pool.fetchrow(
            f"SELECT 1 FROM {table} WHERE ip_address = $1",  # noqa: S608
            ip_address,
        )
        return row is not None

    async def get_host(self, ip_address: str) -> dict[str, Any] | None:
        """Get a single baseline host by IP."""
        if not self._pool:
            return None

        table = f"{self._schema}.network_baseline_hosts"
        row = await self._pool.fetchrow(
            f"SELECT * FROM {table} WHERE ip_address = $1",  # noqa: S608
            ip_address,
        )
        return dict(row) if row else None

    async def get_all_hosts(self) -> list[dict[str, Any]]:
        """Get all baseline hosts."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_baseline_hosts"
        rows = await self._pool.fetch(
            f"SELECT * FROM {table} ORDER BY last_seen DESC",  # noqa: S608
        )
        return [dict(r) for r in rows]

    async def get_unapproved_hosts(self) -> list[dict[str, Any]]:
        """Get hosts that have not been approved into the baseline."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_baseline_hosts"
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM {table}
            WHERE is_baseline = FALSE
            ORDER BY first_seen DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]
