import React, { useState, useEffect } from 'react';
import { useHealth } from '../../hooks/useHealth';
import { useStatistics } from '../../hooks/useStatistics';
import { useDataSources } from '../../hooks/useDataSources';
import { useAlerts } from '../../hooks/useAlerts';
import { usePerformanceHistory } from '../../hooks/usePerformanceHistory';
import { useDevices } from '../../hooks/useDevices';
import { useRAGStatus } from '../../hooks/useRAGStatus';
import { SkeletonCard } from '../skeletons';
import { SystemStatusHero } from '../SystemStatusHero';
import { CoreSystemCard } from '../CoreSystemCard';
import { PerformanceSparkline } from '../PerformanceSparkline';
import { ServiceDetailsModal, ServiceDetail } from '../ServiceDetailsModal';
import { IntegrationDetailsModal } from '../IntegrationDetailsModal';
import { RAGStatusCard } from '../RAGStatusCard';
import { RAGDetailsModal } from '../RAGDetailsModal';
import { DataFreshnessIndicator } from '../DataFreshnessIndicator';
import { ServiceHealthResponse } from '../../types/health';
import { apiService } from '../../services/api';
import { TabProps } from './types';

// Enhanced status color system (Phase 2.2)
const getStatusColors = (status: 'healthy' | 'degraded' | 'unhealthy' | 'paused', darkMode: boolean) => {
  const colors = {
    healthy: {
      bg: darkMode ? 'bg-green-900/30' : 'bg-green-100',
      border: darkMode ? 'border-green-700' : 'border-green-300',
      text: darkMode ? 'text-green-200' : 'text-green-800',
      icon: '✅'
    },
    degraded: {
      bg: darkMode ? 'bg-yellow-900/30' : 'bg-yellow-100',
      border: darkMode ? 'border-yellow-700' : 'border-yellow-300',
      text: darkMode ? 'text-yellow-200' : 'text-yellow-800',
      icon: '⚠️'
    },
    unhealthy: {
      bg: darkMode ? 'bg-red-900/30' : 'bg-red-100',
      border: darkMode ? 'border-red-700' : 'border-red-300',
      text: darkMode ? 'text-red-200' : 'text-red-800',
      icon: '❌'
    },
    paused: {
      bg: darkMode ? 'bg-gray-700' : 'bg-gray-100',
      border: darkMode ? 'border-gray-600' : 'border-gray-300',
      text: darkMode ? 'text-gray-200' : 'text-gray-800',
      icon: '⏸️'
    }
  };
  return colors[status];
};

