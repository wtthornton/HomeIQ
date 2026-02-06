"""
Parse and enrich Home Assistant calendar events
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CalendarEventParser:
    """Parse and enrich calendar events from Home Assistant"""

    # Pre-compiled patterns for detecting work-from-home indicators
    WFH_PATTERNS = [
        re.compile(r'\bWFH\b', re.IGNORECASE),
        re.compile(r'\bWork From Home\b', re.IGNORECASE),
        re.compile(r'\bHome Office\b', re.IGNORECASE),
        re.compile(r'\bRemote Work\b', re.IGNORECASE),
        re.compile(r'\bWorking From Home\b', re.IGNORECASE),
    ]

    # Pre-compiled patterns for detecting home location indicators
    HOME_PATTERNS = [
        re.compile(r'\bHome\b', re.IGNORECASE),
        re.compile(r'\bHouse\b', re.IGNORECASE),
        re.compile(r'\bResidence\b', re.IGNORECASE),
        re.compile(r'\bApartment\b', re.IGNORECASE),
    ]

    # Pre-compiled patterns for detecting away/out indicators
    AWAY_PATTERNS = [
        re.compile(r'\bOffice\b', re.IGNORECASE),
        re.compile(r'\bWork\b', re.IGNORECASE),
        re.compile(r'\bTravel\b', re.IGNORECASE),
        re.compile(r'\bTrip\b', re.IGNORECASE),
        re.compile(r'\bVacation\b', re.IGNORECASE),
        re.compile(r'\bOut of Town\b', re.IGNORECASE),
        re.compile(r'\bBusiness\b', re.IGNORECASE),
    ]

    @staticmethod
    def parse_datetime(dt_value: Any) -> datetime | None:
        """
        Parse datetime from various formats
        
        Args:
            dt_value: Can be datetime object, ISO string, or dict with 'dateTime' or 'date'
        
        Returns:
            Parsed datetime object (timezone-aware) or None
        """
        if dt_value is None:
            return None

        # Already a datetime
        if isinstance(dt_value, datetime):
            # Ensure timezone-aware
            if dt_value.tzinfo is None:
                dt_value = dt_value.replace(tzinfo=timezone.utc)
            return dt_value

        # String format
        if isinstance(dt_value, str):
            try:
                dt_str = dt_value.replace('Z', '+00:00')
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError as e:
                logger.error(f"Failed to parse datetime string '{dt_value}': {e}")
                return None

        # Dict format (HA calendar format)
        if isinstance(dt_value, dict):
            # Timed event (has time component)
            if 'dateTime' in dt_value:
                return CalendarEventParser.parse_datetime(dt_value['dateTime'])

            # All-day event (date only)
            elif 'date' in dt_value:
                try:
                    date_str = dt_value['date']
                    dt = datetime.fromisoformat(date_str)
                    # Set to start/end of day
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError as e:
                    logger.error(f"Failed to parse date '{dt_value['date']}': {e}")
                    return None

        logger.warning(f"Unexpected datetime format: {type(dt_value)} - {dt_value}")
        return None

    @staticmethod
    def parse_ha_event(event: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Home Assistant calendar event to standardized format
        
        Args:
            event: Raw event from HA calendar API
            {
                "summary": "Event title",
                "start": {"dateTime": "..."} or {"date": "..."},
                "end": {"dateTime": "..."} or {"date": "..."},
                "description": "...",
                "location": "..."
            }
        
        Returns:
            Parsed event dict with structure:
            {
                "summary": str,
                "location": str,
                "description": str,
                "start": datetime,
                "end": datetime,
                "is_all_day": bool,
                "raw_event": dict  # Original event for reference
            }
        """
        # Extract basic fields
        summary = event.get('summary', 'Untitled Event')
        location = event.get('location', '')
        description = event.get('description', '')

        # Parse start and end times
        start_dt = CalendarEventParser.parse_datetime(event.get('start'))
        end_dt = CalendarEventParser.parse_datetime(event.get('end'))

        # Determine if all-day event
        # All-day events have 'date' key instead of 'dateTime'
        is_all_day = False
        if isinstance(event.get('start'), dict):
            is_all_day = 'date' in event['start'] and 'dateTime' not in event['start']

        parsed_event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': start_dt,
            'end': end_dt,
            'is_all_day': is_all_day,
            'raw_event': event
        }

        logger.debug(f"Parsed event: {summary} ({start_dt} - {end_dt})")

        return parsed_event

    @staticmethod
    def _matches_patterns(text: str, patterns: list[re.Pattern]) -> bool:
        """
        Check if text matches any of the pre-compiled regex patterns

        Args:
            text: Text to check
            patterns: List of pre-compiled regex patterns

        Returns:
            True if any pattern matches, False otherwise
        """
        if not text:
            return False

        for pattern in patterns:
            if pattern.search(text):
                return True

        return False

    @staticmethod
    def detect_occupancy_indicators(event: dict[str, Any]) -> dict[str, bool]:
        """
        Detect home/WFH/away indicators in event
        
        Args:
            event: Parsed event dict (from parse_ha_event)
        
        Returns:
            Dict with occupancy indicators:
            {
                "is_wfh": bool,        # Working from home
                "is_home": bool,       # Event at home
                "is_away": bool,       # Event away from home
                "confidence": float    # Confidence level (0.0-1.0)
            }
        """
        summary = event.get('summary', '')
        location = event.get('location', '')
        description = event.get('description', '')

        # Combine all text for pattern matching
        all_text = f"{summary} {location} {description}"

        # Check patterns
        is_wfh = CalendarEventParser._matches_patterns(all_text, CalendarEventParser.WFH_PATTERNS)
        is_home = CalendarEventParser._matches_patterns(all_text, CalendarEventParser.HOME_PATTERNS)
        is_away = CalendarEventParser._matches_patterns(all_text, CalendarEventParser.AWAY_PATTERNS)

        # Calculate confidence
        # Higher confidence if explicit indicators found
        confidence = 0.5  # Default medium confidence

        if is_wfh or is_home:
            confidence = 0.85  # High confidence for home indicators
        elif is_away:
            confidence = 0.75  # Good confidence for away indicators

        # Boost confidence if multiple indicators
        indicator_count = sum([is_wfh, is_home, is_away])
        if indicator_count > 1:
            confidence = min(confidence + 0.1, 0.95)

        indicators = {
            'is_wfh': is_wfh,
            'is_home': is_home or is_wfh,  # WFH implies home
            'is_away': is_away and not is_wfh and not is_home,  # Away only if not home
            'confidence': confidence
        }

        if is_wfh or is_home or is_away:
            logger.debug(f"Event '{summary}' indicators: {indicators}")

        return indicators

    @staticmethod
    def parse_and_enrich_event(event: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and enrich event with occupancy indicators in one call
        
        Args:
            event: Raw event from HA calendar API
        
        Returns:
            Fully parsed and enriched event dict
        """
        # Parse event
        parsed = CalendarEventParser.parse_ha_event(event)

        # Add occupancy indicators
        indicators = CalendarEventParser.detect_occupancy_indicators(parsed)
        parsed.update(indicators)

        return parsed

    @staticmethod
    def parse_multiple_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parse and enrich multiple events
        
        Args:
            events: List of raw events from HA calendar API
        
        Returns:
            List of parsed and enriched events
        """
        parsed_events = []

        for event in events:
            try:
                parsed = CalendarEventParser.parse_and_enrich_event(event)
                parsed_events.append(parsed)
            except Exception as e:
                logger.error(f"Failed to parse event {event.get('summary', 'unknown')}: {e}")
                continue

        logger.info(f"Parsed {len(parsed_events)} out of {len(events)} events")

        return parsed_events

    @staticmethod
    def filter_events_by_time(
        events: list[dict[str, Any]],
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Filter events by time range
        
        Args:
            events: List of parsed events
            start_time: Filter events starting after this time (inclusive)
            end_time: Filter events starting before this time (exclusive)
        
        Returns:
            Filtered list of events
        """
        filtered = events

        if start_time:
            filtered = [e for e in filtered if e.get('start') and e['start'] >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.get('start') and e['start'] < end_time]

        logger.debug(f"Filtered {len(events)} events to {len(filtered)} within time range")

        return filtered

    @staticmethod
    def get_current_events(events: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
        """
        Get events that are currently active
        
        Args:
            events: List of parsed events
            now: Current time (defaults to datetime.now(timezone.utc))
        
        Returns:
            List of events where start <= now < end
        """
        if now is None:
            now = datetime.now(timezone.utc)

        current = [
            event for event in events
            if event.get('start') and event.get('end')
            and event['start'] <= now < event['end']
        ]

        logger.debug(f"Found {len(current)} current events out of {len(events)}")

        return current

    @staticmethod
    def get_upcoming_events(
        events: list[dict[str, Any]],
        now: datetime | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get upcoming events (sorted by start time)
        
        Args:
            events: List of parsed events
            now: Current time (defaults to datetime.now(timezone.utc))
            limit: Maximum number of events to return
        
        Returns:
            List of upcoming events, sorted by start time
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Filter to future events
        upcoming = [
            event for event in events
            if event.get('start') and event['start'] > now
        ]

        # Sort by start time
        upcoming.sort(key=lambda e: e['start'])

        # Limit if specified
        if limit:
            upcoming = upcoming[:limit]

        logger.debug(f"Found {len(upcoming)} upcoming events out of {len(events)}")

        return upcoming

