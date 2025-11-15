# Weather API Service

**OpenWeatherMap Integration and Weather Data Storage for HomeIQ**

**Port:** 8009
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
**Container:** `homeiq-weather-api`
**Epic:** 31 (Direct InfluxDB Writes)

## Overview

The Weather API Service provides real-time and historical weather data through a REST API, replacing the previous event enrichment pattern. Weather data is fetched from OpenWeatherMap, cached for efficiency, and written directly to InfluxDB for historical queries and analytics.

### Key Features

- **Real-Time Weather** - Current conditions from OpenWeatherMap
- **24-Hour Forecast** - Weather predictions with hourly granularity
- **Historical Queries** - Access past weather data from InfluxDB
- **Smart Caching** - 15-minute TTL to reduce API calls and costs
- **Direct InfluxDB Writes** - Epic 31 architecture pattern
- **Prometheus Metrics** - Performance and cache statistics
- **Health Monitoring** - Comprehensive health checks with component status

## Quick Start

### Prerequisites

- Python 3.11+
- OpenWeatherMap API key
- InfluxDB 2.x or 3.x

### Running Locally

```bash
cd services/weather-api

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8009
```

### Running with Docker

```bash
# Build and start
docker compose up -d weather-api

# View logs
docker compose logs -f weather-api

# Check health
curl http://localhost:8009/health
```

## API Endpoints

### Core Endpoints

#### `GET /`
Service information and version
```bash
curl http://localhost:8009/
```

#### `GET /health`
Health check with component status
```bash
curl http://localhost:8009/health
```

Response:
```json
{
  "status": "healthy",
  "service": "weather-api",
  "timestamp": "2025-11-15T12:00:00Z",
  "components": {
    "openweathermap": "healthy",
    "influxdb": "healthy",
    "cache": "healthy"
  },
  "cache_stats": {
    "hit_rate": 0.92,
    "size": 5
  }
}
```

#### `GET /metrics`
Prometheus-compatible metrics
```bash
curl http://localhost:8009/metrics
```

### Weather Endpoints

#### `GET /current-weather`
Current weather conditions
```bash
curl http://localhost:8009/current-weather
```

Query parameters:
- `location` (optional): Override default location

Response:
```json
{
  "location": "Las Vegas",
  "temperature": 72.5,
  "feels_like": 70.3,
  "humidity": 35,
  "pressure": 1013,
  "wind_speed": 5.2,
  "wind_direction": 180,
  "conditions": "clear sky",
  "timestamp": "2025-11-15T12:00:00Z"
}
```

#### `GET /forecast`
24-hour weather forecast
```bash
curl http://localhost:8009/forecast
```

Response:
```json
{
  "location": "Las Vegas",
  "forecast": [
    {
      "time": "2025-11-15T13:00:00Z",
      "temperature": 73.2,
      "conditions": "clear sky",
      "precipitation_probability": 0.0
    }
  ]
}
```

#### `GET /historical`
Historical weather queries from InfluxDB
```bash
curl "http://localhost:8009/historical?start=2025-11-01T00:00:00Z&end=2025-11-15T23:59:59Z"
```

Query parameters:
- `start`: Start timestamp (ISO 8601)
- `end`: End timestamp (ISO 8601)
- `location` (optional): Filter by location

#### `GET /cache/stats`
Cache performance statistics
```bash
curl http://localhost:8009/cache/stats
```

Response:
```json
{
  "hit_rate": 0.92,
  "total_requests": 1000,
  "cache_hits": 920,
  "cache_misses": 80,
  "cache_size": 5,
  "ttl_seconds": 900
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEATHER_API_KEY` | - | OpenWeatherMap API key (required) |
| `WEATHER_LOCATION` | `Las Vegas` | Default location for queries |
| `SERVICE_PORT` | `8009` | Service port |
| `CACHE_TTL_SECONDS` | `900` | Cache TTL (15 minutes) |
| `FETCH_INTERVAL_SECONDS` | `300` | Background fetch interval (5 minutes) |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `weather_data` | InfluxDB bucket |
| `LOG_LEVEL` | `INFO` | Logging level |

### Example `.env`

```bash
# OpenWeatherMap API
WEATHER_API_KEY=your_api_key_here
WEATHER_LOCATION=Las Vegas

# Cache Configuration
CACHE_TTL_SECONDS=900  # 15 minutes
FETCH_INTERVAL_SECONDS=300  # 5 minutes

# Service Configuration
SERVICE_PORT=8009

# InfluxDB (Epic 31)
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_token
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=weather_data

# Logging
LOG_LEVEL=INFO
```

## Architecture

### Data Flow (Epic 31)

```
┌──────────────────────────┐
│ OpenWeatherMap API       │
│ (External)               │
└────────┬─────────────────┘
         │
         │ Fetch every 5 minutes
         ↓
┌──────────────────────────┐
│ Weather API Service      │
│ (Port 8009)              │
│                          │
│ ┌──────────────────────┐ │
│ │ Cache (15-min TTL)   │ │
│ │ 92%+ hit rate        │ │
│ └──────────────────────┘ │
└────────┬─────────────────┘
         │
         │ Direct writes (Epic 31)
         ↓
┌──────────────────────────┐
│ InfluxDB                 │
│ Bucket: weather_data     │
│ Measurement: weather     │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│ Consumers                │
│ - Health Dashboard       │
│ - Data API queries       │
│ - AI Automation Service  │
└──────────────────────────┘
```

