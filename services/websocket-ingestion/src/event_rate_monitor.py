"""
Event Rate Monitor for tracking event capture rates
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventRateMonitor:
    """Monitors event capture rates and provides statistics"""

    def __init__(self, window_size_minutes: int = 60):
        self.window_size_minutes = window_size_minutes
        self.event_timestamps = deque(maxlen=window_size_minutes * 200)
        self.events_by_type = {}
        self.events_by_entity = {}
        self._max_entity_entries = 10000
        self.lock = asyncio.Lock()

        # Rate calculation windows
        self.minute_rates = deque(maxlen=60)  # Last 60 minutes
        self.hour_rates = deque(maxlen=24)    # Last 24 hours

        # Statistics
        self.total_events = 0
        self.start_time = datetime.now(timezone.utc)
        self.last_event_time: datetime = None

    async def record_event(self, event_data: dict[str, Any]):
        """
        Record an event for rate monitoring

        Args:
            event_data: The processed event data
        """
        try:
            async with self.lock:
                current_time = datetime.now(timezone.utc)

                # Record timestamp
                self.event_timestamps.append(current_time)
                self.total_events += 1
                self.last_event_time = current_time

                # Record by event type
                event_type = event_data.get("event_type", "unknown")
                self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1

                # Record by entity (for state_changed events)
                if event_type == "state_changed":
                    entity_id = event_data.get("entity_id")
                    if entity_id:
                        self.events_by_entity[entity_id] = self.events_by_entity.get(entity_id, 0) + 1

                        # PERF-002: Evict lowest-count entries if dict exceeds max size
                        if len(self.events_by_entity) > self._max_entity_entries:
                            # Remove the 10% lowest-count entries to avoid frequent evictions
                            sorted_entities = sorted(
                                self.events_by_entity.items(), key=lambda x: x[1]
                            )
                            entries_to_remove = len(self.events_by_entity) - self._max_entity_entries + (self._max_entity_entries // 10)
                            for key, _ in sorted_entities[:entries_to_remove]:
                                del self.events_by_entity[key]

                # Clean old timestamps
                self._clean_old_timestamps(current_time)

                # Calculate rates periodically
                self._calculate_rates(current_time)

        except Exception as e:
            logger.error(f"Error recording event: {e}")

    def _clean_old_timestamps(self, current_time: datetime):
        """Remove timestamps older than the window size"""
        cutoff_time = current_time - timedelta(minutes=self.window_size_minutes)

        while self.event_timestamps and self.event_timestamps[0] < cutoff_time:
            self.event_timestamps.popleft()

    def _calculate_rates(self, current_time: datetime):
        """Calculate event rates for different time windows"""
        try:
            # Calculate events per minute
            minute_ago = current_time - timedelta(minutes=1)
            events_last_minute = sum(1 for ts in self.event_timestamps if ts >= minute_ago)
            self.minute_rates.append(events_last_minute)

            # Calculate events per hour
            hour_ago = current_time - timedelta(hours=1)
            events_last_hour = sum(1 for ts in self.event_timestamps if ts >= hour_ago)
            self.hour_rates.append(events_last_hour)

        except Exception as e:
            logger.error(f"Error calculating rates: {e}")

    async def get_current_rate(self, window_minutes: int = 1) -> float:
        """
        Get current event rate

        Args:
            window_minutes: Time window in minutes

        Returns:
            Events per minute
        """
        try:
            async with self.lock:
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
                recent_events = sum(1 for ts in self.event_timestamps if ts >= cutoff_time)
                return recent_events / window_minutes
        except Exception as e:
            logger.error(f"Error calculating current rate: {e}")
            return 0.0

    async def get_average_rate(self, window_minutes: int = 60) -> float:
        """
        Get average event rate over specified window

        Args:
            window_minutes: Time window in minutes

        Returns:
            Average events per minute
        """
        try:
            async with self.lock:
                if window_minutes == 60 and self.minute_rates:
                    return sum(self.minute_rates) / len(self.minute_rates)
                elif window_minutes == 60 * 24 and self.hour_rates:
                    return sum(self.hour_rates) / len(self.hour_rates) / 60  # Convert to per minute
                else:
                    # Calculate for custom window
                    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
                    recent_events = sum(1 for ts in self.event_timestamps if ts >= cutoff_time)
                    return recent_events / window_minutes
        except Exception as e:
            logger.error(f"Error calculating average rate: {e}")
            return 0.0

    async def get_rate_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive rate statistics

        Returns:
            Dictionary with rate statistics
        """
        try:
            async with self.lock:
                current_time = datetime.now(timezone.utc)
                uptime = current_time - self.start_time

                # Calculate rates (call internal non-locking versions to avoid deadlock)
                cutoff_1min = current_time - timedelta(minutes=1)
                current_rate_1min = sum(1 for ts in self.event_timestamps if ts >= cutoff_1min) / 1
                cutoff_5min = current_time - timedelta(minutes=5)
                current_rate_5min = sum(1 for ts in self.event_timestamps if ts >= cutoff_5min) / 5
                cutoff_15min = current_time - timedelta(minutes=15)
                current_rate_15min = sum(1 for ts in self.event_timestamps if ts >= cutoff_15min) / 15
                average_rate_1hour = sum(self.minute_rates) / len(self.minute_rates) if self.minute_rates else 0.0
                average_rate_24hour = (sum(self.hour_rates) / len(self.hour_rates) / 60) if self.hour_rates else 0.0

                # Calculate overall rate
                overall_rate = self.total_events / (uptime.total_seconds() / 60) if uptime.total_seconds() > 0 else 0

                return {
                    "total_events": self.total_events,
                    "uptime_minutes": uptime.total_seconds() / 60,
                    "start_time": self.start_time.isoformat(),
                    "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
                    "current_rates": {
                        "events_per_minute_1min": round(current_rate_1min, 2),
                        "events_per_minute_5min": round(current_rate_5min, 2),
                        "events_per_minute_15min": round(current_rate_15min, 2)
                    },
                    "average_rates": {
                        "events_per_minute_1hour": round(average_rate_1hour, 2),
                        "events_per_minute_24hour": round(average_rate_24hour, 2),
                        "events_per_minute_overall": round(overall_rate, 2)
                    },
                    "events_by_type": self.events_by_type.copy(),
                    "top_entities": self._get_top_entities(10),
                    "rate_trends": {
                        "minute_rates": list(self.minute_rates),
                        "hour_rates": list(self.hour_rates)
                    }
                }
        except Exception as e:
            logger.error(f"Error getting rate statistics: {e}")
            return {}

    def _get_top_entities(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top entities by event count
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of dictionaries with entity information
        """
        try:
            sorted_entities = sorted(
                self.events_by_entity.items(),
                key=lambda x: x[1],
                reverse=True
            )

            return [
                {"entity_id": entity_id, "event_count": count}
                for entity_id, count in sorted_entities[:limit]
            ]
        except Exception as e:
            logger.error(f"Error getting top entities: {e}")
            return []

    async def get_rate_alerts(self) -> list[dict[str, Any]]:
        """
        Check for rate anomalies and generate alerts

        Returns:
            List of alert dictionaries
        """
        alerts = []

        try:
            current_rate = await self.get_current_rate(1)
            average_rate = await self.get_average_rate(60)

            # Alert if current rate is significantly different from average
            if average_rate > 0:
                rate_ratio = current_rate / average_rate

                if rate_ratio > 3.0:  # 3x higher than average
                    alerts.append({
                        "type": "high_rate",
                        "severity": "warning",
                        "message": f"Event rate is {rate_ratio:.1f}x higher than average",
                        "current_rate": current_rate,
                        "average_rate": average_rate,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                elif rate_ratio < 0.1:  # 10x lower than average
                    alerts.append({
                        "type": "low_rate",
                        "severity": "info",
                        "message": f"Event rate is {rate_ratio:.1f}x lower than average",
                        "current_rate": current_rate,
                        "average_rate": average_rate,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

            # Alert if no events received recently
            if self.last_event_time:
                time_since_last_event = datetime.now(timezone.utc) - self.last_event_time
                if time_since_last_event > timedelta(minutes=5):
                    alerts.append({
                        "type": "no_events",
                        "severity": "warning",
                        "message": f"No events received for {time_since_last_event.total_seconds() / 60:.1f} minutes",
                        "last_event_time": self.last_event_time.isoformat(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        except Exception as e:
            logger.error(f"Error generating rate alerts: {e}")

        return alerts

    async def reset_statistics(self):
        """Reset all statistics"""
        async with self.lock:
            self.event_timestamps.clear()
            self.events_by_type.clear()
            self.events_by_entity.clear()
            self.minute_rates.clear()
            self.hour_rates.clear()
            self.total_events = 0
            self.start_time = datetime.now(timezone.utc)
            self.last_event_time = None
            logger.info("Event rate statistics reset")
