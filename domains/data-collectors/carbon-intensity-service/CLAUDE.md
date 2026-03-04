# Carbon Intensity Service

Fetches grid carbon intensity from the WattTime API and stores time-series data in InfluxDB.

## Architecture
- Single async service class (`CarbonIntensityService`) in `src/main.py`
- WattTime v3 API integration with automatic token refresh
- InfluxDB time-series storage via `influxdb_client_3`
- aiohttp web server for health check endpoint

## Key Patterns
- Cache-first fetching with configurable TTL
- Token refresh with 5-minute buffer before expiry
- Transient error retry with exponential backoff (429, 5xx)
- Auth retry on 401 with automatic token refresh
- All InfluxDB writes use `asyncio.to_thread` to avoid blocking

## Configuration
- `WATTTIME_USERNAME` / `WATTTIME_PASSWORD` for authentication
- `GRID_REGION` for target grid (default: CAISO_NORTH)
- `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
- `FETCH_INTERVAL` polling interval in seconds (default: 900)

## Testing
Run tests: `pytest tests/`
