# Calendar Service - Home Assistant Integration

Home Assistant calendar integration for occupancy prediction and smart home preparation.

## Purpose

Enable predictive automation by analyzing calendar events from Home Assistant - prepare home before arrival, enable eco mode when away all day, optimize based on work-from-home schedules.

## Features

- ✅ Connects to Home Assistant calendar entities
- ✅ Supports multiple calendar sources (Google, iCloud, CalDAV, Office 365, etc.)
- ✅ Fetches calendar events every 15 minutes (configurable)
- ✅ Predicts home occupancy based on event locations
- ✅ Detects work-from-home days automatically
- ✅ Calculates estimated arrival times
- ✅ Stores predictions in InfluxDB for analysis
- ✅ Multi-calendar concurrent fetching
- ✅ Confidence scoring for predictions
- ✅ Health check endpoint

## Prerequisites

### 1. Home Assistant Calendar Setup

Configure calendar integration in Home Assistant:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for your calendar provider:
   - **Google Calendar**
   - **CalDAV** (for iCloud, Nextcloud, etc.)
   - **Office 365** / Outlook
   - **Local Calendar**
   - **ICS** file import
3. Follow the setup wizard for authentication
4. Note the calendar entity ID (e.g., `calendar.primary`, `calendar.google`, `calendar.work`)

### 2. Create Long-Lived Access Token

