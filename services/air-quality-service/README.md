# Air Quality Service

**Real-Time AQI Data for Health-Based Automation**

**Port:** 8012
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
**Container:** `homeiq-air-quality`
**Epic:** 31 (Direct InfluxDB Writes)

## Overview

The Air Quality Service fetches real-time Air Quality Index (AQI) data from AirNow API and writes directly to InfluxDB, enabling Home Assistant automations to respond to air quality changes - close windows when AQI is poor, adjust HVAC filtration, send health alerts.

### Key Features

- **Hourly Updates** - AQI data every hour from AirNow
- **Multi-Parameter Tracking** - PM2.5, PM10, Ozone levels
- **Smart Caching** - 1-hour TTL with graceful fallback
- **Direct InfluxDB Writes** - Epic 31 architecture pattern
- **Health Monitoring** - Comprehensive health checks
- **AQI Categories** - Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous

## Quick Start

### Prerequisites

- Python 3.11+
- AirNow API key (free from https://docs.airnowapi.org/)
- InfluxDB 2.x or 3.x

### Running Locally

```bash
cd services/air-quality-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8012
```

### Running with Docker

```bash
# Build and start
docker compose up -d air-quality-service

# View logs
docker compose logs -f air-quality-service

# Check health
curl http://localhost:8012/health
```

## API Endpoints

### `GET /health`
Service health check with component status

### `GET /current-aqi`
Get current air quality data

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRNOW_API_KEY` | - | AirNow API key (required) |
| `LATITUDE` | `36.1699` | Location latitude |
| `LONGITUDE` | `-115.1398` | Location longitude |
| `SERVICE_PORT` | `8012` | Service port |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `air_quality_data` | InfluxDB bucket |

### Example `.env`

```bash
AIRNOW_API_KEY=your_api_key_here
LATITUDE=36.1699
LONGITUDE=-115.1398
SERVICE_PORT=8012
```

## InfluxDB Schema

### Measurement: air_quality

**Tags:**
- `location` - "lat,lon" format
- `category` - AQI category (Good, Moderate, Unhealthy, etc.)
- `parameter` - Pollutant (PM2.5, PM10, Ozone)

**Fields:**
- `aqi` (integer) - Air Quality Index (0-500)
- `pm25` (integer) - PM2.5 concentration
- `pm10` (integer) - PM10 concentration
- `ozone` (integer) - Ozone concentration

## AQI Categories

| AQI Range | Category | Health Implications |
|-----------|----------|---------------------|
| 0-50 | Good | Safe for everyone |
| 51-100 | Moderate | Unusually sensitive people should limit outdoor exertion |
| 101-150 | Unhealthy for Sensitive Groups | Sensitive groups should reduce outdoor exertion |
| 151-200 | Unhealthy | Everyone should reduce outdoor exertion |
| 201-300 | Very Unhealthy | Everyone should avoid outdoor exertion |
| 301-500 | Hazardous | Everyone should remain indoors |

## Automation Examples

### Close Windows When AQI Poor

```yaml
automation:
  - alias: "Close Windows When AQI Poor"
    trigger:
      - platform: numeric_state
        entity_id: sensor.aqi
        above: 100
    action:
      - service: cover.close_cover
        entity_id: cover.all_windows
      - service: notify.mobile_app
        data:
          message: "Poor air quality - windows closed (AQI: {{ states('sensor.aqi') }})"
```

## Related Documentation

- [Epic 31: Direct InfluxDB Writes](../../docs/prd/epic-31-weather-api-service-migration.md)
- [Weather API](../weather-api/README.md) - Similar Epic 31 pattern
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8012/health
- **API Docs:** http://localhost:8012/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced API endpoint documentation
- Added comprehensive AQI category reference
- Epic 31 architecture context

### 2.0 (October 2025)
- Epic 31 migration to direct InfluxDB writes
- Smart caching with 1-hour TTL

### 1.0 (Initial Release)
- AirNow API integration
- Hourly AQI fetching

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8012
**Epic:** 31 (Direct InfluxDB Writes)
