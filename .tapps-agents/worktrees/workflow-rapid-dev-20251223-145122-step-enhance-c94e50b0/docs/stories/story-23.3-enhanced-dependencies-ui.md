# Story 23.3: Enhanced Dependencies Tab UI with Real-Time Metrics

## Story Overview

**Story ID**: 23.3  
**Epic**: 23 - Enhanced Dependencies Tab Real-Time Metrics  
**Story Type**: Frontend UI  
**Priority**: High  
**Estimated Effort**: 2 weeks  
**Assigned To**: Frontend Team  

## User Story

**As a** system administrator  
**I want** the Dependencies tab to display real-time metrics with per-API performance data  
**So that** I can monitor system performance and identify issues quickly  

## Acceptance Criteria

### Primary Criteria
- [ ] Dependencies tab shows real-time events/sec and events/hour (not hardcoded zeros)
- [ ] Per-API metrics table displays individual service performance
- [ ] Active/inactive API counts are displayed prominently
- [ ] Metrics update every 5 seconds via polling
- [ ] UI remains responsive during updates

### Secondary Criteria
- [ ] Service status indicators show active/inactive/error states
- [ ] Metrics table is sortable by different columns
- [ ] Error states are clearly indicated with appropriate styling
- [ ] Loading states are shown during metric collection
- [ ] Responsive design works on different screen sizes

## Technical Requirements

### Real-Time Metrics Hook
```typescript
// useRealTimeMetrics.ts
export interface APIMetrics {
  serviceName: string;
  port: number;
  status: 'active' | 'inactive' | 'error';
  eventsPerSecond: number;
  eventsPerHour: number;
  totalEvents: number;
  uptimeSeconds: number;
  lastActivity: Date;
  errorMessage?: string;
}

export interface RealTimeMetrics {
  eventsPerSecond: number;
  eventsPerHour: number;
  activeAPIs: APIMetrics[];
  inactiveAPIs: number;
  dataSourcesActive: string[];
  lastUpdate: Date;
}

export const useRealTimeMetrics = (refreshInterval: number = 5000) => {
  const [metrics, setMetrics] = useState<RealTimeMetrics>({
    eventsPerSecond: 0,
    eventsPerHour: 0,
    activeAPIs: [],
    inactiveAPIs: 0,
    dataSourcesActive: [],
    lastUpdate: new Date(),
  });
  
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/v1/real-time-metrics');
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
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);
  
  return metrics;
};
```

