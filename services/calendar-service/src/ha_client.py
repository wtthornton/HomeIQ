"""
Home Assistant REST API Client for Calendar Integration
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)


class HomeAssistantCalendarClient:
    """Client for Home Assistant Calendar REST API"""

    def __init__(self, base_url: str, token: str, timeout: int = 10):
        """
        Initialize Home Assistant Calendar Client

        Args:
            base_url: Home Assistant base URL (e.g., http://homeassistant.local:8123)
            token: Long-lived access token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Initialize HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=self.timeout,
            )
            logger.info("Home Assistant client session created")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Home Assistant client session closed")

    async def test_connection(self) -> bool:
        """
        Test connection to Home Assistant

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with self.session.get(f"{self.base_url}/api/") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Connected to Home Assistant: {data.get('message', 'OK')}")
                    return True
                logger.error(f"HA connection failed: HTTP {response.status}")
                return False
        except Exception as e:
            logger.exception(f"HA connection test failed: {e}")
            return False

    async def get_calendars(self) -> list[str]:
        """
        Get list of available calendar entities

        Returns:
            List of calendar entity IDs (e.g., ['calendar.primary', 'calendar.work'])
        """
        try:
            async with self.session.get(f"{self.base_url}/api/states") as response:
                if response.status != 200:
                    logger.error(f"Failed to get states: HTTP {response.status}")
                    return []

                states = await response.json()

                # Filter for calendar entities
                calendars = [
                    state["entity_id"]
                    for state in states
                    if state["entity_id"].startswith("calendar.")
                ]

                logger.info(f"Found {len(calendars)} calendar entities: {calendars}")
                return calendars

        except ClientError as e:
            logger.exception(f"Network error getting calendars: {e}")
            return []
        except Exception as e:
            logger.exception(f"Error getting calendars: {e}")
            return []

    async def get_events(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """
        Get calendar events within time range

        Args:
            calendar_id: Calendar entity ID (with or without 'calendar.' prefix)
            start: Start datetime (timezone-aware)
            end: End datetime (timezone-aware)

        Returns:
            List of calendar events with structure:
            [
                {
                    "summary": "Event title",
                    "start": {"dateTime": "2025-10-16T14:00:00-07:00"} or {"date": "2025-10-16"},
                    "end": {"dateTime": "2025-10-16T15:00:00-07:00"} or {"date": "2025-10-17"},
                    "description": "Event description",
                    "location": "Event location"
                }
            ]
        """
        # Ensure calendar_id doesn't have 'calendar.' prefix for API call
        if calendar_id.startswith("calendar."):
            calendar_id = calendar_id[9:]  # Remove 'calendar.' prefix

        # Format timestamps for HA API
        start_str = start.isoformat()
        end_str = end.isoformat()

        url = f"{self.base_url}/api/calendars/calendar.{calendar_id}"
        params = {
            "start": start_str,
            "end": end_str,
        }

        try:
            logger.debug(f"Fetching events for calendar.{calendar_id} from {start_str} to {end_str}")

            async with self.session.get(url, params=params) as response:
                if response.status == 404:
                    logger.warning(f"Calendar not found: calendar.{calendar_id}")
                    return []

                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Failed to get events: HTTP {response.status}, {text}")
                    return []

                events = await response.json()
                logger.info(f"Retrieved {len(events)} events from calendar.{calendar_id}")
                return events

        except ClientError as e:
            logger.exception(f"Network error getting events from calendar.{calendar_id}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Error getting events from calendar.{calendar_id}: {e}")
            return []

    async def get_calendar_state(self, calendar_id: str) -> dict[str, Any] | None:
        """
        Get current calendar entity state

        Args:
            calendar_id: Calendar entity ID (with or without 'calendar.' prefix)

        Returns:
            Calendar state dict with current event info, or None if not found
            {
                "entity_id": "calendar.primary",
                "state": "on" or "off",
                "attributes": {
                    "message": "Current event summary",
                    "all_day": false,
                    "start_time": "2025-10-16 14:00:00",
                    "end_time": "2025-10-16 15:00:00",
                    "location": "Conference Room",
                    "description": "Event description"
                }
            }
        """
        # Ensure calendar_id has 'calendar.' prefix for state API
        if not calendar_id.startswith("calendar."):
            calendar_id = f"calendar.{calendar_id}"

        url = f"{self.base_url}/api/states/{calendar_id}"

        try:
            async with self.session.get(url) as response:
                if response.status == 404:
                    logger.warning(f"Calendar state not found: {calendar_id}")
                    return None

                if response.status != 200:
                    logger.error(f"Failed to get calendar state: HTTP {response.status}")
                    return None

                state = await response.json()
                logger.debug(f"Retrieved state for {calendar_id}: {state.get('state')}")
                return state

        except ClientError as e:
            logger.exception(f"Network error getting calendar state {calendar_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Error getting calendar state {calendar_id}: {e}")
            return None

    async def get_events_from_multiple_calendars(
        self,
        calendar_ids: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get events from multiple calendars concurrently

        Args:
            calendar_ids: List of calendar entity IDs
            start: Start datetime
            end: End datetime

        Returns:
            Dict mapping calendar_id to list of events
            {
                "calendar.primary": [...events...],
                "calendar.work": [...events...]
            }
        """
        tasks = [
            self.get_events(calendar_id, start, end)
            for calendar_id in calendar_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        events_by_calendar = {}
        for calendar_id, result in zip(calendar_ids, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Error fetching events from {calendar_id}: {result}")
                events_by_calendar[calendar_id] = []
            else:
                events_by_calendar[calendar_id] = result

        total_events = sum(len(events) for events in events_by_calendar.values())
        logger.info(f"Retrieved {total_events} total events from {len(calendar_ids)} calendars")

        return events_by_calendar

