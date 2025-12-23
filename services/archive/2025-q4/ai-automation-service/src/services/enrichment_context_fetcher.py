"""
Enrichment Context Fetcher

Fetches cached enrichment data from InfluxDB for Ask AI suggestions.
Uses cached data from scheduled enrichment services (weather, carbon, energy, air quality).

Performance: <100ms for all enrichment data (cached queries)
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EnrichmentContextFetcher:
    """
    Fetch cached enrichment data from InfluxDB for contextual AI suggestions.

    Data sources:
    - Weather: temperature, conditions, forecast
    - Carbon: grid carbon intensity, renewable %
    - Energy: electricity pricing, off-peak hours
    - Air Quality: AQI, pollutants
    """

    def __init__(self, influxdb_client):
        """
        Initialize enrichment context fetcher.

        Args:
            influxdb_client: InfluxDB client for querying enrichment data
        """
        self.influxdb = influxdb_client
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes

        logger.info("EnrichmentContextFetcher initialized")

    async def get_all_enrichment(self, entity_ids: set[str] | None = None) -> dict[str, Any]:
        """
        Get all available enrichment data.

        Args:
            entity_ids: Optional set of entity IDs for selective enrichment

        Returns:
            Dictionary with all enrichment context
        """
        enrichment = {}

        try:
            # Fetch all enrichment in parallel
            import asyncio

            results = await asyncio.gather(
                self.get_current_weather(),
                self.get_carbon_intensity(),
                self.get_electricity_pricing(),
                self.get_air_quality(),
                return_exceptions=True
            )

            # Unpack results
            weather, carbon, energy, air = results

            if isinstance(weather, dict) and weather:
                enrichment['weather'] = weather
            if isinstance(carbon, dict) and carbon:
                enrichment['carbon'] = carbon
            if isinstance(energy, dict) and energy:
                enrichment['energy'] = energy
            if isinstance(air, dict) and air:
                enrichment['air_quality'] = air

            logger.info(f"✅ Fetched {len(enrichment)} enrichment types")
            return enrichment

        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch enrichment data: {e}")
            return {}

    async def get_current_weather(self) -> dict[str, Any] | None:
        """
        Get current weather data from InfluxDB cache.

        Returns:
            Weather context dictionary or None if unavailable
        """
        cache_key = 'weather'

        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']

        try:
            # Query latest weather data from InfluxDB
            query = '''
            from(bucket: "weather_data")
              |> range(start: -1h)
              |> filter(fn: (r) => r._measurement == "weather")
              |> last()
            '''

            result = await self.influxdb.query(query)

            if not result or result.empty:
                logger.debug("No weather data found in InfluxDB")
                return None

            # Parse weather data
            weather = self._parse_weather_data(result)

            # Cache result
            self._cache[cache_key] = {
                'data': weather,
                'timestamp': datetime.now(timezone.utc)
            }

            logger.debug(f"Weather: {weather.get('current_temperature')}°F, {weather.get('condition')}")
            return weather

        except Exception as e:
            logger.warning(f"Failed to fetch weather data: {e}")
            return None

    async def get_carbon_intensity(self) -> dict[str, Any] | None:
        """
        Get current grid carbon intensity from InfluxDB cache.

        Returns:
            Carbon context dictionary or None if unavailable
        """
        cache_key = 'carbon'

        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']

        try:
            # Query latest carbon intensity from InfluxDB
            query = '''
            from(bucket: "home_assistant_events")
              |> range(start: -1h)
              |> filter(fn: (r) => r._measurement == "carbon_intensity")
              |> last()
            '''

            result = await self.influxdb.query(query)

            if not result or result.empty:
                logger.debug("No carbon intensity data found in InfluxDB")
                return None

            # Parse carbon data
            carbon = self._parse_carbon_data(result)

            # Cache result
            self._cache[cache_key] = {
                'data': carbon,
                'timestamp': datetime.now(timezone.utc)
            }

            logger.debug(f"Carbon: {carbon.get('carbon_intensity')} gCO2/kWh, {carbon.get('renewable_percentage')}% renewable")
            return carbon

        except Exception as e:
            logger.warning(f"Failed to fetch carbon intensity data: {e}")
            return None

    async def get_electricity_pricing(self) -> dict[str, Any] | None:
        """
        Get current electricity pricing from InfluxDB cache.

        Returns:
            Energy pricing context dictionary or None if unavailable
        """
        cache_key = 'energy'

        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']

        try:
            # Query latest electricity pricing from InfluxDB
            query = '''
            from(bucket: "home_assistant_events")
              |> range(start: -1h)
              |> filter(fn: (r) => r._measurement == "electricity_pricing")
              |> last()
            '''

            result = await self.influxdb.query(query)

            if not result or result.empty:
                logger.debug("No electricity pricing data found in InfluxDB")
                return None

            # Parse energy pricing data
            energy = self._parse_energy_data(result)

            # Cache result
            self._cache[cache_key] = {
                'data': energy,
                'timestamp': datetime.now(timezone.utc)
            }

            logger.debug(f"Energy: ${energy.get('current_price')}/kWh, peak={energy.get('peak_period')}")
            return energy

        except Exception as e:
            logger.warning(f"Failed to fetch electricity pricing data: {e}")
            return None

    async def get_air_quality(self) -> dict[str, Any] | None:
        """
        Get current air quality (AQI) from InfluxDB cache.

        Returns:
            Air quality context dictionary or None if unavailable
        """
        cache_key = 'air_quality'

        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']

        try:
            # Query latest air quality from InfluxDB
            query = '''
            from(bucket: "home_assistant_events")
              |> range(start: -2h)
              |> filter(fn: (r) => r._measurement == "air_quality")
              |> last()
            '''

            result = await self.influxdb.query(query)

            if not result or result.empty:
                logger.debug("No air quality data found in InfluxDB")
                return None

            # Parse air quality data
            air = self._parse_air_quality_data(result)

            # Cache result
            self._cache[cache_key] = {
                'data': air,
                'timestamp': datetime.now(timezone.utc)
            }

            logger.debug(f"Air Quality: AQI {air.get('aqi')} ({air.get('category')})")
            return air

        except Exception as e:
            logger.warning(f"Failed to fetch air quality data: {e}")
            return None

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid (within TTL)"""
        if key not in self._cache:
            return False

        age = (datetime.now(timezone.utc) - self._cache[key]['timestamp']).total_seconds()
        return age < self._cache_ttl

    def _parse_weather_data(self, result) -> dict[str, Any]:
        """Parse InfluxDB weather query result"""
        try:
            # Extract latest values from result
            # InfluxDB returns pandas DataFrame or list of records
            if hasattr(result, 'iloc'):
                # DataFrame format
                row = result.iloc[-1]
                return {
                    'current_temperature': float(row.get('temperature', 0)),
                    'feels_like': float(row.get('feels_like', 0)),
                    'condition': str(row.get('condition', 'Unknown')),
                    'humidity': int(row.get('humidity', 0)),
                    'wind_speed': float(row.get('wind_speed', 0)),
                    'timestamp': row.get('_time', datetime.now(timezone.utc)).isoformat()
                }
            else:
                # List format
                record = result[-1] if isinstance(result, list) and result else {}
                return {
                    'current_temperature': float(record.get('temperature', 0)),
                    'feels_like': float(record.get('feels_like', 0)),
                    'condition': str(record.get('condition', 'Unknown')),
                    'humidity': int(record.get('humidity', 0)),
                    'wind_speed': float(record.get('wind_speed', 0)),
                    'timestamp': record.get('_time', datetime.now(timezone.utc))
                }
        except Exception as e:
            logger.warning(f"Failed to parse weather data: {e}")
            return {}

    def _parse_carbon_data(self, result) -> dict[str, Any]:
        """Parse InfluxDB carbon intensity query result"""
        try:
            if hasattr(result, 'iloc'):
                row = result.iloc[-1]
                return {
                    'carbon_intensity': float(row.get('carbon_intensity_gco2_kwh', 0)),
                    'renewable_percentage': float(row.get('renewable_percentage', 0)),
                    'fossil_percentage': float(row.get('fossil_percentage', 0)),
                    'forecast_1h': float(row.get('forecast_1h', 0)),
                    'timestamp': row.get('_time', datetime.now(timezone.utc)).isoformat()
                }
            else:
                record = result[-1] if isinstance(result, list) and result else {}
                return {
                    'carbon_intensity': float(record.get('carbon_intensity_gco2_kwh', 0)),
                    'renewable_percentage': float(record.get('renewable_percentage', 0)),
                    'fossil_percentage': float(record.get('fossil_percentage', 0)),
                    'forecast_1h': float(record.get('forecast_1h', 0)),
                    'timestamp': record.get('_time', datetime.now(timezone.utc))
                }
        except Exception as e:
            logger.warning(f"Failed to parse carbon data: {e}")
            return {}

    def _parse_energy_data(self, result) -> dict[str, Any]:
        """Parse InfluxDB electricity pricing query result"""
        try:
            if hasattr(result, 'iloc'):
                row = result.iloc[-1]
                return {
                    'current_price': float(row.get('current_price', 0)),
                    'currency': str(row.get('currency', 'USD')),
                    'peak_period': bool(row.get('peak_period', False)),
                    'timestamp': row.get('_time', datetime.now(timezone.utc)).isoformat()
                }
            else:
                record = result[-1] if isinstance(result, list) and result else {}
                return {
                    'current_price': float(record.get('current_price', 0)),
                    'currency': str(record.get('currency', 'USD')),
                    'peak_period': bool(record.get('peak_period', False)),
                    'timestamp': record.get('_time', datetime.now(timezone.utc))
                }
        except Exception as e:
            logger.warning(f"Failed to parse energy pricing data: {e}")
            return {}

    def _parse_air_quality_data(self, result) -> dict[str, Any]:
        """Parse InfluxDB air quality query result"""
        try:
            if hasattr(result, 'iloc'):
                row = result.iloc[-1]
                return {
                    'aqi': int(row.get('aqi', 0)),
                    'category': str(row.get('category', 'Unknown')),
                    'pm25': int(row.get('pm25', 0)),
                    'pm10': int(row.get('pm10', 0)),
                    'ozone': int(row.get('ozone', 0)),
                    'timestamp': row.get('_time', datetime.now(timezone.utc)).isoformat()
                }
            else:
                record = result[-1] if isinstance(result, list) and result else {}
                return {
                    'aqi': int(record.get('aqi', 0)),
                    'category': str(record.get('category', 'Unknown')),
                    'pm25': int(record.get('pm25', 0)),
                    'pm10': int(record.get('pm10', 0)),
                    'ozone': int(record.get('ozone', 0)),
                    'timestamp': record.get('_time', datetime.now(timezone.utc))
                }
        except Exception as e:
            logger.warning(f"Failed to parse air quality data: {e}")
            return {}


