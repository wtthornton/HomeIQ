"""
Synergy Patterns Generator

Generate realistic multi-device automation patterns with conditional logic, delays, and state-dependent triggers.

Epic AI-11: Complex Multi-Device Synergies
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SynergyPatternGenerator:
    """
    Generate multi-device synergy patterns for synthetic training data.
    
    Creates realistic automation patterns:
    - 2-device synergies (motion + light)
    - 3-device synergies (motion + light + brightness sensor)
    - Conditional logic (time between sunset/sunrise)
    - State-dependent triggers (only if home)
    - Delay patterns (turn off after 5 minutes)
    """
    
    def __init__(self):
        """Initialize synergy pattern generator."""
        logger.info("SynergyPatternGenerator initialized")
    
    def generate_synergy_events(
        self,
        devices: list[dict[str, Any]],
        automations: list[dict[str, Any]] | None = None,
        start_date: datetime | None = None,
        days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Generate synergy events based on device combinations and automations.
        
        Args:
            devices: List of devices
            automations: Optional list of automations (from blueprint templates)
            start_date: Optional start date for time-based patterns
            days: Number of days to generate events for
        
        Returns:
            List of synergy event sequences
        """
        synergy_events = []
        
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Generate 2-device synergies
        two_device_synergies = self._generate_two_device_synergies(
            devices, start_date, days
        )
        synergy_events.extend(two_device_synergies)
        
        # Generate 3-device synergies
        three_device_synergies = self._generate_three_device_synergies(
            devices, start_date, days
        )
        synergy_events.extend(three_device_synergies)
        
        # Generate state-dependent synergies
        state_dependent = self._generate_state_dependent_synergies(
            devices, start_date, days
        )
        synergy_events.extend(state_dependent)
        
        logger.info(f"✅ Generated {len(synergy_events)} synergy event sequences")
        return synergy_events
    
    def _generate_two_device_synergies(
        self,
        devices: list[dict[str, Any]],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """Generate 2-device synergy events (motion + light)."""
        synergy_events = []
        
        # Find motion sensors and lights
        motion_sensors = [
            d for d in devices
            if d.get('device_type') == 'binary_sensor' and d.get('device_class') == 'motion'
        ]
        lights = [
            d for d in devices
            if d.get('device_type') == 'light'
        ]
        
        if not motion_sensors or not lights:
            return synergy_events
        
        # Generate synergies for matching areas
        for motion in motion_sensors:
            motion_area = motion.get('area', '')
            
            # Find lights in same area
            area_lights = [l for l in lights if l.get('area') == motion_area]
            
            if not area_lights:
                continue
            
            light = random.choice(area_lights)
            
            # Generate synergy events for each day
            for day in range(days):
                day_date = start_date + timedelta(days=day)
                
                # Generate 2-5 motion triggers per day
                num_triggers = random.randint(2, 5)
                
                for _ in range(num_triggers):
                    # Random time during day (but prefer evening for motion-light)
                    hour = random.randint(18, 23) if random.random() < 0.6 else random.randint(0, 23)
                    minute = random.randint(0, 59)
                    
                    trigger_time = day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Check if time is between sunset (6 PM) and sunrise (6 AM next day)
                    is_night = hour >= 18 or hour < 6
                    
                    if is_night:
                        # Motion triggers → Light turns on
                        motion_event = {
                            'event_type': 'state_changed',
                            'entity_id': motion.get('entity_id'),
                            'state': 'on',
                            'timestamp': trigger_time.isoformat(),
                            'attributes': {
                                'device_type': 'binary_sensor',
                                'device_class': 'motion',
                                'synergy_trigger': True
                            }
                        }
                        
                        # Light turns on (slight delay)
                        light_on_time = trigger_time + timedelta(seconds=2)
                        light_on_event = {
                            'event_type': 'state_changed',
                            'entity_id': light.get('entity_id'),
                            'state': 'on',
                            'timestamp': light_on_time.isoformat(),
                            'attributes': {
                                'device_type': 'light',
                                'synergy_action': True,
                                'synergy_trigger_entity': motion.get('entity_id'),
                                'brightness_pct': random.randint(50, 100),
                                'condition': 'time_between_sunset_sunrise'
                            }
                        }
                        
                        # Light turns off after delay (5 minutes)
                        delay_minutes = 5
                        light_off_time = light_on_time + timedelta(minutes=delay_minutes)
                        light_off_event = {
                            'event_type': 'state_changed',
                            'entity_id': light.get('entity_id'),
                            'state': 'off',
                            'timestamp': light_off_time.isoformat(),
                            'attributes': {
                                'device_type': 'light',
                                'synergy_delay': True,
                                'delay_minutes': delay_minutes,
                                'synergy_trigger_entity': motion.get('entity_id')
                            }
                        }
                        
                        synergy_events.extend([motion_event, light_on_event, light_off_event])
        
        return synergy_events
    
    def _generate_three_device_synergies(
        self,
        devices: list[dict[str, Any]],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """Generate 3-device synergy events (motion + light + brightness sensor)."""
        synergy_events = []
        
        # Find motion sensors, lights, and brightness sensors
        motion_sensors = [
            d for d in devices
            if d.get('device_type') == 'binary_sensor' and d.get('device_class') == 'motion'
        ]
        lights = [
            d for d in devices
            if d.get('device_type') == 'light'
        ]
        brightness_sensors = [
            d for d in devices
            if d.get('device_type') == 'sensor' and d.get('device_class') == 'illuminance'
        ]
        
        if not motion_sensors or not lights or not brightness_sensors:
            return synergy_events
        
        # Generate synergies for matching areas
        for motion in motion_sensors:
            motion_area = motion.get('area', '')
            
            # Find lights and brightness sensors in same area
            area_lights = [l for l in lights if l.get('area') == motion_area]
            area_brightness = [b for b in brightness_sensors if b.get('area') == motion_area]
            
            if not area_lights or not area_brightness:
                continue
            
            light = random.choice(area_lights)
            brightness = random.choice(area_brightness)
            
            # Generate synergy events for each day
            for day in range(days):
                day_date = start_date + timedelta(days=day)
                
                # Generate 1-3 triggers per day (less frequent than 2-device)
                num_triggers = random.randint(1, 3)
                
                for _ in range(num_triggers):
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    
                    trigger_time = day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Motion triggers
                    motion_event = {
                        'event_type': 'state_changed',
                        'entity_id': motion.get('entity_id'),
                        'state': 'on',
                        'timestamp': trigger_time.isoformat(),
                        'attributes': {
                            'device_type': 'binary_sensor',
                            'device_class': 'motion',
                            'synergy_trigger': True
                        }
                    }
                    
                    # Check brightness (conditional)
                    brightness_value = random.randint(0, 100)  # lux
                    brightness_threshold = 50  # Only turn on if below threshold
                    
                    brightness_event = {
                        'event_type': 'state_changed',
                        'entity_id': brightness.get('entity_id'),
                        'state': str(brightness_value),
                        'timestamp': (trigger_time + timedelta(seconds=1)).isoformat(),
                        'attributes': {
                            'device_type': 'sensor',
                            'device_class': 'illuminance',
                            'synergy_condition': True,
                            'unit_of_measurement': 'lx'
                        }
                    }
                    
                    # Light adjusts based on brightness (only if below threshold)
                    if brightness_value < brightness_threshold:
                        light_adjust_time = trigger_time + timedelta(seconds=2)
                        light_adjust_event = {
                            'event_type': 'state_changed',
                            'entity_id': light.get('entity_id'),
                            'state': 'on',
                            'timestamp': light_adjust_time.isoformat(),
                            'attributes': {
                                'device_type': 'light',
                                'synergy_action': True,
                                'synergy_trigger_entity': motion.get('entity_id'),
                                'synergy_condition_entity': brightness.get('entity_id'),
                                'brightness_pct': random.randint(70, 100),
                                'condition_met': True,
                                'brightness_value': brightness_value
                            }
                        }
                        
                        # Light turns off after delay
                        delay_minutes = 5
                        light_off_time = light_adjust_time + timedelta(minutes=delay_minutes)
                        light_off_event = {
                            'event_type': 'state_changed',
                            'entity_id': light.get('entity_id'),
                            'state': 'off',
                            'timestamp': light_off_time.isoformat(),
                            'attributes': {
                                'device_type': 'light',
                                'synergy_delay': True,
                                'delay_minutes': delay_minutes,
                                'synergy_trigger_entity': motion.get('entity_id')
                            }
                        }
                        
                        synergy_events.extend([motion_event, brightness_event, light_adjust_event, light_off_event])
                    else:
                        # Brightness too high, no light action
                        synergy_events.extend([motion_event, brightness_event])
        
        return synergy_events
    
    def _generate_state_dependent_synergies(
        self,
        devices: list[dict[str, Any]],
        start_date: datetime,
        days: int
    ) -> list[dict[str, Any]]:
        """Generate state-dependent synergy events (only if home)."""
        synergy_events = []
        
        # Find presence sensors
        presence_sensors = [
            d for d in devices
            if d.get('device_type') in ['device_tracker', 'person']
        ]
        
        # Find action devices (lights, switches, climate)
        action_devices = [
            d for d in devices
            if d.get('device_type') in ['light', 'switch', 'climate']
        ]
        
        if not presence_sensors or not action_devices:
            return synergy_events
        
        # Generate synergies
        for presence in presence_sensors:
            # Generate home/away state changes
            for day in range(days):
                day_date = start_date + timedelta(days=day)
                
                # Morning: arrive home (if away)
                arrive_time = day_date.replace(hour=8, minute=0, second=0, microsecond=0)
                arrive_event = {
                    'event_type': 'state_changed',
                    'entity_id': presence.get('entity_id'),
                    'state': 'home',
                    'timestamp': arrive_time.isoformat(),
                    'attributes': {
                        'device_type': presence.get('device_type'),
                        'synergy_trigger': True,
                        'presence_state': 'home'
                    }
                }
                
                # Evening: leave home
                leave_time = day_date.replace(hour=18, minute=0, second=0, microsecond=0)
                leave_event = {
                    'event_type': 'state_changed',
                    'entity_id': presence.get('entity_id'),
                    'state': 'not_home',
                    'timestamp': leave_time.isoformat(),
                    'attributes': {
                        'device_type': presence.get('device_type'),
                        'synergy_trigger': True,
                        'presence_state': 'away'
                    }
                }
                
                # When arriving home, trigger actions (only if home)
                if random.random() < 0.7:  # 70% chance
                    action_device = random.choice(action_devices)
                    action_time = arrive_time + timedelta(minutes=1)
                    
                    action_event = {
                        'event_type': 'state_changed',
                        'entity_id': action_device.get('entity_id'),
                        'state': 'on' if action_device.get('device_type') in ['light', 'switch'] else 'heat',
                        'timestamp': action_time.isoformat(),
                        'attributes': {
                            'device_type': action_device.get('device_type'),
                            'synergy_action': True,
                            'synergy_trigger_entity': presence.get('entity_id'),
                            'condition': 'only_if_home',
                            'presence_state': 'home'
                        }
                    }
                    
                    synergy_events.extend([arrive_event, action_event])
                
                # When leaving, reduce activity (only if away)
                if random.random() < 0.5:  # 50% chance
                    action_device = random.choice(action_devices)
                    action_time = leave_time + timedelta(minutes=5)
                    
                    reduce_event = {
                        'event_type': 'state_changed',
                        'entity_id': action_device.get('entity_id'),
                        'state': 'off' if action_device.get('device_type') in ['light', 'switch'] else 'idle',
                        'timestamp': action_time.isoformat(),
                        'attributes': {
                            'device_type': action_device.get('device_type'),
                            'synergy_action': True,
                            'synergy_trigger_entity': presence.get('entity_id'),
                            'condition': 'only_if_away',
                            'presence_state': 'away'
                        }
                    }
                    
                    synergy_events.extend([leave_event, reduce_event])
                else:
                    synergy_events.append(leave_event)
        
        return synergy_events

