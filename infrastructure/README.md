# Infrastructure Configuration

This directory contains environment configuration for all services.

## Setup

### Option 1: Manual Setup
Copy the templates and edit them:
```bash
cd infrastructure
cp env.websocket.template .env.websocket
cp env.weather.template .env.weather
cp env.influxdb.template .env.influxdb

# Edit files with your actual credentials
nano .env.websocket
nano .env.weather
nano .env.influxdb
```

### Option 2: Dashboard Setup (Recommended)
1. Start the services: `docker-compose up -d`
2. Open the dashboard: http://localhost:3000
3. Go to "Configuration" page
4. Edit credentials directly in the UI
5. Click "Save" and "Restart Service"

## Configuration Files

- `.env.websocket` - Home Assistant connection
- `.env.weather` - Weather API credentials
- `.env.influxdb` - InfluxDB connection
- `*.template` - Template files (safe to commit)

**⚠️ Never commit `.env.*` files to git!**

## Security

Files are automatically set to `chmod 600` (owner read/write only) when saved through the dashboard.

Manual setup:
```bash
chmod 600 .env.*
```

## Troubleshooting

### Configuration not loading?
1. Check file exists: `ls -la .env.*`
2. Check permissions: `ls -l .env.*` (should be `-rw-------`)
3. Check docker-compose.yml has `env_file` directive
4. Restart service: Dashboard > Service Control > Restart

### Can't edit through dashboard?
1. Check admin-api is running: `docker-compose ps admin-api`
2. Check logs: `docker-compose logs admin-api`
3. Check file permissions allow read/write

## Services Configuration

### websocket-ingestion
- **File**: `.env.websocket`
- **Required**: HA_URL, HA_TOKEN
- **Restart Required**: Yes

### weather-api  
- **File**: `.env.weather`
- **Required**: WEATHER_API_KEY, WEATHER_LAT, WEATHER_LON
- **Restart Required**: Yes

### influxdb connections
- **File**: `.env.influxdb`
- **Required**: INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
- **Restart Required**: Yes (all services using InfluxDB)

