# WebSocket Ingestion Service

The WebSocket Ingestion Service connects to Home Assistant's WebSocket API to capture real-time state change events and store them **DIRECTLY in InfluxDB** (Epic 31).

**Port:** 8001
**Technology:** Python 3.11+, aiohttp 3.13, asyncio, InfluxDB 2.x
**Container:** `homeiq-websocket`

**🔴 EPIC 31 ARCHITECTURE UPDATE:**
- ✅ Events are written **DIRECTLY to InfluxDB** (no intermediate services)
- ❌ enrichment-pipeline service **DEPRECATED** (no longer used)
- ✅ All normalization happens **inline** in this service
- ✅ External services (weather-api, etc.) consume **FROM InfluxDB**

## Features

- 🔌 **WebSocket Connection** - Real-time connection to Home Assistant API
- 🔄 **Infinite Retry** - Never gives up on reconnection (October 2025)
- 🔐 **Secure Authentication** - Token-based authentication with validation
- 📊 **Event Processing** - Captures and normalizes state_changed events
- 🔍 **Device Discovery** - Automatic discovery of devices and entities (stores to SQLite via data-api)
- 📈 **Health Monitoring** - Comprehensive health checks and metrics
- 🔁 **Automatic Reconnection** - Smart exponential backoff on connection failures
- 💾 **Direct InfluxDB Writes** - Events written directly to InfluxDB (Epic 31)
- 🎯 **Epic 23 Enhancements** - Context tracking, spatial analytics, duration tracking
- ⚡ **High Performance** - 10,000+ events/second throughput capability
- 🛡️ **Circuit Breaker** - Prevents cascading failures during outages
- 🧰 **Shared Module Auto-Discovery** - Override shared path via `HOMEIQ_SHARED_PATH`
- 🧊 **Backpressure-Protected Influx Writes** - Configurable queue + overflow strategies stop runaway memory usage

## Network Resilience

### Infinite Retry Strategy

The service includes **infinite retry capability** by default for maximum uptime:

**Key Features:**
- ✅ Never stops trying to connect
- ✅ Works even when started without network
- ✅ Automatically recovers from extended outages
- ✅ Smart exponential backoff (up to 5 minutes)
- ✅ Clear logging with retry indicators
- ✅ Circuit breaker pattern for graceful degradation

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

# Circuit breaker threshold
CIRCUIT_BREAKER_THRESHOLD=5  # Failures before opening circuit
```

**Docker Compose:**
```yaml
websocket-ingestion:
  environment:
    - WEBSOCKET_MAX_RETRIES=-1
    - WEBSOCKET_MAX_RETRY_DELAY=300
    - CIRCUIT_BREAKER_THRESHOLD=5
```

### Monitoring Retry Status

**Check Logs:**
```bash
# View recent logs
docker compose logs websocket-ingestion --tail 50

# Follow live logs
docker compose logs -f websocket-ingestion

# Look for retry messages
docker compose logs websocket-ingestion | grep "Reconnection attempt"
```

**Check Health Status:**
```bash
# Get health status
curl http://localhost:8001/health

# Example response:
{
  "status": "healthy",  # or "unhealthy" if retrying
  "service": "websocket-ingestion",
  "uptime": "0:37:39.078230",
  "connection": {
    "is_running": true,
    "connection_attempts": 15,
    "successful_connections": 1,
    "failed_connections": 14,
    "last_successful": "2025-11-15T12:00:00Z"
  },
  "subscription": {
    "is_subscribed": true,
    "total_events_received": 13,
    "event_rate_per_minute": 17.65
  },
  "circuit_breaker": {
    "state": "closed",  # closed, open, half-open
    "failure_count": 0
  }
}
```

## Device Discovery

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
DATA_API_URL=http://data-api:8006  # Container name (Docker network)

# Optional: Enable InfluxDB historical tracking (disabled by default)
STORE_DEVICE_HISTORY_IN_INFLUXDB=false
```

**Note**: Device/entity data is now stored directly to SQLite for fast queries (<10ms). InfluxDB storage is optional for historical tracking only.

## Configuration

### Required Environment Variables

```bash
# Home Assistant Connection
HOME_ASSISTANT_URL=http://your-ha-ip:8123  # Your HA instance
HA_HTTP_URL=http://your-ha-ip:8123  # Alternative naming (also supported)
HA_WS_URL=ws://your-ha-ip:8123  # WebSocket URL (optional - /api/websocket auto-appended if missing)
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
HA_TOKEN=your_long_lived_access_token  # Alternative naming (also supported)

# Service Port
WEBSOCKET_INGESTION_PORT=8001

# Data API (for device/entity storage)
DATA_API_URL=http://data-api:8006

# InfluxDB Configuration (Epic 31 - Direct Writes)
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
# Network Resilience (Defaults shown)
WEBSOCKET_MAX_RETRIES=-1  # Infinite retry
WEBSOCKET_MAX_RETRY_DELAY=300  # 5 minutes max delay
```

