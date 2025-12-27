# Story 23.5: Error Handling and Resilience for Real-Time Metrics

## Story Overview

**Story ID**: 23.5  
**Epic**: 23 - Enhanced Dependencies Tab Real-Time Metrics  
**Story Type**: Quality Assurance  
**Priority**: Medium  
**Estimated Effort**: 1 week  
**Assigned To**: Backend Team  

## User Story

**As a** system administrator  
**I want** the real-time metrics system to handle service failures gracefully  
**So that** the dashboard remains functional even when some services are unavailable  

## Acceptance Criteria

### Primary Criteria
- [ ] Dashboard displays partial data when some services are unavailable
- [ ] Error states are clearly indicated in the UI
- [ ] System continues to function with 0% service availability
- [ ] Failed service calls don't block other service metrics collection
- [ ] Error messages are informative and actionable

### Secondary Criteria
- [ ] Retry logic handles temporary service unavailability
- [ ] Timeout handling prevents hanging requests
- [ ] Circuit breaker pattern prevents cascading failures
- [ ] Error logging provides sufficient debugging information
- [ ] Graceful degradation maintains user experience

## Technical Requirements

### Admin API Error Handling
```python
# admin-api/src/resilient_metrics_collector.py
class ResilientMetricsCollector:
    def __init__(self):
        self.service_timeouts = {
            "websocket-ingestion": 2.0,
            "enrichment-pipeline": 2.0,
            "data-api": 1.0,
            "sports-data": 3.0,
            "weather-api": 3.0,
            # ... other services
        }
        self.circuit_breakers = {}
        self.retry_config = {
            "max_retries": 2,
            "retry_delay": 0.5,
            "backoff_factor": 2.0
        }
    
    async def get_service_metrics_with_resilience(self, service_name: str, port: int, service_type: str):
        """Get metrics with comprehensive error handling"""
        try:
            # Check circuit breaker
            if self._is_circuit_open(service_name):
                return self._get_fallback_metrics(service_name, port, service_type, "circuit_open")
            
            # Get metrics with timeout and retry
            metrics = await self._get_metrics_with_retry(service_name, port)
            
            # Reset circuit breaker on success
            self._reset_circuit_breaker(service_name)
            
            return metrics
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting metrics from {service_name}")
            self._record_circuit_breaker_failure(service_name)
            return self._get_fallback_metrics(service_name, port, service_type, "timeout")
            
        except aiohttp.ClientError as e:
            logger.warning(f"Client error getting metrics from {service_name}: {e}")
            self._record_circuit_breaker_failure(service_name)
            return self._get_fallback_metrics(service_name, port, service_type, "client_error")
            
        except Exception as e:
            logger.error(f"Unexpected error getting metrics from {service_name}: {e}")
            self._record_circuit_breaker_failure(service_name)
            return self._get_fallback_metrics(service_name, port, service_type, "unexpected_error")
    
    async def _get_metrics_with_retry(self, service_name: str, port: int):
        """Get metrics with retry logic"""
        timeout = self.service_timeouts.get(service_name, 2.0)
        
        for attempt in range(self.retry_config["max_retries"] + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session:
                    async with session.get(f"http://localhost:{port}/api/v1/event-rate") as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status
                            )
            except Exception as e:
                if attempt == self.retry_config["max_retries"]:
                    raise e
                
                # Wait before retry
                delay = self.retry_config["retry_delay"] * (self.retry_config["backoff_factor"] ** attempt)
                await asyncio.sleep(delay)
                logger.info(f"Retrying metrics collection for {service_name} (attempt {attempt + 1})")
    
    def _is_circuit_open(self, service_name: str) -> bool:
        """Check if circuit breaker is open for service"""
        if service_name not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[service_name]
        if breaker["state"] == "open":
            # Check if enough time has passed to try again
            if datetime.now() - breaker["last_failure"] > timedelta(minutes=5):
                breaker["state"] = "half_open"
                return False
            return True
        
        return False
    
    def _record_circuit_breaker_failure(self, service_name: str):
        """Record a failure for circuit breaker"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None
            }
        
        breaker = self.circuit_breakers[service_name]
        breaker["failure_count"] += 1
        breaker["last_failure"] = datetime.now()
        
        # Open circuit after 3 consecutive failures
        if breaker["failure_count"] >= 3:
            breaker["state"] = "open"
            logger.warning(f"Circuit breaker opened for {service_name}")
    
    def _reset_circuit_breaker(self, service_name: str):
        """Reset circuit breaker on success"""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None
            }
    
    def _get_fallback_metrics(self, service_name: str, port: int, service_type: str, error_type: str):
        """Get fallback metrics when service is unavailable"""
        return {
            "service_name": service_name,
            "port": port,
            "service_type": service_type,
            "status": "error",
            "events_per_second": 0,
            "events_per_hour": 0,
            "total_events": 0,
            "uptime_seconds": 0,
            "last_activity": None,
            "error_message": f"Service unavailable: {error_type}",
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }
```

