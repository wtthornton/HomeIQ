# External Data Sources Fix Summary

**Date:** $(Get-Date -Format "yyyy-MM-dd")
**Status:** Configuration Updated - Ready for API Keys

## Overview

Fixed missing environment variables for external data source services that were showing errors in the dashboard.

## Services Fixed

### 1. Carbon Intensity Service (Port 8010) ❌ → ✅
**Status:** Configuration added, requires API credentials

**Required Environment Variables:**
- `WATTTIME_USERNAME` - WattTime API username
- `WATTTIME_PASSWORD` - WattTime API password
- `GRID_REGION` - Grid region (default: CAISO_NORTH)
- `INFLUXDB_TOKEN` - InfluxDB authentication token

**API Setup:**
1. Register at https://watttime.org
2. Get username and password
3. Add to `.env` file

**Alternative:** Can use `WATTTIME_API_TOKEN` instead, but it expires every 30 minutes (not recommended)

### 2. Air Quality Service (Port 8012) ❌ → ✅
**Status:** Configuration added, requires API key

**Required Environment Variables:**
- `WEATHER_API_KEY` - OpenWeatherMap API key (shared with weather-api service)
- `LATITUDE` - Location latitude (default: 36.1699 - Las Vegas)
- `LONGITUDE` - Location longitude (default: -115.1398 - Las Vegas)
- `INFLUXDB_TOKEN` - InfluxDB authentication token

**Optional:**
- `HOME_ASSISTANT_URL` / `HA_HTTP_URL` - For automatic location detection
- `HOME_ASSISTANT_TOKEN` / `HA_TOKEN` - Home Assistant authentication

**API Setup:**
1. Register at https://openweathermap.org/api
2. Get API key (free tier available)
3. Add to `.env` file as `WEATHER_API_KEY`

### 3. Electricity Pricing Service (Port 8011) ❌ → ✅
**Status:** Configuration added, no API key required for awattar

**Required Environment Variables:**
- `PRICING_PROVIDER` - Provider name (default: awattar)
- `PRICING_API_KEY` - Optional (not needed for awattar)
- `INFLUXDB_TOKEN` - InfluxDB authentication token

**Note:** Awattar provider is free and doesn't require an API key. Service should work once started.

### 4. Calendar Service (Port 8013) ⚠️
**Status:** Currently commented out in docker-compose.yml

**Required Environment Variables (when enabled):**
- `HA_HTTP_URL` / `HA_WS_URL` - Home Assistant URL
- `HA_TOKEN` / `HOME_ASSISTANT_TOKEN` - Home Assistant long-lived access token
- `CALENDAR_ENTITIES` - Comma-separated list of calendar entities (default: calendar.primary)
- `CALENDAR_FETCH_INTERVAL` - Fetch interval in seconds (default: 900)
- `INFLUXDB_TOKEN` - InfluxDB authentication token

**To Enable:**
1. Uncomment the calendar service section in `docker-compose.yml` (lines 480-524)
2. Ensure Home Assistant token is configured
3. Restart with: `docker-compose --profile production up -d calendar`

## Changes Made

### 1. Environment Variables Added to .env

The following variables were added to `.env` with placeholder values:

```bash
# Carbon Intensity
WATTTIME_USERNAME=your_watttime_username
WATTTIME_PASSWORD=your_watttime_password
GRID_REGION=CAISO_NORTH

# Air Quality
LATITUDE=36.1699
LONGITUDE=-115.1398

# Electricity Pricing
PRICING_PROVIDER=awattar
PRICING_API_KEY=

# Calendar Service
CALENDAR_ENTITIES=calendar.primary
CALENDAR_FETCH_INTERVAL=900
```

### 2. Script Created

Created `scripts/fix-external-data-sources-env.py` to:
- Check for missing environment variables
- Add missing variables with appropriate defaults
- Provide setup instructions

## Next Steps

### Step 1: Add API Keys to .env

1. **Open `.env` file** in the project root
2. **Replace placeholder values** with actual API keys:

```bash
# WattTime API (for Carbon Intensity)
WATTTIME_USERNAME=your_actual_username
WATTTIME_PASSWORD=your_actual_password

# OpenWeatherMap API (for Air Quality)
WEATHER_API_KEY=your_actual_api_key_here

# Home Assistant Token (for Calendar Service, if enabled)
HA_TOKEN=your_long_lived_access_token
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
```

### Step 2: Start Services

Services use the `production` profile. Start them with:

```bash
# Start all external data source services
docker-compose --profile production up -d carbon-intensity air-quality electricity-pricing

# Or start all services
docker-compose --profile production up -d
```

### Step 3: Verify Services

Check service health:

```powershell
# Check service status
docker-compose --profile production ps carbon-intensity air-quality electricity-pricing

# Check health endpoints
Invoke-WebRequest -Uri "http://localhost:8010/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8011/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8012/health" -UseBasicParsing

# Check logs
docker-compose --profile production logs carbon-intensity --tail 50
docker-compose --profile production logs air-quality --tail 50
docker-compose --profile production logs electricity-pricing --tail 50
```

### Step 4: Enable Calendar Service (Optional)

If you want to enable the calendar service:

1. **Uncomment** the calendar service in `docker-compose.yml` (lines 480-524)
2. **Add** `env_file: - .env` to the calendar service configuration
3. **Ensure** `HA_TOKEN` or `HOME_ASSISTANT_TOKEN` is set in `.env`
4. **Start** the service:
   ```bash
   docker-compose --profile production up -d calendar
   ```

## Service Dependencies

All services require:
- **InfluxDB** - Must be running and accessible
- **InfluxDB Token** - Must be set in `.env` as `INFLUXDB_TOKEN`

## Troubleshooting

### Service Won't Start

1. **Check if production profile is used:**
   ```bash
   docker-compose --profile production ps
   ```

2. **Check logs for errors:**
   ```bash
   docker-compose --profile production logs <service-name> --tail 100
   ```

3. **Verify environment variables:**
   ```bash
   docker-compose --profile production config | Select-String -Pattern "WATTTIME|WEATHER|PRICING"
   ```

### Service Shows Error in Dashboard

1. **Check service health endpoint:**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:<port>/health" -UseBasicParsing
   ```

2. **Common issues:**
   - Missing API keys → Add to `.env` and restart service
   - Invalid API keys → Verify keys are correct
   - InfluxDB connection issues → Check `INFLUXDB_TOKEN` and InfluxDB status
   - Network issues → Verify services can reach external APIs

### API Key Issues

- **WattTime:** Free tier limited to 1-2 US regions. Paid tier required for international.
- **OpenWeatherMap:** Free tier has rate limits. Check quota if requests fail.
- **Awattar:** No API key needed, but service is for European markets.

## Files Modified

1. `.env` - Added missing environment variables
2. `scripts/fix-external-data-sources-env.py` - Created script to check and fix env vars

## References

- WattTime API: https://watttime.org
- OpenWeatherMap API: https://openweathermap.org/api
- Awattar API: https://www.awattar.de (German electricity market)
- Home Assistant Long-Lived Tokens: Profile → Security → Long-Lived Access Tokens