### Component Architecture

```
src/
├── main.py                # FastAPI application
├── config.py              # Pydantic settings
├── weather_client.py      # OpenWeatherMap client
├── cache.py               # Weather data cache
├── influxdb_writer.py     # Direct InfluxDB writes
└── background_tasks.py    # Periodic weather fetching
```

## Performance

### Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| Cached weather | <10ms | <50ms | >100ms |
| Uncached weather | <500ms | <1s | >2s |
| Historical queries | <200ms | <500ms | >1s |
| InfluxDB writes | <50ms | <100ms | >200ms |

### Resource Usage

- **Memory:** ~50-100MB
- **CPU:** <5% typical
- **Network:** ~1KB per weather fetch
- **InfluxDB:** ~100 bytes per data point

### Cache Performance

- **Hit Rate Target:** >90%
- **TTL:** 15 minutes
- **Background Fetch:** Every 5 minutes
- **Cost Savings:** ~92% reduction in API calls

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn src.main:app --reload --port 8009

# Access API docs
http://localhost:8009/docs
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test
pytest tests/test_weather_client.py -v
```

### Manual Testing

```bash
# Test health
curl http://localhost:8009/health

# Test current weather
curl http://localhost:8009/current-weather

# Test forecast
curl http://localhost:8009/forecast

# Test cache stats
curl http://localhost:8009/cache/stats
```

## Monitoring

### Structured Logging

Logs include:
- API request/response timing
- OpenWeatherMap API calls and responses
- Cache hits/misses
- InfluxDB write status
- Error tracking with stack traces

### Prometheus Metrics

- `weather_api_requests_total` - Total API requests
- `weather_cache_hits_total` - Cache hits
- `weather_cache_misses_total` - Cache misses
- `weather_openweathermap_calls_total` - External API calls
- `weather_influxdb_writes_total` - InfluxDB writes
- `weather_api_response_time_seconds` - Response time histogram

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker compose logs weather-api
```

**Common issues:**
- Missing `WEATHER_API_KEY` → Add OpenWeatherMap API key
- InfluxDB not accessible → Check `INFLUXDB_URL` and token
- Port 8009 in use → Change `SERVICE_PORT`

### OpenWeatherMap API Errors

**Symptoms:**
- 401 Unauthorized → Invalid API key
- 429 Too Many Requests → Rate limit exceeded
- 404 Not Found → Invalid location

**Solutions:**
- Verify API key: https://home.openweathermap.org/api_keys
- Check rate limits (60 calls/minute on free tier)
- Use valid city names or coordinates

### Cache Not Working

**Check cache stats:**
```bash
curl http://localhost:8009/cache/stats
```

**Low hit rate causes:**
- TTL too short → Increase `CACHE_TTL_SECONDS`
- Multiple locations queried → Cache is per-location
- Service restarting frequently → Cache clears on restart

### InfluxDB Write Failures

**Check InfluxDB:**
```bash
curl http://localhost:8086/health
```

**Verify token:**
```bash
curl -H "Authorization: Token $INFLUXDB_TOKEN" \
  http://localhost:8086/api/v2/buckets
```

## Dependencies

### Core

```
fastapi==0.121.2            # Web framework
uvicorn[standard]==0.38.0   # ASGI server
pydantic==2.12.4            # Data validation
python-dotenv==1.2.1        # Environment variables
```

### HTTP & Data

```
aiohttp==3.13.2             # Async HTTP client for OpenWeatherMap
influxdb3-python[pandas]==0.3.0  # InfluxDB 3.x client
```

### Development & Testing

```
pytest==8.3.3               # Testing framework
pytest-asyncio==0.23.0      # Async test support
httpx==0.27.2               # HTTP testing client
```

## Related Documentation

- [Epic 31: Direct InfluxDB Writes](../../docs/prd/epic-31-weather-api-service-migration.md)
- [Story 31.1: Service Foundation](../../docs/stories/31.1-weather-api-service-foundation.md)
- [Weather Architecture Analysis](../../implementation/analysis/WEATHER_ARCHITECTURE_ANALYSIS.md)
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8009/health
- **API Docs:** http://localhost:8009/docs

## Implementation Status

- ✅ **Story 31.1:** Service Foundation (FastAPI, Docker, health checks)
- ✅ **Story 31.2:** Data Collection & InfluxDB Persistence
- ✅ **Story 31.3:** API Endpoints & Query Support
- ✅ **Story 31.4:** Event Pipeline Decoupling
- ✅ **Story 31.5:** Dashboard Integration

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive API endpoint documentation
- Improved troubleshooting section
- Added performance targets and metrics
- Updated Epic 31 architecture context

### 2.0 (October 2025)
- Epic 31 migration to direct InfluxDB writes
- Removed enrichment pipeline dependency
- Added smart caching (15-minute TTL)
- Background fetch every 5 minutes

### 1.0 (Initial Release)
- OpenWeatherMap integration
- Basic weather data fetching
- Event enrichment pattern (deprecated)

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8009
**Epic:** 31 (Direct InfluxDB Writes)
