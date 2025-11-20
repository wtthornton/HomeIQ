"""
Weather Opportunity Detector

Detects weather-aware automation opportunities using enrichment data.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.5: Weather Context Integration
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WeatherOpportunityDetector:
    """
    Detects weather-aware automation opportunities.
    
    Uses weather data from InfluxDB (already flowing via enrichment-pipeline)
    to suggest climate automations like frost protection, pre-heating/cooling.
    
    Story AI3.5: Weather Context Integration
    Epic AI-3: Cross-Device Synergy & Contextual Opportunities
    """

    def __init__(
        self,
        influxdb_client,
        data_api_client,
        frost_threshold_f: float = 32.0,
        heat_threshold_f: float = 85.0,
        min_confidence: float = 0.7
    ):
        """
        Initialize weather opportunity detector.
        
        Args:
            influxdb_client: InfluxDB client for weather queries
            data_api_client: Data API client for device queries
            frost_threshold_f: Frost protection threshold (default: 32°F)
            heat_threshold_f: Pre-cooling threshold (default: 85°F)
            min_confidence: Minimum confidence for opportunities
        """
        self.influxdb = influxdb_client
        self.data_api = data_api_client
        self.frost_threshold = frost_threshold_f
        self.heat_threshold = heat_threshold_f
        self.min_confidence = min_confidence

        # Cache for performance
        self._weather_cache = None
        self._climate_devices_cache = None

        logger.info(
            f"WeatherOpportunityDetector initialized: "
            f"frost_threshold={frost_threshold_f}°F, heat_threshold={heat_threshold_f}°F"
        )

    async def detect_opportunities(self, days: int = 7) -> list[dict]:
        """
        Detect all weather-aware automation opportunities.
        
        Args:
            days: Days of weather history to analyze (default: 7)
        
        Returns:
            List of weather opportunity dictionaries
        """
        start_time = datetime.now(timezone.utc)
        logger.info("🌤️ Starting weather opportunity detection...")

        try:
            # Step 1: Get weather data
            weather_data = await self._get_weather_data(days)

            if not weather_data:
                logger.warning("⚠️ No weather data found in InfluxDB, but continuing with weather opportunity detection")
                logger.warning("   → Weather data may be stored under different measurement name")
                # Continue with empty weather data - still try to find opportunities
                weather_data = []

            logger.info(f"📊 Retrieved {len(weather_data)} weather records")

            # Step 2: Get climate devices
            climate_devices = await self._get_climate_devices()

            if not climate_devices:
                logger.info("ℹ️  No climate devices found, but continuing with weather opportunities")
                # Continue with empty climate devices - still try to find opportunities
                climate_devices = []

            logger.info(f"🌡️  Found {len(climate_devices)} climate devices")

            # Step 3: Detect opportunities
            opportunities = []

            # Frost protection opportunities (even with empty data)
            frost_opps = await self._detect_frost_protection(weather_data, climate_devices)
            opportunities.extend(frost_opps)
            logger.info(f"   ❄️  Frost protection: {len(frost_opps)} opportunities")

            # Pre-cooling opportunities (even with empty data)
            cooling_opps = await self._detect_precooling(weather_data, climate_devices)
            opportunities.extend(cooling_opps)
            logger.info(f"   🧊 Pre-cooling: {len(cooling_opps)} opportunities")

            # Always create at least one generic weather opportunity if no specific ones found
            # This ensures weather-aware automations are suggested even with minimal data
            if not opportunities and (weather_data or climate_devices):
                generic_opp = {
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'weather_context',
                    'devices': [d.get('entity_id', 'unknown') for d in climate_devices[:2]] if climate_devices else ['weather.forecast_home'],
                    'relationship': 'weather_aware_automation',
                    'area': 'home',
                    'impact_score': 0.6,
                    'complexity': 'medium',
                    'confidence': 0.7,
                    'rationale': 'Weather-aware automation opportunity based on available climate devices and weather patterns'
                }
                opportunities.append(generic_opp)
                logger.info("   🌤️  Created generic weather opportunity")

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"✅ Weather opportunity detection complete in {duration:.1f}s\n"
                f"   Total opportunities: {len(opportunities)}"
            )

            return opportunities

        except Exception as e:
            logger.error(f"❌ Weather opportunity detection failed: {e}", exc_info=True)
            return []

    async def _get_weather_data(self, days: int) -> list[dict]:
        """
        Get weather data from normalized Home Assistant events in InfluxDB.
        
        Args:
            days: Days of history to query
        
        Returns:
            List of weather records
        """
        if self._weather_cache is not None:
            return self._weather_cache

        try:
            # Query normalized HA weather events from InfluxDB
            # Weather data is stored as HA events with domain="weather" and domain="sensor" for weather sensors
            query = f'''
            import "strings"
            
            from(bucket: "home_assistant_events")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r["domain"] == "weather" or 
                        (r["domain"] == "sensor" and (
                          strings.containsStr(v: r["entity_id"], substr: "weather") or
                          strings.containsStr(v: r["entity_id"], substr: "temperature") or
                          strings.containsStr(v: r["entity_id"], substr: "humidity") or
                          strings.containsStr(v: r["entity_id"], substr: "pressure") or
                          strings.containsStr(v: r["entity_id"], substr: "wind") or
                          strings.containsStr(v: r["entity_id"], substr: "sun")
                        )))
              |> filter(fn: (r) => r["_field"] == "state")
              |> sort(columns: ["_time"])
              |> limit(n: 500)
            '''

            result = self.influxdb.query_api.query(query, org=self.influxdb.org)

            # Parse weather records from normalized HA events
            weather_records = []
            logger.info(f"🌤️  Weather query returned {len(result)} tables")

            for table in result:
                for record in table.records:
                    weather_records.append({
                        'time': record.get_time(),
                        'entity_id': record.values.get('entity_id'),
                        'domain': record.values.get('domain'),
                        'field': record.values.get('_field', 'state'),
                        'value': record.get_value(),
                        'location': record.values.get('area_id', 'home')
                    })

            self._weather_cache = weather_records
            logger.info(f"📊 Retrieved {len(weather_records)} normalized weather events from HA")

            return weather_records

        except Exception as e:
            logger.warning(f"Failed to get weather data from HA events: {e}")
            return []

    async def _get_climate_devices(self) -> list[dict]:
        """Get all climate-related devices from data-api."""
        if self._climate_devices_cache is not None:
            return self._climate_devices_cache

        try:
            # Get all devices
            all_devices = await self.data_api.fetch_devices()

            # Get all entities
            all_entities = await self.data_api.fetch_entities()

            # Filter for climate entities
            climate_entities = [
                e for e in all_entities
                if e['entity_id'].startswith('climate.')
            ]

            self._climate_devices_cache = climate_entities
            logger.debug(f"Found {len(climate_entities)} climate devices")

            return climate_entities

        except Exception as e:
            logger.warning(f"Failed to get climate devices: {e}")
            return []

    async def _detect_frost_protection(
        self,
        weather_data: list[dict],
        climate_devices: list[dict]
    ) -> list[dict]:
        """
        Detect frost protection opportunities.
        
        Triggered when forecast shows temps below freezing.
        """
        opportunities = []

        # Get recent low temperatures
        low_temps = [
            r for r in weather_data
            if r['field'] == 'forecast_low' or (r['field'] == 'temperature' and r['value'] < 40)
        ]

        if not low_temps:
            return []

        # Check if any temps below frost threshold
        min_temp = min(r['value'] for r in low_temps)

        if min_temp < self.frost_threshold:
            logger.info(f"❄️  Frost risk detected: {min_temp:.1f}°F (threshold: {self.frost_threshold}°F)")

            # Create opportunity for each climate device
            for device in climate_devices:
                opportunities.append({
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'weather_context',
                    'devices': [device['entity_id']],
                    'trigger_entity': 'weather.forecast',
                    'action_entity': device['entity_id'],
                    'area': device.get('area_id', 'unknown'),
                    'relationship': 'frost_protection',
                    'impact_score': 0.88,  # High - prevents damage
                    'complexity': 'medium',
                    'confidence': 0.85,
                    'opportunity_metadata': {
                        'trigger_name': 'Weather Forecast',
                        'action_name': device.get('friendly_name', device['entity_id']),
                        'weather_condition': f'Temperature below {self.frost_threshold}°F',
                        'current_low': min_temp,
                        'suggested_action': 'Set minimum temperature to 62°F overnight',
                        'rationale': f"Forecast shows {min_temp:.1f}°F - enable frost protection to prevent frozen pipes"
                    }
                })

        return opportunities

    async def _detect_precooling(
        self,
        weather_data: list[dict],
        climate_devices: list[dict]
    ) -> list[dict]:
        """
        Detect pre-cooling opportunities.
        
        Triggered when forecast shows hot afternoon temps.
        """
        opportunities = []

        # Get high temperatures
        high_temps = [
            r for r in weather_data
            if r['field'] == 'forecast_high'
        ]

        if not high_temps:
            return []

        # Check for hot days
        max_temp = max(r['value'] for r in high_temps)

        if max_temp > self.heat_threshold:
            logger.info(f"🔥 Hot day detected: {max_temp:.1f}°F (threshold: {self.heat_threshold}°F)")

            # Create opportunity for each climate device
            for device in climate_devices:
                opportunities.append({
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'weather_context',
                    'devices': [device['entity_id']],
                    'trigger_entity': 'weather.forecast',
                    'action_entity': device['entity_id'],
                    'area': device.get('area_id', 'unknown'),
                    'relationship': 'precooling',
                    'impact_score': 0.75,  # Medium-high - energy savings
                    'complexity': 'medium',
                    'confidence': 0.78,
                    'opportunity_metadata': {
                        'trigger_name': 'Weather Forecast',
                        'action_name': device.get('friendly_name', device['entity_id']),
                        'weather_condition': f'High temperature {max_temp:.1f}°F',
                        'current_high': max_temp,
                        'suggested_action': 'Pre-cool before peak heat (save 15-20% energy)',
                        'rationale': f"Forecast shows {max_temp:.1f}°F - pre-cool early to reduce energy costs"
                    }
                })

        return opportunities

    def clear_cache(self):
        """Clear cached data."""
        self._weather_cache = None
        self._climate_devices_cache = None
        logger.debug("Weather opportunity detector cache cleared")

