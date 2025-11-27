"""
Synthetic Carbon Intensity Generator

Generate realistic carbon intensity data for synthetic homes based on grid region profiles.
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


class CarbonIntensityDataPoint(BaseModel):
    """Pydantic model for carbon intensity data point (2025 best practice)."""
    
    timestamp: str
    intensity: float  # gCO2/kWh
    renewable_percentage: float | None = None
    forecast: list[float] | None = None


class SyntheticCarbonIntensityGenerator:
    """
    Generate realistic carbon intensity data for synthetic homes.
    
    NUC-Optimized: Uses in-memory dictionaries, no external API calls.
    Performance target: <50ms per home for basic generation.
    """
    
    # Grid region profiles with baseline carbon intensity and renewable capacity
    GRID_REGIONS: dict[str, dict[str, Any]] = {
        'california': {
            'baseline': 250,  # gCO2/kWh
            'renewable_capacity': 0.4,  # 40% renewable
            'intensity_range': (150, 400),
            'solar_capacity': 0.3
        },
        'texas': {
            'baseline': 400,
            'renewable_capacity': 0.25,  # 25% renewable
            'intensity_range': (300, 550),
            'solar_capacity': 0.15
        },
        'germany': {
            'baseline': 350,
            'renewable_capacity': 0.5,  # 50% renewable
            'intensity_range': (200, 500),
            'solar_capacity': 0.2
        },
        'coal_heavy': {
            'baseline': 600,
            'renewable_capacity': 0.1,  # 10% renewable
            'intensity_range': (500, 700),
            'solar_capacity': 0.05
        }
    }
    
    def __init__(self):
        """Initialize carbon intensity generator (NUC-optimized, no heavy initialization)."""
        logger.debug("SyntheticCarbonIntensityGenerator initialized")
    
    def _get_grid_region(
        self,
        home: dict[str, Any],
        location: dict[str, Any] | None = None
    ) -> str:
        """
        Determine grid region from home location.
        
        Uses simple heuristic based on location metadata or defaults to 'california'.
        
        Args:
            home: Home dictionary with metadata
            location: Optional location dict
        
        Returns:
            Grid region identifier (california, texas, germany, coal_heavy)
        """
        # Try to get region from location parameter
        if location and 'region' in location:
            region = location['region'].lower()
            if region in self.GRID_REGIONS:
                return region
        
        # Try to get region from home metadata
        if home.get('metadata', {}).get('grid_region'):
            region = home['metadata']['grid_region'].lower()
            if region in self.GRID_REGIONS:
                return region
        
        # Try to infer from country/state if available
        if location:
            country = location.get('country', '').lower()
            if 'germany' in country or 'de' in country:
                return 'germany'
            state = location.get('state', '').lower()
            if 'texas' in state or 'tx' in state:
                return 'texas'
            if 'california' in state or 'ca' in state:
                return 'california'
        
        # Default fallback to california (cleaner grid)
        logger.debug(f"No grid region data found for home, defaulting to california")
        return 'california'
    
    def _get_season(self, date: datetime) -> str:
        """
        Determine season from date.
        
        Args:
            date: Date to determine season for
        
        Returns:
            Season string: 'winter', 'spring', 'summer', 'fall'
        """
        month = date.month
        # Northern hemisphere seasons
        if month in (12, 1, 2):
            return 'winter'
        elif month in (3, 4, 5):
            return 'spring'
        elif month in (6, 7, 8):
            return 'summer'
        else:  # 9, 10, 11
            return 'fall'
    
    def _calculate_seasonal_solar(
        self,
        season: str,
        grid_region: str
    ) -> float:
        """
        Calculate seasonal solar factor.
        
        Summer: 50-70% reduction (more solar generation)
        Winter: 20-30% reduction (less solar generation)
        Spring/Fall: Intermediate values
        
        Args:
            season: Season string
            grid_region: Grid region identifier
        
        Returns:
            Multiplier factor (0.3-0.8) for seasonal solar impact
        """
        region_config = self.GRID_REGIONS[grid_region]
        solar_capacity = region_config.get('solar_capacity', 0.2)
        
        # Seasonal solar reduction factors
        # Summer has strongest solar impact (more reduction = lower factor)
        # Winter has weakest solar impact (less reduction = higher factor)
        seasonal_reduction_potential = {
            'summer': 0.6,   # 60% reduction potential (strongest)
            'spring': 0.4,   # 40% reduction potential
            'fall': 0.4,     # 40% reduction potential
            'winter': 0.25   # 25% reduction potential (weakest)
        }
        
        reduction_potential = seasonal_reduction_potential.get(season, 0.4)
        
        # Scale by solar capacity (regions with more solar get stronger seasonal effect)
        # California (0.3 solar) gets full effect, coal_heavy (0.05 solar) gets minimal
        solar_scale = min(1.0, solar_capacity / 0.2)  # Normalize to 0.2 baseline
        
        # Calculate reduction amount and apply to get final factor
        # Summer: 0.6 * 1.0 * 0.5 = 0.3 reduction → factor = 0.7
        # Winter: 0.25 * 1.0 * 0.5 = 0.125 reduction → factor = 0.875
        reduction_amount = reduction_potential * solar_scale * 0.5
        seasonal_factor = 1.0 - reduction_amount
        
        return max(0.3, min(0.8, seasonal_factor))
    
    def _calculate_renewable_percentage(
        self,
        intensity: float,
        grid_region: str,
        season: str,
        hour: float
    ) -> float:
        """
        Calculate renewable percentage based on grid region, season, and time.
        
        Higher renewable percentage when:
        - Grid has more renewable capacity
        - Summer season (more solar)
        - Daytime hours (solar generation)
        
        Args:
            intensity: Current carbon intensity (gCO2/kWh)
            grid_region: Grid region identifier
            season: Season string
            hour: Hour of day (0-23)
        
        Returns:
            Renewable percentage (0-100)
        """
        region_config = self.GRID_REGIONS[grid_region]
        base_renewable = region_config.get('renewable_capacity', 0.2)
        solar_capacity = region_config.get('solar_capacity', 0.2)
        
        # Base renewable percentage from grid region
        renewable_pct = base_renewable * 100
        
        # Seasonal adjustment (summer has more solar)
        seasonal_adjustments = {
            'summer': 20,   # +20% in summer
            'spring': 10,   # +10% in spring
            'fall': 10,     # +10% in fall
            'winter': 0     # No adjustment in winter
        }
        renewable_pct += seasonal_adjustments.get(season, 0)
        
        # Time-of-day adjustment (solar during day)
        hour_normalized = hour % 24
        if 10 <= hour_normalized <= 15:
            # Solar peak hours: additional renewable from solar
            solar_contribution = solar_capacity * 30  # Up to 30% from solar
            renewable_pct += solar_contribution
        elif 6 <= hour_normalized <= 9 or 16 <= hour_normalized <= 19:
            # Morning/evening: partial solar
            solar_contribution = solar_capacity * 15  # Up to 15% from solar
            renewable_pct += solar_contribution
        
        # Cap at 100%
        renewable_pct = min(100.0, renewable_pct)
        
        # Ensure minimum based on grid region (even at worst times)
        min_renewable = base_renewable * 50  # At least 50% of base capacity
        renewable_pct = max(min_renewable, renewable_pct)
        
        return round(renewable_pct, 1)
    
    def _generate_forecast(
        self,
        current_intensity: float,
        grid_region: str,
        season: str,
        hour: float
    ) -> list[float]:
        """
        Generate 24-hour forecast (96 values for 15-minute intervals).
        
        Forecast should be realistic and consistent with current patterns.
        
        Args:
            current_intensity: Current carbon intensity
            grid_region: Grid region identifier
            season: Season string
            hour: Current hour of day
        
        Returns:
            List of 96 forecast values (24 hours * 4 quarters)
        """
        forecast = []
        region_config = self.GRID_REGIONS[grid_region]
        intensity_min, intensity_max = region_config['intensity_range']
        
        # Generate forecast starting from current hour
        for i in range(96):  # 24 hours * 4 quarters
            forecast_hour = (hour + (i * 0.25)) % 24
            
            # Calculate expected intensity for this forecast hour
            baseline = (intensity_min + intensity_max) / 2.0
            time_factor = self._calculate_time_of_day_factor(forecast_hour, grid_region)
            seasonal_factor = self._calculate_seasonal_solar(season, grid_region)
            
            # Apply both time-of-day and seasonal factors
            forecast_intensity = baseline * time_factor * seasonal_factor
            
            # Add some variation (±5% for forecast uncertainty)
            variation = random.uniform(-0.05, 0.05)
            forecast_intensity = forecast_intensity * (1.0 + variation)
            
            # Ensure within bounds
            forecast_intensity = max(intensity_min, min(intensity_max, forecast_intensity))
            forecast.append(round(forecast_intensity, 1))
        
        return forecast
    
    def _calculate_time_of_day_factor(
        self,
        hour: float,
        grid_region: str
    ) -> float:
        """
        Calculate time-of-day factor for carbon intensity.
        
        Patterns:
        - Solar peak (10 AM - 3 PM): Lower carbon intensity (solar generation)
        - Evening peak (6 PM - 9 PM): Higher carbon intensity (demand spike)
        - Night (midnight - 6 AM): Moderate carbon intensity (lower demand)
        
        Args:
            hour: Hour of day (0-23, can include fractional hours for 15-min intervals)
            grid_region: Grid region identifier
        
        Returns:
            Multiplier factor (0.7-1.3) to apply to baseline intensity
        """
        region_config = self.GRID_REGIONS[grid_region]
        solar_capacity = region_config.get('solar_capacity', 0.2)
        
        # Normalize hour to 0-24 range
        hour_normalized = hour % 24
        
        # Solar peak: 10 AM - 3 PM (10-15 hours)
        # Solar generation reduces carbon intensity
        if 10 <= hour_normalized <= 15:
            # Peak solar at noon (12:00), gradual transitions
            if hour_normalized <= 12:
                # Morning ramp-up (10 AM to noon)
                solar_factor = (hour_normalized - 10) / 2.0  # 0.0 to 1.0
            else:
                # Afternoon ramp-down (noon to 3 PM)
                solar_factor = 1.0 - ((hour_normalized - 12) / 3.0)  # 1.0 to 0.0
            
            # Apply solar reduction (stronger in regions with more solar capacity)
            solar_reduction = solar_capacity * solar_factor * 0.3  # Up to 30% reduction
            return 1.0 - solar_reduction
        
        # Evening peak: 6 PM - 9 PM (18-21 hours)
        # Increased demand, less solar, higher carbon intensity
        elif 18 <= hour_normalized <= 21:
            # Peak demand at 7:30 PM (19.5 hours)
            if hour_normalized <= 19.5:
                # Ramp-up (6 PM to 7:30 PM)
                peak_factor = (hour_normalized - 18) / 1.5  # 0.0 to 1.0
            else:
                # Ramp-down (7:30 PM to 9 PM)
                peak_factor = 1.0 - ((hour_normalized - 19.5) / 1.5)  # 1.0 to 0.0
            
            # Apply evening peak increase (15-25% increase)
            peak_increase = 0.15 + (peak_factor * 0.1)  # 15% to 25%
            return 1.0 + peak_increase
        
        # Night hours (midnight - 6 AM): Lower demand, moderate carbon
        elif hour_normalized < 6:
            return 0.9  # 10% reduction due to lower demand
        
        # Other hours: Baseline
        else:
            return 1.0
    
    def generate_carbon_intensity(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int,
        location: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate basic carbon intensity data for a home.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date for carbon intensity generation
            days: Number of days to generate
            location: Optional location data
        
        Returns:
            List of carbon intensity data dictionaries (15-minute intervals)
        """
        # Get grid region for this home
        grid_region = self._get_grid_region(home, location)
        region_config = self.GRID_REGIONS[grid_region]
        
        # Generate 15-minute interval carbon intensity data
        carbon_data = []
        current_date = start_date.replace(minute=0, second=0, microsecond=0)
        
        for day in range(days):
            for hour in range(24):
                for quarter in range(4):  # 4 quarters per hour (15-minute intervals)
                    # Calculate timestamp (15-minute intervals)
                    minutes = quarter * 15
                    timestamp = current_date + timedelta(days=day, hours=hour, minutes=minutes)
                    timestamp_str = timestamp.isoformat()
                    
                    # Calculate hour with quarter-hour precision
                    hour_with_quarter = hour + (quarter * 0.25)
                    
                    # Get season for this date
                    season = self._get_season(timestamp)
                    
                    # Get baseline intensity (midpoint of range)
                    intensity_min, intensity_max = region_config['intensity_range']
                    baseline_intensity = (intensity_min + intensity_max) / 2.0
                    
                    # Apply time-of-day factor
                    time_factor = self._calculate_time_of_day_factor(hour_with_quarter, grid_region)
                    
                    # Apply seasonal solar factor
                    seasonal_factor = self._calculate_seasonal_solar(season, grid_region)
                    
                    # Combine factors
                    intensity = baseline_intensity * time_factor * seasonal_factor
                    
                    # Add random variation (±10%)
                    random_variation = random.uniform(-0.1, 0.1)
                    intensity = intensity * (1.0 + random_variation)
                    
                    # Ensure intensity stays within region bounds
                    intensity = max(intensity_min, min(intensity_max, intensity))
                    
                    # Calculate renewable percentage
                    renewable_pct = self._calculate_renewable_percentage(
                        intensity,
                        grid_region,
                        season,
                        hour_with_quarter
                    )
                    
                    # Generate 24-hour forecast
                    forecast = self._generate_forecast(
                        intensity,
                        grid_region,
                        season,
                        hour_with_quarter
                    )
                    
                    # Create carbon intensity data point
                    carbon_point = {
                        'timestamp': timestamp_str,
                        'intensity': round(intensity, 1),
                        'renewable_percentage': renewable_pct,
                        'forecast': forecast
                    }
                    
                    carbon_data.append(carbon_point)
        
        logger.debug(f"Generated {len(carbon_data)} carbon intensity data points for {grid_region} grid")
        return carbon_data
    
    def correlate_with_energy_devices(
        self,
        carbon_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Correlate carbon intensity data with high-energy device events.
        
        Rules:
        - EV charging prefers low-carbon periods (solar peak, night)
        - HVAC usage correlates with carbon intensity (prefer low-carbon times)
        - High-energy devices (EV, HVAC, water heater) adjust based on carbon
        
        Args:
            carbon_data: List of carbon intensity data points (15-minute intervals)
            device_events: List of existing device events
            devices: Optional list of devices (to identify energy devices)
        
        Returns:
            List of correlated/adjusted device events
        """
        # Find high-energy devices
        energy_devices = []
        ev_devices = []
        hvac_devices = []
        
        if devices:
            for device in devices:
                device_type = device.get('device_type', '')
                device_class = device.get('device_class', '')
                
                # EV devices
                if device_type == 'sensor' and 'battery' in device_class.lower():
                    ev_devices.append(device)
                elif 'ev' in device_type.lower() or 'electric_vehicle' in device_type.lower():
                    ev_devices.append(device)
                
                # HVAC devices
                if device_type == 'climate' or device_class in ('thermostat', 'temperature'):
                    hvac_devices.append(device)
                
                # Other high-energy devices (water heater, pool pump, etc.)
                if device_type in ('water_heater', 'switch') and device_class and 'energy' in device_class.lower():
                    energy_devices.append(device)
        
        # Create maps for quick lookup
        carbon_by_timestamp = {c['timestamp']: c for c in carbon_data}
        events_by_entity = {}
        for event in device_events:
            entity_id = event.get('entity_id', '')
            if entity_id not in events_by_entity:
                events_by_entity[entity_id] = []
            events_by_entity[entity_id].append(event)
        
        correlated_events = []
        
        # Correlate EV charging
        ev_events = self._correlate_ev_charging(
            carbon_data,
            device_events,
            ev_devices,
            events_by_entity
        )
        correlated_events.extend(ev_events)
        
        # Correlate HVAC
        hvac_events = self._correlate_hvac_carbon(
            carbon_data,
            device_events,
            hvac_devices,
            events_by_entity
        )
        correlated_events.extend(hvac_events)
        
        # Correlate other high-energy devices
        energy_events = self._correlate_high_energy_devices(
            carbon_data,
            device_events,
            energy_devices,
            events_by_entity
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
        
        logger.debug(f"Correlated {len(correlated_events)} events with carbon intensity data")
        return correlated_events
    
    def _correlate_ev_charging(
        self,
        carbon_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        ev_devices: list[dict[str, Any]],
        events_by_entity: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """
        Correlate EV charging with low-carbon periods.
        
        EV charging prefers:
        - Solar peak hours (10 AM - 3 PM) - low carbon
        - Night hours (midnight - 6 AM) - lower demand, often lower carbon
        - Avoids evening peak (6 PM - 9 PM) - high carbon
        """
        correlated_events = []
        ev_entity_ids = {d.get('entity_id') for d in ev_devices if d.get('entity_id')}
        
        # Find low-carbon periods (solar peak and night)
        low_carbon_periods = []
        for carbon_point in carbon_data:
            timestamp = carbon_point['timestamp']
            intensity = carbon_point['intensity']
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = dt.hour
            
            # Solar peak (10 AM - 3 PM) or night (midnight - 6 AM)
            is_low_carbon = (10 <= hour <= 15) or (hour < 6)
            
            if is_low_carbon:
                low_carbon_periods.append((timestamp, intensity))
        
        # Sort by carbon intensity (lowest first)
        low_carbon_periods.sort(key=lambda x: x[1])
        
        # Correlate EV charging events with low-carbon periods
        for entity_id, events in events_by_entity.items():
            if entity_id not in ev_entity_ids:
                continue
            
            # Find EV charging events
            for event in events:
                if 'charging' not in event.get('state', '').lower() and 'on' not in event.get('state', '').lower():
                    continue
                
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                
                # Find nearest low-carbon period
                best_period = None
                min_time_diff = float('inf')
                
                for period_timestamp, period_intensity in low_carbon_periods:
                    period_time = datetime.fromisoformat(period_timestamp.replace('Z', '+00:00'))
                    time_diff = abs((event_time - period_time).total_seconds())
                    
                    # Prefer periods within 4 hours
                    if time_diff < min_time_diff and time_diff < 14400:  # 4 hours
                        min_time_diff = time_diff
                        best_period = (period_timestamp, period_intensity)
                
                if best_period and min_time_diff < 14400:
                    # Adjust event to low-carbon period
                    adjusted_event = event.copy()
                    adjusted_event['timestamp'] = best_period[0]
                    adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                    adjusted_event['attributes']['carbon_intensity'] = best_period[1]
                    adjusted_event['attributes']['carbon_optimized'] = True
                    correlated_events.append(adjusted_event)
        
        return correlated_events
    
    def _correlate_hvac_carbon(
        self,
        carbon_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        hvac_devices: list[dict[str, Any]],
        events_by_entity: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """
        Correlate HVAC usage with carbon intensity.
        
        HVAC should prefer low-carbon periods when possible:
        - Pre-cool/pre-heat during low-carbon periods
        - Reduce usage during high-carbon periods (evening peak)
        """
        correlated_events = []
        hvac_entity_ids = {d.get('entity_id') for d in hvac_devices if d.get('entity_id')}
        
        # Create carbon intensity map
        carbon_by_timestamp = {c['timestamp']: c for c in carbon_data}
        
        # Process HVAC events
        for entity_id, events in events_by_entity.items():
            if entity_id not in hvac_entity_ids:
                continue
            
            for event in events:
                event_timestamp = event['timestamp']
                
                # Find nearest carbon data point
                event_time = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                closest_carbon = None
                min_time_diff = float('inf')
                
                for carbon_point in carbon_data:
                    carbon_time = datetime.fromisoformat(carbon_point['timestamp'].replace('Z', '+00:00'))
                    time_diff = abs((event_time - carbon_time).total_seconds())
                    
                    if time_diff < min_time_diff and time_diff < 3600:  # Within 1 hour
                        min_time_diff = time_diff
                        closest_carbon = carbon_point
                
                if closest_carbon:
                    intensity = closest_carbon['intensity']
                    renewable_pct = closest_carbon.get('renewable_percentage', 0)
                    
                    # Add carbon context to HVAC event
                    adjusted_event = event.copy()
                    adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                    adjusted_event['attributes']['carbon_intensity'] = intensity
                    adjusted_event['attributes']['renewable_percentage'] = renewable_pct
                    adjusted_event['attributes']['carbon_correlated'] = True
                    
                    # If high carbon and HVAC is on, suggest reducing usage
                    if intensity > 400 and event.get('state') not in ('off', 'idle'):
                        adjusted_event['attributes']['carbon_optimization_suggestion'] = 'reduce_usage'
                    
                    correlated_events.append(adjusted_event)
        
        return correlated_events
    
    def _correlate_high_energy_devices(
        self,
        carbon_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        energy_devices: list[dict[str, Any]],
        events_by_entity: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """
        Correlate other high-energy devices (water heater, pool pump, etc.) with carbon intensity.
        
        High-energy devices should prefer low-carbon periods when possible.
        """
        correlated_events = []
        energy_entity_ids = {d.get('entity_id') for d in energy_devices if d.get('entity_id')}
        
        # Create carbon intensity map
        carbon_by_timestamp = {c['timestamp']: c for c in carbon_data}
        
        # Process energy device events
        for entity_id, events in events_by_entity.items():
            if entity_id not in energy_entity_ids:
                continue
            
            for event in events:
                event_timestamp = event['timestamp']
                
                # Find nearest carbon data point
                event_time = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                closest_carbon = None
                min_time_diff = float('inf')
                
                for carbon_point in carbon_data:
                    carbon_time = datetime.fromisoformat(carbon_point['timestamp'].replace('Z', '+00:00'))
                    time_diff = abs((event_time - carbon_time).total_seconds())
                    
                    if time_diff < min_time_diff and time_diff < 3600:  # Within 1 hour
                        min_time_diff = time_diff
                        closest_carbon = carbon_point
                
                if closest_carbon:
                    intensity = closest_carbon['intensity']
                    
                    # Add carbon context to energy device event
                    adjusted_event = event.copy()
                    adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                    adjusted_event['attributes']['carbon_intensity'] = intensity
                    adjusted_event['attributes']['carbon_correlated'] = True
                    
                    correlated_events.append(adjusted_event)
        
        return correlated_events

