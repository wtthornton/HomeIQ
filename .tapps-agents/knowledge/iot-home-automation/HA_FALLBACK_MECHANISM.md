# Home Assistant Fallback Mechanism

## Overview

All Home Assistant connections in the system now implement an automatic fallback mechanism that tries primary HA URLs and tokens first, and if they fail, automatically falls back to Nabu Casa URLs and tokens.

## Connection Priority

The system follows this priority order for HA connections:

1. **Primary HA** (`HA_HTTP_URL`/`HA_WS_URL` + `HA_TOKEN`)
2. **Nabu Casa Fallback** (`NABU_CASA_URL` + `NABU_CASA_TOKEN`)
3. **Local HA Fallback** (`LOCAL_HA_URL` + `LOCAL_HA_TOKEN`)

## Environment Variables

### Primary HA Configuration
```bash
# HTTP URL for REST API calls
HA_HTTP_URL=http://192.168.1.86:8123

# WebSocket URL for real-time events (optional, will be derived from HA_HTTP_URL if not set)
HA_WS_URL=ws://192.168.1.86:8123/api/websocket

# Long-lived access token
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Nabu Casa Fallback Configuration
```bash
# Nabu Casa URL (HTTPS)
NABU_CASA_URL=https://your-domain.ui.nabu.casa

# Nabu Casa long-lived access token
NABU_CASA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Local HA Fallback Configuration (Optional)
```bash
# Local HA URL for development/testing
LOCAL_HA_URL=http://localhost:8123

# Local HA token
LOCAL_HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Services Using Fallback

### 1. WebSocket Ingestion Service (Port 8001)
- **File**: `services/websocket-ingestion/src/main.py`
- **Usage**: Real-time event ingestion from HA
- **Fallback**: Uses `shared.ha_connection_manager`

### 2. Calendar Service (Port 8007)
- **File**: `services/calendar-service/src/main.py`
- **Usage**: Calendar event fetching for occupancy prediction
- **Fallback**: Uses `shared.ha_connection_manager`

### 3. Device Intelligence Service (Port 8019)
- **File**: `services/device-intelligence-service/src/clients/ha_client.py`
- **Usage**: Device discovery and intelligence analysis
- **Fallback**: Built-in fallback logic (already implemented)

### 4. AI Automation Service (Port 8018)
- **File**: `services/ai-automation-service/src/api/ask_ai_router.py`
- **Usage**: AI-powered automation suggestions
- **Fallback**: Uses `shared.ha_connection_manager`

## Implementation Details

### Shared HA Connection Manager

The `shared/ha_connection_manager.py` provides a unified interface for all services:

```python
from shared.ha_connection_manager import ha_connection_manager

# Get the best available connection
connection_config = await ha_connection_manager.get_connection()

# Use WebSocket client
async with ha_connection_manager.get_websocket_client() as websocket:
    # Make HA WebSocket calls
    pass

# Use HTTP client
http_client = await ha_connection_manager.get_http_client()
```

### Connection Testing

The system automatically tests each connection in priority order:

1. **WebSocket Connection Test**: Establishes WebSocket connection
2. **Authentication Test**: Verifies token validity
3. **Response Time Measurement**: Tracks connection performance
4. **Automatic Fallback**: Switches to next available connection on failure

### Connection Statistics

The system tracks connection statistics:

```python
stats = ha_connection_manager.get_connection_stats()
# Returns:
{
    'current_connection': 'Primary HA',
    'total_connections': 3,
    'connection_stats': {
        'Primary HA': {
            'total_attempts': 10,
            'successful_attempts': 8,
            'failed_attempts': 2,
            'avg_response_time': 0.15,
            'last_success': 1640995200.0,
            'last_failure': None
        },
        'Nabu Casa Fallback': {
            'total_attempts': 2,
            'successful_attempts': 2,
            'failed_attempts': 0,
            'avg_response_time': 0.45,
            'last_success': 1640995200.0,
            'last_failure': None
        }
    },
    'health_status': 'healthy'
}
```

## Configuration Examples

### Development Environment
```bash
# Primary HA (local development)
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=dev_token_here

# Nabu Casa fallback (production HA)
NABU_CASA_URL=https://home.ui.nabu.casa
NABU_CASA_TOKEN=prod_token_here
```

### Production Environment
```bash
# Primary HA (local network)
HA_HTTP_URL=http://homeassistant.local:8123
HA_TOKEN=production_token_here

