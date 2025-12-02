"""
Synthetic Event Generator

Generate synthetic events for training home type classifier.
Uses device-type-specific frequencies from production analysis.
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticEventGenerator:
    """
    Generate synthetic events for training with diverse event types.
    
    Uses device-type-specific frequencies (from production analysis):
    - Lights: 11 events/day
    - Binary sensors: 36 events/day
    - Sensors: 26 events/day
    - etc.
    
    Event type distribution (Epic AI-11):
    - state_change: 60%
    - automation_trigger: 15%
    - script_call: 8%
    - scene_activation: 5%
    - voice_command: 5%
    - webhook_trigger: 4%
    - api_call: 3%
    """
    
    # Event type distribution (Epic AI-11)
    EVENT_TYPE_DISTRIBUTION = {
        'state_changed': 0.60,
        'automation_triggered': 0.15,
        'script_started': 0.08,
        'scene_activated': 0.05,
        'voice_command': 0.05,
        'webhook_triggered': 0.04,
        'api_call': 0.03
    }
    
    # Voice assistant platforms
    VOICE_PLATFORMS = ['alexa', 'google_assistant', 'assist', 'siri']
    
    # Webhook sources
    WEBHOOK_SOURCES = ['ifttt', 'zapier', 'custom_api', 'homebridge', 'node_red']
    
    # API service types
    API_SERVICES = ['weather', 'calendar', 'notifications', 'music', 'news', 'shopping']
    
    # Scene types
    SCENE_TYPES = ['lighting', 'climate', 'security', 'entertainment', 'sleep', 'away']
    
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
        days: int = 7,
        progress_callback=None
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic events for devices.
        
        Args:
            devices: List of device dictionaries
            days: Number of days of events to generate
            progress_callback: Optional callback function(device_num, total_devices, days_processed, total_days)
        
        Returns:
            List of event dictionaries
        """
        total_devices = len(devices)
        logger.info(f"Generating events for {total_devices} devices over {days} days...")
        
        events = []
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        for device_idx, device in enumerate(devices):
            device_num = device_idx + 1
            device_type = device.get('device_type', 'sensor')
            entity_id = device.get('entity_id', 'unknown.entity')
            area = device.get('area', 'unknown')
            
            # Get event frequency for device type
            events_per_day = self.EVENT_FREQUENCIES.get(device_type, 7.5)
            
            # Generate events for each day
            for day in range(days):
                day_start = start_time + timedelta(days=day)
                
                # Progress update every 10 devices or every 10 days (more frequent for long runs)
                progress_interval = 10 if days <= 30 else 5
                if (device_num % progress_interval == 0 or device_num == total_devices) and (day == 0 or day % progress_interval == 0 or day == days - 1):
                    if progress_callback:
                        progress_callback(device_num, total_devices, day + 1, days)
                
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
                    
                    # Select event type based on distribution
                    event_type = self._select_event_type()
                    
                    # Generate event based on type
                    event = self._generate_event_by_type(
                        event_type=event_type,
                        device=device,
                        entity_id=entity_id,
                        device_type=device_type,
                        area=area,
                        event_time=event_time
                    )
                    
                    events.append(event)
            
            # Progress update after each device (for longer runs)
            if days >= 30 and (device_num % 5 == 0 or device_num == total_devices):
                logger.debug(f"   Processed {device_num}/{total_devices} devices, {len(events)} events so far...")
        
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
    
    def _select_event_type(self) -> str:
        """
        Select event type based on distribution.
        
        Returns:
            Event type string
        """
        rand = random.random()
        cumulative = 0.0
        
        for event_type, probability in self.EVENT_TYPE_DISTRIBUTION.items():
            cumulative += probability
            if rand <= cumulative:
                return event_type
        
        # Fallback to state_changed
        return 'state_changed'
    
    def _generate_event_by_type(
        self,
        event_type: str,
        device: dict[str, Any],
        entity_id: str,
        device_type: str,
        area: str,
        event_time: datetime
    ) -> dict[str, Any]:
        """
        Generate event based on event type.
        
        Args:
            event_type: Type of event to generate
            device: Device dictionary
            entity_id: Entity ID
            device_type: Device type
            area: Area name
            event_time: Event timestamp
        
        Returns:
            Event dictionary
        """
        if event_type == 'state_changed':
            return self._generate_state_changed_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'automation_triggered':
            return self._generate_automation_trigger_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'script_started':
            return self._generate_script_call_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'scene_activated':
            return self._generate_scene_activation_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'voice_command':
            return self._generate_voice_command_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'webhook_triggered':
            return self._generate_webhook_trigger_event(
                entity_id, device_type, area, device, event_time
            )
        elif event_type == 'api_call':
            return self._generate_api_call_event(
                entity_id, device_type, area, device, event_time
            )
        else:
            # Fallback to state_changed
            return self._generate_state_changed_event(
                entity_id, device_type, area, device, event_time
            )
    
    def _generate_state_changed_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate state_changed event (existing logic)."""
        state = self._generate_state(device_type)
        
        return {
            'event_type': 'state_changed',
            'entity_id': entity_id,
            'state': state,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'device_type': device_type,
                'area': area,
                'device_class': device.get('device_class'),
                'friendly_name': device.get('friendly_name', device.get('name'))
            }
        }
    
    def _generate_automation_trigger_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate automation_triggered event."""
        automation_id = f"automation.{area.lower().replace(' ', '_')}_automation_{random.randint(1, 5)}"
        
        return {
            'event_type': 'automation_triggered',
            'entity_id': automation_id,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'trigger_entity_id': entity_id,
                'trigger_device_type': device_type,
                'area': area,
                'trigger_state': self._generate_state(device_type),
                'automation_name': f"{area} Automation"
            }
        }
    
    def _generate_script_call_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate script_started event."""
        script_id = f"script.{area.lower().replace(' ', '_')}_script_{random.randint(1, 3)}"
        script_names = ['turn_on_lights', 'turn_off_lights', 'set_climate', 'security_mode']
        
        return {
            'event_type': 'script_started',
            'entity_id': script_id,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'script_name': random.choice(script_names),
                'trigger_entity_id': entity_id,
                'area': area,
                'device_type': device_type
            }
        }
    
    def _generate_scene_activation_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate scene_activated event."""
        scene_id = f"scene.{area.lower().replace(' ', '_')}_{random.choice(self.SCENE_TYPES)}"
        scene_names = {
            'lighting': ['Evening Lights', 'Morning Lights', 'Dimmed'],
            'climate': ['Comfort Mode', 'Energy Save', 'Away Mode'],
            'security': ['Away', 'Home', 'Night'],
            'entertainment': ['Movie Mode', 'Party Mode'],
            'sleep': ['Bedtime', 'Sleep'],
            'away': ['Away', 'Vacation']
        }
        
        scene_type = random.choice(self.SCENE_TYPES)
        scene_name = random.choice(scene_names.get(scene_type, ['Scene']))
        
        return {
            'event_type': 'scene_activated',
            'entity_id': scene_id,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'scene_name': scene_name,
                'scene_type': scene_type,
                'area': area,
                'trigger_entity_id': entity_id if device_type in ['light', 'switch'] else None
            }
        }
    
    def _generate_voice_command_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate voice_command event."""
        platform = random.choice(self.VOICE_PLATFORMS)
        commands = {
            'alexa': ['turn on lights', 'set temperature', 'lock doors', 'play music'],
            'google_assistant': ['turn on lights', 'set thermostat', 'lock front door', 'play music'],
            'assist': ['turn on kitchen light', 'set living room temperature', 'activate scene'],
            'siri': ['turn on lights', 'set temperature', 'lock doors']
        }
        
        command = random.choice(commands.get(platform, ['turn on lights']))
        
        return {
            'event_type': 'voice_command',
            'entity_id': entity_id,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'platform': platform,
                'command': command,
                'area': area,
                'device_type': device_type,
                'user': f"user_{random.randint(1, 5)}"
            }
        }
    
    def _generate_webhook_trigger_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate webhook_triggered event."""
        source = random.choice(self.WEBHOOK_SOURCES)
        webhook_id = f"webhook.{source}_{random.randint(1, 10)}"
        
        return {
            'event_type': 'webhook_triggered',
            'entity_id': webhook_id,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'webhook_source': source,
                'webhook_id': webhook_id,
                'trigger_entity_id': entity_id,
                'area': area,
                'device_type': device_type,
                'payload': {'action': random.choice(['trigger', 'update', 'notify'])}
            }
        }
    
    def _generate_api_call_event(
        self,
        entity_id: str,
        device_type: str,
        area: str,
        device: dict[str, Any],
        event_time: datetime
    ) -> dict[str, Any]:
        """Generate api_call event."""
        service = random.choice(self.API_SERVICES)
        api_endpoint = f"api.{service}_{random.randint(1, 5)}"
        
        return {
            'event_type': 'api_call',
            'entity_id': api_endpoint,
            'timestamp': event_time.isoformat(),
            'attributes': {
                'service': service,
                'endpoint': api_endpoint,
                'method': random.choice(['GET', 'POST', 'PUT']),
                'status_code': random.choice([200, 200, 200, 201, 429, 500]),  # Mostly success, some errors
                'area': area,
                'device_type': device_type
            }
        }

