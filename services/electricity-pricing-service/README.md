# Electricity Pricing Service

**Real-Time Electricity Pricing and Forecasts for Cost-Aware Automation**

**Port:** 8011
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
**Container:** `homeiq-electricity-pricing`
**Epic:** 31 (Direct InfluxDB Writes)

## Overview

The Electricity Pricing Service fetches real-time electricity pricing and forecasts from utility APIs and writes directly to InfluxDB, enabling Home Assistant automations to schedule high-energy tasks (EV charging, pool pumps, water heaters) during cheapest electricity hours, reducing energy costs by 20-40%.

### Key Features

- **Hourly Updates** - Electricity pricing every hour
- **24-Hour Forecasts** - Price predictions for optimal scheduling
- **Cheapest Hours API** - Identify optimal time windows
- **Smart Caching** - 1-hour TTL with graceful fallback
- **Direct InfluxDB Writes** - Epic 31 architecture pattern
- **Multi-Provider Support** - Awattar (more coming soon)
- **Peak Period Detection** - Identify high-cost periods

## Quick Start

### Prerequisites

- Python 3.11+
- InfluxDB 2.x or 3.x
- Supported utility provider (Awattar, Tibber, Octopus Energy)

### Running Locally

```bash
cd services/electricity-pricing-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8011
```

### Running with Docker

```bash
# Build and start
docker compose up -d electricity-pricing-service

# View logs
docker compose logs -f electricity-pricing-service

# Check health
curl http://localhost:8011/health
```

## API Endpoints

### `GET /health`
Service health check

### `GET /cheapest-hours?hours=4`
Get cheapest hours in next 24 hours

**Response:**
```json
{
  "cheapest_hours": [2, 3, 4, 5],
  "provider": "awattar",
  "timestamp": "2025-11-15T16:00:00"
}
```

### `GET /current-price`
Get current electricity price

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PRICING_PROVIDER` | `awattar` | Provider name |
| `PRICING_API_KEY` | - | API key (if required by provider) |
| `SERVICE_PORT` | `8011` | Service port |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `pricing_data` | InfluxDB bucket |

### Example `.env`

```bash
PRICING_PROVIDER=awattar
SERVICE_PORT=8011
```

## Supported Providers

### Awattar (Default)
- **Region:** Germany, Austria
- **API:** https://api.awattar.de
- **Cost:** Free
- **Update Frequency:** Hourly
- **Currency:** EUR

**Future Providers:**
- Tibber (Nordic countries)
- Octopus Energy (UK)
- PG&E (California)

## InfluxDB Schema

### Measurement: electricity_pricing

**Tags:**
- `provider` - Provider name (e.g., "awattar")
- `currency` - Currency code (EUR, USD, GBP)

**Fields:**
- `current_price` (float) - Current price per kWh
- `peak_period` (boolean) - True if in peak pricing period

### Measurement: electricity_pricing_forecast

**Tags:**
- `provider` - Provider name

**Fields:**
- `price` (float) - Forecast price per kWh
- `hour_offset` (integer) - Hours from now (0-23)

## Automation Examples

### Charge EV During Cheap Hours

```yaml
automation:
  - alias: "Charge EV During Cheap Electricity"
    trigger:
      - platform: time_pattern
        hours: "*"
    condition:
      - condition: template
        value_template: >
          {{ now().hour in [2, 3, 4, 5] }}
      - condition: numeric_state
        entity_id: sensor.ev_battery_level
        below: 90
    action:
      - service: switch.turn_on
        entity_id: switch.ev_charger
      - service: notify.mobile_app
        data:
          message: "EV charging during cheap electricity hours"
```

## Query Examples

### Get Current Price

```flux
from(bucket: "pricing_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "electricity_pricing")
  |> filter(fn: (r) => r._field == "current_price")
  |> last()
```

### Find Cheapest 4-Hour Window

```flux
from(bucket: "pricing_data")
  |> range(start: -1h, stop: now())
  |> filter(fn: (r) => r._measurement == "electricity_pricing_forecast")
  |> filter(fn: (r) => r._field == "price")
  |> sort(columns: ["_value"])
  |> limit(n: 4)
```

## Related Documentation

- [Epic 31: Direct InfluxDB Writes](../../docs/prd/epic-31-weather-api-service-migration.md)
- [Weather API](../weather-api/README.md) - Similar Epic 31 pattern
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8011/health
- **API Docs:** http://localhost:8011/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced API endpoint documentation
- Added provider reference
- Epic 31 architecture context

### 2.0 (October 2025)
- Epic 31 migration to direct InfluxDB writes
- Added cheapest-hours API endpoint

### 1.0 (Initial Release)
- Awattar integration
- Hourly price fetching

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8011
**Epic:** 31 (Direct InfluxDB Writes)
