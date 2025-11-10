"""
Unit tests for Calendar Event Parser
"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from event_parser import CalendarEventParser


class TestParseDatetime:
    """Tests for parse_datetime method"""
    
    def test_parse_datetime_object(self):
        """Test parsing datetime object"""
        dt = datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc)
        result = CalendarEventParser.parse_datetime(dt)
        
        assert result == dt
        assert result.tzinfo is not None
    
    def test_parse_datetime_naive(self):
        """Test parsing naive datetime (adds UTC)"""
        dt = datetime(2025, 10, 16, 14, 0, 0)
        result = CalendarEventParser.parse_datetime(dt)
        
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 16
        assert result.tzinfo is not None
    
    def test_parse_iso_string_with_timezone(self):
        """Test parsing ISO string with timezone"""
        dt_str = "2025-10-16T14:00:00-07:00"
        result = CalendarEventParser.parse_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 16
        assert result.hour == 14
    
    def test_parse_iso_string_with_z(self):
        """Test parsing ISO string with Z suffix"""
        dt_str = "2025-10-16T14:00:00Z"
        result = CalendarEventParser.parse_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.tzinfo is not None
    
    def test_parse_dict_with_datetime(self):
        """Test parsing dict with dateTime key"""
        dt_dict = {"dateTime": "2025-10-16T14:00:00-07:00"}
        result = CalendarEventParser.parse_datetime(dt_dict)
        
        assert result is not None
        assert result.year == 2025
    
    def test_parse_dict_with_date(self):
        """Test parsing dict with date key (all-day)"""
        dt_dict = {"date": "2025-10-16"}
        result = CalendarEventParser.parse_datetime(dt_dict)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 16
    
    def test_parse_none(self):
        """Test parsing None"""
        result = CalendarEventParser.parse_datetime(None)
        assert result is None
    
    def test_parse_invalid_string(self):
        """Test parsing invalid string"""
        result = CalendarEventParser.parse_datetime("not a date")
        assert result is None


class TestParseHAEvent:
    """Tests for parse_ha_event method"""
    
    def test_parse_timed_event(self):
        """Test parsing timed event"""
        event = {
            "summary": "Team Meeting",
            "start": {"dateTime": "2025-10-16T14:00:00-07:00"},
            "end": {"dateTime": "2025-10-16T15:00:00-07:00"},
            "location": "Conference Room",
            "description": "Weekly sync"
        }
        
        result = CalendarEventParser.parse_ha_event(event)
        
        assert result["summary"] == "Team Meeting"
        assert result["location"] == "Conference Room"
        assert result["description"] == "Weekly sync"
        assert result["is_all_day"] is False
        assert result["start"] is not None
        assert result["end"] is not None
    
    def test_parse_all_day_event(self):
        """Test parsing all-day event"""
        event = {
            "summary": "Holiday",
            "start": {"date": "2025-10-16"},
            "end": {"date": "2025-10-17"}
        }
        
        result = CalendarEventParser.parse_ha_event(event)
        
        assert result["summary"] == "Holiday"
        assert result["is_all_day"] is True
        assert result["start"] is not None
        assert result["end"] is not None
    
    def test_parse_event_minimal(self):
        """Test parsing event with minimal fields"""
        event = {
            "start": {"dateTime": "2025-10-16T14:00:00Z"},
            "end": {"dateTime": "2025-10-16T15:00:00Z"}
        }
        
        result = CalendarEventParser.parse_ha_event(event)
        
        assert result["summary"] == "Untitled Event"
        assert result["location"] == ""
        assert result["description"] == ""
    
    def test_parse_event_preserves_raw(self):
        """Test that raw event is preserved"""
        event = {
            "summary": "Test",
            "start": {"dateTime": "2025-10-16T14:00:00Z"},
            "end": {"dateTime": "2025-10-16T15:00:00Z"}
        }
        
        result = CalendarEventParser.parse_ha_event(event)
        
        assert "raw_event" in result
        assert result["raw_event"] == event


class TestDetectOccupancyIndicators:
    """Tests for detect_occupancy_indicators method"""
    
    def test_detect_wfh_in_summary(self):
        """Test detecting WFH in summary"""
        event = {
            "summary": "WFH Day",
            "location": "",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_wfh"] is True
        assert indicators["is_home"] is True
        assert indicators["confidence"] >= 0.8
    
    def test_detect_work_from_home(self):
        """Test detecting 'Work From Home' phrase"""
        event = {
            "summary": "Work From Home",
            "location": "",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_wfh"] is True
        assert indicators["is_home"] is True
    
    def test_detect_home_in_location(self):
        """Test detecting home in location"""
        event = {
            "summary": "Meeting",
            "location": "Home Office",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_home"] is True
        assert indicators["confidence"] >= 0.8
    
    def test_detect_away_in_location(self):
        """Test detecting away location"""
        event = {
            "summary": "Client Meeting",
            "location": "Office Downtown",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_away"] is True
        assert indicators["is_home"] is False
    
    def test_detect_travel(self):
        """Test detecting travel"""
        event = {
            "summary": "Business Trip",
            "location": "",
            "description": "Travel to NYC"
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_away"] is True
    
    def test_no_indicators(self):
        """Test event with no clear indicators"""
        event = {
            "summary": "Dentist Appointment",
            "location": "123 Main St",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_wfh"] is False
        assert indicators["is_away"] is False
        # Medium confidence for ambiguous events
        assert 0.4 <= indicators["confidence"] <= 0.6
    
    def test_wfh_overrides_away(self):
        """Test that WFH overrides away indicators"""
        event = {
            "summary": "WFH - Office Meetings",
            "location": "Home",
            "description": ""
        }
        
        indicators = CalendarEventParser.detect_occupancy_indicators(event)
        
        assert indicators["is_wfh"] is True
        assert indicators["is_home"] is True
        assert indicators["is_away"] is False


class TestParseAndEnrichEvent:
    """Tests for parse_and_enrich_event method"""
    
    def test_parse_and_enrich(self):
        """Test complete parse and enrich"""
        event = {
            "summary": "WFH Day",
            "start": {"dateTime": "2025-10-16T09:00:00-07:00"},
            "end": {"dateTime": "2025-10-16T17:00:00-07:00"},
            "location": "Home"
        }
        
        result = CalendarEventParser.parse_and_enrich_event(event)
        
        assert result["summary"] == "WFH Day"
        assert result["is_wfh"] is True
        assert result["is_home"] is True
        assert result["confidence"] > 0.8


class TestParseMultipleEvents:
    """Tests for parse_multiple_events method"""
    
    def test_parse_multiple_events(self):
        """Test parsing multiple events"""
        events = [
            {
                "summary": "Meeting 1",
                "start": {"dateTime": "2025-10-16T09:00:00Z"},
                "end": {"dateTime": "2025-10-16T10:00:00Z"}
            },
            {
                "summary": "Meeting 2",
                "start": {"dateTime": "2025-10-16T14:00:00Z"},
                "end": {"dateTime": "2025-10-16T15:00:00Z"}
            }
        ]
        
        results = CalendarEventParser.parse_multiple_events(events)
        
        assert len(results) == 2
        assert results[0]["summary"] == "Meeting 1"
        assert results[1]["summary"] == "Meeting 2"
    
    def test_parse_multiple_events_with_error(self):
        """Test parsing multiple events with one invalid"""
        events = [
            {
                "summary": "Valid Event",
                "start": {"dateTime": "2025-10-16T09:00:00Z"},
                "end": {"dateTime": "2025-10-16T10:00:00Z"}
            },
            {
                "summary": "Invalid Event",
                "start": "not a valid format"
            }
        ]
        
        # Should skip invalid event and continue
        results = CalendarEventParser.parse_multiple_events(events)
        
        # Should still get the valid event
        assert len(results) >= 1
        assert results[0]["summary"] == "Valid Event"


class TestFilterEventsByTime:
    """Tests for filter_events_by_time method"""
    
    def test_filter_by_start_time(self):
        """Test filtering by start time"""
        now = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Past Event",
                "start": datetime(2025, 10, 16, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Future Event",
                "start": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        filtered = CalendarEventParser.filter_events_by_time(events, start_time=now)
        
        assert len(filtered) == 1
        assert filtered[0]["summary"] == "Future Event"
    
    def test_filter_by_end_time(self):
        """Test filtering by end time"""
        cutoff = datetime(2025, 10, 16, 13, 0, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Morning Event",
                "start": datetime(2025, 10, 16, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Afternoon Event",
                "start": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        filtered = CalendarEventParser.filter_events_by_time(events, end_time=cutoff)
        
        assert len(filtered) == 1
        assert filtered[0]["summary"] == "Morning Event"


class TestGetCurrentEvents:
    """Tests for get_current_events method"""
    
    def test_get_current_events(self):
        """Test getting currently active events"""
        now = datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Current Event",
                "start": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Past Event",
                "start": datetime(2025, 10, 16, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Future Event",
                "start": datetime(2025, 10, 16, 16, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        current = CalendarEventParser.get_current_events(events, now)
        
        assert len(current) == 1
        assert current[0]["summary"] == "Current Event"
    
    def test_get_current_events_none(self):
        """Test when no events are current"""
        now = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Future Event",
                "start": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        current = CalendarEventParser.get_current_events(events, now)
        
        assert len(current) == 0


class TestGetUpcomingEvents:
    """Tests for get_upcoming_events method"""
    
    def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        now = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Past Event",
                "start": datetime(2025, 10, 16, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "First Upcoming",
                "start": datetime(2025, 10, 16, 13, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Second Upcoming",
                "start": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 16, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        upcoming = CalendarEventParser.get_upcoming_events(events, now)
        
        assert len(upcoming) == 2
        assert upcoming[0]["summary"] == "First Upcoming"
        assert upcoming[1]["summary"] == "Second Upcoming"
    
    def test_get_upcoming_events_with_limit(self):
        """Test getting upcoming events with limit"""
        now = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        events = [
            {
                "summary": "Event 1",
                "start": datetime(2025, 10, 16, 13, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Event 2",
                "start": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Event 3",
                "start": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 16, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        upcoming = CalendarEventParser.get_upcoming_events(events, now, limit=2)
        
        assert len(upcoming) == 2
        assert upcoming[0]["summary"] == "Event 1"
        assert upcoming[1]["summary"] == "Event 2"
    
    def test_get_upcoming_events_sorted(self):
        """Test that upcoming events are sorted by start time"""
        now = datetime(2025, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        # Events in random order
        events = [
            {
                "summary": "Later Event",
                "start": datetime(2025, 10, 16, 15, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 16, 0, 0, tzinfo=timezone.utc)
            },
            {
                "summary": "Earlier Event",
                "start": datetime(2025, 10, 16, 13, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        upcoming = CalendarEventParser.get_upcoming_events(events, now)
        
        # Should be sorted
        assert upcoming[0]["summary"] == "Earlier Event"
        assert upcoming[1]["summary"] == "Later Event"

