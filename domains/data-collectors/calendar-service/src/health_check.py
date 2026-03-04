"""Health Check State Tracker for Calendar Service.

Tracks HA connection status, calendar discovery, and fetch statistics.
Used by the StandardHealthCheck registered checks.
"""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class HealthCheckState:
    """Tracks health state for calendar service dependency checks."""

    def __init__(self) -> None:
        self.start_time = datetime.now(UTC)
        self.last_successful_fetch: datetime | None = None
        self.total_fetches: int = 0
        self.failed_fetches: int = 0
        self.ha_connected: bool = False
        self.calendar_count: int = 0
        self.calendars_discovered: int = 0

    async def check_ha_connected(self) -> bool:
        """Check if Home Assistant connection is healthy."""
        return self.ha_connected

    async def check_calendars_discovered(self) -> bool:
        """Check if calendars have been discovered successfully."""
        return not (self.calendar_count > 0 and self.calendars_discovered == 0)

    async def check_recent_fetch(self) -> bool:
        """Check if a successful fetch occurred within the last 30 minutes."""
        if not self.last_successful_fetch:
            return True  # No fetch yet is OK during startup
        time_since_last = (datetime.now(UTC) - self.last_successful_fetch).total_seconds()
        return time_since_last <= 1800  # 30 minutes
