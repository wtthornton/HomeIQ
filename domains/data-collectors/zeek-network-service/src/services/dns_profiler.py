"""DNS behavior profiler — builds per-device DNS query profiles in PostgreSQL.

Categorizes domains by suffix matching (cloud_api, ntp, update_check,
ad_tracker, social_media, unknown). Maintains rolling 7-day query counts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import asyncpg
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-dns-profiler")

# Domain suffix → category mapping
_DOMAIN_CATEGORIES: dict[str, str] = {
    # Cloud / API
    "amazonaws.com": "cloud_api",
    "azure.com": "cloud_api",
    "googleapis.com": "cloud_api",
    "cloudfront.net": "cloud_api",
    "akamaized.net": "cloud_api",
    "tuya.com": "cloud_api",
    "smartthings.com": "cloud_api",
    "hubitat.com": "cloud_api",
    "home-assistant.io": "cloud_api",
    "nabucasa.com": "cloud_api",
    # NTP
    "ntp.org": "ntp",
    "pool.ntp.org": "ntp",
    "time.google.com": "ntp",
    "time.windows.com": "ntp",
    "time.apple.com": "ntp",
    "time.cloudflare.com": "ntp",
    # Update checks
    "ubuntu.com": "update_check",
    "debian.org": "update_check",
    "raspbian.org": "update_check",
    "archlinux.org": "update_check",
    "pypi.org": "update_check",
    "npmjs.org": "update_check",
    "docker.io": "update_check",
    "ghcr.io": "update_check",
    "github.com": "update_check",
    # Ad trackers
    "doubleclick.net": "ad_tracker",
    "googlesyndication.com": "ad_tracker",
    "googleadservices.com": "ad_tracker",
    "facebook.net": "ad_tracker",
    "adnxs.com": "ad_tracker",
    "criteo.com": "ad_tracker",
    "advertising.com": "ad_tracker",
    "taboola.com": "ad_tracker",
    # Social media
    "facebook.com": "social_media",
    "twitter.com": "social_media",
    "instagram.com": "social_media",
    "tiktok.com": "social_media",
    "reddit.com": "social_media",
    "youtube.com": "social_media",
    "linkedin.com": "social_media",
}


def classify_domain(domain: str) -> tuple[str, str]:
    """Classify a domain into a category.

    Returns:
        Tuple of (domain_suffix, category).
    """
    domain_lower = domain.lower().rstrip(".")

    # Exact match first (e.g., "time.google.com")
    if domain_lower in _DOMAIN_CATEGORIES:
        return domain_lower, _DOMAIN_CATEGORIES[domain_lower]

    # Suffix matching — check progressively shorter suffixes
    parts = domain_lower.split(".")
    for i in range(len(parts)):
        suffix = ".".join(parts[i:])
        if suffix in _DOMAIN_CATEGORIES:
            return suffix, _DOMAIN_CATEGORIES[suffix]

    # Use the registrable domain (last 2 parts) as the suffix
    if len(parts) >= 2:
        return ".".join(parts[-2:]), "unknown"
    return domain_lower, "unknown"


class DnsProfiler:
    """Builds per-device DNS query profiles in PostgreSQL."""

    def __init__(self, dsn: str, schema: str = "devices") -> None:
        self._dsn = dsn
        self._schema = schema
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Create the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            logger.info("DnsProfiler connected to PostgreSQL")
        except Exception as e:
            logger.error("DnsProfiler failed to connect to PostgreSQL: %s", e)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def record_query(self, device_ip: str, domain: str) -> None:
        """Record a DNS query from a device, upserting the profile entry."""
        if not self._pool:
            return

        suffix, category = classify_domain(domain)
        table = f"{self._schema}.network_device_dns_profiles"
        now = datetime.now(UTC)

        await self._pool.execute(
            f"""
            INSERT INTO {table}
                (device_ip, domain_suffix, category, query_count_7d,
                 last_query_at, first_seen, last_updated)
            VALUES ($1, $2, $3, 1, $4, $4, $4)
            ON CONFLICT (device_ip, domain_suffix) DO UPDATE SET
                query_count_7d = {table}.query_count_7d + 1,
                last_query_at = EXCLUDED.last_query_at,
                last_updated = EXCLUDED.last_updated
            """,  # noqa: S608
            device_ip,
            suffix,
            category,
            now,
        )

    async def expire_old_counts(self) -> int:
        """Reset query counts older than 7 days. Returns rows affected."""
        if not self._pool:
            return 0

        table = f"{self._schema}.network_device_dns_profiles"
        result = await self._pool.execute(
            f"""
            DELETE FROM {table}
            WHERE last_query_at < NOW() - INTERVAL '7 days'
            """,  # noqa: S608
        )
        # asyncpg returns "DELETE N"
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def get_device_profile(self, device_ip: str) -> list[dict[str, Any]]:
        """Get DNS profile for a device — all domain categories with counts."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_device_dns_profiles"
        rows = await self._pool.fetch(
            f"""
            SELECT domain_suffix, category, query_count_7d, last_query_at
            FROM {table}
            WHERE device_ip = $1
            ORDER BY query_count_7d DESC
            """,  # noqa: S608
            device_ip,
        )
        return [dict(r) for r in rows]

    async def get_category_summary(self, device_ip: str) -> dict[str, int]:
        """Get DNS profile summary grouped by category."""
        if not self._pool:
            return {}

        table = f"{self._schema}.network_device_dns_profiles"
        rows = await self._pool.fetch(
            f"""
            SELECT category, SUM(query_count_7d)::int AS total_queries
            FROM {table}
            WHERE device_ip = $1
            GROUP BY category
            ORDER BY total_queries DESC
            """,  # noqa: S608
            device_ip,
        )
        return {r["category"]: r["total_queries"] for r in rows}

    async def get_all_profiles(self) -> list[dict[str, Any]]:
        """Get all device DNS profiles (summary per device)."""
        if not self._pool:
            return []

        table = f"{self._schema}.network_device_dns_profiles"
        rows = await self._pool.fetch(
            f"""
            SELECT device_ip,
                   COUNT(DISTINCT domain_suffix)::int AS unique_domains,
                   SUM(query_count_7d)::int AS total_queries_7d,
                   MAX(last_query_at) AS last_query_at
            FROM {table}
            GROUP BY device_ip
            ORDER BY total_queries_7d DESC
            """,  # noqa: S608
        )
        return [dict(r) for r in rows]
