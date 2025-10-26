# Home Assistant Connection Analysis and Unified Strategy

## Current State Analysis

### Issues Identified

1. **Inconsistent Connection Patterns**: Different services use different approaches:
   - `websocket-ingestion`: Uses `shared.ha_connection_manager` ✅
   - `calendar-service`: Uses `shared.ha_connection_manager` ✅  
   - `device-intelligence-service`: Has custom fallback logic ❌
   - `smart-meter`: Uses direct HA_HTTP_URL/HA_TOKEN ❌
   - Other services: Various patterns ❌

2. **Environment Variable Inconsistencies**:
   - `infrastructure/env.production` has placeholder values
   - Some services use `HA_HTTP_URL` while others use `HOME_ASSISTANT_URL`
   - Missing `HA_WS_URL` configuration in production env

3. **Missing Circuit Breaker Pattern**: No resilience patterns implemented

4. **No Centralized Connection Health Monitoring**: Each service manages its own connection state

## Best Practices from Context7 Research

### Circuit Breaker Pattern Implementation
Based on pybreaker documentation, we should implement:
- **Failure Threshold**: 5 consecutive failures
- **Reset Timeout**: 60 seconds
- **Success Threshold**: 3 consecutive successes
- **State Management**: Track open/closed/half-open states

### Connection Management Patterns
- **Singleton Pattern**: Single connection manager instance
- **Fallback Chain**: Primary → Nabu Casa → Local HA
- **Health Monitoring**: Continuous connection health checks
- **Automatic Recovery**: Self-healing connection management

## Unified Strategy Implementation

### 1. Enhanced HA Connection Manager

The existing `shared/ha_connection_manager.py` needs enhancement with:

```python
class EnhancedHAConnectionManager:
    """Enhanced HA Connection Manager with Circuit Breaker Pattern"""
    
    def __init__(self):
        self.connections: List[HAConnectionConfig] = []
        self.current_connection: Optional[HAConnectionConfig] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_monitor: ConnectionHealthMonitor = ConnectionHealthMonitor()
        
    async def get_connection_with_circuit_breaker(self) -> Optional[HAConnectionConfig]:
        """Get connection with circuit breaker protection"""
        for connection in self.connections:
            breaker = self.circuit_breakers.get(connection.name)
            if breaker and breaker.current_state == 'open':
                continue
                
            try:
                if await self._test_connection(connection):
                    self.current_connection = connection
                    return connection
            except Exception as e:
                if breaker:
                    breaker.record_failure(e)
                continue
                
        return None
```

### 2. Environment Variable Standardization

**Standardized Environment Variables**:
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

### 3. Service Integration Strategy

**All services should use the unified connection manager**:

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

### 4. Docker Compose Standardization

**All HA-dependent services should have consistent environment configuration**:

```yaml
services:
  websocket-ingestion:
    env_file:
      - infrastructure/env.production
    environment:
      # Home Assistant Configuration (unified)
      - HA_HTTP_URL=${HA_HTTP_URL:-}
      - HA_WS_URL=${HA_WS_URL:-}
      - HA_TOKEN=${HA_TOKEN:-}
      - NABU_CASA_URL=${NABU_CASA_URL:-}
      - NABU_CASA_TOKEN=${NABU_CASA_TOKEN:-}
      - LOCAL_HA_URL=${LOCAL_HA_URL:-}
      - LOCAL_HA_TOKEN=${LOCAL_HA_TOKEN:-}
      
  smart-meter:
    env_file:
      - infrastructure/env.production
    environment:
      # Same HA configuration as websocket-ingestion
      - HA_HTTP_URL=${HA_HTTP_URL:-}
      - HA_WS_URL=${HA_WS_URL:-}
      - HA_TOKEN=${HA_TOKEN:-}
      - NABU_CASA_URL=${NABU_CASA_URL:-}
      - NABU_CASA_TOKEN=${NABU_CASA_TOKEN:-}
```

## Implementation Plan

### Phase 1: Fix Current Issues
1. ✅ Fix InfluxDB connection (already completed)
2. 🔄 Update environment variables with real values
3. 🔄 Implement circuit breaker pattern
4. 🔄 Standardize all service configurations

### Phase 2: Enhance Connection Manager
1. Add circuit breaker integration
2. Implement health monitoring
3. Add connection metrics and logging
4. Create connection status API endpoint

### Phase 3: Service Migration
1. Update all services to use unified connection manager
2. Remove custom fallback logic from individual services
3. Implement consistent error handling
4. Add connection health checks to all services

### Phase 4: Monitoring and Alerting
1. Add connection health dashboard
2. Implement alerting for connection failures
3. Add metrics collection for connection statistics
4. Create troubleshooting documentation

## Security Considerations

Based on security best practices:
- **Environment Variables**: All secrets stored in environment variables
- **Token Management**: Long-lived access tokens with proper scoping
- **Network Security**: HTTPS/WSS for cloud connections
- **Access Control**: Proper authentication and authorization
- **Monitoring**: Comprehensive logging of connection attempts and failures

## Next Steps

1. **Immediate**: Fix environment variables with real HA connection details
2. **Short-term**: Implement circuit breaker pattern in connection manager
3. **Medium-term**: Migrate all services to unified connection strategy
4. **Long-term**: Add comprehensive monitoring and alerting