### Frontend Error Handling
```typescript
// useRealTimeMetrics.ts
export const useRealTimeMetrics = (refreshInterval: number = 5000) => {
  const [metrics, setMetrics] = useState<RealTimeMetrics>({
    eventsPerSecond: 0,
    eventsPerHour: 0,
    activeAPIs: [],
    inactiveAPIs: 0,
    dataSourcesActive: [],
    lastUpdate: new Date(),
  });
  
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const response = await fetch('/api/v1/real-time-metrics', {
          signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        setMetrics({
          eventsPerSecond: data.events_per_second || 0,
          eventsPerHour: data.events_per_hour || 0,
          activeAPIs: data.active_apis || [],
          inactiveAPIs: data.inactive_apis || 0,
          dataSourcesActive: data.data_sources_active || [],
          lastUpdate: new Date()
        });
        
      } catch (error) {
        console.error('Failed to fetch real-time metrics:', error);
        
        if (error.name === 'AbortError') {
          setError('Request timeout - metrics may be stale');
        } else if (error.name === 'TypeError') {
          setError('Network error - check connection');
        } else {
          setError(`Failed to fetch metrics: ${error.message}`);
        }
        
        // Don't clear existing metrics on error - show stale data
        // setMetrics(prev => ({ ...prev, lastUpdate: new Date() }));
        
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);
  
  return { metrics, error, isLoading };
};
```