### Enhanced Dependencies Tab Component
```typescript
// DependenciesTab.tsx
export const DependenciesTab: React.FC<TabProps> = ({ darkMode }) => {
  const realTimeMetrics = useRealTimeMetrics(5000); // 5-second polling
  const [services, setServices] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState<keyof APIMetrics>('serviceName');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Fetch services data for dependencies graph
  useEffect(() => {
    const fetchServices = async () => {
      try {
        const response = await fetch('/api/v1/services');
        if (response.ok) {
          const data = await response.json();
          setServices(data.services || []);
        }
      } catch (error) {
        console.error('Error fetching services:', error);
      }
    };

    fetchServices();
    const interval = setInterval(fetchServices, 30000);
    return () => clearInterval(interval);
  }, []);

  // Sort active APIs
  const sortedAPIs = useMemo(() => {
    return [...realTimeMetrics.activeAPIs].sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      return 0;
    });
  }, [realTimeMetrics.activeAPIs, sortBy, sortOrder]);

  const handleSort = (column: keyof APIMetrics) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  return (
    <div className="space-y-8">
      {/* Enhanced Header with Real-Time Metrics */}
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
          
          {/* Real-Time Metrics Display */}
          <div className={`px-6 py-3 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className={`text-2xl font-bold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                  {realTimeMetrics.eventsPerSecond.toFixed(1)}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  events/sec
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                  {realTimeMetrics.eventsPerHour.toFixed(0)}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  events/hour
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                  {realTimeMetrics.activeAPIs.length}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  active APIs
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
                  {realTimeMetrics.inactiveAPIs}
                </div>
                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  inactive APIs
                </div>
              </div>
            </div>
            <div className={`text-xs text-center mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
              Last updated: {realTimeMetrics.lastUpdate.toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Per-API Metrics Table */}
        {realTimeMetrics.activeAPIs.length > 0 && (
          <div className="mt-6">
            <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Active API Metrics
            </h3>
            <div className="overflow-x-auto">
              <table className={`w-full text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <thead>
                  <tr className={`border-b ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                    <th 
                      className="text-left py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => handleSort('serviceName')}
                    >
                      Service {sortBy === 'serviceName' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="text-right py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => handleSort('eventsPerSecond')}
                    >
                      Events/sec {sortBy === 'eventsPerSecond' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="text-right py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => handleSort('eventsPerHour')}
                    >
                      Events/hour {sortBy === 'eventsPerHour' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="text-right py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => handleSort('totalEvents')}
                    >
                      Total Events {sortBy === 'totalEvents' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="text-right py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => handleSort('uptimeSeconds')}
                    >
                      Uptime {sortBy === 'uptimeSeconds' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="text-center py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAPIs.map((api) => (
                    <tr key={api.serviceName} className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-100'}`}>
                      <td className="py-2 font-medium">{api.serviceName}</td>
                      <td className="text-right py-2">{api.eventsPerSecond.toFixed(2)}</td>
                      <td className="text-right py-2">{api.eventsPerHour.toFixed(0)}</td>
                      <td className="text-right py-2">{api.totalEvents.toLocaleString()}</td>
                      <td className="text-right py-2">{formatUptime(api.uptimeSeconds)}</td>
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Error States */}
        {realTimeMetrics.activeAPIs.length === 0 && realTimeMetrics.inactiveAPIs > 0 && (
          <div className={`mt-4 p-4 rounded-lg ${darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-center">
              <span className="text-red-500 mr-2">⚠️</span>
              <span className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                No active APIs detected. {realTimeMetrics.inactiveAPIs} services are inactive or unreachable.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Dependency Graph */}
      <AnimatedDependencyGraph 
        services={services}
        darkMode={darkMode}
        realTimeData={realTimeMetrics}
      />
    </div>
  );
};
```

### Utility Functions
```typescript
// utils/timeFormatting.ts
export const formatUptime = (seconds: number): string => {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
};
```

## Testing Requirements

### Unit Tests
- [ ] useRealTimeMetrics hook fetches data correctly
- [ ] Metrics table sorting works for all columns
- [ ] Error states are displayed appropriately
- [ ] Utility functions format data correctly

### Integration Tests
- [ ] Dependencies tab displays real-time data
- [ ] Polling updates work every 5 seconds
- [ ] UI remains responsive during updates
- [ ] Error handling works when API is unavailable

### Visual Tests
- [ ] Dark mode styling is correct
- [ ] Responsive design works on different screen sizes
- [ ] Loading states are visually appealing
- [ ] Status indicators are clear and consistent

## Definition of Done

- [ ] Real-time metrics display correctly
- [ ] Per-API metrics table is functional
- [ ] Sorting works for all columns
- [ ] Error states are handled gracefully
- [ ] UI remains responsive during updates
- [ ] Unit tests achieve 90% coverage
- [ ] Integration tests pass
- [ ] Visual tests pass
- [ ] Code review is completed

## Dependencies

### Internal Dependencies
- **Story 23.2**: Consolidated Real-Time Metrics Endpoint (must be complete)
- Existing AnimatedDependencyGraph component
- React hooks and state management

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **UI Performance**: Frequent updates may cause lag
  - *Mitigation*: Use React.memo and useMemo for optimization

### Medium Risk
- **Memory Leaks**: Polling intervals may not be cleaned up
  - *Mitigation*: Proper useEffect cleanup in useRealTimeMetrics hook

### Low Risk
- **Data Inconsistency**: UI may show stale data during updates
  - *Mitigation*: Show loading states during data fetching

## Success Metrics

- **UI Responsiveness**: No lag during 5-second updates
- **Data Accuracy**: Metrics match API responses
- **Error Handling**: Graceful degradation when services are unavailable
- **User Experience**: Clear visual indicators for all states

## Notes

This story transforms the Dependencies tab from a static display to a dynamic, real-time monitoring dashboard. The UI must be performant and user-friendly while providing comprehensive system visibility.
