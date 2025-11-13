"""
OpenWeatherMap client utilities used by websocket-ingestion tests.

This module provides:
* WeatherData dataclass for normalized responses
* OpenWeatherMapClient with minimal rate limiting and statistics
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp


def _get_nested(data: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Any:
    """Safely extract nested keys from dictionaries."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


@dataclass
class WeatherData:
    """Normalized weather data from OpenWeatherMap responses."""

    api_response: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "openweathermap"

    def __post_init__(self) -> None:
        main_block = self.api_response.get("main", {})
        weather_block = (self.api_response.get("weather") or [{}])[0]
        wind_block = self.api_response.get("wind", {})
        clouds_block = self.api_response.get("clouds", {})
        coord_block = self.api_response.get("coord", {})
        sys_block = self.api_response.get("sys", {})

        self.temperature: Optional[float] = main_block.get("temp")
        self.feels_like: Optional[float] = main_block.get("feels_like")
        self.humidity: Optional[int] = main_block.get("humidity")
        self.pressure: Optional[int] = main_block.get("pressure")
        self.weather_condition: Optional[str] = weather_block.get("main")
        self.weather_description: Optional[str] = weather_block.get("description")
        self.wind_speed: Optional[float] = wind_block.get("speed")
        self.wind_direction: Optional[int] = wind_block.get("deg")
        self.cloudiness: Optional[int] = clouds_block.get("all")
        self.visibility: Optional[int] = self.api_response.get("visibility")
        self.location: Optional[str] = self.api_response.get("name")
        self.country: Optional[str] = sys_block.get("country")
        self.coordinates: Dict[str, Optional[float]] = {
            "lat": coord_block.get("lat"),
            "lon": coord_block.get("lon"),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable representation of the weather data."""
        return {
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "weather_condition": self.weather_condition,
            "weather_description": self.weather_description,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "cloudiness": self.cloudiness,
            "visibility": self.visibility,
            "location": self.location,
            "country": self.country,
            "coordinates": self.coordinates,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class OpenWeatherMapClient:
    """Async client for retrieving current weather data."""

    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/2.5") -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 1.0

        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_error: Optional[str] = None

        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Create the aiohttp session."""
        if self.session and not self.session.closed:
            return

        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_current_weather(self, city: str, *, units: str = "metric") -> Optional[WeatherData]:
        """Fetch current weather by city name."""
        params = {"q": city, "appid": self.api_key, "units": units}
        return await self._fetch_weather(params)

    async def get_current_weather_by_coordinates(
        self, latitude: float, longitude: float, *, units: str = "metric"
    ) -> Optional[WeatherData]:
        """Fetch current weather by latitude/longitude."""
        params = {"lat": latitude, "lon": longitude, "appid": self.api_key, "units": units}
        return await self._fetch_weather(params)

    def configure_rate_limit(self, delay_seconds: float) -> None:
        """Adjust rate limit delay applied between requests."""
        if delay_seconds <= 0:
            raise ValueError("Rate limit delay must be greater than zero")
        self.rate_limit_delay = delay_seconds

    def get_statistics(self) -> Dict[str, Any]:
        """Return request statistics."""
        success_rate = 0.0
        if self.total_requests:
            success_rate = round((self.successful_requests / self.total_requests) * 100, 2)

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "last_error": self.last_error,
            "rate_limit_delay": self.rate_limit_delay,
        }

    def reset_statistics(self) -> None:
        """Reset all tracked statistics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_error = None

    async def _fetch_weather(self, params: Dict[str, Any]) -> Optional[WeatherData]:
        """Internal helper to execute the HTTP request."""
        if not self.session or self.session.closed:
            await self.start()

        async with self._lock:
            await asyncio.sleep(self.rate_limit_delay)

            self.total_requests += 1

            try:
                assert self.session is not None  # For type checkers
                async with self.session.get(f"{self.base_url}/weather", params=params) as response:
                    if response.status == 200:
                        payload = await response.json()
                        self.successful_requests += 1
                        self.last_error = None
                        return WeatherData(payload)

                    error_text = await response.text()
                    self.failed_requests += 1
                    self.last_error = error_text or f"Request failed with status {response.status}"
                    return None

            except asyncio.TimeoutError:
                self.failed_requests += 1
                self.last_error = "Request timeout"
                return None
            except aiohttp.ClientError as exc:
                self.failed_requests += 1
                self.last_error = str(exc)
                return None


