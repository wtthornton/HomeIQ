"""
Multi-Source Contextual Fusion Detector

Combines data from all 6 enrichment services to create sophisticated,
multi-factor automation suggestions:

Data Sources:
1. Weather (temperature, humidity, condition)
2. Carbon Intensity (grid carbon, renewable %)
3. Electricity Pricing (current price, cheapest hours)
4. Air Quality (AQI, PM2.5, pollutants)
5. Calendar (occupancy, work-from-home)
6. Smart Meter (power consumption, phantom loads)

Epic: Multi-Source Contextual Fusion (#2)
Improvement: 2-3x more sophisticated automations, 25-40% cost savings
"""

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ..clients.data_enrichment_client import DataEnrichmentClient
from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class FusionDetector(MLPatternDetector):
    """
    Multi-source contextual fusion pattern detector.

    Creates sophisticated automation suggestions by combining:
    - Time patterns (existing)
    - Weather conditions
    - Energy optimization (carbon + pricing)
    - Air quality conditions
    - Occupancy patterns
    - Power consumption patterns
    """

    def __init__(
        self,
        enrichment_client: DataEnrichmentClient | None = None,
        min_fusion_confidence: float = 0.75,
        enable_energy_optimization: bool = True,
        enable_air_quality_triggers: bool = True,
        enable_occupancy_patterns: bool = True,
        **kwargs
    ):
        """
        Initialize fusion detector.

        Args:
            enrichment_client: DataEnrichmentClient for fetching enrichment data
            min_fusion_confidence: Minimum confidence for fusion patterns
            enable_energy_optimization: Enable energy-based suggestions
            enable_air_quality_triggers: Enable air quality-based suggestions
            enable_occupancy_patterns: Enable occupancy-based suggestions
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.enrichment_client = enrichment_client or DataEnrichmentClient()
        self.min_fusion_confidence = min_fusion_confidence
        self.enable_energy_optimization = enable_energy_optimization
        self.enable_air_quality_triggers = enable_air_quality_triggers
        self.enable_occupancy_patterns = enable_occupancy_patterns

        # Fusion pattern types
        self.fusion_types = [
            'ev_charging_optimization',     # EV charging with pricing + carbon + solar
            'hvac_air_quality',              # HVAC control with AQI + occupancy
            'energy_peak_shifting',          # Load shifting with pricing + carbon
            'phantom_load_detection',        # Smart meter phantom load → automation
            'occupancy_aware',               # Only when home/away
            'weather_comfort',               # Weather + occupancy → HVAC
            'carbon_aware_scheduling'        # Schedule high-energy tasks during clean energy
        ]

        logger.info(
            f"FusionDetector initialized: energy={enable_energy_optimization}, "
            f"air_quality={enable_air_quality_triggers}, occupancy={enable_occupancy_patterns}"
        )

    async def detect_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect fusion patterns combining multiple data sources.

        Args:
            events_df: Events DataFrame

        Returns:
            List of fusion pattern dictionaries
        """
        start_time = datetime.now(timezone.utc)

        if not self._validate_events_dataframe(events_df):
            return []

        # Fetch all enrichment data in parallel
        logger.info("📊 Fetching enrichment data from 6 services...")
        enrichment_data = await self.enrichment_client.get_all_enrichment_data()

        available_sources = [k for k, v in enrichment_data.items() if v is not None]
        logger.info(f"✅ Enrichment data available: {available_sources}")

        # Detect different fusion pattern types
        fusion_patterns = []

        # 1. EV Charging Optimization (pricing + carbon + solar/time)
        if self.enable_energy_optimization:
            ev_patterns = await self._detect_ev_charging_patterns(
                events_df, enrichment_data
            )
            fusion_patterns.extend(ev_patterns)

        # 2. HVAC + Air Quality Integration
        if self.enable_air_quality_triggers:
            hvac_air_patterns = await self._detect_hvac_air_quality_patterns(
                events_df, enrichment_data
            )
            fusion_patterns.extend(hvac_air_patterns)

        # 3. Energy Peak Shifting (dishwasher, laundry, etc.)
        if self.enable_energy_optimization:
            peak_shift_patterns = await self._detect_peak_shifting_patterns(
                events_df, enrichment_data
            )
            fusion_patterns.extend(peak_shift_patterns)

        # 4. Phantom Load Detection + Action
        phantom_patterns = await self._detect_phantom_load_patterns(
            events_df, enrichment_data
        )
        fusion_patterns.extend(phantom_patterns)

        # 5. Occupancy-Aware Automations
        if self.enable_occupancy_patterns:
            occupancy_patterns = await self._detect_occupancy_aware_patterns(
                events_df, enrichment_data
            )
            fusion_patterns.extend(occupancy_patterns)

        # 6. Weather Comfort Automation
        weather_comfort_patterns = await self._detect_weather_comfort_patterns(
            events_df, enrichment_data
        )
        fusion_patterns.extend(weather_comfort_patterns)

        # 7. Carbon-Aware Scheduling
        if self.enable_energy_optimization:
            carbon_patterns = await self._detect_carbon_aware_patterns(
                events_df, enrichment_data
            )
            fusion_patterns.extend(carbon_patterns)

        # Filter by confidence
        final_patterns = [
            p for p in fusion_patterns
            if p.get('confidence', 0) >= self.min_fusion_confidence
        ]

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ Detected {len(final_patterns)} fusion patterns in {duration:.2f}s "
            f"({len(fusion_patterns)} total, {len(final_patterns)} above confidence threshold)"
        )

        return final_patterns

    async def _detect_ev_charging_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect EV charging optimization opportunities.

        Multi-factor logic:
        - Charge when price < threshold AND carbon < threshold AND occupancy=home
        - Prioritize overnight + low carbon + low price windows
        """
        patterns = []

        # Find EV charger entities
        ev_entities = events_df[
            events_df['entity_id'].str.contains('ev|charger|charging', case=False, na=False)
        ]['entity_id'].unique()

        if len(ev_entities) == 0:
            return patterns

        pricing = enrichment_data.get('pricing')
        carbon = enrichment_data.get('carbon')
        calendar = enrichment_data.get('calendar')

        # Need at least pricing or carbon data
        if not pricing and not carbon:
            return patterns

        logger.info(f"🔌 Analyzing {len(ev_entities)} EV charging devices...")

        for ev_entity in ev_entities:
            # Calculate optimal charging windows
            optimal_conditions = []

            # Price condition
            if pricing and pricing.get('current_price'):
                price_threshold = pricing['current_price'] * 0.7  # 30% below current
                optimal_conditions.append(f"price < {price_threshold:.2f} {pricing.get('currency', 'EUR')}/kWh")

            # Carbon condition
            if carbon and carbon.get('carbon_intensity_gco2_kwh'):
                carbon_threshold = 300  # g CO2/kWh (clean energy threshold)
                optimal_conditions.append(f"carbon < {carbon_threshold}g CO2/kWh")

            # Occupancy condition
            if calendar and calendar.get('currently_home') is not None:
                optimal_conditions.append("when home")

            # Create pattern
            pattern = self._create_pattern_dict(
                pattern_type='fusion_ev_charging',
                pattern_id=self._generate_pattern_id('fusion_ev'),
                confidence=0.85,  # High confidence for energy optimization
                occurrences=1,  # Single suggestion
                devices=[ev_entity],
                metadata={
                    'fusion_type': 'ev_charging_optimization',
                    'data_sources': ['pricing', 'carbon', 'calendar'],
                    'conditions': optimal_conditions,
                    'priority': 'high',
                    'estimated_savings_percent': 30,
                    'recommendation': (
                        f"Charge EV {ev_entity} during optimal windows: "
                        f"{', '.join(optimal_conditions)}"
                    ),
                    'automation_template': {
                        'trigger': 'time_pattern',
                        'condition': [
                            'price_below_threshold' if pricing else None,
                            'carbon_below_threshold' if carbon else None,
                            'occupancy_home' if calendar else None
                        ],
                        'action': f"switch.turn_on {ev_entity}"
                    }
                }
            )

            patterns.append(pattern)

        return patterns

    async def _detect_hvac_air_quality_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect HVAC + Air Quality integration opportunities.

        Logic:
        - Close windows and turn on air purifier when AQI > 100 AND occupancy detected
        - Reduce HVAC when AQI is good AND windows open
        """
        patterns = []

        air_quality = enrichment_data.get('air_quality')
        calendar = enrichment_data.get('calendar')

        if not air_quality:
            return patterns

        # Find HVAC and window entities
        hvac_entities = events_df[
            events_df['entity_id'].str.contains('climate|hvac|thermostat', case=False, na=False)
        ]['entity_id'].unique()

        window_entities = events_df[
            events_df['entity_id'].str.contains('window', case=False, na=False)
        ]['entity_id'].unique()

        air_purifier_entities = events_df[
            events_df['entity_id'].str.contains('purifier|air_filter', case=False, na=False)
        ]['entity_id'].unique()

        if len(hvac_entities) == 0 and len(air_purifier_entities) == 0:
            return patterns

        aqi = air_quality.get('aqi', 0)
        category = air_quality.get('category', 'unknown')

        logger.info(f"🌫️ Current AQI: {aqi} ({category}), analyzing {len(hvac_entities)} HVAC devices...")

        # Pattern 1: Poor AQI → Close windows + Air purifier
        if aqi > 100 and len(window_entities) > 0 and len(air_purifier_entities) > 0:
            pattern = self._create_pattern_dict(
                pattern_type='fusion_hvac_air_quality',
                pattern_id=self._generate_pattern_id('fusion_hvac_aqi'),
                confidence=0.80,
                occurrences=1,
                devices=list(window_entities) + list(air_purifier_entities),
                metadata={
                    'fusion_type': 'hvac_air_quality',
                    'data_sources': ['air_quality', 'calendar'],
                    'current_aqi': aqi,
                    'current_category': category,
                    'priority': 'high' if aqi > 150 else 'medium',
                    'recommendation': (
                        "When AQI > 100, close windows and turn on air purifier"
                    ),
                    'automation_template': {
                        'trigger': 'numeric_state sensor.aqi above 100',
                        'condition': 'occupancy_home' if calendar else None,
                        'action': [
                            f"notify: Close windows, AQI is {category}",
                            f"turn_on: {air_purifier_entities[0] if len(air_purifier_entities) > 0 else 'air_purifier'}"
                        ]
                    }
                }
            )
            patterns.append(pattern)

        return patterns

    async def _detect_peak_shifting_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect energy peak shifting opportunities (dishwasher, laundry, etc.).

        Logic:
        - Delay high-energy appliances until [carbon low AND price low AND not peak]
        """
        patterns = []

        pricing = enrichment_data.get('pricing')
        carbon = enrichment_data.get('carbon')

        if not pricing and not carbon:
            return patterns

        # Find high-energy appliances
        appliance_keywords = ['dishwasher', 'washer', 'dryer', 'water_heater', 'pool_pump']
        appliance_entities = []

        for keyword in appliance_keywords:
            matching = events_df[
                events_df['entity_id'].str.contains(keyword, case=False, na=False)
            ]['entity_id'].unique()
            appliance_entities.extend(matching)

        if len(appliance_entities) == 0:
            return patterns

        logger.info(f"⚡ Analyzing {len(appliance_entities)} high-energy appliances for peak shifting...")

        # Get cheapest hours if available
        cheapest_hours = []
        if pricing and pricing.get('cheapest_hours'):
            cheapest_hours = pricing['cheapest_hours']

        for appliance in appliance_entities:
            conditions = []

            if pricing:
                conditions.append(f"during cheapest hours: {cheapest_hours if cheapest_hours else 'overnight'}")

            if carbon and carbon.get('carbon_intensity_gco2_kwh'):
                carbon_val = carbon['carbon_intensity_gco2_kwh']
                conditions.append(f"when carbon < 300g CO2/kWh (current: {carbon_val})")

            pattern = self._create_pattern_dict(
                pattern_type='fusion_peak_shifting',
                pattern_id=self._generate_pattern_id('fusion_peak'),
                confidence=0.78,
                occurrences=1,
                devices=[appliance],
                metadata={
                    'fusion_type': 'energy_peak_shifting',
                    'data_sources': ['pricing', 'carbon'],
                    'conditions': conditions,
                    'priority': 'medium',
                    'estimated_savings_percent': 25,
                    'recommendation': (
                        f"Delay {appliance} until " + " AND ".join(conditions)
                    ),
                    'cheapest_hours': cheapest_hours if cheapest_hours else None
                }
            )
            patterns.append(pattern)

        return patterns

    async def _detect_phantom_load_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect phantom load opportunities using smart meter data.

        Logic:
        - Smart meter detects >100W phantom load at night → Suggest smart plug automation
        """
        patterns = []

        smart_meter = enrichment_data.get('smart_meter')

        if not smart_meter:
            return patterns

        phantom_detected = smart_meter.get('phantom_load_detected', False)
        circuits = smart_meter.get('circuits', [])

        if not phantom_detected and not circuits:
            return patterns

        logger.info("💡 Analyzing smart meter data for phantom loads...")

        # Analyze circuits for high standby power
        for circuit in circuits:
            circuit_name = circuit.get('circuit_name')
            power_w = circuit.get('power_w', 0)

            # Phantom load threshold: > 50W at night
            if power_w > 50:
                pattern = self._create_pattern_dict(
                    pattern_type='fusion_phantom_load',
                    pattern_id=self._generate_pattern_id('fusion_phantom'),
                    confidence=0.82,
                    occurrences=1,
                    devices=[circuit_name],
                    metadata={
                        'fusion_type': 'phantom_load_detection',
                        'data_sources': ['smart_meter'],
                        'circuit': circuit_name,
                        'power_w': power_w,
                        'priority': 'medium',
                        'estimated_savings_kwh_year': power_w * 24 * 365 / 1000,  # Rough estimate
                        'recommendation': (
                            f"Circuit '{circuit_name}' has {power_w}W phantom load. "
                            f"Consider smart plug automation to turn off at night."
                        )
                    }
                )
                patterns.append(pattern)

        return patterns

    async def _detect_occupancy_aware_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect occupancy-aware automation opportunities.

        Logic:
        - Add "only when home" conditions to existing automations
        - Pre-arrival automations (AC on 30 min before arrival)
        """
        patterns = []

        calendar = enrichment_data.get('calendar')

        if not calendar:
            return patterns

        currently_home = calendar.get('currently_home')
        hours_until_arrival = calendar.get('hours_until_arrival')

        logger.info(f"🏠 Occupancy: home={currently_home}, arrival in {hours_until_arrival}h")

        # Pattern 1: Pre-arrival climate control
        if hours_until_arrival and 0 < hours_until_arrival < 2:
            climate_entities = events_df[
                events_df['entity_id'].str.contains('climate|thermostat', case=False, na=False)
            ]['entity_id'].unique()

            for climate in climate_entities:
                pattern = self._create_pattern_dict(
                    pattern_type='fusion_occupancy_prearrival',
                    pattern_id=self._generate_pattern_id('fusion_occupancy'),
                    confidence=0.85,
                    occurrences=1,
                    devices=[climate],
                    metadata={
                        'fusion_type': 'occupancy_aware',
                        'data_sources': ['calendar'],
                        'hours_until_arrival': hours_until_arrival,
                        'priority': 'high',
                        'recommendation': (
                            f"Start {climate} {int(hours_until_arrival * 60)} minutes before arrival"
                        )
                    }
                )
                patterns.append(pattern)

        return patterns

    async def _detect_weather_comfort_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect weather-based comfort automation opportunities.

        Logic:
        - Weather + occupancy → HVAC automation
        """
        patterns = []

        weather = enrichment_data.get('weather')
        calendar = enrichment_data.get('calendar')

        if not weather:
            return patterns

        temperature = weather.get('temperature')
        humidity = weather.get('humidity')
        condition = weather.get('condition')

        if temperature is None:
            return patterns

        logger.info(f"🌤️ Weather: {temperature}°C, {humidity}%, {condition}")

        # Find climate control entities
        climate_entities = events_df[
            events_df['entity_id'].str.contains('climate|thermostat|fan', case=False, na=False)
        ]['entity_id'].unique()

        if len(climate_entities) == 0:
            return patterns

        # Pattern: Extreme temperature automation
        if temperature > 30 or temperature < 5:
            for climate in climate_entities:
                pattern = self._create_pattern_dict(
                    pattern_type='fusion_weather_comfort',
                    pattern_id=self._generate_pattern_id('fusion_weather'),
                    confidence=0.80,
                    occurrences=1,
                    devices=[climate],
                    metadata={
                        'fusion_type': 'weather_comfort',
                        'data_sources': ['weather', 'calendar'],
                        'temperature': temperature,
                        'condition': condition,
                        'priority': 'high' if abs(temperature - 20) > 15 else 'medium',
                        'recommendation': (
                            f"Auto-adjust {climate} when temperature reaches {temperature}°C "
                            f"({'hot' if temperature > 25 else 'cold'})"
                        ),
                        'occupancy_required': calendar is not None
                    }
                )
                patterns.append(pattern)

        return patterns

    async def _detect_carbon_aware_patterns(
        self,
        events_df: pd.DataFrame,
        enrichment_data: dict[str, Any]
    ) -> list[dict]:
        """
        Detect carbon-aware scheduling opportunities.

        Logic:
        - Schedule high-energy tasks during high renewable % periods
        """
        patterns = []

        carbon = enrichment_data.get('carbon')

        if not carbon:
            return patterns

        renewable_pct = carbon.get('renewable_percentage')
        carbon_intensity = carbon.get('carbon_intensity_gco2_kwh')

        if renewable_pct is None:
            return patterns

        logger.info(f"🌱 Grid: {renewable_pct}% renewable, {carbon_intensity}g CO2/kWh")

        # High renewable threshold: > 60%
        if renewable_pct > 60:
            # Find high-energy appliances
            appliance_keywords = ['water_heater', 'pool_pump', 'ev', 'charger']
            appliance_entities = []

            for keyword in appliance_keywords:
                matching = events_df[
                    events_df['entity_id'].str.contains(keyword, case=False, na=False)
                ]['entity_id'].unique()
                appliance_entities.extend(matching)

            for appliance in appliance_entities:
                pattern = self._create_pattern_dict(
                    pattern_type='fusion_carbon_aware',
                    pattern_id=self._generate_pattern_id('fusion_carbon'),
                    confidence=0.77,
                    occurrences=1,
                    devices=[appliance],
                    metadata={
                        'fusion_type': 'carbon_aware_scheduling',
                        'data_sources': ['carbon'],
                        'renewable_percentage': renewable_pct,
                        'carbon_intensity': carbon_intensity,
                        'priority': 'medium',
                        'recommendation': (
                            f"Run {appliance} when renewable energy is high "
                            f"(currently {renewable_pct}%)"
                        )
                    }
                )
                patterns.append(pattern)

        return patterns

    async def close(self):
        """Clean up resources"""
        if self.enrichment_client:
            await self.enrichment_client.close()
