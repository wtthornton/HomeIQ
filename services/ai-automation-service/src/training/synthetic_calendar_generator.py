"""
Synthetic Calendar Generator

Generate realistic calendar events for synthetic homes based on work schedules and routines.
NUC-optimized: Uses in-memory dictionaries, no external API calls.

2025 Best Practices:
- Python 3.11+ type hints
- Pydantic models for data validation
- Structured logging
- Memory-efficient (<50MB per generator instance)
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CalendarEvent(BaseModel):
    """Pydantic model for calendar event data point (2025 best practice)."""
    
    timestamp: str
    event_type: str  # work, routine, travel
    summary: str
    location: str | None = None
    presence_state: str  # home, away, work


class SyntheticCalendarGenerator:
    """
    Generate realistic calendar events for synthetic homes.
    
    NUC-Optimized: Uses in-memory dictionaries, no external API calls.
    Performance target: <100ms per home for basic generation.
    """
    
    # Work schedule profiles
    WORK_SCHEDULES: dict[str, dict[str, Any]] = {
        'standard_9to5': {
            'start': 9,  # 9 AM
            'end': 17,   # 5 PM
            'location': 'office',
            'days': [0, 1, 2, 3, 4]  # Monday-Friday
        },
        'shift_work': {
            'start': 22,  # 10 PM
            'end': 6,     # 6 AM (next day)
            'location': 'work',
            'days': [0, 1, 2, 3, 4]  # Monday-Friday
        },
        'remote': {
            'start': 9,   # 9 AM
            'end': 17,    # 5 PM
            'location': 'home',
            'days': [0, 1, 2, 3, 4]  # Monday-Friday
        }
    }
    
    def __init__(self):
        """Initialize calendar generator (NUC-optimized, no heavy initialization)."""
        logger.debug("SyntheticCalendarGenerator initialized")
    
    def _get_work_schedule(
        self,
        home: dict[str, Any]
    ) -> str:
        """
        Determine work schedule from home metadata.
        
        Args:
            home: Home dictionary with metadata
        
        Returns:
            Work schedule identifier (standard_9to5, shift_work, remote)
        """
        # Try to get from home metadata
        if home.get('metadata', {}).get('work_schedule'):
            schedule = home['metadata']['work_schedule'].lower()
            if schedule in self.WORK_SCHEDULES:
                return schedule
        
        # Default to standard 9-5
        return 'standard_9to5'
    
    def generate_calendar(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """
        Generate calendar events for a synthetic home.
        
        Generates daily calendar events for the specified number of days.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date/time for calendar data
            days: Number of days to generate
        
        Returns:
            List of calendar event dictionaries (compatible with CalendarEvent model)
        """
        work_schedule = self._get_work_schedule(home)
        logger.debug(f"Generating calendar events for schedule: {work_schedule}")
        
        calendar_events = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day in range(days):
            # Generate basic work events (will be enhanced in later stories)
            timestamp = current_date + timedelta(days=day)
            
            # For now, create a simple work event placeholder
            # Will be enhanced in Story 34.6
            work_event = {
                'timestamp': timestamp.isoformat(),
                'event_type': 'work',
                'summary': 'Work',
                'location': self.WORK_SCHEDULES[work_schedule]['location'],
                'presence_state': 'work' if work_schedule != 'remote' else 'home'
            }
            
            calendar_events.append(work_event)
        
        logger.debug(f"Generated {len(calendar_events)} calendar events")
        return calendar_events
    
    def _generate_work_schedule_events(
        self,
        work_schedule: str,
        current_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """
        Generate work schedule events (Story 34.6).
        
        Includes:
        - Standard 9-5 work events
        - Shift work patterns (night shifts)
        - Remote work patterns
        - Commute events
        """
        events = []
        schedule_config = self.WORK_SCHEDULES[work_schedule]
        
        for day_offset in range(days):
            date = current_date + timedelta(days=day_offset)
            day_of_week = date.weekday()  # 0=Monday, 6=Sunday
            
            # Check if this is a work day
            if day_of_week not in schedule_config['days']:
                continue
            
            start_hour = schedule_config['start']
            end_hour = schedule_config['end']
            location = schedule_config['location']
            
            # Handle shift work (overnight)
            if work_schedule == 'shift_work' and start_hour > end_hour:
                # Night shift: starts at 22:00, ends at 06:00 next day
                work_start = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                work_end = date + timedelta(days=1)
                work_end = work_end.replace(hour=end_hour, minute=0, second=0, microsecond=0)
                
                # Commute to work (before shift)
                commute_to = work_start - timedelta(minutes=30)
                events.append({
                    'timestamp': commute_to.isoformat(),
                    'event_type': 'commute',
                    'summary': 'Commute to Work',
                    'location': 'work',
                    'presence_state': 'away'
                })
                
                # Work event
                events.append({
                    'timestamp': work_start.isoformat(),
                    'event_type': 'work',
                    'summary': 'Work (Shift)',
                    'location': location,
                    'presence_state': 'work'
                })
                
                # Work end / commute home
                events.append({
                    'timestamp': work_end.isoformat(),
                    'event_type': 'commute',
                    'summary': 'Commute Home',
                    'location': 'home',
                    'presence_state': 'away'
                })
            else:
                # Standard work day (9-5 or remote)
                work_start = date.replace(hour=start_hour, minute=random.randint(0, 15), second=0, microsecond=0)
                work_end = date.replace(hour=end_hour, minute=random.randint(0, 30), second=0, microsecond=0)
                
                # Commute events (only for non-remote)
                if location != 'home':
                    commute_to = work_start - timedelta(minutes=random.randint(20, 45))
                    events.append({
                        'timestamp': commute_to.isoformat(),
                        'event_type': 'commute',
                        'summary': 'Commute to Work',
                        'location': 'work',
                        'presence_state': 'away'
                    })
                    
                    commute_home = work_end + timedelta(minutes=random.randint(20, 45))
                    events.append({
                        'timestamp': commute_home.isoformat(),
                        'event_type': 'commute',
                        'summary': 'Commute Home',
                        'location': 'home',
                        'presence_state': 'away'
                    })
                
                # Work event
                events.append({
                    'timestamp': work_start.isoformat(),
                    'event_type': 'work',
                    'summary': 'Work',
                    'location': location,
                    'presence_state': 'work' if location != 'home' else 'home'
                })
                
                # Work end event
                events.append({
                    'timestamp': work_end.isoformat(),
                    'event_type': 'work',
                    'summary': 'Work End',
                    'location': location,
                    'presence_state': 'work' if location != 'home' else 'home'
                })
        
        return events
    
    def _generate_routine_events(
        self,
        current_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """
        Generate routine events (Story 34.7).
        
        Includes:
        - Daily routines (morning, evening)
        - Weekly routines (grocery, gym)
        - Occasional travel events
        """
        events = []
        
        for day_offset in range(days):
            date = current_date + timedelta(days=day_offset)
            day_of_week = date.weekday()
            
            # Morning routine (7-8 AM)
            morning_time = date.replace(hour=random.randint(7, 8), minute=random.randint(0, 30))
            events.append({
                'timestamp': morning_time.isoformat(),
                'event_type': 'routine',
                'summary': 'Morning Routine',
                'location': 'home',
                'presence_state': 'home'
            })
            
            # Evening routine (7-9 PM)
            evening_time = date.replace(hour=random.randint(19, 21), minute=random.randint(0, 30))
            events.append({
                'timestamp': evening_time.isoformat(),
                'event_type': 'routine',
                'summary': 'Evening Routine',
                'location': 'home',
                'presence_state': 'home'
            })
            
            # Weekly routines
            if day_of_week == 0:  # Monday - Grocery shopping
                grocery_time = date.replace(hour=random.randint(14, 16), minute=random.randint(0, 30))
                events.append({
                    'timestamp': grocery_time.isoformat(),
                    'event_type': 'routine',
                    'summary': 'Grocery Shopping',
                    'location': 'store',
                    'presence_state': 'away'
                })
            
            if day_of_week in [2, 4]:  # Wednesday or Friday - Gym
                gym_time = date.replace(hour=random.randint(18, 20), minute=random.randint(0, 30))
                events.append({
                    'timestamp': gym_time.isoformat(),
                    'event_type': 'routine',
                    'summary': 'Gym',
                    'location': 'gym',
                    'presence_state': 'away'
                })
        
        # Occasional travel (10% chance per week)
        if random.random() < 0.1:
            travel_day = random.randint(0, min(days - 1, 6))
            travel_date = current_date + timedelta(days=travel_day)
            travel_start = travel_date.replace(hour=random.randint(10, 14))
            
            events.append({
                'timestamp': travel_start.isoformat(),
                'event_type': 'travel',
                'summary': 'Travel',
                'location': 'away',
                'presence_state': 'away'
            })
            
            # Return from travel (1-3 days later)
            return_day = travel_day + random.randint(1, 3)
            if return_day < days:
                return_date = current_date + timedelta(days=return_day)
                return_time = return_date.replace(hour=random.randint(14, 18))
                
                events.append({
                    'timestamp': return_time.isoformat(),
                    'event_type': 'travel',
                    'summary': 'Return from Travel',
                    'location': 'home',
                    'presence_state': 'home'
                })
        
        return events
    
    def generate_calendar(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """
        Generate calendar events for a synthetic home (Enhanced with Stories 34.6-34.7).
        
        Generates:
        - Work schedule events (9-5, shift, remote)
        - Commute events
        - Routine events (daily, weekly)
        - Travel events
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date/time for calendar data
            days: Number of days to generate
        
        Returns:
            List of calendar event dictionaries (compatible with CalendarEvent model)
        """
        work_schedule = self._get_work_schedule(home)
        logger.debug(f"Generating calendar events for schedule: {work_schedule}")
        
        calendar_events = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Generate work schedule events (Story 34.6)
        work_events = self._generate_work_schedule_events(work_schedule, current_date, days)
        calendar_events.extend(work_events)
        
        # Generate routine events (Story 34.7)
        routine_events = self._generate_routine_events(current_date, days)
        calendar_events.extend(routine_events)
        
        # Sort by timestamp
        calendar_events.sort(key=lambda e: e.get('timestamp', ''))
        
        logger.debug(f"Generated {len(calendar_events)} calendar events")
        return calendar_events
    
    def calculate_presence_patterns(
        self,
        calendar_events: list[dict[str, Any]],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """
        Calculate presence patterns from calendar events (Story 34.8).
        
        Creates presence states (home, away, work) based on calendar events.
        Adds presence transitions for realistic state changes.
        
        Args:
            calendar_events: List of calendar events
            start_date: Start date for presence calculation
            days: Number of days
        
        Returns:
            List of presence state dictionaries
        """
        presence_states = []
        
        # Default to home state
        current_state = 'home'
        
        # Create hourly presence states
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Build event map by hour
        events_by_hour: dict[str, dict[str, Any]] = {}
        for event in calendar_events:
            event_dt = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            hour_key = event_dt.strftime('%Y-%m-%d-%H')
            events_by_hour[hour_key] = event
        
        for day_offset in range(days):
            date = current_date + timedelta(days=day_offset)
            
            for hour in range(24):
                hour_dt = date.replace(hour=hour)
                hour_key = hour_dt.strftime('%Y-%m-%d-%H')
                
                # Check if there's a calendar event at this hour
                if hour_key in events_by_hour:
                    event = events_by_hour[hour_key]
                    current_state = event.get('presence_state', current_state)
                
                # Add presence state
                presence_states.append({
                    'timestamp': hour_dt.isoformat(),
                    'presence_state': current_state,
                    'transition': hour_key in events_by_hour
                })
        
        logger.debug(f"Calculated {len(presence_states)} presence states")
        return presence_states
    
    def correlate_with_devices(
        self,
        calendar_events: list[dict[str, Any]],
        presence_states: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Correlate calendar/presence with device events (Story 34.9).
        
        Rules:
        - Away → security devices turn on
        - Home → comfort devices adjust
        - Work → away from home devices
        
        Args:
            calendar_events: List of calendar events
            presence_states: List of presence states
            device_events: List of existing device events
            devices: Optional list of devices
        
        Returns:
            List of correlated/adjusted device events
        """
        correlated_events = []
        
        # Find security devices
        security_devices = []
        comfort_devices = []
        
        if devices:
            for device in devices:
                device_type = device.get('device_type', '')
                device_class = device.get('device_class', '')
                
                # Security devices
                if device_type in ('alarm_control_panel', 'lock', 'binary_sensor'):
                    if device_class in ('motion', 'door', 'window') or device_type == 'lock':
                        security_devices.append(device)
                
                # Comfort devices (HVAC, lights)
                if device_type in ('climate', 'light', 'fan'):
                    comfort_devices.append(device)
        
        # Create presence map
        presence_by_timestamp = {
            p['timestamp']: p['presence_state']
            for p in presence_states
        }
        
        # Track device states
        device_states: dict[str, str] = {}
        
        # Group device events by entity
        events_by_entity: dict[str, list[dict[str, Any]]] = {}
        for event in device_events:
            entity_id = event.get('entity_id', '')
            if entity_id not in events_by_entity:
                events_by_entity[entity_id] = []
            events_by_entity[entity_id].append(event)
        
        # Correlate based on presence changes
        for presence_state in presence_states:
            if not presence_state.get('transition'):
                continue
            
            timestamp = presence_state['timestamp']
            presence = presence_state['presence_state']
            
            # Away → security on
            if presence == 'away':
                for device in security_devices:
                    entity_id = device.get('entity_id')
                    if entity_id and entity_id not in device_states:
                        correlated_events.append({
                            'entity_id': entity_id,
                            'timestamp': timestamp,
                            'state': 'on' if device.get('device_type') != 'lock' else 'locked',
                            'event_type': 'state_changed',
                            'calendar_correlated': True
                        })
                        device_states[entity_id] = 'on'
            
            # Home → comfort devices
            elif presence == 'home':
                for device in comfort_devices:
                    entity_id = device.get('entity_id')
                    if entity_id:
                        # Lights on, HVAC adjust
                        if device.get('device_type') == 'light':
                            correlated_events.append({
                                'entity_id': entity_id,
                                'timestamp': timestamp,
                                'state': 'on',
                                'event_type': 'state_changed',
                                'calendar_correlated': True
                            })
        
        # Add original events that weren't correlated
        correlated_entity_timestamps = {
            (e.get('entity_id'), e.get('timestamp'))
            for e in correlated_events
        }
        
        for event in device_events:
            key = (event.get('entity_id'), event.get('timestamp'))
            if key not in correlated_entity_timestamps:
                correlated_events.append(event)
        
        # Sort by timestamp
        correlated_events.sort(key=lambda e: e.get('timestamp', ''))
        
        logger.debug(f"Correlated {len(correlated_events)} device events with calendar/presence")
        return correlated_events

