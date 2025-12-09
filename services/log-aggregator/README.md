# Log Aggregator Service

**Centralized log collection and querying for all HomeIQ services**

**Port:** 8015
**Technology:** Python 3.11+, aiohttp, Docker API
**Container:** homeiq-log-aggregator
**Database:** In-memory (10,000 log entries) + File storage
**Scale:** Optimized for ~25 microservices

## Overview

The Log Aggregator Service provides centralized log collection, storage, and querying for all services in the HomeIQ platform. It collects logs directly from Docker containers using the Docker API and makes them available via a RESTful API for monitoring and debugging.

### Key Features

- **Docker Integration** - Collects logs directly from Docker containers via Docker API
- **Real-time Collection** - Continuous background log collection (every 30 seconds)
- **In-Memory Storage** - Keeps last 10,000 log entries in memory for fast queries
- **File Persistence** - Stores logs to `/app/logs` directory for historical access
- **Multi-Format Support** - Handles both JSON and plain-text logs
- **Container Metadata** - Enriches logs with container name and ID
- **Filtering** - Query by service name, log level, time range
- **Search** - Full-text search across log messages
- **Statistics** - Log counts by service and level
- **CORS Support** - Configured for health-dashboard and AI UI access

## API Endpoints

### Health Endpoint

```bash
GET /health
```
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "log-aggregator",
  "timestamp": "2025-12-09T10:30:00Z",
  "logs_collected": 5432
}
```

### Log Query Endpoint

```bash
GET /api/v1/logs
```
Query recent logs with optional filtering.

**Query Parameters:**
- `service` (optional) - Filter by service name
- `level` (optional) - Filter by log level (INFO, ERROR, DEBUG, WARNING)
- `limit` (optional) - Number of logs to return (default: 100)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-12-09T10:30:00Z",
      "service": "ai-automation-service",
      "level": "INFO",
      "message": "Pattern analysis completed",
      "container_name": "homeiq-ai-automation",
      "container_id": "abc123"
    }
  ],
  "count": 150,
  "filters": {
    "service": "ai-automation-service",
    "level": "INFO",
    "limit": 100
  }
}
```

### Log Search Endpoint

```bash
GET /api/v1/logs/search
```
Search logs by message content.