export const OverviewTab: React.FC<TabProps> = ({ darkMode }) => {
  // Enhanced health monitoring (Epic 17.2)
  const [enhancedHealth, setEnhancedHealth] = useState<ServiceHealthResponse | null>(null);
  const [enhancedHealthLoading, setEnhancedHealthLoading] = useState(true);
  
  // Phase 2: Service details modal
  const [selectedService, setSelectedService] = useState<{
    title: string;
    icon: string;
    service: string;
    status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
    details: ServiceDetail[];
  } | null>(null);
  
  // Phase 2.1: Integration details modal
  const [selectedIntegration, setSelectedIntegration] = useState<{
    platform: string;
    deviceCount: number;
    healthy: boolean;
  } | null>(null);
  
  // Phase 3: Sparkline time range control
  const [sparklineTimeRange, setSparklineTimeRange] = useState('1h');
  
  // RAG Status modal
  const [showRAGDetails, setShowRAGDetails] = useState(false);

  // Error state for enhanced health
  const [enhancedHealthError, setEnhancedHealthError] = useState<string | null>(null);

  // Fetch enhanced health data
  useEffect(() => {
    const fetchEnhancedHealth = async () => {
      try {
        setEnhancedHealthError(null);
        const data = await apiService.getEnhancedHealth();
        setEnhancedHealth(data);
        setEnhancedHealthLoading(false);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch enhanced health';
        console.error('Failed to fetch enhanced health:', error);
        setEnhancedHealthError(errorMessage);
        setEnhancedHealthLoading(false);
        // Don't clear existing data on error - show stale data with error indicator
      }
    };

    fetchEnhancedHealth();
    const interval = setInterval(fetchEnhancedHealth, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, []);

  // Fetch container data
  useEffect(() => {
    const fetchContainers = async () => {
      try {
        const containerData = await apiService.getContainers();
        setContainers(containerData);
        setContainersLoading(false);
      } catch (error) {
        console.error('Failed to fetch containers:', error);
        setContainersLoading(false);
      }
    };

    fetchContainers();
    const interval = setInterval(fetchContainers, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, []);

  // Fetch critical alerts for banner (Story 21.6)
  // TEMPORARILY DISABLED due to resource exhaustion issue
  // const { alerts, summary } = useAlerts({
  //   filters: { severity: 'critical' },
  //   pollInterval: 120000, // Increased to 2 minutes to reduce load
  //   autoRefresh: true
  // });
  const alerts: any[] = [];
  const summary = null;

  // HTTP polling for health and statistics (30s refresh)
  const { health, loading: healthLoading, error: healthError } = useHealth(30000);
  const { statistics, loading: statsLoading, error: statsError } = useStatistics('1h', 30000);
  const { dataSources } = useDataSources(30000);
  
  // RAG Status calculation
  // Only show loading if we're actively loading AND haven't received any data yet
  // Once loading completes (even if data is null), stop showing loading spinner
  // This prevents infinite loading when APIs fail or return null
  // Also stop loading if we have an error (don't wait indefinitely)
  const hasError = enhancedHealthError || statsError;
  const isActivelyLoading = !hasError && (enhancedHealthLoading || statsLoading) && !enhancedHealth && !statistics;
  const { ragStatus, loading: ragLoading } = useRAGStatus({
    enhancedHealth,
    statistics,
    loading: isActivelyLoading
  });
  
  // Devices & Integrations data (for HA Integration section)
  const { devices, entities, integrations, loading: devicesLoading } = useDevices();
  
  // Container data for service status
  const [containers, setContainers] = useState<any[]>([]);
  const [containersLoading, setContainersLoading] = useState(true);
  
  // Extract metrics from the actual API response structure
  const websocketMetrics = statistics?.metrics?.['websocket-ingestion'];
  
  // Only show loading if we don't have ANY data yet (first load)
  // If we have partial data (health but no stats), show the data we have
  const hasInitialData = !healthLoading && !enhancedHealthLoading;
  const shouldShowLoading = statsLoading && !hasInitialData && !statistics;

  // Calculate critical alert counts
  const criticalAlerts = alerts.filter(a => a.severity === 'critical' && a.status === 'active');
  const totalCritical = summary?.critical || criticalAlerts.length;

  // Calculate overall system status
  const calculateOverallStatus = (): 'operational' | 'degraded' | 'error' => {
    // Critical alerts = immediate error state
    if (totalCritical > 0) return 'error';
    
    // RAG status check - if red = error, amber = degraded
    if (ragStatus) {
      if (ragStatus.overall === 'red') return 'error';
      if (ragStatus.overall === 'amber') return 'degraded';
    }
    
    // Check if any core dependencies are unhealthy
    const influxdb = enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB');
    const websocket = enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion');
    
    const unhealthyDeps = [influxdb, websocket].filter(d => d?.status !== 'healthy').length;
    
    if (unhealthyDeps > 0) return 'degraded';
    if (health?.status !== 'healthy') return 'degraded';
    
    // Check data source health - if any are unhealthy = degraded
    // Exclude non-critical data sources (like Calendar) from affecting overall health
    const criticalDataSources = ['weather', 'carbonIntensity', 'electricityPricing', 'airQuality', 'smartMeter'];
    const unhealthyDataSources = Object.entries(dataSources || {})
      .filter(([key, ds]) => 
        criticalDataSources.includes(key) && 
        (ds?.status === 'error' || ds?.status === 'unhealthy')
      ).length;
    
    // Only degrade if critical data sources are unhealthy
    if (unhealthyDataSources > 0) return 'degraded';
    
    return 'operational';
  };

  // Calculate aggregated metrics for Hero section
  // CRITICAL: Only return real values if data has loaded, otherwise return null to prevent false data display
  const calculateAggregatedMetrics = () => {
    // Don't show default values until we have real data
    const hasData = enhancedHealth || statistics;
    if (!hasData && (enhancedHealthLoading || statsLoading)) {
      return null; // Still loading - don't show false data
    }

    const uptime = enhancedHealth?.metrics?.uptime_human || 'N/A';
    const throughput = websocketMetrics?.events_per_minute ?? null; // Use null instead of 0
    const errorRate = websocketMetrics?.error_rate ?? null; // Use null instead of 0
    
    // Calculate average latency across services
    const latencies = enhancedHealth?.dependencies
      ?.filter(d => d.response_time_ms !== undefined)
      .map(d => d.response_time_ms!) || [];
    const avgLatency = latencies.length > 0 
      ? latencies.reduce((sum, val) => sum + val, 0) / latencies.length 
      : null; // Use null instead of 0
    
    return { uptime, throughput, latency: avgLatency, errorRate };
  };

  const metrics = calculateAggregatedMetrics();
  const overallStatus = calculateOverallStatus();
  
  // Determine if we should show loading state (no data yet and still loading)
  const isInitialLoad = !enhancedHealth && !statistics && (enhancedHealthLoading || statsLoading);
  
  // Phase 2: Track performance history for sparkline
  const { history: throughputHistory, stats: throughputStats } = usePerformanceHistory(
    metrics.throughput,
    { maxDataPoints: 60, sampleInterval: 60000 }
  );

  // Calculate HA Integration health metrics
  const calculateHAIntegrationHealth = () => {
    const totalDevices = devices.length;
    const totalEntities = entities.length;

    // Build integration → unique device_id set using entities when available
    // This is the most reliable source for platform information.
    const integrationToDeviceIds = new Map<string, Set<string>>();
    if (totalEntities > 0) {
      entities.forEach(entity => {
        const platform = entity.platform || 'unknown';
        const deviceId = entity.device_id || `__no_device__:${entity.entity_id}`;
        if (!integrationToDeviceIds.has(platform)) {
          integrationToDeviceIds.set(platform, new Set());
        }
        integrationToDeviceIds.get(platform)!.add(deviceId);
      });
    } else {
      // Fallback: estimate using device.integration field when entities are unavailable
      devices.forEach(device => {
        const platform = device.integration || 'unknown';
        if (!integrationToDeviceIds.has(platform)) {
          integrationToDeviceIds.set(platform, new Set());
        }
        integrationToDeviceIds.get(platform)!.add(device.device_id);
      });
    }

    // Convert to counts
    const integrationDeviceCounts = new Map<string, number>();
    integrationToDeviceIds.forEach((deviceIdSet, platform) => {
      integrationDeviceCounts.set(platform, deviceIdSet.size);
    });
    
    // Calculate health based on recent activity and device count
    let topIntegrations = Array.from(integrationDeviceCounts.entries())
      .map(([platform, deviceCount]) => {
        // Determine health based on device count and recent activity
        // If we have devices, assume the integration is healthy
        // This is more reliable than relying on integration state data that may not exist
        const isHealthy = deviceCount > 0;
        
        return {
          platform,
          deviceCount,
          healthy: isHealthy
        };
      })
      .sort((a, b) => b.deviceCount - a.deviceCount)
      .slice(0, 6);

    // If we have named integrations alongside 'unknown', drop 'unknown' for clarity
    const hasNamed = topIntegrations.some(i => i.platform !== 'unknown');
    if (hasNamed) {
      topIntegrations = topIntegrations.filter(i => i.platform !== 'unknown');
    }
    
    // Calculate overall health percentage
    const totalPlatforms = hasNamed
      ? Array.from(integrationDeviceCounts.keys()).filter(k => k !== 'unknown').length
      : integrationDeviceCounts.size;
    const healthyPlatforms = topIntegrations.filter(i => i.healthy).length;
    const healthPercent = totalPlatforms > 0 
      ? Math.round((healthyPlatforms / totalPlatforms) * 100) 
      : 0;
    
    return {
      totalDevices,
      totalEntities,
      totalIntegrations: totalPlatforms,
      healthPercent,
      topIntegrations
    };
  };
  
  // Only calculate if we're showing the section
  const haIntegration = devices.length > 0 ? calculateHAIntegrationHealth() : null;

  // Calculate data freshness for display
  const getDataFreshness = () => {
    const updates: Date[] = [];
    if (enhancedHealth) updates.push(new Date()); // Approximate - would need timestamp from API
    if (statistics) updates.push(new Date());
    if (updates.length === 0) return null;
    return new Date(Math.max(...updates.map(d => d.getTime())));
  };

  const lastDataUpdate = getDataFreshness();
  const isDataStale = lastDataUpdate ? (Date.now() - lastDataUpdate.getTime()) > 60000 : false;

  return (
    <>
      {/* Data Freshness Indicator - Show at top if data is stale, loading, or has errors */}
      {(isDataStale || isInitialLoad || enhancedHealthError || statsError || healthError) && (
        <div className={`mb-4 p-3 rounded-lg border ${
          enhancedHealthError || statsError || healthError
            ? darkMode ? 'bg-red-900/20 border-red-700' : 'bg-red-50 border-red-200'
            : isInitialLoad
              ? darkMode ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'
              : darkMode ? 'bg-yellow-900/20 border-yellow-700' : 'bg-yellow-50 border-yellow-200'
        }`}>
          <DataFreshnessIndicator
            lastUpdate={lastDataUpdate}
            isStale={isDataStale}
            loading={isInitialLoad}
            error={enhancedHealthError || statsError || healthError || null}
            darkMode={darkMode}
          />
          {/* Additional error details */}
          {(enhancedHealthError || statsError || healthError) && (
            <div className={`mt-2 text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
              <p className="font-medium">API Connection Issues:</p>
              <ul className="list-disc list-inside mt-1 space-y-1">
                {enhancedHealthError && <li>Enhanced Health: {enhancedHealthError}</li>}
                {statsError && <li>Statistics: {statsError}</li>}
                {healthError && <li>Health: {healthError}</li>}
              </ul>
              <p className="mt-2 text-xs opacity-75">
                Showing cached data. Refresh will be attempted automatically.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Critical Alerts Banner (Story 21.6) */}
      {totalCritical > 0 && (
        <div className={`mb-6 rounded-lg shadow-md p-6 border-2 ${
          darkMode 
            ? 'bg-red-900/20 border-red-500/50' 
            : 'bg-red-50 border-red-300'
        }`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <span className="text-3xl">🚨</span>
              <div>
                <h3 className={`text-lg font-bold ${darkMode ? 'text-red-200' : 'text-red-800'} mb-1`}>
                  {totalCritical} Critical {totalCritical === 1 ? 'Alert' : 'Alerts'} Requiring Immediate Attention
                </h3>
                <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                  System health is degraded. Review and resolve critical issues immediately.
                </p>
                {criticalAlerts.slice(0, 3).map(alert => (
                  <div key={alert.id} className={`mt-2 text-sm ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
                    <span className="font-medium">• {alert.service}:</span> {alert.message}
                  </div>
                ))}
                {totalCritical > 3 && (
                  <p className={`mt-2 text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                    ... and {totalCritical - 3} more
                  </p>
                )}
              </div>
            </div>
            <a
              href="#alerts"
              onClick={(e) => {
                e.preventDefault();
                const alertsTab = document.querySelector('[data-tab="alerts"]') as HTMLElement;
                if (alertsTab) alertsTab.click();
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                darkMode
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              View All Alerts →
            </a>
          </div>
        </div>
      )}

      {/* System Status Hero Section - Phase 2: With Trends */}
      {isInitialLoad || !metrics ? (
        <div className="mb-8">
          <SkeletonCard variant="metric" />
        </div>
      ) : (
        <SystemStatusHero
          overallStatus={overallStatus}
          uptime={metrics.uptime}
          throughput={metrics.throughput ?? 0}
          latency={metrics.latency ?? 0}
          errorRate={metrics.errorRate ?? 0}
          lastUpdate={new Date()}
          darkMode={darkMode}
          loading={enhancedHealthLoading || statsLoading}
          trends={{
            throughput: throughputStats.previous,
            latency: metrics.latency ?? 0,
            errorRate: metrics.errorRate ?? 0
          }}
        />
      )}

      {/* Core System Components - Phase 3: With animations */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 Core System Components
          </h2>
          {/* Component-level freshness indicator */}
          {enhancedHealth && (
            <DataFreshnessIndicator
              lastUpdate={lastDataUpdate}
              isStale={isDataStale}
              loading={enhancedHealthLoading || statsLoading}
              error={enhancedHealthError || statsError}
              darkMode={darkMode}
              className="text-xs"
            />
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" role="group" aria-label="Core system components">
          {healthLoading || enhancedHealthLoading ? (
            <>
              <SkeletonCard variant="service" />
              <SkeletonCard variant="service" />
            </>
          ) : (
            <>
              {/* Ingestion Card - Phase 2: Clickable for details */}
              <CoreSystemCard
                title="INGESTION"
                icon="🔌"
                service="WebSocket Connection"
                status={
                  enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion')?.status === 'healthy'
                    ? 'healthy'
                    : enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion')?.status === 'degraded'
                      ? 'degraded'
                      : 'unhealthy'
                }
                metrics={{
                  primary: {
                    label: 'Events per Hour',
                    value: websocketMetrics?.events_per_minute 
                      ? (websocketMetrics.events_per_minute * 60)
                      : (shouldShowLoading ? 'Loading...' : 0),
                    unit: websocketMetrics?.events_per_minute ? 'evt/h' : ''
                  },
                  secondary: {
                    label: 'Total Events',
                    value: websocketMetrics?.total_events_received ?? (shouldShowLoading ? 'Loading...' : 0),
                    unit: websocketMetrics?.total_events_received !== undefined ? 'events' : ''
                  }
                }}
                uptime={enhancedHealth?.metrics?.uptime_human || 'N/A'}
                darkMode={darkMode}
                loading={shouldShowLoading}
                onExpand={() => setSelectedService({
                  title: 'INGESTION',
                  icon: '🔌',
                  service: 'WebSocket Connection',
                  status: enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion')?.status === 'healthy' ? 'healthy' : 'unhealthy',
                  details: [
                    { label: 'Events per Minute', value: websocketMetrics?.events_per_minute || 0, unit: 'evt/min' },
                    { label: 'Events per Hour', value: (websocketMetrics?.events_per_minute || 0) * 60, unit: 'evt/h' },
                    { label: 'Total Events Received', value: websocketMetrics?.total_events_received || 0, unit: 'events' },
                    { label: 'Connection Status', value: enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion')?.status || 'unknown' },
                    { label: 'Response Time', value: (enhancedHealth?.dependencies?.find(d => d.name === 'WebSocket Ingestion')?.response_time_ms ?? 0).toFixed(1), unit: 'ms' },
                    { label: 'Uptime', value: enhancedHealth?.metrics?.uptime_human || 'N/A' }
                  ]
                })}
              />

              {/* Storage Card - Phase 2: Clickable for details */}
              <CoreSystemCard
                title="STORAGE"
                icon="🗄️"
                service="InfluxDB Database"
                status={
                  enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.status === 'healthy'
                    ? 'healthy'
                    : enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.status === 'degraded'
                      ? 'degraded'
                      : 'unhealthy'
                }
                metrics={{
                  primary: {
                    label: 'Response Time',
                    value: enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.response_time_ms !== undefined
                      ? enhancedHealth.dependencies.find(d => d.name === 'InfluxDB')!.response_time_ms!.toFixed(1)
                      : (shouldShowLoading ? 'Loading...' : '0.0'),
                    unit: enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.response_time_ms !== undefined ? 'ms' : ''
                  },
                  secondary: {
                    label: 'Availability',
                    value: enhancedHealth?.metrics?.uptime_percentage !== undefined
                      ? enhancedHealth.metrics.uptime_percentage.toFixed(2)
                      : (shouldShowLoading ? 'Loading...' : '0.0'),
                    unit: enhancedHealth?.metrics?.uptime_percentage !== undefined ? '%' : ''
                  }
                }}
                uptime={enhancedHealth?.metrics?.uptime_human || 'N/A'}
                darkMode={darkMode}
                loading={shouldShowLoading}
                onExpand={() => setSelectedService({
                  title: 'STORAGE',
                  icon: '🗄️',
                  service: 'InfluxDB Database',
                  status: enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.status === 'healthy' ? 'healthy' : 'unhealthy',
                  details: [
                    { label: 'Response Time', value: (enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.response_time_ms ?? 0).toFixed(1), unit: 'ms' },
                    { label: 'Availability', value: enhancedHealth?.metrics?.uptime_percentage?.toFixed(2) ?? '0.0', unit: '%' },
                    { label: 'Connection Status', value: enhancedHealth?.dependencies?.find(d => d.name === 'InfluxDB')?.status || 'unknown' },
                    { label: 'Database Type', value: 'InfluxDB 2.7' },
                    { label: 'Uptime', value: enhancedHealth?.metrics?.uptime_human || 'N/A' }
                  ]
                })}
              />
            </>
          )}
        </div>
      </div>

      {/* RAG Status Monitor - Option 1: Integrated RAG Status Card */}
      <div className="mb-8" data-testid="rag-status-section">
        <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🚦 RAG Status Monitor
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <RAGStatusCard
            ragStatus={ragStatus}
            loading={ragLoading}
            darkMode={darkMode}
            onExpand={() => setShowRAGDetails(true)}
          />
        </div>
      </div>

      {/* Active Data Sources - Phase 2: Clickable */}
      <div className="mb-8">
        <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🔗 Active Data Sources
        </h2>
        <div className={`rounded-lg shadow p-6 ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
          <div className="flex flex-wrap gap-4">
            {Object.entries(dataSources || {}).map(([key, value]) => (
              <button
                key={key}
                onClick={() => {
                  const dataSourcesTab = document.querySelector('[data-tab="data-sources"]') as HTMLElement;
                  if (dataSourcesTab) dataSourcesTab.click();
                }}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                  darkMode 
                    ? 'hover:bg-gray-700' 
                    : 'hover:bg-gray-100'
                }`}
              >
                <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <span className="text-xl" title={value?.status_detail || value?.status || 'unknown'}>
                  {value?.status_detail === 'credentials_missing' || value?.credentials_configured === false 
                    ? '🔑' 
                    : value?.status === 'healthy' 
                      ? '✅' 
                      : value?.status === 'error' 
                        ? '❌' 
                        : value?.status === 'degraded' 
                          ? '⚠️' 
                          : '⏸️'}
                </span>
              </button>
            ))}
            {(!dataSources || Object.keys(dataSources).length === 0) && (
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                No active data sources configured
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Phase 2/3: Performance Sparkline with configurable time range */}
      {/* TEMPORARY: Disabled due to null handling issues - will fix separately */}
      {false && throughputHistory.length > 0 && throughputStats.current != null && (
        <div className="mb-8">
          <PerformanceSparkline
            data={throughputHistory}
            current={throughputStats.current}
            peak={throughputStats.peak || 0}
            average={throughputStats.average || 0}
            unit="evt/min"
            darkMode={darkMode}
            selectedTimeRange={sparklineTimeRange}
            onTimeRangeChange={setSparklineTimeRange}
          />
        </div>
      )}

      {/* Home Assistant Integration Status */}
      {/* Re-enabled with comprehensive null safety */}
      {true && <div className="mb-8">
        <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🏠 Home Assistant Integration
        </h2>
        
        {devicesLoading && devices.length === 0 ? (
          <SkeletonCard variant="metric" />
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {/* Devices Card */}
              <div className={`p-4 rounded-lg shadow border ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Devices
                    </p>
                    <p className="text-3xl font-bold mt-1">
                      {haIntegration?.totalDevices || 0}
                    </p>
                  </div>
                  <div className="text-4xl">📱</div>
                </div>
              </div>

              {/* Entities Card */}
              <div className={`p-4 rounded-lg shadow border ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Entities
                    </p>
                    <p className="text-3xl font-bold mt-1">
                      {haIntegration?.totalEntities || 0}
                    </p>
                  </div>
                  <div className="text-4xl">🔌</div>
                </div>
              </div>

              {/* Active Services Card */}
              <div className={`p-4 rounded-lg shadow border ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Active Services
                    </p>
                    <p className="text-3xl font-bold mt-1">
                      {containers?.filter(c => c.status === 'running').length || 0}
                    </p>
                  </div>
                  <div className="text-4xl">🔧</div>
                </div>
              </div>

              {/* System Health Card */}
              <div className={`p-4 rounded-lg shadow border ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      System Health
                    </p>
                    <p className="text-3xl font-bold mt-1">
                      {overallStatus === 'operational' ? '100' : 
                        overallStatus === 'degraded' ? '75' : '25'}%
                    </p>
                  </div>
                  <div className="text-4xl">
                    {overallStatus === 'operational' ? '✅' : 
                      overallStatus === 'degraded' ? '⚠️' : '❌'}
                  </div>
                </div>
              </div>
            </div>

            {/* Top Integrations - Enhanced */}
            {((haIntegration?.topIntegrations || []).some(i => i.platform !== 'unknown')) && (
              <div className={`p-6 rounded-lg shadow border ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <h3 className={`text-sm font-semibold mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Top Integrations
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(haIntegration?.topIntegrations || []).map(({ platform, deviceCount, healthy }) => {
                    const status = healthy ? 'healthy' : 'degraded';
                    const colors = getStatusColors(status, darkMode);
                    
                    return (
                      <div 
                        key={platform}
                        className={`relative p-4 rounded-lg border-2 transition-all duration-300 ${
                          colors.bg
                        } ${colors.border} hover:shadow-lg hover:scale-105 group`}
                      >
                        <button
                          onClick={() => {
                            // Set URL parameter for integration context
                            const url = new URL(window.location.href);
                            url.searchParams.set('integration', platform);
                            window.history.replaceState({}, '', url.toString());
                            
                            // Trigger custom event for tab navigation
                            window.dispatchEvent(new CustomEvent('navigateToTab', { 
                              detail: { tabId: 'devices' } 
                            }));
                          }}
                          className="w-full flex items-center space-x-3 cursor-pointer text-left"
                          aria-label={`View devices for ${platform} integration`}
                        >
                          <span className="text-2xl flex-shrink-0">
                            {colors.icon}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-semibold truncate ${colors.text}`}>
                              {platform}
                            </p>
                            <p className={`text-xs mt-1 ${colors.text} opacity-75`}>
                              {deviceCount} {deviceCount === 1 ? 'device' : 'devices'}
                            </p>
                          </div>
                        </button>
                        
                        {/* Info button for modal */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedIntegration({ platform, deviceCount, healthy });
                          }}
                          className={`absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center transition-all ${
                            darkMode 
                              ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' 
                              : 'bg-white hover:bg-gray-100 text-gray-600'
                          } opacity-0 group-hover:opacity-100 shadow-md`}
                          aria-label={`View details for ${platform} integration`}
                          title="View details"
                        >
                          ℹ️
                        </button>
                      </div>
                    );
                  })}
                </div>
                
                {/* View All Devices Button */}
                <div className="mt-4 text-center">
                  <button
                    onClick={() => {
                      const devicesTab = document.querySelector('[data-tab="devices"]') as HTMLElement;
                      if (devicesTab) devicesTab.click();
                    }}
                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    View All Devices →
                  </button>
                </div>
              </div>
            )}

            {/* Empty State */}
            {(haIntegration?.totalDevices || 0) === 0 && (
              <div className={`p-8 rounded-lg shadow border text-center ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="text-6xl mb-4">🏠</div>
                <p className={`text-lg font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  No Home Assistant devices discovered yet
                </p>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Waiting for Home Assistant connection and device discovery...
                </p>
              </div>
            )}

            {/* Devices API Connection Status */}
            <div className={`mt-4 p-4 rounded-lg shadow border ${
              darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">
                    {devicesLoading ? '⏳' : (haIntegration?.totalDevices || 0) > 0 ? '✅' : '⚠️'}
                  </div>
                  <div>
                    <p className={`text-sm font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      HA Devices API Status
                    </p>
                    <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {devicesLoading 
                        ? 'Loading device data...' 
                        : (haIntegration?.totalDevices || 0) > 0 
                          ? `Connected - ${haIntegration.totalDevices} devices discovered`
                          : 'Connected - Awaiting device discovery'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    const devicesTab = document.querySelector('[data-tab="devices"]') as HTMLElement;
                    if (devicesTab) devicesTab.click();
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                  }`}
                >
                  View Details →
                </button>
              </div>
            </div>
          </>
        )}
      </div>}

      {/* Footer */}
      <div className={`text-center text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'} mt-12 pt-8 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <p className="font-semibold">
          🏠 HA Ingestor Dashboard - Real-time System Health Monitoring
        </p>
        <p className="text-xs mt-2">
          {haIntegration?.totalDevices || 0} Devices • {haIntegration?.totalEntities || 0} Entities • {haIntegration?.totalIntegrations || 0} Integrations •{' '}
          {Object.values(dataSources || {}).filter(d => d?.status === 'healthy').length}/{Object.values(dataSources || {}).filter(d => d !== null).length} Data Sources Healthy •{' '}
          {containers?.filter(c => c.status === 'running').length || 0} Services Running • Built with React & TypeScript
        </p>
      </div>

      {/* Phase 2: Service Details Modal */}
      {selectedService && (
        <ServiceDetailsModal
          isOpen={true}
          onClose={() => setSelectedService(null)}
          title={selectedService.title}
          icon={selectedService.icon}
          service={selectedService.service}
          status={selectedService.status}
          details={selectedService.details}
          darkMode={darkMode}
        />
      )}

      {/* Phase 2.1: Integration Details Modal */}
      {selectedIntegration && (
        <IntegrationDetailsModal
          isOpen={true}
          onClose={() => setSelectedIntegration(null)}
          platform={selectedIntegration.platform}
          deviceCount={selectedIntegration.deviceCount}
          healthy={selectedIntegration.healthy}
          darkMode={darkMode}
        />
      )}

      {/* RAG Details Modal */}
      <RAGDetailsModal
        isOpen={showRAGDetails}
        onClose={() => setShowRAGDetails(false)}
        ragStatus={ragStatus}
        darkMode={darkMode}
      />
    </>
  );
};