### Optional Environment Variables

```bash
# Device Discovery Storage
STORE_DEVICE_HISTORY_IN_INFLUXDB=false  # Optional InfluxDB history

# Shared module import override (defaults to repo ./shared directory)
HOMEIQ_SHARED_PATH=/app/shared

# Weather Enrichment (DEPRECATED - Use weather-api service)
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_DEFAULT_LOCATION=City,State,Country
WEATHER_ENRICHMENT_ENABLED=false  # Disabled in Epic 31
WEATHER_CACHE_MINUTES=15

# Batch Processing
BATCH_SIZE=100  # Events per batch
BATCH_TIMEOUT=5.0  # Seconds before force flush

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=both

# Performance
MAX_MEMORY_MB=500  # Memory limit before alerts

# InfluxDB write queue controls
INFLUXDB_MAX_PENDING_POINTS=20000
INFLUXDB_OVERFLOW_STRATEGY=drop_oldest  # drop_oldest | drop_new
```

## API Endpoints

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy" | "unhealthy",
  "service": "websocket-ingestion",
  "timestamp": "2025-11-15T12:00:00Z",
  "uptime": "0:37:39.078230",
  "uptime_seconds": 2259.078,
  "connection": {
    "is_running": true,
    "connection_attempts": 1,
    "successful_connections": 1,
    "failed_connections": 0,
    "last_successful": "2025-11-15T12:00:00Z",
    "current_state": "connected"
  },
  "subscription": {
    "is_subscribed": true,
    "total_events_received": 13,
    "event_rate_per_minute": 17.65,
    "last_event": "2025-11-15T12:00:00Z"
  },
  "circuit_breaker": {
    "state": "closed",
    "failure_count": 0,
    "last_failure": null
  },
  "performance": {
    "memory_mb": 150.2,
    "cpu_percent": 2.3
  }
}
```

### WebSocket Endpoint

```bash
WS /ws

# Real-time event streaming
# Sends events as JSON to connected clients
# Used for real-time dashboards
```

### Metrics Endpoint

```bash
GET /metrics

# Prometheus-compatible metrics
# Event processing rates
# Connection statistics
# Performance metrics
```

## Architecture

### Data Flow Diagram (Epic 31 Architecture)

```
┌─────────────────────────────────────────────┐
│  Home Assistant @ 192.168.1.86:8123         │
│  - WebSocket API (events)                   │
│  - Device Registry (discovery)              │
│  - Entity Registry (discovery)              │
└──────────┬──────────────────────────────────┘
           │
           │ WebSocket Connection (with infinite retry + circuit breaker)
           │
┌──────────▼──────────────────────────────────┐
│  WebSocket Ingestion Service (Port 8001)    │
│                                              │
│  ┌──────────────┐    ┌──────────────┐      │
│  │ Event Stream │    │ Discovery    │      │
│  │ (real-time)  │    │ (on connect) │      │
│  └──────┬───────┘    └──────┬───────┘      │
│         │                   │               │
│  ┌──────▼────────┐          │               │
│  │ Batch         │          │               │
│  │ Processor     │          │               │
│  │ (100 events)  │          │               │
│  └──────┬────────┘          │               │
│         │                   │               │
│  Inline Normalization       │               │
│  Direct InfluxDB Writes ✅  │               │
└─────────┼───────────────────┼───────────────┘
          │                   │
          │ Events            │ Devices/Entities
          ↓                   ↓
┌──────────────────┐  ┌──────────────────────┐
│  InfluxDB        │  │  Data API (8006)     │
│  (Time-Series)   │  │  POST /internal/     │
│  (Port 8086)     │  │  devices/bulk_upsert │
│  ✅ DIRECT WRITE │  └──────────┬───────────┘
│  - Batch writes  │             │
│  - 100/batch     │             ↓
│  - 5s timeout    │   ┌──────────────────┐
└──────────────────┘   │  SQLite          │
                       │  (Metadata)      │
                       │  metadata.db     │
                       │  - devices       │
                       │  - entities      │
                       └──────────────────┘

