"""
Context Correlator

Apply context-aware patterns to synthetic events based on weather, energy, brightness, presence, and seasonal factors.

Epic AI-11: Context-Aware Event Generation
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ContextCorrelator:
    """
    Correlate events with external context (weather, energy, brightness, presence, season).
    
    Applies realistic patterns:
    - Weather-driven: rain → close windows, frost → heating
    - Energy-aware: low carbon → EV charging, off-peak → appliances
    - Brightness-aware: sunset → lights on
    - Presence-aware: home/away modes
    - Seasonal: summer vs winter behaviors
    """
    
    # Temperature thresholds for HVAC
    HEATING_THRESHOLD = 18.0  # °C - turn on heat below this
    COOLING_THRESHOLD = 25.0  # °C - turn on AC above this
    
    # Carbon intensity thresholds
    LOW_CARBON_THRESHOLD = 200.0  # gCO2/kWh - low carbon
    HIGH_CARBON_THRESHOLD = 400.0  # gCO2/kWh - high carbon
    
    def __init__(self):
        """Initialize context correlator."""
        logger.info("ContextCorrelator initialized")
    
    def apply_context_patterns(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        weather_data: list[dict[str, Any]] | None = None,
        carbon_data: list[dict[str, Any]] | None = None,
        start_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Apply context-aware patterns to events.
        
        Args:
            events: List of existing events
            devices: List of devices
            weather_data: Optional weather data points
            carbon_data: Optional carbon intensity data points
            start_date: Optional start date for time-based patterns
        
        Returns:
            List of events with context patterns applied
        """
        correlated_events = events.copy()
        
        # Apply weather-driven patterns
        if weather_data:
            correlated_events = self._apply_weather_patterns(
                correlated_events, devices, weather_data
            )
        
        # Apply energy-aware patterns
        if carbon_data:
            correlated_events = self._apply_energy_patterns(
                correlated_events, devices, carbon_data
            )
        
        # Apply brightness-aware patterns
        if start_date:
            correlated_events = self._apply_brightness_patterns(
                correlated_events, devices, start_date
            )
        
        # Apply presence-aware patterns
        correlated_events = self._apply_presence_patterns(
            correlated_events, devices
        )
        
        # Apply seasonal adjustments
        if start_date:
            correlated_events = self._apply_seasonal_adjustments(
                correlated_events, devices, start_date
            )
        
        # Sort events by timestamp
        correlated_events.sort(key=lambda e: e.get('timestamp', ''))
        
        logger.info(f"Applied context patterns to {len(correlated_events)} events")
        return correlated_events
    
    def _apply_weather_patterns(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        weather_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply weather-driven patterns to events."""
        # Create weather lookup by timestamp (hourly)
        weather_lookup = {}
        for weather_point in weather_data:
            timestamp = weather_point.get('timestamp', '')
            # Use hour as key for lookup
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                weather_lookup[hour_key] = weather_point
            except (ValueError, AttributeError):
                continue
        
        # Find relevant devices
        window_devices = [d for d in devices if d.get('device_type') == 'cover' and 'window' in d.get('name', '').lower()]
        hvac_devices = [d for d in devices if d.get('device_type') == 'climate']
        
        new_events = []
        
        for event in events:
            event_time = event.get('timestamp', '')
            entity_id = event.get('entity_id', '')
            
            # Get weather for this event's hour
            try:
                dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                weather = weather_lookup.get(hour_key)
            except (ValueError, AttributeError):
                weather = None
            
            if weather:
                temp = weather.get('temperature', 20.0)
                condition = weather.get('condition', '')
                
                # Rain → close windows
                if condition in ['rain', 'rainy', 'storm', 'stormy']:
                    for window in window_devices:
                        if window.get('entity_id') == entity_id:
                            # Generate close event
                            close_event = {
                                'event_type': 'state_changed',
                                'entity_id': entity_id,
                                'state': 'closed',
                                'timestamp': event_time,
                                'attributes': {
                                    'device_type': 'cover',
                                    'context': 'weather_rain',
                                    'weather_condition': condition
                                }
                            }
                            new_events.append(close_event)
                
                # Frost/cold → increase heating
                if temp < self.HEATING_THRESHOLD:
                    for hvac in hvac_devices:
                        if hvac.get('entity_id') == entity_id:
                            # Generate heating event
                            heat_event = {
                                'event_type': 'state_changed',
                                'entity_id': entity_id,
                                'state': 'heat',
                                'timestamp': event_time,
                                'attributes': {
                                    'device_type': 'climate',
                                    'context': 'weather_cold',
                                    'temperature': temp,
                                    'target_temperature': self.HEATING_THRESHOLD + 2
                                }
                            }
                            new_events.append(heat_event)
                
                # Hot weather → increase cooling
                if temp > self.COOLING_THRESHOLD:
                    for hvac in hvac_devices:
                        if hvac.get('entity_id') == entity_id:
                            # Generate cooling event
                            cool_event = {
                                'event_type': 'state_changed',
                                'entity_id': entity_id,
                                'state': 'cool',
                                'timestamp': event_time,
                                'attributes': {
                                    'device_type': 'climate',
                                    'context': 'weather_hot',
                                    'temperature': temp,
                                    'target_temperature': self.COOLING_THRESHOLD - 2
                                }
                            }
                            new_events.append(cool_event)
        
        events.extend(new_events)
        return events
    
    def _apply_energy_patterns(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        carbon_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply energy-aware patterns to events."""
        # Create carbon lookup by timestamp (hourly)
        carbon_lookup = {}
        for carbon_point in carbon_data:
            timestamp = carbon_point.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                carbon_lookup[hour_key] = carbon_point
            except (ValueError, AttributeError):
                continue
        
        # Find energy devices
        ev_devices = [d for d in devices if 'ev' in d.get('name', '').lower() or 'electric' in d.get('name', '').lower()]
        switch_devices = [d for d in devices if d.get('device_type') == 'switch']
        
        new_events = []
        
        for event in events:
            event_time = event.get('timestamp', '')
            
            # Get carbon intensity for this event's hour
            try:
                dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                carbon = carbon_lookup.get(hour_key)
            except (ValueError, AttributeError):
                carbon = None
            
            if carbon:
                intensity = carbon.get('carbon_intensity', 300.0)
                
                # Low carbon → charge EV, run appliances
                if intensity < self.LOW_CARBON_THRESHOLD:
                    # Random chance to trigger EV charging or appliance use
                    if random.random() < 0.3:  # 30% chance
                        target_device = None
                        if ev_devices and random.random() < 0.5:
                            target_device = random.choice(ev_devices)
                        elif switch_devices:
                            target_device = random.choice(switch_devices)
                        
                        if target_device:
                            energy_event = {
                                'event_type': 'state_changed',
                                'entity_id': target_device.get('entity_id'),
                                'state': 'on',
                                'timestamp': event_time,
                                'attributes': {
                                    'device_type': target_device.get('device_type'),
                                    'context': 'energy_low_carbon',
                                    'carbon_intensity': intensity
                                }
                            }
                            new_events.append(energy_event)
                
                # High carbon → reduce energy usage
                elif intensity > self.HIGH_CARBON_THRESHOLD:
                    # Random chance to turn off non-essential devices
                    if random.random() < 0.2:  # 20% chance
                        for switch in switch_devices:
                            if random.random() < 0.3:  # 30% chance per switch
                                reduce_event = {
                                    'event_type': 'state_changed',
                                    'entity_id': switch.get('entity_id'),
                                    'state': 'off',
                                    'timestamp': event_time,
                                    'attributes': {
                                        'device_type': 'switch',
                                        'context': 'energy_high_carbon',
                                        'carbon_intensity': intensity
                                    }
                                }
                                new_events.append(reduce_event)
        
        events.extend(new_events)
        return events
    
    def _apply_brightness_patterns(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        start_date: datetime
    ) -> list[dict[str, Any]]:
        """Apply brightness-aware patterns (sunset → lights on)."""
        light_devices = [d for d in devices if d.get('device_type') == 'light']
        
        if not light_devices:
            return events
        
        new_events = []
        
        # Generate sunset/sunrise events for each day
        for day_offset in range(30):  # Up to 30 days
            day_date = start_date + timedelta(days=day_offset)
            
            # Approximate sunset (6 PM) and sunrise (6 AM)
            sunset_time = day_date.replace(hour=18, minute=0, second=0)
            sunrise_time = (day_date + timedelta(days=1)).replace(hour=6, minute=0, second=0)
            
            # Sunset → turn on lights
            for light in light_devices:
                if random.random() < 0.7:  # 70% chance lights turn on at sunset
                    sunset_event = {
                        'event_type': 'state_changed',
                        'entity_id': light.get('entity_id'),
                        'state': 'on',
                        'timestamp': sunset_time.isoformat(),
                        'attributes': {
                            'device_type': 'light',
                            'context': 'brightness_sunset',
                            'brightness_pct': random.randint(50, 100)
                        }
                    }
                    new_events.append(sunset_event)
            
            # Sunrise → turn off lights
            for light in light_devices:
                if random.random() < 0.5:  # 50% chance lights turn off at sunrise
                    sunrise_event = {
                        'event_type': 'state_changed',
                        'entity_id': light.get('entity_id'),
                        'state': 'off',
                        'timestamp': sunrise_time.isoformat(),
                        'attributes': {
                            'device_type': 'light',
                            'context': 'brightness_sunrise'
                        }
                    }
                    new_events.append(sunrise_event)
        
        events.extend(new_events)
        return events
    
    def _apply_presence_patterns(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply presence-aware patterns (home/away modes)."""
        # Find presence sensors
        presence_sensors = [
            d for d in devices
            if d.get('device_type') == 'device_tracker' or d.get('device_type') == 'person'
        ]
        
        if not presence_sensors:
            return events
        
        # Simulate presence patterns (home during day, away sometimes)
        # This is a simplified model - in reality, presence would be tracked per event
        # For now, we'll add presence context to existing events
        
        for event in events:
            # Add presence context randomly (simulating home/away states)
            if 'attributes' not in event:
                event['attributes'] = {}
            
            # 70% chance of being home during normal hours
            presence_state = 'home' if random.random() < 0.7 else 'away'
            event['attributes']['presence'] = presence_state
            
            # If away, reduce some device activity
            if presence_state == 'away':
                device_type = event.get('attributes', {}).get('device_type', '')
                if device_type in ['light', 'switch']:
                    # Slightly reduce activity when away
                    if random.random() < 0.3:  # 30% chance to skip this event
                        event['attributes']['context'] = 'presence_away_reduced'
        
        return events
    
    def _apply_seasonal_adjustments(
        self,
        events: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        start_date: datetime
    ) -> list[dict[str, Any]]:
        """Apply seasonal adjustments (summer vs winter behaviors)."""
        # Determine season from start date
        month = start_date.month
        
        if month in [12, 1, 2]:  # Winter (Northern Hemisphere)
            season = 'winter'
        elif month in [3, 4, 5]:  # Spring
            season = 'spring'
        elif month in [6, 7, 8]:  # Summer
            season = 'summer'
        else:  # Fall
            season = 'fall'
        
        hvac_devices = [d for d in devices if d.get('device_type') == 'climate']
        
        # Adjust HVAC behavior based on season
        for event in events:
            entity_id = event.get('entity_id', '')
            device_type = event.get('attributes', {}).get('device_type', '')
            
            if device_type == 'climate':
                # Add seasonal context
                if 'attributes' not in event:
                    event['attributes'] = {}
                
                event['attributes']['season'] = season
                
                # Adjust target temperatures based on season
                if season == 'winter':
                    event['attributes']['seasonal_adjustment'] = 'heating_priority'
                elif season == 'summer':
                    event['attributes']['seasonal_adjustment'] = 'cooling_priority'
                else:
                    event['attributes']['seasonal_adjustment'] = 'balanced'
        
        return events

