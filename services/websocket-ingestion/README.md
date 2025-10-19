# WebSocket Ingestion Service

The WebSocket Ingestion Service connects to Home Assistant's WebSocket API to capture real-time state change events and store them in InfluxDB with optional weather enrichment.

## Features

- 🔌 **WebSocket Connection** - Real-time connection to Home Assistant API
- 🔄 **Infinite Retry** - Never gives up on reconnection (NEW - October 2025)
- 🔐 **Secure Authentication** - Token-based authentication with validation
- 🌤️ **Weather Enrichment** - Automatic weather data enrichment for events
- 📊 **Event Processing** - Captures and normalizes state_changed events
- 🔍 **Device Discovery** - Automatic discovery of devices and entities (NEW - stores directly to SQLite)
- 📈 **Health Monitoring** - Comprehensive health checks and metrics
- 🔁 **Automatic Reconnection** - Smart exponential backoff on connection failures
- 💾 **Direct SQLite Storage** - Devices/entities stored directly to SQLite via data-api (October 2025)

## Network Resilience (NEW)

### Infinite Retry Strategy

The service now includes **infinite retry capability** by default:

**Key Features:**
- ✅ Never stops trying to connect
- ✅ Works even when started without network
- ✅ Automatically recovers from extended outages
- ✅ Smart exponential backoff (up to 5 minutes)
- ✅ Clear logging with retry indicators

**Default Behavior:**
```
Attempt 1/∞ in 1.0s
Attempt 2/∞ in 2.0s
Attempt 3/∞ in 4.0s
...
Attempt 10/∞ in 300.0s  (capped at 5 minutes)
Attempt 11/∞ in 300.0s
... continues forever ...
```

### Configuration

**Environment Variables:**
```bash
# -1 = infinite retry (recommended for production)
# Or set a specific number (e.g., 100)
WEBSOCKET_MAX_RETRIES=-1

# Maximum delay between retry attempts (seconds)
WEBSOCKET_MAX_RETRY_DELAY=300  # 5 minutes default
```

**Docker Compose:**
```yaml
websocket-ingestion:
  environment:
    - WEBSOCKET_MAX_RETRIES=-1
    - WEBSOCKET_MAX_RETRY_DELAY=300
```

### Monitoring Retry Status

**Check Logs:**
```bash
# View recent logs
docker logs homeiq-websocket --tail 50

# Follow live logs
docker logs -f homeiq-websocket

# Look for retry messages
docker logs homeiq-websocket | grep "Reconnection attempt"
```

**Check Health Status:**
```bash
# Get health status
curl http://localhost:8001/health

# Example response:
{
  "status": "healthy",  # or "unhealthy" if retrying
  "connection": {
    "is_running": true,
    "connection_attempts": 15,
    "successful_connections": 1,
    "failed_connections": 14
  }
}
```

## Device Discovery (NEW - October 2025)

### How It Works

**Trigger**: Runs automatically on every WebSocket connection to Home Assistant

**Process**:
1. Connect to HA at configured URL (e.g., http://192.168.1.86:8123)
2. Authenticate with long-lived token
3. Query device registry: `config/device_registry/list`
4. Query entity registry: `config/entity_registry/list`
5. **POST to data-api** → Stores in SQLite (primary storage) ✅
6. (Optional) Store snapshot in InfluxDB for history tracking

**Data Flow**:
```
Home Assistant @ 192.168.1.86:8123
         ↓ WebSocket Discovery
  Discovery Service
         ↓ HTTP POST
    Data-API → SQLite ✅ PRIMARY
         ↓ Served via
    /api/devices, /api/entities
```

**Frequency**: 
- On initial connection
- On reconnection after disconnect
- Real-time updates via registry event subscriptions

### Discovery Configuration

```bash
# Data API endpoint for device/entity storage
DATA_API_URL=http://homeiq-data-api:8006  # Container name (Docker network)

# Optional: Enable InfluxDB historical tracking (disabled by default)
STORE_DEVICE_HISTORY_IN_INFLUXDB=false
```

**Note**: Device/entity data is now stored directly to SQLite for fast queries (<10ms). InfluxDB storage is optional for historical tracking only.

## Configuration

### Required Environment Variables

```bash
# Home Assistant Connection
HOME_ASSISTANT_URL=http://your-ha-ip:8123  # Your HA instance
HOME_ASSISTANT_TOKEN=your_long_lived_access_token

# Service Port
WEBSOCKET_INGESTION_PORT=8001

# Data API (for device/entity storage)
DATA_API_URL=http://homeiq-data-api:8006  # NEW

# Network Resilience (Optional - Defaults shown)
WEBSOCKET_MAX_RETRIES=-1
WEBSOCKET_MAX_RETRY_DELAY=300
```

### Optional Environment Variables

```bash
# Device Discovery Storage
STORE_DEVICE_HISTORY_IN_INFLUXDB=false  # NEW - Optional InfluxDB history

# Weather Enrichment
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_DEFAULT_LOCATION=City,State,Country
WEATHER_ENRICHMENT_ENABLED=true
WEATHER_CACHE_MINUTES=15

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=both
```

## API Endpoints

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy" | "unhealthy",
  "service": "websocket-ingestion",
  "uptime": "0:37:39.078230",
  "connection": {
    "is_running": true,
    "connection_attempts": 1,
    "successful_connections": 1,
    "failed_connections": 0
  },
  "subscription": {
    "is_subscribed": true,
    "total_events_received": 13,
    "event_rate_per_minute": 17.65
  }
}
```

### WebSocket Endpoint
```bash
WS /ws

