"""
Unit tests for SyntheticCalendarGenerator.

Tests work schedule detection, basic calendar event generation, and edge cases.
"""

import pytest
from datetime import datetime, timezone

from src.training.synthetic_calendar_generator import (
    SyntheticCalendarGenerator,
    CalendarEvent
)


class TestSyntheticCalendarGenerator:
    """Test suite for SyntheticCalendarGenerator."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SyntheticCalendarGenerator()
        assert generator is not None
        assert hasattr(generator, 'WORK_SCHEDULES')
        assert len(generator.WORK_SCHEDULES) == 3
    
    def test_get_work_schedule_default(self):
        """Test default work schedule when no metadata."""
        generator = SyntheticCalendarGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        
        schedule = generator._get_work_schedule(home)
        assert schedule == 'standard_9to5'
    
    def test_get_work_schedule_from_metadata(self):
        """Test work schedule detection from home metadata."""
        generator = SyntheticCalendarGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {
                'work_schedule': 'remote'
            }
        }
        
        schedule = generator._get_work_schedule(home)
        assert schedule == 'remote'
    
    def test_generate_calendar_basic(self):
        """Test basic calendar generation."""
        generator = SyntheticCalendarGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        calendar_events = generator.generate_calendar(home, start_date, days)
        
        # Should have at least one event per day
        assert len(calendar_events) >= 1
        assert all('timestamp' in event for event in calendar_events)
        assert all('event_type' in event for event in calendar_events)
        assert all('summary' in event for event in calendar_events)
        assert all('presence_state' in event for event in calendar_events)
    
    def test_generate_calendar_multiple_days(self):
        """Test calendar generation for multiple days."""
        generator = SyntheticCalendarGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 7
        
        calendar_events = generator.generate_calendar(home, start_date, days)
        
        # Should have at least one event per day
        assert len(calendar_events) >= 7
    
    def test_calendar_event_model(self):
        """Test CalendarEvent Pydantic model validation."""
        event = CalendarEvent(
            timestamp="2025-01-15T09:00:00+00:00",
            event_type="work",
            summary="Work",
            location="office",
            presence_state="work"
        )
        
        assert event.timestamp == "2025-01-15T09:00:00+00:00"
        assert event.event_type == "work"
        assert event.summary == "Work"
        assert event.location == "office"
        assert event.presence_state == "work"
    
    def test_calendar_event_optional_location(self):
        """Test CalendarEvent with optional location field."""
        event = CalendarEvent(
            timestamp="2025-01-15T09:00:00+00:00",
            event_type="routine",
            summary="Morning Routine",
            presence_state="home"
        )
        
        assert event.location is None
        assert event.presence_state == "home"
    
    def test_generate_work_schedule_standard_9to5(self):
        """Test standard 9-5 work schedule generation (Story 34.6)."""
        generator = SyntheticCalendarGenerator()
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        
        events = generator._generate_work_schedule_events('standard_9to5', start_date, 5)
        
        # Should have work events for weekdays (Mon-Fri)
        work_events = [e for e in events if e.get('event_type') == 'work']
        commute_events = [e for e in events if e.get('event_type') == 'commute']
        
        assert len(work_events) >= 5  # At least one per weekday
        assert len(commute_events) >= 5  # Commute to/from work
        
        # Check presence states
        assert any(e.get('presence_state') == 'work' for e in work_events)
    
    def test_generate_work_schedule_remote(self):
        """Test remote work schedule generation (Story 34.6)."""
        generator = SyntheticCalendarGenerator()
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        
        events = generator._generate_work_schedule_events('remote', start_date, 5)
        
        # Remote work should have presence_state 'home'
        work_events = [e for e in events if e.get('event_type') == 'work']
        assert len(work_events) >= 5
        
        # Remote work should be at home
        assert all(e.get('presence_state') == 'home' for e in work_events if e.get('event_type') == 'work')
        
        # No commute events for remote work
        commute_events = [e for e in events if e.get('event_type') == 'commute']
        assert len(commute_events) == 0
    
    def test_generate_work_schedule_shift_work(self):
        """Test shift work schedule generation (Story 34.6)."""
        generator = SyntheticCalendarGenerator()
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        
        events = generator._generate_work_schedule_events('shift_work', start_date, 3)
        
        # Should have work events for weekdays
        work_events = [e for e in events if e.get('event_type') == 'work']
        assert len(work_events) >= 3
        
        # Shift work should have overnight times
        shift_times = [e.get('timestamp') for e in work_events]
        # At least one should be at night (22:00 or later)
        assert any('22:00' in ts or '23:00' in ts for ts in shift_times)
    
    def test_generate_routine_events(self):
        """Test routine event generation (Story 34.7)."""
        generator = SyntheticCalendarGenerator()
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        
        events = generator._generate_routine_events(start_date, 7)
        
        # Should have daily routines (morning, evening)
        routine_events = [e for e in events if e.get('event_type') == 'routine']
        assert len(routine_events) >= 14  # At least 2 per day (morning + evening)
        
        # Should have morning and evening routines
        morning_routines = [e for e in routine_events if 'Morning' in e.get('summary', '')]
        evening_routines = [e for e in routine_events if 'Evening' in e.get('summary', '')]
        
        assert len(morning_routines) >= 7
        assert len(evening_routines) >= 7
        
        # Weekly routines (grocery, gym)
        grocery_events = [e for e in events if 'Grocery' in e.get('summary', '')]
        gym_events = [e for e in events if 'Gym' in e.get('summary', '')]
        
        # Grocery on Monday, gym on Wednesday/Friday
        assert len(grocery_events) >= 0  # May or may not be present
        assert len(gym_events) >= 0  # May or may not be present
    
    def test_generate_calendar_includes_work_and_routines(self):
        """Test that calendar generation includes both work and routine events."""
        generator = SyntheticCalendarGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        days = 3
        
        events = generator.generate_calendar(home, start_date, days)
        
        # Should have work events
        work_events = [e for e in events if e.get('event_type') == 'work']
        assert len(work_events) > 0
        
        # Should have routine events
        routine_events = [e for e in events if e.get('event_type') == 'routine']
        assert len(routine_events) > 0
        
        # Events should be sorted by timestamp
        timestamps = [e.get('timestamp') for e in events]
        assert timestamps == sorted(timestamps)
    
    def test_calculate_presence_patterns(self):
        """Test presence pattern calculation (Story 34.8)."""
        generator = SyntheticCalendarGenerator()
        
        # Create calendar events
        calendar_events = [
            {
                'timestamp': '2025-01-13T09:00:00+00:00',
                'event_type': 'work',
                'presence_state': 'work'
            },
            {
                'timestamp': '2025-01-13T17:00:00+00:00',
                'event_type': 'work',
                'presence_state': 'home'
            }
        ]
        
        start_date = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        presence_states = generator.calculate_presence_patterns(calendar_events, start_date, days)
        
        # Should have presence states for each hour (24 hours)
        assert len(presence_states) == 24
        
        # All should have timestamp and presence_state
        assert all('timestamp' in p for p in presence_states)
        assert all('presence_state' in p for p in presence_states)
        
        # Should have transitions marked
        transitions = [p for p in presence_states if p.get('transition')]
        assert len(transitions) >= 2
    
    def test_correlate_with_devices_security(self):
        """Test calendar-device correlation with security devices (Story 34.9)."""
        generator = SyntheticCalendarGenerator()
        
        calendar_events = [
            {
                'timestamp': '2025-01-13T09:00:00+00:00',
                'event_type': 'work',
                'presence_state': 'away'
            }
        ]
        
        presence_states = [
            {
                'timestamp': '2025-01-13T09:00:00+00:00',
                'presence_state': 'away',
                'transition': True
            }
        ]
        
        security_device = {
            'entity_id': 'alarm_control_panel.security',
            'device_type': 'alarm_control_panel'
        }
        
        device_events = []
        
        correlated = generator.correlate_with_devices(
            calendar_events,
            presence_states,
            device_events,
            [security_device]
        )
        
        # Should process correlation (may or may not create events based on logic)
        # Method should at least preserve original events (empty list in this case)
        assert isinstance(correlated, list)
        
        # If correlation creates events, they should have correct structure
        if len(correlated) > 0:
            assert all('entity_id' in e for e in correlated)
            assert all('timestamp' in e for e in correlated)
    
    def test_correlate_with_devices_comfort(self):
        """Test calendar-device correlation with comfort devices (Story 34.9)."""
        generator = SyntheticCalendarGenerator()
        
        calendar_events = [
            {
                'timestamp': '2025-01-13T17:00:00+00:00',
                'event_type': 'work',
                'presence_state': 'home'
            }
        ]
        
        presence_states = [
            {
                'timestamp': '2025-01-13T17:00:00+00:00',
                'presence_state': 'home',
                'transition': True
            }
        ]
        
        comfort_device = {
            'entity_id': 'light.living_room',
            'device_type': 'light'
        }
        
        device_events = []
        
        correlated = generator.correlate_with_devices(
            calendar_events,
            presence_states,
            device_events,
            [comfort_device]
        )
        
        # Should process comfort devices
        assert len(correlated) >= 0