# Nabu Casa fallback (remote access)
NABU_CASA_URL=https://home.ui.nabu.casa
NABU_CASA_TOKEN=nabu_casa_token_here
```

### Cloud-Only Environment
```bash
# No local HA, only Nabu Casa
NABU_CASA_URL=https://home.ui.nabu.casa
NABU_CASA_TOKEN=nabu_casa_token_here
```

## Error Handling

### Connection Failures
- **Primary HA fails**: Automatically tries Nabu Casa
- **Nabu Casa fails**: Tries Local HA (if configured)
- **All connections fail**: Service logs error and retries periodically

### Authentication Failures
- **Invalid token**: Logs error and tries next connection
- **Expired token**: Logs warning and tries next connection
- **Network timeout**: Logs warning and tries next connection

### Logging
All connection attempts and failures are logged with correlation IDs:

```
2025-01-20 10:30:15 INFO [corr:abc123] ✅ Primary HA connection configured: ws://192.168.1.86:8123/api/websocket
2025-01-20 10:30:15 INFO [corr:abc123] ✅ Nabu Casa fallback configured: wss://home.ui.nabu.casa/api/websocket
2025-01-20 10:30:16 INFO [corr:abc123] 🎯 Selected connection: Primary HA
2025-01-20 10:30:16 INFO [corr:abc123] 🔌 WebSocket connected to Primary HA
```

## Health Monitoring

### Health Endpoints
Each service exposes health endpoints that include HA connection status:

```bash
# WebSocket Ingestion Service
curl http://localhost:8001/health

# Calendar Service
curl http://localhost:8007/health

# Device Intelligence Service
curl http://localhost:8019/health

# AI Automation Service
curl http://localhost:8018/health
```

### Health Response Example
```json
{
    "status": "healthy",
    "service": "websocket-ingestion",
    "version": "1.0.0",
    "ha_connection": {
        "current": "Primary HA",
        "status": "connected",
        "url": "ws://192.168.1.86:8123/api/websocket",
        "fallback_available": true,
        "last_switch": null
    },
    "uptime": "2h 15m 30s"
}
```

## Troubleshooting

### Common Issues

1. **No connections available**
   - Check environment variables are set correctly
   - Verify HA is running and accessible
   - Check token validity

2. **Primary HA fails, fallback works**
   - Check local network connectivity
   - Verify HA is running on expected IP/port
   - Check firewall settings

3. **All connections fail**
   - Verify HA is running
   - Check token permissions
   - Verify network connectivity

### Debug Commands

```bash
# Check HA connection status
curl http://localhost:8001/health | jq '.ha_connection'

# Test HA connectivity
curl -H "Authorization: Bearer $HA_TOKEN" http://192.168.1.86:8123/api/

# Check service logs
docker logs homeiq-websocket-ingestion | grep "HA connection"
```

## Migration Guide

### From Old Configuration
If you're migrating from the old configuration format:

**Old Format:**
```bash
HOME_ASSISTANT_URL=http://192.168.1.86:8123
HOME_ASSISTANT_TOKEN=token_here
```

**New Format:**
```bash
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=token_here
NABU_CASA_URL=https://home.ui.nabu.casa
NABU_CASA_TOKEN=nabu_token_here
```

### Backward Compatibility
The system still supports the old variable names for backward compatibility:
- `HOME_ASSISTANT_URL` → `HA_HTTP_URL`
- `HOME_ASSISTANT_TOKEN` → `HA_TOKEN`

## Best Practices

1. **Always configure Nabu Casa fallback** for production environments
2. **Use long-lived access tokens** with appropriate permissions
3. **Monitor connection statistics** via health endpoints
4. **Test fallback scenarios** during deployment
5. **Keep tokens secure** and rotate them regularly
6. **Use correlation IDs** for debugging connection issues

## Security Considerations

1. **Token Security**: Store tokens in secure environment files
2. **Network Security**: Use HTTPS/WSS for remote connections
3. **Access Control**: Limit token permissions to required scopes
4. **Monitoring**: Monitor for unusual connection patterns
5. **Rotation**: Regularly rotate access tokens

This fallback mechanism ensures high availability and resilience for all Home Assistant integrations in the system.