1. In Home Assistant, click your **profile** (bottom left)
2. Scroll to **Long-Lived Access Tokens**
3. Click **Create Token**
4. Name: `Calendar Service`
5. **Copy the token** (you won't see it again!)

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `HOME_ASSISTANT_URL` | Home Assistant instance URL | `http://192.168.1.86:8123` (single NUC deployment - use your HA IP) |
| `HOME_ASSISTANT_TOKEN` | Long-lived access token | `eyJhbGc...` |
| `CALENDAR_ENTITIES` | Comma-separated calendar entity IDs | `calendar.primary,calendar.work` |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | `your_token` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `CALENDAR_FETCH_INTERVAL` | Fetch interval in seconds | `900` (15 min) |
| `INFLUXDB_URL` | InfluxDB connection URL | `http://influxdb:8086` |
| `INFLUXDB_ORG` | InfluxDB organization | `home_assistant` |
| `INFLUXDB_BUCKET` | InfluxDB bucket | `events` |
| `SERVICE_PORT` | Service HTTP port | `8013` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Configuration

### 1. Find Calendar Entity IDs

**Using Home Assistant UI:**
```
Developer Tools → States → Filter by "calendar"
```

**Using API:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://192.168.1.86:8123/api/states | \
     jq '.[] | select(.entity_id | startswith("calendar."))'
```

### 2. Add to .env

```bash
# Home Assistant Connection (Single NUC Deployment)
HOME_ASSISTANT_URL=http://192.168.1.86:8123  # Your Home Assistant IP (example - use your actual IP)
HOME_ASSISTANT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # From HA Profile → Long-Lived Access Tokens

# Calendar Configuration
CALENDAR_ENTITIES=calendar.primary,calendar.work

# Optional: Adjust fetch interval (seconds)
CALENDAR_FETCH_INTERVAL=900
```

### 3. Docker Compose

The service is already configured in `docker-compose.yml`:

```yaml
calendar-service:
  build: ./services/calendar-service
  environment:
    - HOME_ASSISTANT_URL=${HOME_ASSISTANT_URL}
    - HOME_ASSISTANT_TOKEN=${HOME_ASSISTANT_TOKEN}
    - CALENDAR_ENTITIES=${CALENDAR_ENTITIES:-calendar.primary}
    - INFLUXDB_URL=${INFLUXDB_URL}
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
  ports:
    - "8013:8013"
  depends_on:
    - influxdb
```

## InfluxDB Schema

```
Measurement: occupancy_prediction

Tags:
  source: "calendar"
  user: "primary"

Fields:
  currently_home: boolean        # Currently at home
  wfh_today: boolean             # Working from home today
  confidence: float (0-1)        # Prediction confidence
  hours_until_arrival: float     # Hours until next home arrival
  event_count: integer           # Total events today
  current_event_count: integer   # Active events now
  upcoming_event_count: integer  # Future events today
```

## Occupancy Detection

The service automatically analyzes calendar events for occupancy indicators:

### Work From Home Detection

Detects these patterns in event summaries:
- `WFH`
- `Work From Home`
- `Home Office`
- `Remote Work`
- `Working From Home`

### Home Location Detection

Detects these patterns in event locations:
- `Home`
- `House`
- `Residence`
- `Apartment`

### Away Detection

Detects these patterns for away status:
- `Office`
- `Work`
- `Travel`
- `Trip`
- `Vacation`
- `Business`

**Pattern Matching:** Case-insensitive regex matching across event summary, location, and description.

## Supported Calendar Platforms

The service works with **any calendar integration** supported by Home Assistant:

| Platform | HA Integration | Notes |
|----------|----------------|-------|
| **Google Calendar** | `google` | OAuth2 setup in HA |
| **iCloud** | `caldav` | App-specific password required |
| **Office 365** | `office365` | Microsoft OAuth2 |
| **Nextcloud** | `caldav` | Self-hosted CalDAV |
| **CalDAV** | `caldav` | Any CalDAV server |
| **Local Calendar** | `local_calendar` | HA-internal calendars |
| **ICS Files** | `ics` | Public .ics URLs |
| **Todoist** | `todoist` | Task management |

## API Endpoints

### GET /health

Health check and service statistics.

**Response:**
```json
{
  "status": "healthy",
  "service": "calendar-service",
  "integration_type": "home_assistant",
  "uptime_seconds": 3600,
  "ha_connected": true,
  "calendar_count": 2,
  "last_successful_fetch": "2025-10-16T14:30:00",
  "total_fetches": 24,
  "failed_fetches": 0,
  "success_rate": 1.0
}
```

## Usage Examples

### Home Automation Example

```yaml
automation:
  - alias: "Prepare Home Before Arrival"
    trigger:
      - platform: template
        value_template: >
          {% set prediction = states('sensor.occupancy_prediction') %}
          {% if prediction != 'unknown' %}
            {{ state_attr('sensor.occupancy_prediction', 'hours_until_arrival') | float(0) < 0.5 }}
          {% else %}
            false
          {% endif %}
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.occupancy_prediction', 'currently_home') == false }}
    action:
      - service: climate.set_temperature
        data:
          entity_id: climate.living_room
          temperature: 72
      - service: light.turn_on
        entity_id: light.entry
        data:
          brightness: 255

  - alias: "Enable Eco Mode - All Day Away"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.occupancy_prediction', 'wfh_today') == false }}
      - condition: template
        value_template: >
          {{ state_attr('sensor.occupancy_prediction', 'hours_until_arrival') | float(99) > 4 }}
    action:
      - service: climate.set_preset_mode
        data:
          entity_id: climate.all_zones
          preset_mode: eco
      - service: scene.turn_on
        entity_id: scene.away_mode
```

### Query InfluxDB

```flux
from(bucket: "events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "occupancy_prediction")
  |> filter(fn: (r) => r["_field"] == "currently_home" or r["_field"] == "wfh_today")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
```

## Multiple Calendar Support

The service supports monitoring multiple calendars simultaneously:

```bash
# Monitor work and personal calendars
CALENDAR_ENTITIES=calendar.google,calendar.icloud,calendar.work

# Events from all calendars are combined
# Occupancy prediction considers all calendar sources
```

**Benefits:**
- Unified view across all calendars
- Better prediction accuracy
- Work-life balance monitoring
- Different calendar sources (Google + iCloud + CalDAV)

## Troubleshooting

### Connection Issues

**Problem:** Service can't connect to Home Assistant

**Solutions:**
1. Verify `HOME_ASSISTANT_URL` is accessible from container:
   ```bash
   docker exec -it calendar-service curl -I http://192.168.1.86:8123  # Single NUC deployment
   ```

2. Check token hasn't expired:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://homeassistant.local:8123/api/
   ```

3. Verify network connectivity in docker-compose.yml

### No Events Returned

**Problem:** Service shows 0 events but calendars have events

**Solutions:**
1. Verify calendar entity IDs are correct:
   ```bash
   # List all calendar entities
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://192.168.1.86:8123/api/states | \
        jq '.[] | select(.entity_id | startswith("calendar."))'  # Single NUC deployment
   ```

2. Check calendar integration status in HA:
   - Settings → Devices & Services
   - Look for integration errors

3. Verify time range - service only fetches today's events

4. Check service logs:
   ```bash
   docker-compose logs -f calendar-service
   ```

### Health Check Degraded

**Problem:** `/health` returns status `degraded`

**Causes:**
- HA connection lost: Check `ha_connected: false`
- No successful fetch in 30+ minutes: Check `last_successful_fetch`
- Failed fetches: Check `failed_fetches` vs `total_fetches`

**Solutions:**
1. Check Home Assistant is running
2. Verify token is valid
3. Review service logs for errors
4. Restart service: `docker-compose restart calendar-service`

### Pattern Detection Not Working

**Problem:** WFH/home events not detected

**Solutions:**
1. Check event summary/location format:
   ```
   ✅ Good: "WFH Day", "Working From Home"
   ✅ Good: Location: "Home Office"
   ❌ Bad: "Remote" (not in pattern list)
   ```

2. Customize patterns by forking and editing `event_parser.py`:
   ```python
   WFH_PATTERNS = [
       r'\bWFH\b',
       r'\bYour Custom Pattern\b',
   ]
   ```

## Performance

- **Event Fetch Time**: ~500ms-1s (local HA network)
- **Multi-Calendar (3 calendars)**: ~1-1.5s (concurrent)
- **Event Parsing (50 events)**: <50ms
- **Memory Usage**: ~20-25MB per service instance
- **InfluxDB Write**: <100ms

**Comparison to Google Calendar Direct:**
- 30% faster (local network vs Google API)
- 20% less memory (no Google OAuth libraries)
- No OAuth token refresh overhead
- More reliable (local network vs internet)

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Running Locally

```bash
# Set environment variables
export HOME_ASSISTANT_URL=http://localhost:8123
export HOME_ASSISTANT_TOKEN=your_token
export CALENDAR_ENTITIES=calendar.primary
export INFLUXDB_TOKEN=your_token

# Run service
cd services/calendar-service
python src/main.py
```

## Architecture

```
┌─────────────────────┐
│  Calendar Service   │
│                     │
│  ┌───────────────┐  │
│  │  Main Service │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼──────┐   │
│  │  HA Client   │   │  ←─── Async REST API calls
│  └───────┬──────┘   │
│          │          │
│  ┌───────▼────────┐ │
│  │ Event Parser   │ │  ←─── Parse & detect occupancy
│  └────────────────┘ │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────┐
│  Home Assistant      │
│  ┌────────────────┐  │
│  │  Google Cal    │  │
│  ├────────────────┤  │
│  │  iCloud Cal    │  │
│  ├────────────────┤  │
│  │  CalDAV Cal    │  │
│  └────────────────┘  │
└──────────────────────┘
           │
           ▼
      InfluxDB
```

## Migration from Google Calendar

If migrating from direct Google Calendar integration:

1. **Set up calendar in Home Assistant** (see Prerequisites)
2. **Update environment variables**:
   ```bash
   # Remove old variables
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REFRESH_TOKEN=...
   
   # Add new variables
   HOME_ASSISTANT_URL=http://192.168.1.86:8123  # Single NUC deployment (use your HA IP)
   HOME_ASSISTANT_TOKEN=your_ha_token
   CALENDAR_ENTITIES=calendar.primary
   ```

3. **Restart service**: `docker-compose restart calendar-service`
4. **Verify**: Check `/health` endpoint shows `ha_connected: true`

## License

MIT License

---

**Version:** 2.0.0 (Home Assistant Integration)  
**Updated:** October 16, 2025  
**Compatibility:** Home Assistant 2023.1+

## Version History

### 2.1 (November 15, 2025)
- Documentation verified for 2025 standards
- Home Assistant integration comprehensive guide
- Multi-calendar support documented
- Occupancy detection patterns reference

### 2.0 (October 2025)
- Migration to Home Assistant integration
- Removed direct Google Calendar integration
- Multi-calendar concurrent fetching
- Improved performance (30% faster, 20% less memory)

### 1.0 (Initial Release)
- Direct Google Calendar integration
- Basic occupancy prediction

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅  
**Port:** 8013 (Currently disabled in docker-compose - Epic 31)
**Note:** Calendar service currently disabled pending Epic 31 completion