### Enhanced UI Error States
```typescript
// DependenciesTab.tsx
export const DependenciesTab: React.FC<TabProps> = ({ darkMode }) => {
  const { metrics, error, isLoading } = useRealTimeMetrics(5000);
  const [services, setServices] = useState<any[]>([]);

  return (
    <div className="space-y-8">
      {/* Error Banner */}
      {error && (
        <div className={`p-4 rounded-lg ${darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center">
            <span className="text-red-500 mr-2">⚠️</span>
            <span className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
              {error}
            </span>
          </div>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <div className={`p-4 rounded-lg ${darkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
            <span className={`text-sm ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
              Updating metrics...
            </span>
          </div>
        </div>
      )}

      {/* Enhanced Header with Error States */}
      <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} flex items-center gap-3`}>
              <span className="animate-pulse">🌊</span>
              Complete Architecture Flow
            </h2>
            <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              AI Automation • Hybrid Database • Pattern Detection • Click nodes for details
            </p>
          </div>
          
          {/* Real-Time Metrics Display with Error States */}
          <div className={`px-6 py-3 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  error ? (darkMode ? 'text-red-400' : 'text-red-600') :
                  (darkMode ? 'text-green-400' : 'text-green-600')
                }`}>
                  {error ? '?' : metrics.eventsPerSecond.toFixed(1)}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  events/sec
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  error ? (darkMode ? 'text-red-400' : 'text-red-600') :
                  (darkMode ? 'text-blue-400' : 'text-blue-600')
                }`}>
                  {error ? '?' : metrics.eventsPerHour.toFixed(0)}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  events/hour
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  error ? (darkMode ? 'text-red-400' : 'text-red-600') :
                  (darkMode ? 'text-green-400' : 'text-green-600')
                }`}>
                  {error ? '?' : metrics.activeAPIs.length}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  active APIs
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  error ? (darkMode ? 'text-red-400' : 'text-red-600') :
                  (darkMode ? 'text-red-400' : 'text-red-600')
                }`}>
                  {error ? '?' : metrics.inactiveAPIs}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  inactive APIs
                </div>
              </div>
            </div>
            <div className={`text-xs text-center mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
              Last updated: {metrics.lastUpdate.toLocaleTimeString()}
              {error && <span className="text-red-500 ml-2">(Error)</span>}
            </div>
          </div>
        </div>

        {/* Per-API Metrics Table with Error States */}
        {metrics.activeAPIs.length > 0 && (
          <div className="mt-6">
            <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Active API Metrics
            </h3>
            <div className="overflow-x-auto">
              <table className={`w-full text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <thead>
                  <tr className={`border-b ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                    <th className="text-left py-2">Service</th>
                    <th className="text-right py-2">Events/sec</th>
                    <th className="text-right py-2">Events/hour</th>
                    <th className="text-right py-2">Total Events</th>
                    <th className="text-right py-2">Uptime</th>
                    <th className="text-center py-2">Status</th>
                    <th className="text-left py-2">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.activeAPIs.map((api) => (
                    <tr key={api.serviceName} className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-100'}`}>
                      <td className="py-2 font-medium">{api.serviceName}</td>
                      <td className="text-right py-2">
                        {api.status === 'error' ? '?' : api.eventsPerSecond.toFixed(2)}
                      </td>
                      <td className="text-right py-2">
                        {api.status === 'error' ? '?' : api.eventsPerHour.toFixed(0)}
                      </td>
                      <td className="text-right py-2">
                        {api.status === 'error' ? '?' : api.totalEvents.toLocaleString()}
                      </td>
                      <td className="text-right py-2">
                        {api.status === 'error' ? '?' : formatUptime(api.uptimeSeconds)}
                      </td>
                      <td className="text-center py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          api.status === 'active' 
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                            : api.status === 'error'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                        }`}>
                          {api.status}
                        </span>
                      </td>
                      <td className="text-left py-2 text-xs text-red-600">
                        {api.errorMessage || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* No Active APIs State */}
        {metrics.activeAPIs.length === 0 && metrics.inactiveAPIs > 0 && (
          <div className={`mt-4 p-4 rounded-lg ${darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-center">
              <span className="text-red-500 mr-2">⚠️</span>
              <span className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                No active APIs detected. {metrics.inactiveAPIs} services are inactive or unreachable.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Dependency Graph */}
      <AnimatedDependencyGraph 
        services={services}
        darkMode={darkMode}
        realTimeData={metrics}
      />
    </div>
  );
};
```

## Testing Requirements

### Unit Tests
- [ ] Circuit breaker opens after 3 failures
- [ ] Circuit breaker resets after success
- [ ] Retry logic works correctly
- [ ] Fallback metrics are generated properly
- [ ] Error handling covers all exception types

### Integration Tests
- [ ] System continues to function with 0% service availability
- [ ] Partial data is displayed when some services fail
- [ ] Error states are clearly indicated
- [ ] Timeout handling works correctly

### Load Tests
- [ ] System handles high error rates gracefully
- [ ] Memory usage remains stable during failures
- [ ] Performance doesn't degrade significantly

## Definition of Done

- [ ] Comprehensive error handling implemented
- [ ] Circuit breaker pattern prevents cascading failures
- [ ] UI displays error states clearly
- [ ] System remains functional with service failures
- [ ] Error logging provides debugging information
- [ ] Unit tests achieve 90% coverage
- [ ] Integration tests pass
- [ ] Load tests meet criteria
- [ ] Code review is completed

## Dependencies

### Internal Dependencies
- **Story 23.2**: Consolidated Real-Time Metrics Endpoint (must be complete)
- **Story 23.3**: Enhanced Dependencies Tab UI (must be complete)
- Error handling infrastructure

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **Cascading Failures**: Service failures may cause system-wide issues
  - *Mitigation*: Circuit breaker pattern and timeout handling

### Medium Risk
- **Poor User Experience**: Error states may confuse users
  - *Mitigation*: Clear error messages and graceful degradation

### Low Risk
- **Performance Impact**: Error handling may add overhead
  - *Mitigation*: Efficient error handling and minimal logging

## Success Metrics

- **System Availability**: 99.9% uptime even with service failures
- **Error Recovery**: <5 seconds to recover from temporary failures
- **User Experience**: Clear error states and partial data display
- **Debugging**: Comprehensive error logging for troubleshooting

## Notes

This story ensures the real-time metrics system is robust and resilient. The system must continue to provide value even when individual services are unavailable, and users must be clearly informed about any issues.