# Real-time event streaming
# Sends events as JSON
```

## Development

### Running Locally

```bash
# Install dependencies
cd services/websocket-ingestion
pip install -r requirements.txt

# Run service
python -m src.main
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### Connection Issues

**Problem**: Service can't connect to Home Assistant

**Check:**
1. Home Assistant URL is correct
2. Access token is valid
3. Network connectivity exists
4. Home Assistant is accessible from Docker network

**With infinite retry (default):**
- Service will keep trying automatically
- Check logs for retry attempts
- Service will recover when HA becomes available

### No Events Being Received

**Problem**: Connected but no events flowing

**Check:**
1. Subscription status in health endpoint
2. Home Assistant is generating state_changed events
3. Token has proper permissions
4. Check enrichment pipeline is running

### High Memory Usage

**Problem**: Service memory usage is high

**Solution:**
1. Check batch processor configuration
2. Review weather enrichment cache size
3. Monitor event rate and processing
4. Consider reducing cache TTL

## Architecture

### Data Flow Diagram

```
┌─────────────────────────────────────────────┐
│  Home Assistant @ 192.168.1.86:8123         │
│  - WebSocket API (events)                   │
│  - Device Registry (discovery)              │
│  - Entity Registry (discovery)              │
└──────────┬──────────────────────────────────┘
           │
           │ WebSocket Connection (with infinite retry)
           │
┌──────────▼──────────────────────────────────┐
│  WebSocket Ingestion Service                │
│                                              │
│  ┌──────────────┐    ┌──────────────┐      │
│  │ Event Stream │    │ Discovery    │      │
│  │ (real-time)  │    │ (on connect) │      │
│  └──────┬───────┘    └──────┬───────┘      │
│         │                   │               │
└─────────┼───────────────────┼───────────────┘
          │                   │
          │ Events            │ Devices/Entities
          ↓                   ↓
┌──────────────────┐  ┌──────────────────────┐
│  Enrichment      │  │  Data API            │
│  Pipeline        │  │  (Port 8006)         │
│  (Port 8002)     │  │                      │
└────────┬─────────┘  │  POST /internal/     │
         │            │  devices/bulk_upsert │
         ↓            └──────────┬───────────┘
┌──────────────────┐             │
│  InfluxDB        │◄────────────┘
│  (Time-Series)   │  SQLite
│  (Port 8086)     │  (Metadata) ✅ PRIMARY
└──────────────────┘  └──────────────────────┘
```

### Storage Strategy (Updated October 2025)

| Data Type | Storage | Purpose |
|-----------|---------|---------|
| **HA Events** | InfluxDB | Time-series state changes |
| **Devices** | SQLite (via data-api) | Current metadata, fast queries ✅ |
| **Entities** | SQLite (via data-api) | Current metadata, fast queries ✅ |
| **Device History** | InfluxDB (optional) | Historical snapshots (disabled) |
```

## Performance

- **Event Processing**: 15-25 events/minute typical
- **Weather Cache**: 92%+ hit rate
- **Connection Uptime**: 99.9%+ with infinite retry
- **Memory Usage**: ~150MB typical
- **CPU Usage**: <5% typical

## Security

- ✅ Token validation before connection
- ✅ Secure WebSocket (wss://) support
- ✅ No secrets in logs (tokens masked)
- ✅ Health endpoint has no sensitive data
- ✅ CORS protection on WebSocket endpoint

## Related Documentation

- [Troubleshooting Guide](../../docs/TROUBLESHOOTING_GUIDE.md)
- [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md)
- [Infinite Retry Implementation](../../implementation/INFINITE_RETRY_IMPLEMENTATION_COMPLETE.md)
- [Network Resilience Plan](../../implementation/NETWORK_RESILIENCE_SIMPLE_FIX.md)

## Version History

- **v1.1.0** (October 2025) - Added infinite retry strategy, improved resilience
- **v1.0.0** (2024) - Initial release with WebSocket connection and weather enrichment