# Query intent classification functions
def should_include_weather(query_text: str, entity_ids: set[str]) -> bool:
    """
    Determine if weather enrichment is relevant to the query.

    Weather is relevant for:
    - Queries mentioning weather, temperature, cold, hot, frost, heat
    - Climate/thermostat/HVAC entities
    - Outdoor entities (sprinkler, garage door, etc.)
    """
    if not query_text:
        query_text = ""

    query_lower = query_text.lower()

    # Weather keywords
    weather_keywords = [
        'weather', 'temperature', 'cold', 'hot', 'warm', 'cool',
        'frost', 'freeze', 'heat', 'rain', 'snow', 'sun', 'outdoor'
    ]

    if any(keyword in query_lower for keyword in weather_keywords):
        return True

    # Climate entities
    climate_domains = {'climate', 'thermostat', 'switch', 'fan'}
    for entity_id in entity_ids:
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        if domain in climate_domains:
            return True

    return False


def should_include_carbon(query_text: str, entity_ids: set[str]) -> bool:
    """
    Determine if carbon intensity enrichment is relevant to the query.

    Carbon is relevant for:
    - Queries mentioning green, eco, sustainable, carbon, renewable
    - Schedulable high-power devices (EV charger, HVAC, pool pump)
    """
    if not query_text:
        query_text = ""

    query_lower = query_text.lower()

    # Carbon keywords
    carbon_keywords = [
        'green', 'eco', 'sustainable', 'carbon', 'renewable',
        'clean', 'environment', 'grid'
    ]

    if any(keyword in query_lower for keyword in carbon_keywords):
        return True

    # High-power schedulable devices
    high_power_keywords = ['charger', 'hvac', 'pool', 'heater', 'dryer', 'washer']
    for entity_id in entity_ids:
        if any(keyword in entity_id.lower() for keyword in high_power_keywords):
            return True

    return False


