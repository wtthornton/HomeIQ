# Smart Meter Service

**Real-Time Power Consumption Data for Device-Level Energy Monitoring**

**Port:** 8014
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
**Container:** `homeiq-smart-meter`
**Epic:** 31 (Direct InfluxDB Writes)

## Overview

The Smart Meter Service collects real-time power consumption data from smart meters and writes directly to InfluxDB, enabling whole-home and circuit-level energy monitoring to identify energy waste, detect phantom loads, and optimize device usage.

### Key Features

- **5-Minute Updates** - Power consumption every 5 minutes
- **Circuit-Level Breakdown** - Track individual circuits via Home Assistant sensors
- **Phantom Load Detection** - 3AM baseline analysis
- **High Consumption Alerting** - >10kW threshold monitoring
- **Direct InfluxDB Writes** - Epic 31 architecture pattern
- **Adapter Pattern** - Support for multiple meter types
- **Graceful Fallback** - Mock data if no adapter configured

## Quick Start

### Prerequisites

- Python 3.11+
- InfluxDB 2.x or 3.x
- Home Assistant (with power sensors) or compatible smart meter

### Running Locally

```bash
cd services/smart-meter-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8014
```

### Running with Docker

```bash
# Build and start
docker compose up -d smart-meter-service

# View logs
docker compose logs -f smart-meter-service

# Check health
curl http://localhost:8014/health
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `METER_TYPE` | `home_assistant` | Meter adapter type |
| `HOME_ASSISTANT_URL` | `http://homeassistant:8123` | HA URL |
| `HOME_ASSISTANT_TOKEN` | - | HA long-lived access token |
| `SERVICE_PORT` | `8014` | Service port |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `smart_meter_data` | InfluxDB bucket |

### Example `.env`

```bash
METER_TYPE=home_assistant
HOME_ASSISTANT_URL=http://homeassistant:8123
HOME_ASSISTANT_TOKEN=your_long_lived_token_here
SERVICE_PORT=8014
```

## Supported Adapters

### ✅ Home Assistant (Implemented)
**Type:** `home_assistant`

Pulls energy data from Home Assistant sensors. Automatically discovers power sensors.

**Expected HA Sensors:**
- Whole-home power: `sensor.total_power`, `sensor.power_total`, `sensor.home_power`, or `sensor.power_consumption` (in Watts)
- Daily energy: `sensor.daily_energy`, `sensor.energy_daily`, or `sensor.energy_today` (in kWh)
- Circuit sensors: Any sensor with:
  - `entity_id` starting with `sensor.power_*`
  - `device_class: power`
  - `unit_of_measurement: W` or `kW`

**Features:**
- Automatic sensor discovery
- Multiple sensor name patterns supported
- Handles unavailable/unknown states gracefully
- Converts kW to W automatically
- Falls back to mock data if connection fails

### 🚧 Future Adapters
- **Emporia Vue** - Hardware energy monitor
- **Sense** - AI-powered energy monitor
- **Shelly EM** - Local MQTT integration
- **IoTaWatt** - Local REST API

## InfluxDB Schema

### Measurement: smart_meter

**Tags:**
- `meter_type` - Adapter type (e.g., "home_assistant")

**Fields:**
- `total_power_w` (float) - Total home power (Watts)
- `daily_kwh` (float) - Daily energy consumption (kWh)

### Measurement: smart_meter_circuit

**Tags:**
- `circuit_name` - Circuit identifier

**Fields:**
- `power_w` (float) - Circuit power (Watts)
- `percentage` (float) - Percentage of total power

## Phantom Load Detection

The service monitors power consumption at 3 AM (typical baseline) to detect phantom loads - devices consuming power when the home should be idle.

**Threshold:** >200W at 3 AM considered high phantom load

## Automation Examples

### High Consumption Alert

```yaml
automation:
  - alias: "High Power Consumption Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.total_power
        above: 10000
    action:
      - service: notify.mobile_app
        data:
          message: "High power consumption detected: {{ states('sensor.total_power') }}W"
```

### Phantom Load Detection

```yaml
automation:
  - alias: "Phantom Load Alert"
    trigger:
      - platform: time
        at: "03:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.total_power
        above: 200
    action:
      - service: notify.mobile_app
        data:
          message: "High phantom load detected: {{ states('sensor.total_power') }}W at 3 AM"
```

## Related Documentation

- [Epic 31: Direct InfluxDB Writes](../../docs/prd/epic-31-weather-api-service-migration.md)
- [Weather API](../weather-api/README.md) - Similar Epic 31 pattern
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8014/health
- **API Docs:** http://localhost:8014/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced Home Assistant adapter documentation
- Added phantom load detection reference
- Epic 31 architecture context

### 2.0 (October 2025)
- Epic 31 migration to direct InfluxDB writes
- Home Assistant adapter implementation
- Circuit-level breakdown

### 1.0 (Initial Release)
- Generic smart meter integration
- Mock data adapter

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8014
**Epic:** 31 (Direct InfluxDB Writes)
