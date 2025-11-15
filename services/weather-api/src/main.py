"""
Weather API Service - Simple, single-file implementation
Following carbon-intensity and air-quality service patterns
Epic 31, Stories 31.1-31.3
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Literal
import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from influxdb_client_3 import InfluxDBClient3, Point

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging
from .health_check import HealthCheckHandler

# Load environment variables
load_dotenv()

SERVICE_NAME = "weather-api"
SERVICE_VERSION = "2.2.0"

# Configure logging
logger = setup_logging(SERVICE_NAME)


# Pydantic Models
class WeatherResponse(BaseModel):
    """Current weather response"""
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    condition: str
    description: str
    wind_speed: float
    cloudiness: int
    location: str
    timestamp: str


class WeatherService:
    """Simple weather service - fetch, cache, store"""
    
    def __init__(self):
        # OpenWeatherMap config
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.location = os.getenv('WEATHER_LOCATION', 'Las Vegas')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.auth_mode: Literal["header", "query"] = os.getenv('WEATHER_API_AUTH_MODE', 'header').lower()  # 2025 default
        if self.auth_mode not in ("header", "query"):
            logger.warning("Invalid WEATHER_API_AUTH_MODE '%s', defaulting to 'header'", self.auth_mode)
            self.auth_mode = "header"
        
        # InfluxDB config
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'weather_data')
        self.max_influx_retries = int(os.getenv('INFLUXDB_WRITE_RETRIES', '3'))
        
        # Cache (simple dict with timestamp)
        self.cached_weather: Optional[Dict[str, Any]] = None
        self.cache_time: Optional[datetime] = None
        self.cache_ttl = int(os.getenv('CACHE_TTL_SECONDS', '900'))  # 15 minutes
        
        # Components
        self.session: Optional[aiohttp.ClientSession] = None
        self.influxdb_client: Optional[InfluxDBClient3] = None
        self.background_task: Optional[asyncio.Task] = None
        self.last_background_error: Optional[str] = None
        self.last_successful_fetch: Optional[datetime] = None
        self.last_influx_write: Optional[datetime] = None
        self.health_handler = HealthCheckHandler(service_name=SERVICE_NAME, version=SERVICE_VERSION)
        
        # Stats
        self.fetch_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        if not self.api_key:
            logger.warning("WEATHER_API_KEY not set - service will run in standby mode")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")
    
    async def startup(self):
        """Initialize service"""
        logger.info("Initializing Weather API Service...")
        
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )
        
        logger.info("Weather API Service initialized")
    
    async def shutdown(self):
        """Cleanup"""
        logger.info("Shutting down Weather API Service...")
        await self.stop_background_task()
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        if self.influxdb_client:
            self.influxdb_client.close()
    
    async def fetch_weather(self) -> Optional[Dict[str, Any]]:
        """Fetch weather from OpenWeatherMap"""
        if not self.api_key:
            return self.cached_weather
        
        if not self.session or self.session.closed:
            raise RuntimeError("HTTP session not initialized")
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": self.location,
                "units": "metric"
            }
            headers = {
                "Accept": "application/json"
            }
            if self.auth_mode == "header":
                headers["X-API-Key"] = self.api_key
            else:
                params["appid"] = self.api_key
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                    weather = {
                        'temperature': data.get("main", {}).get("temp", 0),
                        'feels_like': data.get("main", {}).get("feels_like", 0),
                        'humidity': data.get("main", {}).get("humidity", 0),
                        'pressure': data.get("main", {}).get("pressure", 0),
                        'condition': data.get("weather", [{}])[0].get("main", "Unknown"),
                        'description': data.get("weather", [{}])[0].get("description", ""),
                        'wind_speed': data.get("wind", {}).get("speed", 0),
                        'cloudiness': data.get("clouds", {}).get("all", 0),
                        'location': data.get("name", self.location),
                        'timestamp': timestamp
                    }
                    
                    self.fetch_count += 1
                    logger.info(f"Fetched weather: {weather['temperature']}°C, {weather['condition']}")
                    return weather
                else:
                    if response.status == 401 and self.auth_mode == "header":
                        logger.error("OpenWeatherMap API authentication failed with header mode. "
                                     "Set WEATHER_API_AUTH_MODE=query if your API key does not support headers.")
                    else:
                        logger.error(f"OpenWeatherMap API error: {response.status}")
                    return self.cached_weather
                    
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return self.cached_weather
    
    async def get_current_weather(self) -> Optional[Dict[str, Any]]:
        """Get current weather (cache-first)"""
        # Check cache
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        if self.cached_weather and self.cache_time:
            age = (now - self.cache_time).total_seconds()
            if age < self.cache_ttl:
                self.cache_hits += 1
                return self.cached_weather
        
        # Cache miss - fetch
        self.cache_misses += 1
        weather = await self.fetch_weather()
        
        if weather:
            self.cached_weather = weather
            self.cache_time = now
            self.last_successful_fetch = now
            
            # Write to InfluxDB
            await self.store_in_influxdb(weather)
        
        return weather
    
    async def store_in_influxdb(self, weather: Dict[str, Any]):
        """Store weather in InfluxDB"""
        if not weather:
            return
        
        if not self.influxdb_client:
            logger.warning("InfluxDB client not initialized, skipping write")
            return
        
        timestamp = datetime.fromisoformat(weather['timestamp'])
        
        point = Point("weather") \
            .tag("location", weather['location']) \
            .tag("condition", weather['condition']) \
            .field("temperature", float(weather['temperature'])) \
            .field("humidity", int(weather['humidity'])) \
            .field("pressure", int(weather['pressure'])) \
            .field("wind_speed", float(weather['wind_speed'])) \
            .field("cloudiness", int(weather['cloudiness'])) \
            .time(timestamp)
        
        for attempt in range(1, self.max_influx_retries + 1):
            try:
                await asyncio.to_thread(self.influxdb_client.write, point)
                self.last_influx_write = datetime.utcnow().replace(tzinfo=timezone.utc)
                logger.info("Weather data written to InfluxDB")
                return
            except Exception as e:
                if attempt >= self.max_influx_retries:
                    logger.error("Failed to write to InfluxDB after %s attempts: %s", attempt, e)
                else:
                    backoff = 2 ** (attempt - 1)
                    logger.warning("InfluxDB write failed (attempt %s/%s). Retrying in %ss",
                                   attempt, self.max_influx_retries, backoff)
                    await asyncio.sleep(backoff)
    
    async def run_continuous(self):
        """Background fetch loop"""
        logger.info(f"Starting continuous fetch (every {self.cache_ttl}s)")
        
        while True:
            try:
                await self.get_current_weather()
                await asyncio.sleep(self.cache_ttl)
            except asyncio.CancelledError:
                logger.info("Continuous fetch loop cancelled")
                raise
            except Exception as e:
                self.last_background_error = str(e)
                logger.error(f"Error in continuous loop: {e}")
                await asyncio.sleep(300)

    def start_background_task(self) -> asyncio.Task:
        """Start guarded background task"""
        if self.background_task and not self.background_task.done():
            return self.background_task
        
        async def _run():
            try:
                await self.run_continuous()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_background_error = str(exc)
                logger.exception("Weather background task failed")
        
        self.background_task = asyncio.create_task(_run(), name="weather-fetch-loop")
        return self.background_task

    async def stop_background_task(self):
        """Stop background task gracefully"""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.background_task
        self.background_task = None


# Global service instance
weather_service = None


async def startup():
    """Startup handler"""
    global weather_service
    weather_service = WeatherService()
    await weather_service.startup()
    weather_service.start_background_task()


async def shutdown():
    """Shutdown handler"""
    if weather_service:
        await weather_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Weather API Service",
    description="Standalone weather data service",
    version=SERVICE_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lifecycle
app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics", "/current-weather", "/cache/stats"]
    }


@app.get("/health")
async def health():
    """Health check"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await weather_service.health_handler.handle(weather_service)


@app.get("/metrics")
async def metrics():
    """Lightweight metrics endpoint (JSON)"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await weather_service.health_handler.handle(weather_service)


@app.get("/current-weather", response_model=WeatherResponse)
async def get_current_weather():
    """Get current weather (Story 31.3)"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    weather = await weather_service.get_current_weather()
    
    if not weather:
        raise HTTPException(status_code=503, detail="Weather data unavailable")
    
    return WeatherResponse(**weather)


@app.get("/cache/stats")
async def cache_stats():
    """Cache statistics"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    total = weather_service.cache_hits + weather_service.cache_misses
    hit_rate = (weather_service.cache_hits / total * 100) if total > 0 else 0
    
    return {
        "hits": weather_service.cache_hits,
        "misses": weather_service.cache_misses,
        "hit_rate": round(hit_rate, 2),
        "fetch_count": weather_service.fetch_count,
        "ttl_seconds": weather_service.cache_ttl,
        "last_cache_time": weather_service.cache_time.isoformat() if weather_service.cache_time else None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SERVICE_PORT', '8009'))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
