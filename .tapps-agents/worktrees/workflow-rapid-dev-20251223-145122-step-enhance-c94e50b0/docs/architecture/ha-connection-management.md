# HA Connection Management Architecture

## Overview

The HomeIQ system uses an **enhanced Home Assistant connection manager** that implements the circuit breaker pattern and automatic fallback to ensure reliable connectivity to Home Assistant instances.

## Key Features

### Circuit Breaker Pattern

The connection manager implements a circuit breaker pattern to prevent cascading failures and provide automatic recovery:

- **Failure Threshold**: 5 consecutive failures trigger circuit open
- **Reset Timeout**: 60 seconds before attempting reconnection
- **Success Threshold**: 3 consecutive successes close circuit
- **State Management**: Tracks open/closed/half-open states

### Automatic Fallback Chain

The system maintains multiple connection sources for maximum reliability:

1. **Primary HA** (http://192.168.1.86:8123) - Local Home Assistant instance
2. **Nabu Casa** (cloud URL) - Remote access fallback
3. **Local HA** (http://localhost:8123) - Emergency fallback

### Connection Features

- **Connection Pooling**: Reuses connections for better performance
- **Health Monitoring**: Continuous connection health checks
- **Automatic Recovery**: Self-healing connection management
- **Comprehensive Metrics**: Tracks connection statistics and failures

## Architecture

### Connection Manager Components

```python
class EnhancedHAConnectionManager:
    - Circuit breaker protection for each connection
    - Automatic fallback between connection types
    - Health monitoring and metrics collection
    - Comprehensive error handling and logging
    - Connection pooling and reuse
```

### Circuit Breaker States

```
CLOSED (Normal)
    ↓ (5 failures)
OPEN (Blocking requests)
    ↓ (60s timeout)
HALF_OPEN (Testing recovery)
    ↓ (3 successes)
CLOSED (Normal)
```

### Connection Priority

The system attempts connections in priority order:

1. **Primary HA** - Highest priority, local connection
2. **Nabu Casa** - Medium priority, cloud fallback
3. **Local HA** - Low priority, emergency fallback

## Implementation

### Shared Connection Manager

The connection manager is implemented in `shared/enhanced_ha_connection_manager.py`:

```python
from shared.ha_connection_manager import ha_connection_manager

# Get connection with circuit breaker protection
connection = await ha_connection_manager.get_connection_with_circuit_breaker()

if connection:
    # Use the connection
    async with connection as client:
        # Make HA API calls
        pass
```

### Environment Configuration

Standardized environment variables for all services:

```bash
# Primary HA Configuration
HA_HTTP_URL=http://192.168.1.86:8123
HA_WS_URL=ws://192.168.1.86:8123/api/websocket
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Nabu Casa Fallback Configuration
NABU_CASA_URL=https://your-domain.ui.nabu.casa
NABU_CASA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Local HA Fallback Configuration (Optional)
LOCAL_HA_URL=http://localhost:8123
LOCAL_HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Connection Management Configuration
HA_CONNECTION_TIMEOUT=30
HA_CIRCUIT_BREAKER_FAIL_MAX=5
HA_CIRCUIT_BREAKER_RESET_TIMEOUT=60
HA_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=3
```

## Service Integration

### Using the Unified Connection Manager

All services should use the unified connection manager:

```python
# In each service's main.py
from shared.ha_connection_manager import ha_connection_manager

async def startup(self):
    """Initialize service with unified HA connection"""
    connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()
    
    if not connection_config:
        raise ConnectionError("No Home Assistant connections available")
    
    logger.info(f"Using HA connection: {connection_config.name} ({connection_config.url})")
    
    # Initialize service-specific HA client
    self.ha_client = ServiceSpecificHAClient(
        base_url=connection_config.url,
        token=connection_config.token
    )
```

### Services Using Unified Strategy

The following services have been updated to use the unified connection manager:

- ✅ **websocket-ingestion**: Uses shared connection manager
- ✅ **calendar-service**: Uses shared connection manager
- ✅ **device-intelligence-service**: Uses shared connection manager
- ✅ **smart-meter**: Updated Docker configuration for unified environment variables

## Monitoring and Metrics

### Connection Statistics

The connection manager tracks comprehensive metrics:

- **Successful Connections**: Count of successful connections
- **Failed Connections**: Count of failed connections
- **Last Connection Time**: Timestamp of last connection
- **Last Error**: Details of last error if any
- **Circuit Breaker State**: Current state of circuit breaker
- **Response Times**: Average response times per connection

### Circuit Breaker Metrics

- **Failures**: Total number of failures for each connection
- **Successes**: Total number of successes for each connection
- **Last Failure Time**: Timestamp of last failure
- **Last Success Time**: Timestamp of last success
- **State Changes**: Count of circuit breaker state transitions

## Error Handling

### Connection Errors

The connection manager handles various connection errors:

- **Connection Timeout**: Timeout when connecting to HA
- **Authentication Failed**: Invalid token or credentials
- **Network Error**: Network connectivity issues
- **Service Unavailable**: HA service is down
- **Rate Limiting**: Too many requests to HA

### Automatic Recovery

The system implements automatic recovery:

1. **Immediate Retry**: Retry on transient failures
2. **Exponential Backoff**: Gradually increase retry delay
3. **Circuit Breaker**: Pause requests on persistent failures
4. **Fallback Chain**: Try next available connection
5. **Health Monitoring**: Resume when connection recovers

## Best Practices

### Service Implementation

1. **Use Shared Manager**: Always use the shared connection manager
2. **Handle Errors**: Implement proper error handling
3. **Log Connection Info**: Log connection details for debugging
4. **Monitor Metrics**: Track connection statistics
5. **Test Fallbacks**: Test fallback scenarios

### Configuration

1. **Environment Variables**: Use standardized environment variable names
2. **Circuit Breaker**: Configure appropriate thresholds
3. **Timeouts**: Set reasonable timeout values
4. **Retries**: Configure retry policies
5. **Monitoring**: Enable connection metrics collection

## Security Considerations

### Token Management

- **Long-lived Tokens**: Use long-lived access tokens
- **Proper Scoping**: Ensure tokens have necessary permissions
- **Secure Storage**: Store tokens in environment variables
- **Rotation**: Implement token rotation strategy

### Network Security

- **HTTPS/WSS**: Use encrypted connections for cloud endpoints
- **SSL/TLS**: Verify SSL certificates
- **Network Segmentation**: Isolate HA network if possible
- **Firewall Rules**: Restrict network access appropriately

### Monitoring

- **Audit Logs**: Log all connection attempts and failures
- **Alerting**: Set up alerts for connection failures
- **Metrics**: Track connection health over time
- **Incident Response**: Have procedures for connection issues

## Troubleshooting

### Common Issues

1. **Circuit Breaker Open**: Connection blocked by circuit breaker
   - **Solution**: Wait for reset timeout or manually reset circuit breaker

2. **All Connections Failed**: No available connections
   - **Solution**: Check network connectivity, verify credentials

3. **High Latency**: Slow connection responses
   - **Solution**: Check network conditions, consider connection pooling

4. **Authentication Errors**: Invalid token or credentials
   - **Solution**: Verify token is valid and has necessary permissions

### Debugging

Enable debug logging to diagnose connection issues:

```python
import logging
logging.getLogger('shared.ha_connection_manager').setLevel(logging.DEBUG)
```

Check connection statistics:

```python
stats = ha_connection_manager.get_connection_stats()
print(f"Current connection: {stats['current_connection']}")
print(f"Circuit breaker states: {stats['circuit_breakers']}")
```

## Future Enhancements

### Planned Features

1. **Dynamic Configuration**: Update connection configs at runtime
2. **Health Dashboard**: Visual dashboard for connection monitoring
3. **Advanced Metrics**: More detailed connection analytics
4. **Load Balancing**: Distribute load across multiple HA instances
5. **Geo-redundancy**: Support for geo-distributed HA setups

### Performance Improvements

1. **Connection Pooling**: Improve connection reuse
2. **Async Improvements**: Optimize async operations
3. **Caching**: Cache frequently accessed HA data
4. **Compression**: Enable response compression
5. **Rate Limiting**: Implement intelligent rate limiting