**Query Parameters:**
- `q` (required) - Search query string
- `limit` (optional) - Number of results (default: 100)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-12-09T10:30:00Z",
      "service": "websocket-ingestion",
      "level": "ERROR",
      "message": "Connection failed: timeout",
      "container_name": "homeiq-websocket-ingestion",
      "container_id": "def456"
    }
  ],
  "count": 5,
  "query": "connection failed",
  "limit": 100
}
```

### Manual Log Collection

```bash
POST /api/v1/logs/collect
```
Manually trigger log collection from all containers.

**Response:**
```json
{
  "message": "Collected 250 log entries",
  "logs_collected": 250,
  "total_logs": 5682
}
```

### Log Statistics

```bash
GET /api/v1/logs/stats
```
Get log statistics by service and level.

**Response:**
```json
{
  "total_logs": 5682,
  "services": {
    "ai-automation-service": 1234,
    "websocket-ingestion": 890,
    "data-api": 456
  },
  "levels": {
    "INFO": 4500,
    "ERROR": 123,
    "WARNING": 567,
    "DEBUG": 492
  },
  "recent_logs": 245
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8015` | Service port |
| `LOG_DIRECTORY` | `/app/logs` | Directory for log file storage |
| `MAX_LOGS_MEMORY` | `10000` | Maximum logs to keep in memory |
| `COLLECTION_INTERVAL` | `30` | Background collection interval (seconds) |

## Development

### Running Locally

```bash
cd services/log-aggregator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Ensure Docker socket is accessible
python -m src.main
```

### Running with Docker

```bash
# Build and start service
docker compose up -d log-aggregator

# View logs
docker compose logs -f log-aggregator

# Test health endpoint
curl http://localhost:8015/health

# Query logs
curl http://localhost:8015/api/v1/logs?service=ai-automation-service&level=ERROR
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8015/health

# Get recent logs
curl http://localhost:8015/api/v1/logs

# Filter by service
curl "http://localhost:8015/api/v1/logs?service=websocket-ingestion"

# Filter by level
curl "http://localhost:8015/api/v1/logs?level=ERROR"

# Search logs
curl "http://localhost:8015/api/v1/logs/search?q=connection"

# Get statistics
curl http://localhost:8015/api/v1/logs/stats

# Manually collect logs
curl -X POST http://localhost:8015/api/v1/logs/collect
```

## Dependencies

### System Dependencies

- **Docker Socket** - Requires read access to `/var/run/docker.sock`
  - Mounted as: `/var/run/docker.sock:/var/run/docker.sock:ro`
  - Used for: Docker container API access

### Python Dependencies

- `aiohttp` - Async HTTP server
- `aiohttp-cors` - CORS middleware for browser requests
- `docker` - Docker SDK for Python
- `shared` - HomeIQ shared libraries (logging)

## Related Services

### Downstream Consumers

- **health-dashboard** (Port 3000) - Displays aggregated logs in UI
- **ai-automation-ui** (Port 3001) - Monitors service logs

### Data Flow

```
Docker Containers → Log Aggregator → In-Memory Buffer (10k logs)
                                   → File Storage (/app/logs)
                                   → Health Dashboard (via API)
                                   → AI Automation UI (via API)
```

## Architecture Notes

### Docker Integration

The service uses the Docker SDK to collect logs from all running containers:
1. **Container Discovery** - Lists all running Docker containers
2. **Log Collection** - Fetches last 100 lines from each container
3. **Parsing** - Handles both JSON and plain-text log formats
4. **Enrichment** - Adds container name and ID to each log entry
5. **Storage** - Saves to in-memory buffer and file system

### Storage Architecture

**In-Memory Buffer:**
- Fast query performance
- Limited to 10,000 entries (configurable)
- FIFO eviction when full
- Lost on service restart

**File Storage:**
- Persistent across restarts
- Located at `/app/logs`
- Organized by service/date
- Requires volume mount for persistence

### Background Collection Loop

The service runs a continuous background task:
1. Sleep 30 seconds (configurable)
2. Discover all running containers
3. Fetch logs from each container (last 100 lines)
4. Parse and enrich log entries
5. Store in memory and file system
6. Repeat

### Log Parsing

**JSON Format:**
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "service": "ai-automation-service",
  "level": "INFO",
  "message": "Pattern analysis completed"
}
```

**Plain Text Format:**
```
2025-12-09T10:30:00Z INFO: Pattern analysis completed
```

Both formats are parsed and normalized to consistent JSON structure.

## Monitoring

### Health Checks

The `/health` endpoint provides:
- Service status (healthy/unhealthy)
- Current timestamp
- Total logs collected

### Statistics

Track these metrics via `/api/v1/logs/stats`:
- **Total Logs** - Total entries in memory
- **Logs by Service** - Count per service
- **Logs by Level** - Count per level (INFO, ERROR, etc.)
- **Recent Logs** - Logs in last hour

### Performance

- **Memory Usage** - ~100MB for 10,000 log entries
- **CPU Usage** - <5% typical
- **Collection Speed** - ~100 logs/second
- **Query Latency** - <10ms for filtered queries

## Troubleshooting

### Docker Socket Access Issues

**Symptoms:**
```
❌ Failed to initialize Docker client: Permission denied
```

**Solutions:**
1. **Check Volume Mount:**
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock:ro
   ```

2. **Verify Docker Socket Permissions:**
   ```bash
   ls -la /var/run/docker.sock
   # Should be readable by service user
   ```

3. **Check Docker Service:**
   ```bash
   docker ps
   # Should list running containers
   ```

### No Logs Collected

**Possible Causes:**
1. **No Running Containers** - No containers to collect from
2. **Docker Socket Not Mounted** - Volume mount missing
3. **Collection Disabled** - Background task not running

**Solutions:**
```bash
# Check running containers
docker ps

# Check service logs
docker compose logs log-aggregator

# Manually trigger collection
curl -X POST http://localhost:8015/api/v1/logs/collect
```

### High Memory Usage

**Possible Causes:**
1. **Too Many Logs** - MAX_LOGS_MEMORY set too high
2. **Large Log Messages** - Individual log entries very large

**Solutions:**
```bash
# Reduce max logs in memory
export MAX_LOGS_MEMORY=5000

# Check statistics
curl http://localhost:8015/api/v1/logs/stats

# Restart service to clear memory
docker compose restart log-aggregator
```

### Slow Queries

**Possible Causes:**
1. **Too Many Logs** - Searching through large dataset
2. **Complex Search** - Full-text search on large messages

**Solutions:**
```bash
# Use filtering instead of search
curl "http://localhost:8015/api/v1/logs?service=specific-service"

# Reduce limit
curl "http://localhost:8015/api/v1/logs?limit=50"

# Reduce MAX_LOGS_MEMORY
export MAX_LOGS_MEMORY=5000
```

## Security Notes

- **Docker Socket Access** - Service has read-only access to Docker socket
- **CORS Configuration** - Only allows localhost:3000 and localhost:3001
- **No Authentication** - Internal service, assumes trusted network
- **File Permissions** - Log files written with service user permissions

## Version History

- **v1.0.0** (December 2025) - Initial production release
  - Docker API integration for log collection
  - In-memory storage with 10,000 entry limit
  - File persistence to /app/logs
  - RESTful API with filtering and search
  - Background collection loop (30s interval)
  - CORS support for dashboard UIs
  - Statistics and health endpoints

---

**Last Updated:** December 09, 2025
**Version:** 1.0.0
**Status:** Production Ready ✅
**Port:** 8015