def should_include_energy(query_text: str, entity_ids: set[str]) -> bool:
    """
    Determine if electricity pricing enrichment is relevant to the query.

    Energy pricing is relevant for:
    - Queries mentioning schedule, save, cost, cheap, expensive, price
    - High-power devices that can be scheduled
    """
    if not query_text:
        query_text = ""

    query_lower = query_text.lower()

    # Energy/cost keywords
    energy_keywords = [
        'schedule', 'save', 'cost', 'cheap', 'expensive', 'price',
        'off-peak', 'peak', 'rate', 'bill', 'money'
    ]

    if any(keyword in query_lower for keyword in energy_keywords):
        return True

    # High-power schedulable devices
    high_power_keywords = ['charger', 'hvac', 'pool', 'heater', 'dryer', 'washer', 'dishwasher']
    for entity_id in entity_ids:
        if any(keyword in entity_id.lower() for keyword in high_power_keywords):
            return True

    return False


def should_include_air_quality(query_text: str, entity_ids: set[str]) -> bool:
    """
    Determine if air quality enrichment is relevant to the query.

    Air quality is relevant for:
    - Queries mentioning air, purifier, ventilation, indoor, quality
    - Air purifier, fan, ventilation entities
    """
    if not query_text:
        query_text = ""

    query_lower = query_text.lower()

    # Air quality keywords
    air_keywords = [
        'air', 'purifier', 'ventilation', 'indoor', 'quality',
        'filter', 'clean', 'breathe', 'pollution'
    ]

    if any(keyword in query_lower for keyword in air_keywords):
        return True

    # Air quality entities
    air_entity_keywords = ['purifier', 'fan', 'ventilat', 'air']
    for entity_id in entity_ids:
        if any(keyword in entity_id.lower() for keyword in air_entity_keywords):
            return True

    return False


