# Weather API Service

Fetches weather data from OpenWeatherMap and stores in InfluxDB.

## Architecture
- FastAPI application with `WeatherService` class in `src/main.py`
- OpenWeatherMap API integration (header or query auth modes)
- InfluxDB storage with fallback hostname support
- Cache-first strategy with thundering herd protection via asyncio.Lock

## Key Patterns
- Double-check locking for cache-miss fetches
- InfluxDB write retry with DNS fallback reconnection
- Exponential backoff on consecutive background loop failures
- Pydantic response models for type-safe API responses
- All InfluxDB writes use `asyncio.to_thread` to avoid blocking

## Configuration
- `WEATHER_API_KEY` for OpenWeatherMap authentication
- `WEATHER_LOCATION` target city (default: Las Vegas)
- `WEATHER_API_AUTH_MODE` header or query (default: header)
- `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
- `INFLUXDB_FALLBACK_HOSTS` comma-separated fallback hostnames
- `CACHE_TTL_SECONDS` cache duration (default: 900)

## Testing
Run tests: `pytest tests/`
