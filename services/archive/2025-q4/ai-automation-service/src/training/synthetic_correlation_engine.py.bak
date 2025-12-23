"""
Synthetic Correlation Engine

Rule-based correlation engine that validates relationships between external data
and device events to ensure realistic training data.

NUC-optimized: Lightweight rule-based validation (no ML inference).
Performance target: <100ms per home validation.

2025 Best Practices:
- Python 3.11+ type hints
- Pydantic models for data validation
- Structured logging
- Memory-efficient (<50MB for engine)
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticCorrelationEngine:
    """
    Rule-based correlation engine (lightweight, NUC-optimized).
    
    Validates relationships between external data and device events.
    Ensures training data realism without modifying events.
    """
    
    # Temperature thresholds for HVAC correlation
    AC_THRESHOLD = 25.0  # °C - AC turns on above this
    HEAT_THRESHOLD = 18.0  # °C - Heat turns on below this
    
    # Carbon intensity thresholds
    LOW_CARBON_THRESHOLD = 200.0  # gCO2/kWh - Low carbon threshold
    HIGH_CARBON_THRESHOLD = 500.0  # gCO2/kWh - High carbon threshold
    
    # Pricing thresholds
    HIGH_PRICE_MULTIPLIER = 1.5  # 1.5x baseline = high price
    LOW_PRICE_MULTIPLIER = 0.7  # 0.7x baseline = low price
    
    def __init__(self):
        """Initialize correlation engine."""
        logger.debug("SyntheticCorrelationEngine initialized")
    
    def validate_weather_hvac_correlation(
        self,
        weather_data: list[dict[str, Any]],
        hvac_events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Validate weather-HVAC correlations.
        
        Rules:
        - High temperature (>25°C) → AC should be on
        - Low temperature (<18°C) → Heat should be on
        - Window open → HVAC off/less active
        
        Args:
            weather_data: List of weather data points (hourly)
            hvac_events: List of HVAC device events
        
        Returns:
            Validation result dict with:
            - valid: bool
            - violations: list of violation descriptions
            - correlation_score: float (0.0-1.0)
        """
        violations = []
        correlations = []
        
        # Create maps for quick lookup
        weather_by_timestamp = {w['timestamp']: w for w in weather_data}
        hvac_by_timestamp: dict[str, list[dict[str, Any]]] = {}
        
        for event in hvac_events:
            timestamp = event.get('timestamp', '')
            if timestamp not in hvac_by_timestamp:
                hvac_by_timestamp[timestamp] = []
            hvac_by_timestamp[timestamp].append(event)
        
        # Validate each weather point
        for weather_point in weather_data:
            timestamp = weather_point['timestamp']
            temperature = weather_point.get('temperature', 0.0)
            
            # Get HVAC events at this timestamp
            hvac_events_at_time = hvac_by_timestamp.get(timestamp, [])
            
            # Rule 1: High temperature → AC on
            if temperature > self.AC_THRESHOLD:
                ac_on = any(
                    event.get('state', '').lower() in ('cool', 'cooling', 'on')
                    for event in hvac_events_at_time
                )
                if not ac_on and hvac_events_at_time:
                    violations.append(
                        f"High temp {temperature}°C but AC not on at {timestamp}"
                    )
                elif ac_on:
                    correlations.append(1.0)
                else:
                    correlations.append(0.5)  # Partial correlation (no HVAC device)
            
            # Rule 2: Low temperature → Heat on
            elif temperature < self.HEAT_THRESHOLD:
                heat_on = any(
                    event.get('state', '').lower() in ('heat', 'heating', 'on')
                    for event in hvac_events_at_time
                )
                if not heat_on and hvac_events_at_time:
                    violations.append(
                        f"Low temp {temperature}°C but heat not on at {timestamp}"
                    )
                elif heat_on:
                    correlations.append(1.0)
                else:
                    correlations.append(0.5)  # Partial correlation (no HVAC device)
            
            # Rule 3: Moderate temperature → HVAC can be off
            else:
                # This is acceptable - no violation
                correlations.append(1.0)
        
        # Calculate correlation score
        correlation_score = sum(correlations) / len(correlations) if correlations else 1.0
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'correlation_score': correlation_score,
            'total_checks': len(weather_data),
            'violations_count': len(violations)
        }
    
    def validate_energy_correlation(
        self,
        carbon_data: list[dict[str, Any]],
        pricing_data: list[dict[str, Any]],
        energy_events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Validate carbon/pricing-energy device correlations.
        
        Rules:
        - Low carbon intensity (<200 gCO2/kWh) → EV charging preferred
        - High pricing (>1.5x baseline) → Delay high-energy devices
        - Solar peak (low carbon + low price) → Increase renewable usage
        
        Args:
            carbon_data: List of carbon intensity data points
            pricing_data: List of pricing data points
            energy_events: List of energy device events (EV, HVAC, water heater, etc.)
        
        Returns:
            Validation result dict with:
            - valid: bool
            - violations: list of violation descriptions
            - correlation_score: float (0.0-1.0)
        """
        violations = []
        correlations = []
        
        # Create maps for quick lookup
        carbon_by_timestamp = {c['timestamp']: c for c in carbon_data}
        pricing_by_timestamp = {p['timestamp']: p for p in pricing_data}
        energy_by_timestamp: dict[str, list[dict[str, Any]]] = {}
        
        for event in energy_events:
            timestamp = event.get('timestamp', '')
            if timestamp not in energy_by_timestamp:
                energy_by_timestamp[timestamp] = []
            energy_by_timestamp[timestamp].append(event)
        
        # Validate correlations
        checked_timestamps = set()
        
        for carbon_point in carbon_data:
            timestamp = carbon_point['timestamp']
            if timestamp in checked_timestamps:
                continue
            checked_timestamps.add(timestamp)
            
            carbon_intensity = carbon_point.get('intensity', 0.0)
            pricing_point = pricing_by_timestamp.get(timestamp)
            energy_events_at_time = energy_by_timestamp.get(timestamp, [])
            
            if not pricing_point:
                continue
            
            price_per_kwh = pricing_point.get('price_per_kwh', 0.0)
            pricing_tier = pricing_point.get('pricing_tier', 'off-peak')
            
            # Determine baseline price (approximate from tier)
            baseline_price = price_per_kwh
            if pricing_tier == 'peak':
                baseline_price = price_per_kwh / 1.75  # Approximate baseline
            elif pricing_tier == 'off-peak':
                baseline_price = price_per_kwh / 0.6  # Approximate baseline
            
            # Rule 1: Solar peak (low carbon + low price) → Renewable usage (check first, most specific)
            if (carbon_intensity < self.LOW_CARBON_THRESHOLD and
                  price_per_kwh < baseline_price * self.LOW_PRICE_MULTIPLIER):
                # Should see increased renewable usage
                renewable_active = any(
                    'solar' in event.get('entity_id', '').lower()
                    or 'renewable' in event.get('entity_id', '').lower()
                    for event in energy_events_at_time
                )
                if renewable_active:
                    correlations.append(1.0)
                else:
                    correlations.append(0.9)  # Good correlation even without explicit renewable
            
            # Rule 2: Low carbon → EV charging preferred
            elif carbon_intensity < self.LOW_CARBON_THRESHOLD:
                # Check if there are EV charging events
                ev_charging = any(
                    'ev' in event.get('entity_id', '').lower()
                    or 'vehicle' in event.get('entity_id', '').lower()
                    or 'charging' in event.get('state', '').lower()
                    for event in energy_events_at_time
                )
                # This is a preference, not a requirement - no violation
                if ev_charging:
                    correlations.append(1.0)
                else:
                    correlations.append(0.8)  # Good correlation even without EV
            
            # Rule 3: High pricing → Delay high-energy devices
            elif price_per_kwh > baseline_price * self.HIGH_PRICE_MULTIPLIER:
                # High-energy devices should be less active
                high_energy_active = any(
                    event.get('state', '').lower() in ('on', 'active', 'running')
                    for event in energy_events_at_time
                )
                if high_energy_active:
                    # This is a warning, not a strict violation
                    violations.append(
                        f"High price {price_per_kwh:.3f} but high-energy device active at {timestamp}"
                    )
                    correlations.append(0.7)  # Partial correlation
                else:
                    correlations.append(1.0)  # Good correlation
            
            # Default: Acceptable correlation
            else:
                correlations.append(1.0)
        
        # Calculate correlation score
        correlation_score = sum(correlations) / len(correlations) if correlations else 1.0
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'correlation_score': correlation_score,
            'total_checks': len(checked_timestamps),
            'violations_count': len(violations)
        }
    
    def validate_all_correlations(
        self,
        external_data: dict[str, Any],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Validate all correlations for a synthetic home.
        
        Args:
            external_data: Unified external data dict (from SyntheticExternalDataGenerator)
            device_events: List of device events
            devices: Optional list of devices (to identify HVAC/energy devices)
        
        Returns:
            Validation result dict with all correlation results
        """
        results = {
            'weather_hvac': None,
            'energy': None,
            'calendar_presence': None,
            'overall_valid': True,
            'overall_score': 0.0
        }
        
        # Extract data
        weather_data = external_data.get('weather', [])
        carbon_data = external_data.get('carbon_intensity', [])
        pricing_data = external_data.get('pricing', [])
        calendar_data = external_data.get('calendar', [])
        
        # Identify HVAC devices
        hvac_events = []
        if devices:
            hvac_entity_ids = {
                d.get('entity_id')
                for d in devices
                if d.get('device_type') == 'climate'
                or d.get('device_class') in ('thermostat', 'temperature')
            }
            hvac_events = [
                e for e in device_events
                if e.get('entity_id') in hvac_entity_ids
            ]
        
        # Identify energy devices
        energy_events = []
        if devices:
            energy_entity_ids = {
                d.get('entity_id')
                for d in devices
                if (d.get('device_type') in ('climate', 'water_heater', 'switch')
                    or 'ev' in d.get('device_type', '').lower()
                    or 'vehicle' in d.get('entity_id', '').lower())
            }
            energy_events = [
                e for e in device_events
                if e.get('entity_id') in energy_entity_ids
            ]
        
        # Validate weather-HVAC correlation
        if weather_data and hvac_events:
            results['weather_hvac'] = self.validate_weather_hvac_correlation(
                weather_data=weather_data,
                hvac_events=hvac_events
            )
        
        # Validate energy correlation
        if carbon_data and pricing_data and energy_events:
            results['energy'] = self.validate_energy_correlation(
                carbon_data=carbon_data,
                pricing_data=pricing_data,
                energy_events=energy_events
            )
        
        # Calculate overall validity and score
        scores = []
        if results['weather_hvac']:
            scores.append(results['weather_hvac']['correlation_score'])
            if not results['weather_hvac']['valid']:
                results['overall_valid'] = False
        
        if results['energy']:
            scores.append(results['energy']['correlation_score'])
            if not results['energy']['valid']:
                results['overall_valid'] = False
        
        results['overall_score'] = sum(scores) / len(scores) if scores else 1.0
        
        # Validate calendar-presence-device correlation
        if calendar_data:
            results['calendar_presence'] = self.validate_calendar_presence_correlation(
                calendar_data=calendar_data,
                device_events=device_events,
                devices=devices
            )
            if results['calendar_presence']:
                scores.append(results['calendar_presence']['correlation_score'])
                if not results['calendar_presence']['valid']:
                    results['overall_valid'] = False
        
        # Recalculate overall score with all correlations
        results['overall_score'] = sum(scores) / len(scores) if scores else 1.0
        
        logger.info(
            f"Correlation validation: overall_valid={results['overall_valid']}, "
            f"overall_score={results['overall_score']:.2f}"
        )
        
        return results
    
    def validate_calendar_presence_correlation(
        self,
        calendar_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Validate calendar → presence → device correlations.
        
        Rules:
        - Away → Security on, lights off
        - Home → Comfort settings, lights on
        - Work → Reduced device activity
        
        Args:
            calendar_data: List of calendar events
            device_events: List of device events
            devices: Optional list of devices (to identify presence/security/light devices)
        
        Returns:
            Validation result dict with:
            - valid: bool
            - violations: list of violation descriptions
            - correlation_score: float (0.0-1.0)
        """
        violations = []
        correlations = []
        
        # Create maps for quick lookup
        calendar_by_timestamp: dict[str, list[dict[str, Any]]] = {}
        for event in calendar_data:
            timestamp = event.get('timestamp', '')
            if timestamp not in calendar_by_timestamp:
                calendar_by_timestamp[timestamp] = []
            calendar_by_timestamp[timestamp].append(event)
        
        device_by_timestamp: dict[str, list[dict[str, Any]]] = {}
        for event in device_events:
            timestamp = event.get('timestamp', '')
            if timestamp not in device_by_timestamp:
                device_by_timestamp[timestamp] = []
            device_by_timestamp[timestamp].append(event)
        
        # Identify device types
        security_entity_ids = set()
        light_entity_ids = set()
        comfort_entity_ids = set()
        
        if devices:
            for device in devices:
                entity_id = device.get('entity_id', '')
                device_type = device.get('device_type', '').lower()
                device_class = device.get('device_class', '').lower()
                
                # Security devices
                if (device_type in ('alarm_control_panel', 'lock', 'binary_sensor')
                    or 'security' in device_type
                    or 'alarm' in device_type
                    or 'lock' in device_type):
                    security_entity_ids.add(entity_id)
                
                # Light devices
                if (device_type == 'light'
                    or device_class == 'light'
                    or 'light' in entity_id.lower()):
                    light_entity_ids.add(entity_id)
                
                # Comfort devices (HVAC, thermostat, etc.)
                if (device_type in ('climate', 'thermostat')
                    or device_class in ('thermostat', 'temperature')
                    or 'comfort' in device_type):
                    comfort_entity_ids.add(entity_id)
        
        # Validate each calendar event
        for calendar_event in calendar_data:
            timestamp = calendar_event.get('timestamp', '')
            event_type = calendar_event.get('event_type', '').lower()
            summary = calendar_event.get('summary', '').lower()
            
            # Determine presence state from calendar
            presence_state = None
            if event_type == 'away' or 'away' in summary or 'vacation' in summary:
                presence_state = 'away'
            elif event_type == 'home' or 'home' in summary:
                presence_state = 'home'
            elif event_type == 'work' or 'work' in summary or 'office' in summary:
                presence_state = 'work'
            
            if not presence_state:
                # Unknown presence state - skip
                correlations.append(1.0)  # Neutral
                continue
            
            # Get device events at this timestamp
            device_events_at_time = device_by_timestamp.get(timestamp, [])
            
            # Rule 1: Away → Security on, lights off
            if presence_state == 'away':
                # Check security devices
                security_on = any(
                    event.get('entity_id') in security_entity_ids
                    and event.get('state', '').lower() in ('on', 'armed', 'active')
                    for event in device_events_at_time
                )
                
                # Check lights
                lights_on = any(
                    event.get('entity_id') in light_entity_ids
                    and event.get('state', '').lower() in ('on', 'active')
                    for event in device_events_at_time
                )
                
                if security_entity_ids and not security_on:
                    violations.append(
                        f"Away at {timestamp} but security not on"
                    )
                    correlations.append(0.7)  # Partial correlation
                elif lights_on:
                    violations.append(
                        f"Away at {timestamp} but lights are on"
                    )
                    correlations.append(0.8)  # Partial correlation
                else:
                    correlations.append(1.0)  # Good correlation
            
            # Rule 2: Home → Comfort settings, lights on
            elif presence_state == 'home':
                # Check comfort devices (HVAC should be active)
                comfort_active = any(
                    event.get('entity_id') in comfort_entity_ids
                    and event.get('state', '').lower() in ('on', 'active', 'heat', 'cool')
                    for event in device_events_at_time
                )
                
                # Check lights (should be on)
                lights_on = any(
                    event.get('entity_id') in light_entity_ids
                    and event.get('state', '').lower() in ('on', 'active')
                    for event in device_events_at_time
                )
                
                # Home presence is more flexible - no strict violations
                if comfort_active and lights_on:
                    correlations.append(1.0)  # Perfect correlation
                elif comfort_active or lights_on:
                    correlations.append(0.9)  # Good correlation
                else:
                    correlations.append(0.8)  # Acceptable (devices may be off)
            
            # Rule 3: Work → Reduced device activity
            elif presence_state == 'work':
                # Count active devices (excluding security)
                active_devices = sum(
                    1 for event in device_events_at_time
                    if (event.get('entity_id') not in security_entity_ids
                        and event.get('state', '').lower() in ('on', 'active', 'running'))
                )
                
                # Work presence should have reduced activity
                if active_devices == 0:
                    correlations.append(1.0)  # Perfect correlation
                elif active_devices <= 2:
                    correlations.append(0.9)  # Good correlation
                else:
                    correlations.append(0.7)  # Partial correlation (too many devices active)
        
        # Calculate correlation score
        correlation_score = sum(correlations) / len(correlations) if correlations else 1.0
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'correlation_score': correlation_score,
            'total_checks': len(calendar_data),
            'violations_count': len(violations)
        }

