"""
Synthetic Event Generator

Generate synthetic events for training home type classifier.
Uses device-type-specific frequencies from production analysis.

Epic 39, Story 39.2: Synthetic Data Generation Migration
Migrated from ai-automation-service.
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticEventGenerator:
    """
    Generate synthetic events for training.
    
    Uses device-type-specific frequencies (from production analysis):
    - Lights: 11 events/day
    - Binary sensors: 36 events/day
    - Sensors: 26 events/day
    - etc.
    """
    
    # Event frequencies per device type (events per day)
    EVENT_FREQUENCIES = {
        # VERY HIGH (>100/day in production)
        'image': 140,           # Cameras - continuous updates
        'sun': 106,             # Sun position - continuous
        
        # HIGH (20-100/day in production)
        'binary_sensor': 36,    # Motion, door sensors - frequent
        'sensor': 26,           # Temperature, light sensors - periodic
        'media_player': 28,     # Playback state changes
        
        # MEDIUM (5-20/day in production)
        'light': 11,           # On/off cycles
        'weather': 9,          # Periodic updates
        'vacuum': 8,           # Status updates
        'device_tracker': 5,   # Location updates
        'person': 5,           # Presence changes
        
        # LOW (<5/day in production) - with minimums
        'scene': 4,            # Manual activations
        'select': 3,           # Configuration changes
        'automation': 10,      # Trigger events (minimum for testing)
        'switch': 3,          # Manual toggles (minimum)
        'button': 2,          # Manual presses (minimum)
        'event': 2,           # System events (minimum)
        'remote': 2,          # Remote control (minimum)
        'zone': 2,            # Zone changes (minimum)
        'number': 2,          # Number inputs (minimum)
        'update': 2,          # Update checks (minimum)
        'climate': 3,         # Thermostat (minimum)
        'cover': 2,           # Blinds, garage (minimum)
        'lock': 2,            # Smart locks (minimum)
        'fan': 3,             # Fans (minimum)
        'alarm_control_panel': 2,  # Security alarms
        'camera': 5,          # Camera updates
    }
    
    # State values by device type
    DEVICE_STATES = {
        'light': ['on', 'off'],
        'binary_sensor': ['on', 'off'],
        'switch': ['on', 'off'],
        'sensor': lambda: str(random.randint(0, 100)),
        'climate': lambda: str(random.randint(65, 75)),
        'cover': ['open', 'closed', 'opening', 'closing'],
        'media_player': ['playing', 'paused', 'idle', 'off'],
        'vacuum': ['cleaning', 'docked', 'idle', 'returning'],
        'lock': ['locked', 'unlocked'],
        'fan': ['on', 'off'],
        'image': ['idle'],
        'sun': ['above_horizon', 'below_horizon'],
        'person': ['home', 'not_home'],
        'device_tracker': ['home', 'not_home'],
    }
    
    def __init__(self):
        """Initialize event generator."""
        logger.info("SyntheticEventGenerator initialized")
    
    async def generate_events(
        self,
        devices: list[dict[str, Any]],
        days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic events for devices.
        
        Args:
            devices: List of device dictionaries
            days: Number of days of events to generate
        
        Returns:
            List of event dictionaries
        """
        logger.info(f"Generating events for {len(devices)} devices over {days} days...")
        
        events = []
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        for device in devices:
            device_type = device.get('device_type', 'sensor')
            entity_id = device.get('entity_id', 'unknown.entity')
            area = device.get('area', 'unknown')
            
            # Get event frequency for device type
            events_per_day = self.EVENT_FREQUENCIES.get(device_type, 7.5)
            
            # Generate events for each day
            for day in range(days):
                day_start = start_time + timedelta(days=day)
                
                # Distribute events throughout the day
                num_events = int(events_per_day)
                if random.random() < (events_per_day - num_events):
                    num_events += 1
                
                for _ in range(num_events):
                    # Generate random time within day
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    
                    event_time = day_start + timedelta(
                        hours=hour,
                        minutes=minute,
                        seconds=second
                    )
                    
                    # Generate state
                    state = self._generate_state(device_type)
                    
                    event = {
                        'event_type': 'state_changed',
                        'entity_id': entity_id,
                        'state': state,
                        'timestamp': event_time.isoformat(),
                        'attributes': {
                            'device_type': device_type,
                            'area': area,
                            'device_class': device.get('device_class')
                        }
                    }
                    
                    events.append(event)
        
        # Sort events by timestamp
        events.sort(key=lambda e: e['timestamp'])
        
        logger.info(f"✅ Generated {len(events)} events over {days} days")
        return events
    
    def _generate_state(self, device_type: str) -> str:
        """
        Generate state value for device type.
        
        Args:
            device_type: Device type
        
        Returns:
            State value as string
        """
        state_generator = self.DEVICE_STATES.get(device_type)
        
        if state_generator is None:
            return 'unknown'
        elif callable(state_generator):
            return state_generator()
        elif isinstance(state_generator, list):
            return random.choice(state_generator)
        else:
            return str(state_generator)

