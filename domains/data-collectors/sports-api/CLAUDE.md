# Sports API Service

Integrates Home Assistant Team Tracker sensors with InfluxDB for sports data time-series.

## Architecture
- FastAPI application with `SportsService` class in `src/main.py`
- Home Assistant REST API polling for Team Tracker sensors
- InfluxDB storage with fallback hostname support
- Rate-limited API endpoints with API key authentication

## Key Patterns
- Polls HA `/api/states` and filters for `team_tracker` entity IDs
- Parses game states: PRE, IN, POST, BYE, NOT_FOUND
- Extracts automation attributes: colors, winner flags, events, plays
- InfluxDB write retry with DNS fallback reconnection
- Exponential backoff with jitter on consecutive loop failures
- All InfluxDB writes use `asyncio.to_thread` to avoid blocking

## Configuration
- `HA_HTTP_URL` / `HA_TOKEN` for Home Assistant connection
- `SPORTS_POLL_INTERVAL` polling interval in seconds (default: 60)
- `SPORTS_API_KEY` for endpoint authentication
- `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
- `INFLUXDB_FALLBACK_HOSTS` comma-separated fallback hostnames

## Testing
Run tests: `pytest tests/`