def get_selective_enrichment(
    query_text: str,
    entity_ids: set[str],
    fetcher: EnrichmentContextFetcher
) -> dict[str, Any]:
    """
    Get only relevant enrichment data based on query and entities.

    This is more performant than fetching all enrichment types.

    Args:
        query_text: User's natural language query
        entity_ids: Set of entity IDs involved in the query
        fetcher: EnrichmentContextFetcher instance

    Returns:
        Dictionary with only relevant enrichment context
    """
    import asyncio

    tasks = []
    enrichment_types = []

    # Determine which enrichment to fetch
    if should_include_weather(query_text, entity_ids):
        tasks.append(fetcher.get_current_weather())
        enrichment_types.append('weather')

    if should_include_carbon(query_text, entity_ids):
        tasks.append(fetcher.get_carbon_intensity())
        enrichment_types.append('carbon')

    if should_include_energy(query_text, entity_ids):
        tasks.append(fetcher.get_electricity_pricing())
        enrichment_types.append('energy')

    if should_include_air_quality(query_text, entity_ids):
        tasks.append(fetcher.get_air_quality())
        enrichment_types.append('air_quality')

    # Fetch selected enrichment types in parallel
    if not tasks:
        logger.debug("No relevant enrichment types for this query")
        return {}

    logger.info(f"Fetching selective enrichment: {enrichment_types}")

    # Run tasks
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

    # Build enrichment dictionary
    enrichment = {}
    for i, result in enumerate(results):
        if isinstance(result, dict) and result:
            enrichment[enrichment_types[i]] = result

    logger.info(f"✅ Selective enrichment: {len(enrichment)}/{len(enrichment_types)} types fetched")
    return enrichment
