"""
Synthetic Electricity Pricing Generator

Generate realistic electricity pricing data for synthetic homes based on pricing region profiles.
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


class PricingDataPoint(BaseModel):
    """Pydantic model for electricity pricing data point (2025 best practice)."""
    
    timestamp: str
    price_per_kwh: float
    pricing_tier: str  # peak, off-peak, mid-peak
    region: str
    forecast: list[float] | None = None


class SyntheticElectricityPricingGenerator:
    """
    Generate realistic electricity pricing data for synthetic homes.
    
    NUC-Optimized: Uses in-memory dictionaries, no external API calls.
    Performance target: <50ms per home for basic generation.
    """
    
    # Pricing region profiles with baseline prices and currency
    PRICING_REGIONS: dict[str, dict[str, Any]] = {
        'germany_awattar': {
            'baseline': 0.30,  # EUR/kWh
            'currency': 'EUR',
            'price_range': (0.10, 0.50)
        },
        'california_tou': {
            'baseline': 0.25,  # USD/kWh
            'currency': 'USD',
            'price_range': (0.10, 0.50)
        },
        'fixed_rate': {
            'baseline': 0.15,  # USD/kWh
            'currency': 'USD',
            'price_range': (0.10, 0.50)
        }
    }
    
    # Time-of-use price multipliers
    TOU_MULTIPLIERS: dict[str, float] = {
        'peak': 1.75,      # 1.5-2.0x range, using 1.75x
        'mid-peak': 1.0,   # Baseline (1.0x)
        'off-peak': 0.6    # 0.5-0.7x range, using 0.6x
    }
    
    # TOU periods (hour ranges, 0-23)
    TOU_PERIODS: dict[str, dict[str, Any]] = {
        'california_tou': {
            'peak': (17, 21),      # 5 PM - 9 PM (weekdays)
            'mid-peak': (10, 17),  # 10 AM - 5 PM (weekdays)
            'off-peak': [(0, 10), (21, 24)]  # Before 10 AM, after 9 PM (weekdays)
        },
        'germany_awattar': {
            'peak': (8, 20),       # 8 AM - 8 PM (weekdays)
            'mid-peak': (6, 8),    # 6 AM - 8 AM (weekdays)
            'off-peak': [(0, 6), (20, 24)]  # Before 6 AM, after 8 PM (weekdays)
        },
        'fixed_rate': {
            # Fixed rate has no TOU periods - all off-peak
            'peak': None,
            'mid-peak': None,
            'off-peak': [(0, 24)]
        }
    }
    
    def __init__(self):
        """Initialize electricity pricing generator (NUC-optimized, no heavy initialization)."""
        logger.debug("SyntheticElectricityPricingGenerator initialized")
    
    def _get_pricing_region(
        self,
        home: dict[str, Any],
        location: dict[str, Any] | None = None
    ) -> str:
        """
        Determine pricing region from home location.
        
        Uses simple heuristic based on location metadata or defaults to 'fixed_rate'.
        
        Args:
            home: Home dictionary with metadata
            location: Optional location dict
        
        Returns:
            Pricing region identifier (germany_awattar, california_tou, fixed_rate)
        """
        # Try to get region from location parameter
        if location:
            country = location.get('country', '').lower()
            state = location.get('state', '').lower()
            
            if 'germany' in country:
                return 'germany_awattar'
            elif 'california' in state or 'ca' in state:
                return 'california_tou'
        
        # Try to get region from home metadata
        if home.get('metadata', {}).get('pricing_region'):
            region = home['metadata']['pricing_region'].lower()
            if region in self.PRICING_REGIONS:
                return region
        
        # Default to fixed_rate for simplicity
        return 'fixed_rate'
    
    def _calculate_time_of_use_tier(
        self,
        pricing_region: str,
        timestamp: datetime
    ) -> str:
        """
        Calculate time-of-use tier for a given timestamp and region.
        
        Args:
            pricing_region: Pricing region identifier
            timestamp: Timestamp for tier calculation
        
        Returns:
            Pricing tier string (peak, mid-peak, off-peak)
        """
        # Fixed rate regions have no TOU
        if pricing_region == 'fixed_rate':
            return 'off-peak'
        
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = timestamp.weekday()
        is_weekend = day_of_week >= 5  # Saturday or Sunday
        
        # Weekends are typically off-peak for TOU regions
        if is_weekend:
            return 'off-peak'
        
        # Get hour of day
        hour = timestamp.hour
        
        # Get TOU periods for this region
        tou_periods = self.TOU_PERIODS.get(pricing_region, {})
        
        # Check peak period
        peak_period = tou_periods.get('peak')
        if peak_period:
            peak_start, peak_end = peak_period
            if peak_start <= hour < peak_end:
                return 'peak'
        
        # Check mid-peak period
        mid_peak_period = tou_periods.get('mid-peak')
        if mid_peak_period:
            mid_start, mid_end = mid_peak_period
            if mid_start <= hour < mid_end:
                return 'mid-peak'
        
        # Check off-peak periods (list of tuples)
        off_peak_periods = tou_periods.get('off-peak', [])
        for off_start, off_end in off_peak_periods:
            if off_start <= hour < off_end:
                return 'off-peak'
        
        # Default to off-peak if no match
        return 'off-peak'
    
    def _calculate_demand_factor(
        self,
        timestamp: datetime
    ) -> float:
        """
        Calculate demand-based price factor based on time of day.
        
        Higher demand during peak hours (mornings 6-9 AM, evenings 5-9 PM).
        
        Args:
            timestamp: Timestamp for demand calculation
        
        Returns:
            Demand factor multiplier (0.9-1.2)
        """
        hour = timestamp.hour
        
        # High demand periods
        if hour in [6, 7, 8, 17, 18, 19, 20]:  # Morning rush + evening peak
            return random.uniform(1.10, 1.20)  # +10% to +20%
        # Medium demand periods
        elif hour in [9, 10, 15, 16, 21]:  # Just after peaks
            return random.uniform(1.0, 1.10)  # +0% to +10%
        # Low demand periods (night)
        else:
            return random.uniform(0.9, 1.0)  # -10% to 0%
    
    def _generate_forecast(
        self,
        pricing_region: str,
        timestamp: datetime,
        base_price: float
    ) -> list[float]:
        """
        Generate 24-hour price forecast starting from timestamp.
        
        Args:
            pricing_region: Pricing region identifier
            timestamp: Starting timestamp for forecast
            base_price: Current price as baseline
        
        Returns:
            List of 24 forecast prices (one per hour)
        """
        forecast = []
        current_ts = timestamp
        
        for hour_offset in range(24):
            forecast_ts = current_ts + timedelta(hours=hour_offset)
            
            # Calculate forecast price using same logic as main price generation
            pricing_tier = self._calculate_time_of_use_tier(pricing_region, forecast_ts)
            demand_factor = self._calculate_demand_factor(forecast_ts)
            
            # Get baseline and TOU multiplier
            region_config = self.PRICING_REGIONS[pricing_region]
            baseline_price = region_config['baseline']
            tou_multiplier = self.TOU_MULTIPLIERS.get(pricing_tier, 1.0)
            
            # Calculate forecast price
            forecast_price = baseline_price * tou_multiplier * demand_factor
            
            # Add random variation (±5% for forecast - less uncertainty than current)
            random_variation = random.uniform(-0.05, 0.05)
            forecast_price = forecast_price * (1.0 + random_variation)
            
            # Ensure within range
            price_min, price_max = region_config['price_range']
            forecast_price = max(price_min, min(price_max, forecast_price))
            
            forecast.append(round(forecast_price, 4))
        
        return forecast
    
    def _generate_basic_price(
        self,
        pricing_region: str,
        timestamp: datetime
    ) -> float:
        """
        Generate basic price for a given timestamp and region.
        
        Includes TOU multiplier, demand-based variation, and random variation.
        
        Args:
            pricing_region: Pricing region identifier
            timestamp: Timestamp for price calculation
        
        Returns:
            Price per kWh (float)
        """
        region_config = self.PRICING_REGIONS[pricing_region]
        baseline_price = region_config['baseline']
        price_min, price_max = region_config['price_range']
        
        # Calculate TOU tier
        pricing_tier = self._calculate_time_of_use_tier(pricing_region, timestamp)
        
        # Apply TOU multiplier
        tou_multiplier = self.TOU_MULTIPLIERS.get(pricing_tier, 1.0)
        price = baseline_price * tou_multiplier
        
        # Apply demand-based variation
        demand_factor = self._calculate_demand_factor(timestamp)
        price = price * demand_factor
        
        # Add random variation (±10% as per Story 34.3)
        random_variation = random.uniform(-0.10, 0.10)
        price = price * (1.0 + random_variation)
        
        # Ensure price stays within realistic range
        price = max(price_min, min(price_max, price))
        
        return round(price, 4)
    
    def generate_pricing(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int,
        location: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate electricity pricing data for a synthetic home.
        
        Generates hourly pricing data points for the specified number of days.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date/time for pricing data
            days: Number of days to generate
            location: Optional location dictionary
        
        Returns:
            List of pricing data point dictionaries (compatible with PricingDataPoint model)
        """
        # Determine pricing region
        pricing_region = self._get_pricing_region(home, location)
        logger.debug(f"Generating pricing data for region: {pricing_region}")
        
        # Generate pricing data
        pricing_data = []
        current_date = start_date.replace(minute=0, second=0, microsecond=0)
        
        for day in range(days):
            for hour in range(24):
                # Calculate timestamp (hourly intervals)
                timestamp = current_date + timedelta(days=day, hours=hour)
                timestamp_str = timestamp.isoformat()
                
                # Calculate TOU tier
                pricing_tier = self._calculate_time_of_use_tier(pricing_region, timestamp)
                
                # Generate price with TOU multiplier, demand factor, and random variation
                price = self._generate_basic_price(pricing_region, timestamp)
                
                # Generate 24-hour forecast
                forecast = self._generate_forecast(pricing_region, timestamp, price)
                
                # Create pricing data point
                pricing_point = {
                    'timestamp': timestamp_str,
                    'price_per_kwh': price,
                    'pricing_tier': pricing_tier,
                    'region': pricing_region,
                    'forecast': forecast
                }
                
                pricing_data.append(pricing_point)
        
        logger.debug(f"Generated {len(pricing_data)} pricing data points")
        return pricing_data
    
    def correlate_with_energy_devices(
        self,
        pricing_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None,
        pricing_region: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Correlate electricity pricing data with high-energy device events.
        
        Rules:
        - EV charging prefers off-peak periods (lowest prices)
        - HVAC scheduling prefers off-peak for energy-intensive operations
        - High-energy devices (water heater, pool pump) adjust based on pricing
        - Only adjusts events when beneficial (respects existing events)
        
        Args:
            pricing_data: List of pricing data points (hourly)
            device_events: List of existing device events
            devices: Optional list of devices (to identify energy devices)
            pricing_region: Optional pricing region (auto-detected if not provided)
        
        Returns:
            List of correlated/adjusted device events
        """
        # Determine pricing region from pricing data if not provided
        if not pricing_region and pricing_data:
            pricing_region = pricing_data[0].get('region', 'fixed_rate')
        
        # Find high-energy devices
        energy_devices = []
        ev_devices = []
        hvac_devices = []
        
        if devices:
            for device in devices:
                device_type = device.get('device_type', '')
                device_class = device.get('device_class', '')
                entity_id = device.get('entity_id', '')
                
                # EV devices
                if device_type == 'sensor' and 'battery' in device_class.lower():
                    ev_devices.append(device)
                elif 'ev' in device_type.lower() or 'electric_vehicle' in device_type.lower():
                    ev_devices.append(device)
                elif 'ev' in entity_id.lower() or 'vehicle' in entity_id.lower():
                    ev_devices.append(device)
                
                # HVAC devices
                if device_type == 'climate':
                    hvac_devices.append(device)
                elif device_class in ('thermostat', 'temperature') and device_type == 'sensor':
                    hvac_devices.append(device)
                
                # Other high-energy devices
                if device_type == 'water_heater':
                    energy_devices.append(device)
                elif device_type == 'switch' and device_class and 'energy' in device_class.lower():
                    energy_devices.append(device)
        
        # Create maps for quick lookup
        pricing_by_timestamp = {p['timestamp']: p for p in pricing_data}
        
        # Group events by entity_id
        events_by_entity: dict[str, list[dict[str, Any]]] = {}
        for event in device_events:
            entity_id = event.get('entity_id', '')
            if entity_id not in events_by_entity:
                events_by_entity[entity_id] = []
            events_by_entity[entity_id].append(event)
        
        correlated_events = []
        
        # Correlate EV charging
        ev_entity_ids = {d.get('entity_id') for d in ev_devices if d.get('entity_id')}
        ev_events = self._correlate_ev_charging(
            pricing_data,
            device_events,
            ev_entity_ids,
            events_by_entity,
            pricing_region
        )
        correlated_events.extend(ev_events)
        
        # Correlate HVAC
        hvac_entity_ids = {d.get('entity_id') for d in hvac_devices if d.get('entity_id')}
        hvac_events = self._correlate_hvac_pricing(
            pricing_data,
            device_events,
            hvac_entity_ids,
            events_by_entity,
            pricing_region
        )
        correlated_events.extend(hvac_events)
        
        # Correlate other high-energy devices
        energy_entity_ids = {d.get('entity_id') for d in energy_devices if d.get('entity_id')}
        energy_events = self._correlate_high_energy_devices(
            pricing_data,
            device_events,
            energy_entity_ids,
            events_by_entity,
            pricing_region
        )
        correlated_events.extend(energy_events)
        
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
        
        logger.debug(f"Correlated {len(correlated_events)} events with pricing data")
        return correlated_events
    
    def _correlate_ev_charging(
        self,
        pricing_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        ev_entity_ids: set[str],
        events_by_entity: dict[str, list[dict[str, Any]]],
        pricing_region: str
    ) -> list[dict[str, Any]]:
        """
        Correlate EV charging with off-peak pricing periods.
        
        EV charging prefers:
        - Off-peak periods (lowest prices)
        - Night hours (midnight - 6 AM) typically off-peak
        - Avoids peak pricing periods
        """
        correlated_events = []
        
        # Find off-peak pricing periods (lowest prices)
        off_peak_periods = []
        for pricing_point in pricing_data:
            if pricing_point.get('pricing_tier') == 'off-peak':
                off_peak_periods.append((
                    pricing_point['timestamp'],
                    pricing_point['price_per_kwh']
                ))
        
        # Sort by price (lowest first)
        off_peak_periods.sort(key=lambda x: x[1])
        
        # Correlate EV charging events
        for entity_id, events in events_by_entity.items():
            if entity_id not in ev_entity_ids:
                continue
            
            # Find EV charging events (state contains 'charging' or 'on')
            for event in events:
                state = event.get('state', '').lower()
                if 'charging' not in state and 'on' not in state:
                    continue
                
                event_timestamp = event.get('timestamp', '')
                event_dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                
                # Find nearest off-peak period
                best_period = None
                best_price = float('inf')
                
                for period_ts, period_price in off_peak_periods:
                    period_dt = datetime.fromisoformat(period_ts.replace('Z', '+00:00'))
                    time_diff = abs((event_dt - period_dt).total_seconds())
                    
                    # Consider periods within 6 hours (reasonable for EV charging)
                    if time_diff <= 6 * 3600 and period_price < best_price:
                        best_period = period_ts
                        best_price = period_price
                
                # Adjust event if beneficial off-peak period found
                if best_period:
                    adjusted_event = event.copy()
                    adjusted_event['timestamp'] = best_period
                    adjusted_event['pricing_optimized'] = True
                    adjusted_event['original_timestamp'] = event_timestamp
                    correlated_events.append(adjusted_event)
                else:
                    # Keep original event if no better option
                    correlated_events.append(event)
        
        return correlated_events
    
    def _correlate_hvac_pricing(
        self,
        pricing_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        hvac_entity_ids: set[str],
        events_by_entity: dict[str, list[dict[str, Any]]],
        pricing_region: str
    ) -> list[dict[str, Any]]:
        """
        Correlate HVAC scheduling with pricing periods.
        
        HVAC prefers:
        - Off-peak for pre-cooling/pre-heating
        - Avoids peak pricing when possible
        - Only adjusts non-critical operations (comfort settings)
        """
        correlated_events = []
        
        # Find off-peak periods
        off_peak_by_timestamp = {
            p['timestamp']: p['price_per_kwh']
            for p in pricing_data
            if p.get('pricing_tier') == 'off-peak'
        }
        
        # Correlate HVAC events
        for entity_id, events in events_by_entity.items():
            if entity_id not in hvac_entity_ids:
                continue
            
            for event in events:
                event_timestamp = event.get('timestamp', '')
                event_dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                
                # For HVAC, prefer off-peak for scheduling operations
                # Look for off-peak periods within 2 hours before or after
                best_period = None
                best_price = float('inf')
                
                for period_ts, period_price in off_peak_by_timestamp.items():
                    period_dt = datetime.fromisoformat(period_ts.replace('Z', '+00:00'))
                    time_diff = abs((event_dt - period_dt).total_seconds())
                    
                    # Consider periods within 2 hours for HVAC scheduling
                    if time_diff <= 2 * 3600 and period_price < best_price:
                        # Prefer periods before the event (pre-cooling/pre-heating)
                        if period_dt < event_dt:
                            best_period = period_ts
                            best_price = period_price
                
                # Adjust event if beneficial (only for non-peak events)
                current_tier = None
                for p in pricing_data:
                    if p['timestamp'] == event_timestamp:
                        current_tier = p.get('pricing_tier')
                        break
                
                # Only adjust if currently in peak/mid-peak and better option exists
                if best_period and current_tier in ('peak', 'mid-peak'):
                    adjusted_event = event.copy()
                    adjusted_event['timestamp'] = best_period
                    adjusted_event['pricing_optimized'] = True
                    adjusted_event['original_timestamp'] = event_timestamp
                    correlated_events.append(adjusted_event)
                else:
                    # Keep original event
                    correlated_events.append(event)
        
        return correlated_events
    
    def _correlate_high_energy_devices(
        self,
        pricing_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        energy_entity_ids: set[str],
        events_by_entity: dict[str, list[dict[str, Any]]],
        pricing_region: str
    ) -> list[dict[str, Any]]:
        """
        Correlate high-energy devices (water heater, pool pump, etc.) with pricing.
        
        High-energy devices prefer:
        - Off-peak periods
        - Can shift operations within reasonable time windows
        """
        correlated_events = []
        
        # Find off-peak periods
        off_peak_by_timestamp = {
            p['timestamp']: p['price_per_kwh']
            for p in pricing_data
            if p.get('pricing_tier') == 'off-peak'
        }
        
        # Correlate high-energy device events
        for entity_id, events in events_by_entity.items():
            if entity_id not in energy_entity_ids:
                continue
            
            for event in events:
                event_timestamp = event.get('timestamp', '')
                event_dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                
                # Find best off-peak period within 4 hours
                best_period = None
                best_price = float('inf')
                
                for period_ts, period_price in off_peak_by_timestamp.items():
                    period_dt = datetime.fromisoformat(period_ts.replace('Z', '+00:00'))
                    time_diff = abs((event_dt - period_dt).total_seconds())
                    
                    if time_diff <= 4 * 3600 and period_price < best_price:
                        best_period = period_ts
                        best_price = period_price
                
                # Adjust event if beneficial
                current_price = None
                for p in pricing_data:
                    if p['timestamp'] == event_timestamp:
                        current_price = p.get('price_per_kwh')
                        break
                
                if best_period and current_price and best_price < current_price:
                    adjusted_event = event.copy()
                    adjusted_event['timestamp'] = best_period
                    adjusted_event['pricing_optimized'] = True
                    adjusted_event['original_timestamp'] = event_timestamp
                    correlated_events.append(adjusted_event)
                else:
                    correlated_events.append(event)
        
        return correlated_events

