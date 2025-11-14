"""
Data Enrichment Client for AI Automation Service

Provides unified access to all 6 data enrichment services:
- Weather API (Port 8009)
- Carbon Intensity (Port 8010)
- Electricity Pricing (Port 8011)
- Air Quality (Port 8012)
- Calendar Service (Port 8013)
- Smart Meter (Port 8014)

Epic: Multi-Source Contextual Fusion (#2)
"""

import httpx
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class DataEnrichmentClient:
    """Unified client for all data enrichment services"""

    def __init__(
        self,
        weather_url: str = "http://weather-api:8009",
        carbon_url: str = "http://carbon-intensity:8010",
        pricing_url: str = "http://electricity-pricing:8011",
        air_quality_url: str = "http://air-quality:8012",
        calendar_url: str = "http://calendar-service:8013",
        smart_meter_url: str = "http://smart-meter:8014",
        timeout: float = 5.0
    ):
        """
        Initialize data enrichment client.

        Args:
            weather_url: Weather API service URL
            carbon_url: Carbon intensity service URL
            pricing_url: Electricity pricing service URL
            air_quality_url: Air quality service URL
            calendar_url: Calendar service URL
            smart_meter_url: Smart meter service URL
            timeout: Request timeout in seconds
        """
        self.weather_url = weather_url.rstrip('/')
        self.carbon_url = carbon_url.rstrip('/')
        self.pricing_url = pricing_url.rstrip('/')
        self.air_quality_url = air_quality_url.rstrip('/')
        self.calendar_url = calendar_url.rstrip('/')
        self.smart_meter_url = smart_meter_url.rstrip('/')

        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        # Service availability flags (for graceful degradation)
        self.services_available = {
            'weather': True,
            'carbon': True,
            'pricing': True,
            'air_quality': True,
            'calendar': True,
            'smart_meter': True
        }

        logger.info("DataEnrichmentClient initialized with all 6 services")

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't raise, return None for graceful degradation
    )
    async def get_weather(self) -> Optional[Dict[str, Any]]:
        """
        Get current weather data.

        Returns:
            Dictionary with temperature, humidity, condition, etc. or None if unavailable
        """
        if not self.services_available['weather']:
            return None

        try:
            response = await self.client.get(f"{self.weather_url}/weather/current")
            response.raise_for_status()
            data = response.json()

            return {
                'temperature': data.get('temperature'),
                'feels_like': data.get('feels_like'),
                'humidity': data.get('humidity'),
                'pressure': data.get('pressure'),
                'wind_speed': data.get('wind_speed'),
                'clouds': data.get('clouds'),
                'condition': data.get('condition'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.warning(f"Weather API unavailable: {e}")
            self.services_available['weather'] = False
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def get_carbon_intensity(self) -> Optional[Dict[str, Any]]:
        """
        Get current grid carbon intensity.

        Returns:
            Dictionary with carbon_intensity_gco2_kwh, renewable_percentage, etc. or None
        """
        if not self.services_available['carbon']:
            return None

        try:
            response = await self.client.get(f"{self.carbon_url}/carbon/current")
            response.raise_for_status()
            data = response.json()

            return {
                'carbon_intensity_gco2_kwh': data.get('carbon_intensity'),
                'renewable_percentage': data.get('renewable_percentage'),
                'fossil_percentage': data.get('fossil_percentage'),
                'forecast_1h': data.get('forecast_1h'),
                'forecast_24h': data.get('forecast_24h'),
                'region': data.get('region'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.warning(f"Carbon Intensity API unavailable: {e}")
            self.services_available['carbon'] = False
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def get_electricity_pricing(self) -> Optional[Dict[str, Any]]:
        """
        Get current electricity pricing data.

        Returns:
            Dictionary with current_price, peak_period, forecast, etc. or None
        """
        if not self.services_available['pricing']:
            return None

        try:
            response = await self.client.get(f"{self.pricing_url}/pricing/current")
            response.raise_for_status()
            data = response.json()

            # Also get cheapest hours for optimization suggestions
            cheapest_response = await self.client.get(f"{self.pricing_url}/pricing/cheapest-hours?hours=4")
            cheapest_data = cheapest_response.json() if cheapest_response.status_code == 200 else {}

            return {
                'current_price': data.get('current_price'),
                'currency': data.get('currency', 'EUR'),
                'peak_period': data.get('peak_period', False),
                'provider': data.get('provider'),
                'cheapest_hours': cheapest_data.get('cheapest_hours', []),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.warning(f"Electricity Pricing API unavailable: {e}")
            self.services_available['pricing'] = False
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def get_air_quality(self) -> Optional[Dict[str, Any]]:
        """
        Get current air quality data.

        Returns:
            Dictionary with AQI, PM2.5, pollutants, etc. or None
        """
        if not self.services_available['air_quality']:
            return None

        try:
            response = await self.client.get(f"{self.air_quality_url}/air-quality/current")
            response.raise_for_status()
            data = response.json()

            return {
                'aqi': data.get('aqi'),
                'category': data.get('category'),
                'pm25': data.get('pm25'),
                'pm10': data.get('pm10'),
                'ozone': data.get('ozone'),
                'co': data.get('co'),
                'no2': data.get('no2'),
                'so2': data.get('so2'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.warning(f"Air Quality API unavailable: {e}")
            self.services_available['air_quality'] = False
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def get_occupancy_prediction(self) -> Optional[Dict[str, Any]]:
        """
        Get current occupancy prediction from calendar service.

        Returns:
            Dictionary with currently_home, wfh_today, hours_until_arrival, etc. or None
        """
        if not self.services_available['calendar']:
            return None

        try:
            response = await self.client.get(f"{self.calendar_url}/occupancy/current")
            response.raise_for_status()
            data = response.json()

            return {
                'currently_home': data.get('currently_home'),
                'wfh_today': data.get('wfh_today'),
                'confidence': data.get('confidence'),
                'hours_until_arrival': data.get('hours_until_arrival'),
                'event_count': data.get('event_count'),
                'current_event_count': data.get('current_event_count'),
                'upcoming_event_count': data.get('upcoming_event_count'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.debug(f"Calendar service unavailable (may be disabled): {e}")
            self.services_available['calendar'] = False
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def get_smart_meter_data(self) -> Optional[Dict[str, Any]]:
        """
        Get current smart meter power consumption data.

        Returns:
            Dictionary with total_power_w, daily_kwh, circuits, phantom_load, etc. or None
        """
        if not self.services_available['smart_meter']:
            return None

        try:
            response = await self.client.get(f"{self.smart_meter_url}/power/current")
            response.raise_for_status()
            data = response.json()

            # Get circuit breakdown if available
            circuits_response = await self.client.get(f"{self.smart_meter_url}/power/circuits")
            circuits_data = circuits_response.json() if circuits_response.status_code == 200 else {}

            return {
                'total_power_w': data.get('total_power_w'),
                'daily_kwh': data.get('daily_kwh'),
                'circuits': circuits_data.get('circuits', []),
                'phantom_load_detected': data.get('phantom_load_detected', False),
                'high_consumption_alert': data.get('high_consumption_alert', False),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.warning(f"Smart Meter API unavailable: {e}")
            self.services_available['smart_meter'] = False
            return None

    async def get_all_enrichment_data(self) -> Dict[str, Any]:
        """
        Get all enrichment data from all 6 services in parallel.

        Returns:
            Dictionary with keys: weather, carbon, pricing, air_quality, calendar, smart_meter
            Each value is the service response dict or None if unavailable
        """
        import asyncio

        # Fetch all data in parallel for performance
        results = await asyncio.gather(
            self.get_weather(),
            self.get_carbon_intensity(),
            self.get_electricity_pricing(),
            self.get_air_quality(),
            self.get_occupancy_prediction(),
            self.get_smart_meter_data(),
            return_exceptions=True
        )

        # Build response dict
        enrichment_data = {
            'weather': results[0] if not isinstance(results[0], Exception) else None,
            'carbon': results[1] if not isinstance(results[1], Exception) else None,
            'pricing': results[2] if not isinstance(results[2], Exception) else None,
            'air_quality': results[3] if not isinstance(results[3], Exception) else None,
            'calendar': results[4] if not isinstance(results[4], Exception) else None,
            'smart_meter': results[5] if not isinstance(results[5], Exception) else None
        }

        # Log availability
        available_services = [k for k, v in enrichment_data.items() if v is not None]
        logger.info(f"Enrichment data fetched: {len(available_services)}/6 services available")

        return enrichment_data

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
