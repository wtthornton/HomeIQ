# Carbon Intensity Service

**Grid Carbon Intensity Data for Carbon-Aware Automation**

**Port:** 8010
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
**Container:** `homeiq-carbon-intensity`
**Epic:** 31 (Direct InfluxDB Writes)

## Overview

The Carbon Intensity Service fetches real-time grid carbon intensity data from WattTime API and writes directly to InfluxDB, enabling Home Assistant automations to schedule energy-intensive tasks during periods of clean energy (low carbon intensity), reducing environmental impact and potentially saving costs.

### Key Features

- **15-Minute Updates** - Carbon intensity data every 15 minutes
- **Forecasting** - 1-hour and 24-hour forecasts
- **Smart Caching** - 15-minute TTL with graceful fallback
- **Direct InfluxDB Writes** - Epic 31 architecture pattern
- **Renewable Tracking** - Percentage of renewable energy in the grid
- **Health Monitoring** - Comprehensive health checks with fetch statistics

## Quick Start

### Prerequisites

- Python 3.11+
- WattTime API token (free from https://www.watttime.org/api-documentation/)
- InfluxDB 2.x or 3.x

### Get WattTime API Token

```bash
# Register (free tier: 100 calls/day, sufficient for 15-min intervals)
curl -X POST https://api.watttime.org/register \
  -d '{"username":"your_email@example.com","password":"your_password","email":"your_email@example.com","org":"your_org"}'

# Login to get token
curl -X POST https://api.watttime.org/login \
  -d '{"username":"your_email@example.com","password":"your_password"}'
```

### Running Locally

```bash
cd services/carbon-intensity-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8010
```

### Running with Docker

```bash
# Build and start
docker compose up -d carbon-intensity-service

# View logs
docker compose logs -f carbon-intensity-service

# Check health
curl http://localhost:8010/health
```

## API Endpoints

### `GET /health`
Service health check with fetch statistics

### `GET /current-intensity`
Get current carbon intensity data

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WATTTIME_API_TOKEN` | - | WattTime API token (required) |
| `GRID_REGION` | `CAISO_NORTH` | Grid region code |
| `SERVICE_PORT` | `8010` | Service port |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `carbon_data` | InfluxDB bucket |

### Example `.env`

```bash
WATTTIME_API_TOKEN=your_token_here
GRID_REGION=CAISO_NORTH
SERVICE_PORT=8010
```

## InfluxDB Schema

### Measurement: carbon_intensity

**Tags:**
- `region` - Grid region (e.g., "CAISO_NORTH")
- `grid_operator` - Grid operator abbreviation (e.g., "CAISO")

**Fields:**
- `carbon_intensity_gco2_kwh` (float) - Carbon intensity in gCO2/kWh
- `renewable_percentage` (float) - Percentage of renewable energy
- `fossil_percentage` (float) - Percentage of fossil fuel energy
- `forecast_1h` (float) - Forecast for next hour
- `forecast_24h` (float) - Forecast for 24 hours ahead

## Grid Regions

Common WattTime region codes:
- `CAISO_NORTH` - Northern California
- `CAISO_SOUTH` - Southern California
- `ERCOT` - Texas
- `PJM` - Mid-Atlantic and Midwest
- `MISO` - Midwest
- `NYISO` - New York
- `ISONE` - New England
- `SPP` - Southwest Power Pool

See WattTime API documentation for complete list.

## Automation Examples

### Charge EV During Clean Energy

```yaml
automation:
  - alias: "Charge EV During Clean Energy"
    trigger:
      - platform: numeric_state
        entity_id: sensor.grid_carbon_intensity
        below: 200
    condition:
      - condition: state
        entity_id: binary_sensor.ev_plugged_in
        state: "on"
      - condition: numeric_state
        entity_id: sensor.ev_battery_level
        below: 90
    action:
      - service: switch.turn_on
        entity_id: switch.ev_charger
      - service: notify.mobile_app
        data:
          message: "EV charging started - grid is clean ({{ states('sensor.grid_carbon_intensity') }} gCO2/kWh)"
```

## Query Examples

### Get Current Carbon Intensity

```flux
from(bucket: "carbon_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "carbon_intensity")
  |> filter(fn: (r) => r._field == "carbon_intensity_gco2_kwh")
  |> last()
```

### Find Low-Carbon Periods

```flux
from(bucket: "carbon_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "carbon_intensity")
  |> filter(fn: (r) => r._field == "carbon_intensity_gco2_kwh")
  |> filter(fn: (r) => r._value < 200)
```

## Related Documentation

- [Epic 31: Direct InfluxDB Writes](../../docs/prd/epic-31-weather-api-service-migration.md)
- [Weather API](../weather-api/README.md) - Similar Epic 31 pattern
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8010/health
- **API Docs:** http://localhost:8010/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced API endpoint documentation
- Added grid region reference
- Epic 31 architecture context

### 2.0 (October 2025)
- Epic 31 migration to direct InfluxDB writes
- Added 1-hour and 24-hour forecasts

### 1.0 (Initial Release)
- WattTime API integration
- 15-minute carbon intensity fetching

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8010
**Epic:** 31 (Direct InfluxDB Writes)