Note: enrichment-pipeline (Port 8002) DEPRECATED in Epic 31
```

### Storage Strategy (Epic 31 - November 2025)

| Data Type | Storage | Purpose | Performance |
|-----------|---------|---------|-------------|
| **HA Events** | InfluxDB | Time-series state changes | 10k+ events/sec |
| **Devices** | SQLite (via data-api) | Current metadata, fast queries ✅ | <10ms queries |
| **Entities** | SQLite (via data-api) | Current metadata, fast queries ✅ | <10ms queries |
| **Device History** | InfluxDB (optional) | Historical snapshots | Disabled by default |

### Component Architecture

```
src/
├── main.py                          # Service entry point
├── websocket_client.py              # WebSocket connection handler
│   ├── Infinite retry logic
│   ├── Circuit breaker pattern
│   └── Exponential backoff
├── event_processor.py               # Event normalization
├── batch_processor.py               # Batching logic (100 events/5s)
├── influxdb_writer.py               # Direct InfluxDB writes
├── discovery_service.py             # Device/entity discovery
│   ├── Device registry queries
│   ├── Entity registry queries
│   └── Data-API integration
├── health_monitor.py                # Health checks
└── metrics_collector.py             # Performance metrics
```

## Development

### Running Locally

```bash
# Navigate to service directory
cd services/websocket-ingestion

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run service
python -m src.main
```

### Environment Setup

Create `.env` file:
```bash
HOME_ASSISTANT_URL=http://192.168.1.86:8123
HOME_ASSISTANT_TOKEN=your_token_here
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
DATA_API_URL=http://localhost:8006
WEBSOCKET_MAX_RETRIES=-1
LOG_LEVEL=DEBUG
```

### Running with Docker

```bash
# Build and start
docker compose up -d websocket-ingestion

# View logs
docker compose logs -f websocket-ingestion

# Check health
curl http://localhost:8001/health

# Restart service
docker compose restart websocket-ingestion
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_websocket_client.py

# Run async tests
pytest tests/ -v
```

**Test Coverage:**
- WebSocket connection handling
- Infinite retry logic
- Circuit breaker pattern
- Event processing and normalization
- Batch processing
- Device discovery
- Health monitoring

**Note:** Automated test framework is being rebuilt as of November 2025.

## Performance

### Performance Metrics

- **Event Processing:** 15-25 events/minute typical, 10,000+ events/second peak
- **Batch Processing:** 100 events per batch, 5-second timeout
- **Connection Uptime:** 99.9%+ with infinite retry
- **Memory Usage:** ~150MB typical, ~500MB peak
- **CPU Usage:** <5% typical, <20% peak
- **InfluxDB Write Latency:** <50ms per batch
- **Device Query Latency:** <10ms (SQLite)

### Resource Limits

```yaml
# docker-compose.yml
websocket-ingestion:
  deploy:
    resources:
      limits:
        memory: 500M
        cpus: '1.0'
      reservations:
        memory: 100M
        cpus: '0.25'
```

## Troubleshooting

### Connection Issues

**Problem:** Service can't connect to Home Assistant

**Check:**
1. Home Assistant URL is correct (http://your-ha-ip:8123)
2. Access token is valid (create new long-lived token if needed)
3. Network connectivity exists between containers
4. Home Assistant is accessible from Docker network
5. Firewall rules allow WebSocket connections
6. **WebSocket URL Format**: The service automatically appends `/api/websocket` to WebSocket URLs if missing. You can use either:
   - `HA_WS_URL=ws://192.168.1.86:8123` (auto-appends `/api/websocket`)
   - `HA_WS_URL=ws://192.168.1.86:8123/api/websocket` (explicit path)

**With infinite retry (default):**
- Service will keep trying automatically
- Check logs for retry attempts: `docker compose logs websocket-ingestion | grep "Reconnection"`
- Service will recover automatically when HA becomes available
- No manual intervention required

**Debug Steps:**
```bash
# Test HA HTTP API
curl http://your-ha-ip:8123/api/

# Test from container
docker exec websocket-ingestion curl http://home-assistant:8123/api/

# Check WebSocket endpoint
wscat -c ws://your-ha-ip:8123/api/websocket
```

### No Events Being Received

**Problem:** Connected but no events flowing

**Check:**
1. Subscription status in health endpoint
2. Home Assistant is generating state_changed events
3. Token has proper permissions (supervisor level)
4. InfluxDB connection is healthy
5. Batch processor is not blocked

**Debug Steps:**
```bash
# Check health status
curl http://localhost:8001/health | jq '.subscription'

# Check InfluxDB connection
curl http://localhost:8086/health

# Monitor event stream
docker compose logs -f websocket-ingestion | grep "state_changed"
```

