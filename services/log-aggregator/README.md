# Log Aggregator Service

**Port:** 8022
**Purpose:** Centralized log collection from all Docker containers
**Status:** Production Ready

## Overview

The Log Aggregator Service provides centralized log collection, storage, and querying for all services in the HomeIQ platform. It collects logs from Docker containers using the Docker API and makes them available via a RESTful API and WebSocket interface.

## Key Features

- **Docker Integration**: Collects logs directly from Docker containers via Docker API
- **Real-time Collection**: Continuous log collection from running containers
- **In-Memory Storage**: Keeps last 10,000 log entries in memory for fast queries
- **File Persistence**: Stores logs to disk for historical access
- **WebSocket Streaming**: Real-time log streaming to clients
- **Multi-Format Support**: Handles both JSON and plain-text logs
- **Container Metadata**: Enriches logs with container name and ID

## API Endpoints

### Health Check
```
GET /health
```

### Log Queries
```
GET /logs
Query params:
  - container: Filter by container name
  - level: Filter by log level (INFO, ERROR, DEBUG, WARNING)
  - limit: Number of logs to return (default: 100)
  - since: Timestamp filter (ISO 8601)
```

### Log Submission
```
POST /logs
Body: {
  "service": "service-name",
  "level": "INFO|ERROR|DEBUG|WARNING",
  "message": "log message",
  "timestamp": "ISO 8601 timestamp",
  "metadata": {}
}
```

### WebSocket Streaming
```
WS /ws/logs
```
Streams logs in real-time as they are collected

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8022` | Service port |
| `LOG_DIRECTORY` | `/app/logs` | Directory for log file storage |
| `MAX_LOGS_MEMORY` | `10000` | Maximum logs to keep in memory |
| `COLLECTION_INTERVAL` | `5` | Log collection interval (seconds) |

## Docker Configuration

**IMPORTANT**: The service requires access to the Docker socket:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

## Architecture

```
┌──────────────────────┐
│  Log Aggregator Svc  │
│     (Port 8022)      │
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐   ┌──────────────┐
│ Docker  │   │ In-Memory    │
│ Containers   │ Log Buffer   │
│ (via API)│   │ (10k logs)   │
└─────────┘   └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ File Storage │
    │ /app/logs/*  │
    └──────────────┘
```

## Log Collection Process

1. **Container Discovery**: List all running Docker containers
2. **Log Extraction**: Collect last 100 lines from each container
3. **Parsing**: Parse JSON logs or convert plain-text to structured format
4. **Enrichment**: Add container metadata (name, ID)
5. **Storage**: Store in memory buffer and write to disk
6. **Streaming**: Broadcast to WebSocket subscribers

## Log Format

### JSON Logs (Preferred)
```json
{
  "timestamp": "2025-11-11T10:30:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "service": "data-api",
  "container_name": "homeiq-data-api",
  "container_id": "abc123",
  "metadata": {
    "duration_ms": 45,
    "endpoint": "/api/events"
  }
}
```

### Plain Text Logs (Auto-converted)
```
2025-11-11T10:30:00Z Request processed successfully
```
Converted to:
```json
{
  "timestamp": "2025-11-11T10:30:00Z",
  "message": "Request processed successfully",
  "level": "INFO",
  "container_name": "homeiq-data-api",
  "container_id": "abc123"
}
```

## Development

### Running Locally
```bash
cd services/log-aggregator
docker-compose up --build
```

### Testing
```bash
# Health check
curl http://localhost:8022/health

# Get all logs
curl http://localhost:8022/logs

# Filter logs by container
curl "http://localhost:8022/logs?container=data-api&limit=50"

# Filter by log level
curl "http://localhost:8022/logs?level=ERROR"

# Submit custom log
curl -X POST http://localhost:8022/logs \
  -H "Content-Type: application/json" \
  -d '{"service":"test","level":"INFO","message":"Test log"}'
```

### WebSocket Client Example
```javascript
const ws = new WebSocket('ws://localhost:8022/ws/logs');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.container_name}] ${log.message}`);
};
```

## Dependencies

- aiohttp (async web framework)
- aiofiles (async file operations)
- docker-py (Docker API client)
- aiohttp-cors (CORS support)

## Performance

- **Log Collection**: Every 5 seconds (configurable)
- **Memory Footprint**: ~10MB for 10,000 logs
- **Query Latency**: <10ms (in-memory)
- **File Write**: Async, non-blocking
- **Container Scan**: 100-200ms for 20+ containers

## Log Retention

- **Memory**: Last 10,000 logs (rolling buffer)
- **Disk**: All logs persisted to `/app/logs/`
- **File Rotation**: Manual (Docker volume management)

## Monitoring

The service logs its own operations:
- Container discovery results
- Log collection stats (logs/container)
- Parse errors (non-JSON logs)
- Docker API connection status
- WebSocket client connections

## Security Considerations

- **Docker Socket Access**: Read-only access to `/var/run/docker.sock`
- **CORS**: Configured for all origins (adjust for production)
- **No Authentication**: Add authentication layer in production
- **Log Sanitization**: No sensitive data filtering (implement if needed)

## Related Services

- [Admin API](../admin-api/README.md) - Uses logs for system monitoring
- [Health Dashboard](../health-dashboard/README.md) - Displays aggregated logs
- All other services - Log sources

## Troubleshooting

### Service can't connect to Docker
- Verify `/var/run/docker.sock` is mounted
- Check Docker socket permissions
- Ensure Docker daemon is running

### Missing logs from containers
- Check container is running: `docker ps`
- Verify container outputs logs: `docker logs <container>`
- Increase `COLLECTION_INTERVAL` if logs are delayed

### High memory usage
- Reduce `MAX_LOGS_MEMORY` value
- Implement log rotation
- Archive old logs to external storage

## Version History

### 2.1 (November 15, 2025)
- Documentation verified for 2025 standards
- Docker integration documented
- WebSocket streaming detailed
- Performance characteristics documented

### 2.0 (October 2025)
- Docker API integration
- Real-time log collection
- In-memory buffer (10,000 logs)
- WebSocket streaming support

### 1.0 (Initial Release)
- Basic log aggregation
- File persistence

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8022 (Note: Port conflict - update to 8015 in deployment)
