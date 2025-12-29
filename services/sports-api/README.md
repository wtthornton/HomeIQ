# Sports API Service

Home Assistant Team Tracker integration service for HomeIQ.

## Overview

This service integrates with Home Assistant's Team Tracker integration (HACS) to fetch sports data and write it to InfluxDB following Epic 31 architecture patterns.

## Features

- **Home Assistant Integration**: Polls HA REST API for Team Tracker sensors
- **Multi-League Support**: Supports all leagues supported by Team Tracker (NFL, NHL, MLB, NBA, etc.)
- **Game States**: Tracks PRE, IN, POST, BYE, and NOT_FOUND states
- **Comprehensive Attributes**: Captures all Team Tracker sensor attributes
- **InfluxDB Storage**: Writes normalized sports data directly to InfluxDB
- **Standalone Service**: No service dependencies (Epic 31 pattern)

## Architecture

Following Epic 31 architecture patterns:
- Standalone service (no service-to-service HTTP dependencies)
- Direct InfluxDB writes
- Query via data-api service
- Display on health-dashboard

## Configuration

### Environment Variables

```bash
# Home Assistant
HA_HTTP_URL=http://192.168.1.86:8123  # Home Assistant URL
HA_TOKEN=your_long_lived_access_token  # Long-lived access token

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=home_assistant
INFLUXDB_BUCKET=home_assistant_events

# Service
SERVICE_PORT=8005  # Default: 8005
SPORTS_POLL_INTERVAL=60  # Polling interval in seconds (default: 60)
```

### Home Assistant Setup

1. Install Team Tracker integration via HACS
2. Configure Team Tracker sensors in Home Assistant
3. Create a long-lived access token in Home Assistant
4. Set `HA_TOKEN` environment variable

## API Endpoints

### GET `/`
Service information

### GET `/health`
Health check endpoint

### GET `/metrics`
Service metrics (same as health)

### GET `/sports-data`
Get current sports data from Team Tracker sensors

**Response:**
```json
{
  "sensors": [
    {
      "entity_id": "sensor.team_tracker_seahawks",
      "state": "IN",
      "sport": "football",
      "league": "NFL",
      "team_abbr": "SEA",
      "team_name": "Seahawks",
      "team_score": 14,
      "opponent_score": 7,
      "quarter": "2",
      "clock": "5:23",
      ...
    }
  ],
  "count": 1,
  "last_update": "2025-12-29T10:00:00Z"
}
```

### GET `/stats`
Service statistics

## Team Tracker Sensor Attributes

The service captures all Team Tracker sensor attributes, including:

- **Basic Info**: sport, league, team_abbr, team_name, team_id
- **Opponent Info**: opponent_abbr, opponent_name, opponent_id
- **Scores**: team_score, opponent_score
- **Game State**: state (PRE, IN, POST, BYE, NOT_FOUND)
- **Game Progress**: quarter, clock, time_remaining
- **Location**: venue, location
- **Schedule**: date, kickoff_in
- **Media**: tv_network
- **And more**: See Team Tracker documentation for complete attribute list

## Data Flow

```
Home Assistant (Team Tracker Sensors)
        ↓
sports-api (Port 8005)
  - Polls HA REST API
  - Parses sensor data
  - Writes to InfluxDB
        ↓
InfluxDB (bucket: home_assistant_events)
  measurement: sports_data
        ↓
data-api (Port 8006)
  - Query endpoint for sports data
        ↓
health-dashboard (Port 3000)
  - Display sports data
```

## Development

### Run Locally

```bash
cd services/sports-api
pip install -r requirements.txt
python -m src.main
```

### Run with Docker

```bash
docker build -t sports-api .
docker run -p 8005:8005 \
  -e HA_HTTP_URL=http://192.168.1.86:8123 \
  -e HA_TOKEN=your_token \
  -e INFLUXDB_TOKEN=your_token \
  sports-api
```

## Testing

```bash
# Health check
curl http://localhost:8005/health

# Get sports data
curl http://localhost:8005/sports-data

# Get stats
curl http://localhost:8005/stats
```

## Related Services

- **data-api**: Queries sports data from InfluxDB
- **health-dashboard**: Displays sports data in UI
- **websocket-ingestion**: Main event ingestion service

## References

- [Team Tracker Integration](https://github.com/xyzroe/ha-teamtracker) - HACS integration
- [Epic 31 Architecture](./docs/EPIC_31_ARCHITECTURE.md) - Architecture patterns
- [HomeIQ Architecture](./docs/README_ARCHITECTURE_QUICK_REF.md) - Overall architecture