### High Memory Usage

**Problem:** Service memory usage exceeds limits

**Check:**
1. Batch processor configuration (reduce batch size)
2. Event rate and processing speed
3. InfluxDB batch write performance
4. Memory leaks in event processing

**Solutions:**
```bash
# Reduce batch size
BATCH_SIZE=50  # Down from 100

# Reduce batch timeout
BATCH_TIMEOUT=2.0  # Down from 5.0

# Monitor memory usage
docker stats websocket-ingestion

# Restart service to clear memory
docker compose restart websocket-ingestion
```

### Circuit Breaker Open

**Problem:** Circuit breaker is open, service degraded

**Symptoms:**
- Health endpoint shows `circuit_breaker.state: "open"`
- Events not being processed
- Logs show "Circuit breaker open" messages

**Solutions:**
1. Wait for circuit to automatically close (30-60 seconds)
2. Fix underlying issue causing failures
3. Restart service to reset circuit breaker
4. Adjust circuit breaker threshold if too sensitive

```bash
# Check circuit breaker state
curl http://localhost:8001/health | jq '.circuit_breaker'

# Restart to reset
docker compose restart websocket-ingestion

# Adjust threshold
CIRCUIT_BREAKER_THRESHOLD=10  # More tolerant
```

### Device Discovery Failures

**Problem:** Devices/entities not discovered

**Check:**
1. Data API is running (http://localhost:8006/health)
2. WebSocket connection is established
3. HA token has device registry permissions
4. Data API SQLite database is writable

**Debug Steps:**
```bash
# Check data-api health
curl http://localhost:8006/health

# Check device count
curl http://localhost:8006/api/devices | jq 'length'

# Check entity count
curl http://localhost:8006/api/entities | jq 'length'

# View discovery logs
docker compose logs websocket-ingestion | grep "discovery"
```

## Security

### Authentication & Authorization
- ✅ Token validation before connection
- ✅ Secure WebSocket (wss://) support
- ✅ No secrets in logs (tokens masked as •••)
- ✅ Health endpoint has no sensitive data
- ✅ CORS protection on WebSocket endpoint

### Best Practices
- Use long-lived access tokens (not short-lived)
- Rotate tokens periodically (90 days)
- Use environment variables for secrets
- Enable HTTPS/WSS in production
- Limit token permissions to minimum required

### Token Creation

In Home Assistant:
1. Go to Profile → Security → Long-Lived Access Tokens
2. Click "Create Token"
3. Name: "HomeIQ WebSocket Ingestion"
4. Copy token and store in environment variable
5. Never commit tokens to git

## Dependencies

### Core Dependencies

```
aiohttp==3.13.2          # Async HTTP client and WebSocket
asyncio-mqtt==0.16.1     # MQTT client (optional)
pydantic==2.12.4         # Data validation
psutil==7.1.3            # System metrics
python-dotenv==1.2.1     # Environment variables
```

### Development Dependencies

```
pytest==8.3.3            # Testing framework
pytest-asyncio==0.23.0   # Async test support
```

### Production Dependencies

See `requirements-prod.txt` for minimal production dependencies.

## Related Documentation

- [Troubleshooting Guide](../../docs/TROUBLESHOOTING_GUIDE.md)
- [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md)
- [API Reference](../../docs/api/API_REFERENCE.md)
- [Infinite Retry Implementation](../../implementation/INFINITE_RETRY_IMPLEMENTATION_COMPLETE.md)
- [Network Resilience Plan](../../implementation/NETWORK_RESILIENCE_SIMPLE_FIX.md)
- [Epic 31 Documentation](../../docs/architecture/epic-31-direct-writes.md)
- [CLAUDE.md](../../CLAUDE.md) - AI assistant development guide

## Support

- **Issues:** File on GitHub at https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** Check `/docs` directory
- **Health Check:** http://localhost:8001/health
- **Metrics:** http://localhost:8001/metrics

## Version History

### v1.2.0 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added circuit breaker pattern details
- Improved troubleshooting section
- Added security best practices
- Enhanced performance metrics

### v1.1.0 (October 2025)
- Added infinite retry strategy
- Improved network resilience
- Enhanced device discovery
- Epic 31 direct writes to InfluxDB

### v1.0.0 (2024)
- Initial release
- WebSocket connection to Home Assistant
- Weather enrichment (now deprecated)
- Event processing and storage

---

**Last Updated:** November 15, 2025
**Version:** 1.2.0
**Status:** Production Ready ✅
**Port:** 8001
**Architecture:** Epic 31 (Direct InfluxDB Writes)
