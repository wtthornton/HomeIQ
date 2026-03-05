import React, { useState, useEffect } from 'react';
import { ServiceCard } from './ServiceCard';
import { ServiceDetailsModal } from './ServiceDetailsModal';
import { SkeletonCard } from './skeletons';
import { apiService, ContainerInfo, adminApi } from '../services/api';
import type { ServiceStatus, ServiceDefinition, ServiceGroupId } from '../types';
import { fetchAIStats, AIStatsData } from './AIStats';
import { aiApi } from '../services/api';
import type { ServicesHealthResponse } from '../types/health';

interface ServicesTabProps {
  darkMode: boolean;
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

// Service definitions with metadata
export const SERVICE_DEFINITIONS: ServiceDefinition[] = [
  // Core Services
  { id: 'websocket-ingestion', name: 'WebSocket Ingestion', icon: '🏠', type: 'core', port: 8001, description: 'Home Assistant WebSocket client', group: 'core-platform' },
  { id: 'ai-automation-service', name: 'AI Automation Service', icon: '🤖', type: 'core', port: 8018, description: 'AI-powered automation and entity extraction', group: 'automation-intelligence' },
  // DEPRECATED: enrichment-pipeline (Port 8002) - Epic 31: Direct writes to InfluxDB
  // { id: 'enrichment-pipeline', name: 'Enrichment Pipeline', icon: '🔄', type: 'core', port: 8002, description: 'Multi-source data enrichment' },
  // { id: 'data-retention', name: 'Data Retention', icon: '💾', type: 'core', port: 8080, description: 'Storage optimization' }, // TODO: Enable when service is deployed
  { id: 'admin-api', name: 'Admin API', icon: '🔌', type: 'core', port: 8004, description: 'REST API gateway', group: 'core-platform' },
  { id: 'health-dashboard', name: 'Health Dashboard', icon: '📊', type: 'core', port: 3000, description: 'Web UI', group: 'core-platform' },
  { id: 'data-api', name: 'Data API', icon: '🗃️', type: 'core', port: 8006, description: 'Data query and metadata API', group: 'core-platform' },
  { id: 'influxdb', name: 'InfluxDB', icon: '🗄️', type: 'core', port: 8086, description: 'Time-series database', group: 'core-platform' },

  // External Data Services
  { id: 'weather-api', name: 'Weather API', icon: '☁️', type: 'external', port: 8009, description: 'Weather data integration (OpenWeatherMap)', group: 'data-collectors' },
  { id: 'sports-api', name: 'Sports API', icon: '⚽', type: 'external', port: 8005, description: 'Team Tracker integration', group: 'data-collectors' },
  { id: 'carbon-intensity-service', name: 'Carbon Intensity', icon: '🌱', type: 'external', description: 'Carbon footprint tracking', group: 'data-collectors' },
  { id: 'electricity-pricing-service', name: 'Electricity Pricing', icon: '⚡', type: 'external', description: 'Energy cost monitoring', group: 'data-collectors' },
  { id: 'air-quality-service', name: 'Air Quality', icon: '💨', type: 'external', description: 'Air quality monitoring', group: 'data-collectors' },
  { id: 'calendar-service', name: 'Calendar', icon: '📅', type: 'external', description: 'Event correlation', group: 'data-collectors' },
  { id: 'smart-meter-service', name: 'Smart Meter', icon: '📈', type: 'external', description: 'Energy consumption tracking', group: 'data-collectors' },

  // Energy Analytics
  { id: 'energy-correlator', name: 'Energy Correlator', icon: '🔋', type: 'core', port: 8017, description: 'Energy pattern correlation', group: 'energy-analytics' },
  { id: 'energy-forecasting', name: 'Energy Forecasting', icon: '📉', type: 'core', port: 8042, description: 'Energy demand forecasting', group: 'energy-analytics' },
  { id: 'proactive-agent-service', name: 'Proactive Agent', icon: '🧠', type: 'core', port: 8031, description: 'Proactive automation suggestions', group: 'energy-analytics' },

  // Blueprints
  { id: 'blueprint-index', name: 'Blueprint Index', icon: '📋', type: 'core', port: 8031, description: 'Blueprint catalog and search', group: 'blueprints' },
  { id: 'blueprint-suggestion-service', name: 'Blueprint Suggestions', icon: '💡', type: 'core', port: 8032, description: 'AI-powered blueprint recommendations', group: 'blueprints' },
  { id: 'rule-recommendation-ml', name: 'Rule Recommendation', icon: '🎯', type: 'core', port: 8035, description: 'ML-based rule suggestions', group: 'blueprints' },

  // Pattern Analysis
  { id: 'ai-pattern-service', name: 'AI Pattern Service', icon: '🔍', type: 'core', port: 8034, description: 'Pattern detection and synergy analysis', group: 'pattern-analysis' },
  { id: 'api-automation-edge', name: 'Automation Edge', icon: '⚡', type: 'core', port: 8041, description: 'Edge automation processing', group: 'pattern-analysis' },

  // Device Management
  { id: 'device-health-monitor', name: 'Device Health Monitor', icon: '🏥', type: 'core', port: 8019, description: 'Device health tracking', group: 'device-management' },
  { id: 'device-context-classifier', name: 'Context Classifier', icon: '🏷️', type: 'core', port: 8032, description: 'Device context classification', group: 'device-management' },
  { id: 'device-setup-assistant', name: 'Setup Assistant', icon: '🔧', type: 'core', port: 8021, description: 'Device setup guidance', group: 'device-management' },

  // ML Engine
  { id: 'ai-core-service', name: 'AI Core Service', icon: '🤖', type: 'core', port: 8018, description: 'Central AI orchestration', group: 'ml-engine' },
  { id: 'device-intelligence-service', name: 'Device Intelligence', icon: '🧪', type: 'core', port: 8028, description: 'Device behavior analysis', group: 'ml-engine' },
  { id: 'rag-service', name: 'RAG Service', icon: '📚', type: 'core', port: 8027, description: 'Retrieval-augmented generation', group: 'ml-engine' },
];

export const GROUP_DEFINITIONS: Record<ServiceGroupId, { label: string; description: string }> = {
  'core-platform': { label: 'Core Platform', description: 'InfluxDB, Data API, WebSocket Ingestion, Admin API, Health Dashboard' },
  'data-collectors': { label: 'Data Collectors', description: 'Weather, Sports, Smart Meter, Air Quality, Carbon, Electricity, Calendar' },
  'ml-engine': { label: 'ML Engine', description: 'AI Core, Device Intelligence, RAG Service' },
  'automation-intelligence': { label: 'Automation Intelligence', description: 'HA AI Agent, AI Automation, Query Service' },
  'energy-analytics': { label: 'Energy Analytics', description: 'Energy Correlator, Forecasting, Proactive Agent' },
  'blueprints': { label: 'Blueprints', description: 'Blueprint Index, Suggestions, Rule Recommendation' },
  'pattern-analysis': { label: 'Pattern Analysis', description: 'AI Pattern Service, Automation Edge' },
  'device-management': { label: 'Device Management', description: 'Device Health, Classifier, Setup Assistant' },
  'frontends': { label: 'Frontends', description: 'Jaeger, Observability Dashboard, AI Automation UI' },
};

export const ServicesTab: React.FC<ServicesTabProps> = ({ darkMode }) => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [selectedService, setSelectedService] = useState<{ service: ServiceStatus; icon: string } | null>(null);
  const [operatingServices, setOperatingServices] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [aiStats, setAiStats] = useState<AIStatsData | null>(null);
  const [modelComparison, setModelComparison] = useState<any | null>(null);

  const loadServices = async () => {
    try {
      // Load both services (from admin-api health) and containers
      const [servicesHealth, containersData] = await Promise.all([
        adminApi.getServicesHealth(),
        apiService.getContainers().catch(() => []) // Fallback to empty array if containers fail
      ]);

      // Map admin-api services health response to ServiceStatus[] expected by UI
      // Prioritize health API status (more reliable) but use container status as confirmation
      const mappedServices: ServiceStatus[] = Object.entries(servicesHealth as ServicesHealthResponse).map(
        ([serviceName, health]) => {
          // Check if container exists and get its status
          const container = containersData.find(c => c.service_name === serviceName);
          const containerStatus = container?.status?.toLowerCase();
          
          // Determine status: prioritize container status (ground truth) when available
          // If container is stopped, service cannot be running regardless of health API
          let normalized: string;
          
          // First check container status - if stopped/exited, service is stopped
          if (container && containerStatus) {
            if (containerStatus === 'stopped' || containerStatus === 'exited') {
              // Container is stopped - service cannot be running
              normalized = 'stopped';
            } else if (containerStatus === 'running') {
              // Container is running - check health API for actual service health
              if (health.status === 'healthy' || health.status === 'pass') {
                normalized = 'running';
              } else if (health.status === 'degraded') {
                normalized = 'degraded';
              } else if (health.status === 'unhealthy' || health.status === 'error') {
                normalized = 'error';
              } else {
                // Health API unclear but container running - assume running
                normalized = 'running';
              }
            } else {
              // Container in unknown/other state - use health API
              if (health.status === 'healthy' || health.status === 'pass') {
                normalized = 'running';
              } else if (health.status === 'degraded') {
                normalized = 'degraded';
              } else if (health.status === 'unhealthy' || health.status === 'error') {
                normalized = 'error';
              } else {
                normalized = 'stopped';
              }
            }
          } else {
            // No container info - fall back to health API
            if (health.status === 'healthy' || health.status === 'pass') {
              normalized = 'running';
            } else if (health.status === 'degraded') {
              normalized = 'degraded';
            } else if (health.status === 'unhealthy' || health.status === 'error') {
              normalized = 'error';
            } else {
              // No container info and health API is unclear - default to stopped
              normalized = 'stopped';
            }
          }
          
          return {
            service: serviceName,
            running: normalized === 'running' || normalized === 'degraded',
            status: normalized,
            timestamp: health.last_check,
          };
        }
      );

      setServices(mappedServices);
      setContainers(containersData);
      setError('');
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load services');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServices();
    
    if (autoRefresh) {
      const interval = setInterval(loadServices, 5000); // 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // Fetch AI stats when modal opens for ai-automation-service
  useEffect(() => {
    if (!selectedService) {
      setAiStats(null);
      return;
    }

    // Only fetch for ai-automation-service
    if (selectedService.service.service !== 'ai-automation-service') {
      setAiStats(null);
      setModelComparison(null);
      return;
    }

    const loadAIStats = async () => {
      try {
        const stats = await fetchAIStats();
        setAiStats(stats);
      } catch (err) {
        console.error('Failed to load AI stats:', err);
        setAiStats(null);
      }
    };

    const loadModelComparison = async () => {
      try {
        const comparison = await aiApi.getModelComparison();
        setModelComparison(comparison);
      } catch (err) {
        console.error('Failed to load model comparison:', err);
        setModelComparison(null);
      }
    };

    loadAIStats();
    loadModelComparison();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadAIStats();
      loadModelComparison();
    }, 30000);
    return () => clearInterval(interval);
  }, [selectedService]);

  const getServiceDefinition = (serviceName: string): ServiceDefinition => {
    const def = SERVICE_DEFINITIONS.find(
      s => s.id === serviceName || s.name.toLowerCase().includes(serviceName.toLowerCase())
    );
    return def || {
      id: serviceName,
      name: serviceName,
      icon: '🔧',
      type: 'core',
      description: 'Service',
    };
  };

  const handleContainerOperation = async (
    serviceName: string, 
    operation: 'start' | 'stop' | 'restart'
  ) => {
    setOperatingServices(prev => new Set(prev).add(serviceName));
    
    try {
      let response;
      
      switch (operation) {
        case 'start':
          response = await apiService.startContainer(serviceName);
          break;
        case 'stop':
          response = await apiService.stopContainer(serviceName);
          break;
        case 'restart':
          response = await apiService.restartContainer(serviceName);
          break;
      }
      
      if (response.success) {
        // Refresh services after operation
        await loadServices();
      } else {
        alert(`Failed to ${operation} container: ${response.message}`);
      }
    } catch (err: unknown) {
      alert(`Error ${operation}ing container: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setOperatingServices(prev => {
        const newSet = new Set(prev);
        newSet.delete(serviceName);
        return newSet;
      });
    }
  };

  const getContainerStatus = (serviceName: string): string => {
    const container = containers.find(c => c.service_name === serviceName);
    return container?.status || 'unknown';
  };

  // Apply status filter
  const filterByStatus = (s: ServiceStatus) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'healthy') return s.status === 'running';
    if (statusFilter === 'degraded') return s.status === 'degraded';
    if (statusFilter === 'unhealthy') return s.status === 'error' || s.status === 'stopped';
    return true;
  };

  const coreServices = services
    .map(s => ({ ...s, def: getServiceDefinition(s.service) }))
    .filter(s => s.def.type === 'core' && filterByStatus(s));

  const externalServices = services
    .map(s => ({ ...s, def: getServiceDefinition(s.service) }))
    .filter(s => s.def.type === 'external' && filterByStatus(s));

  /**
   * Derive aggregate service status using worst-component strategy
   * (consistent with OverviewTab.calculateOverallStatus):
   *  - Any service in 'error' state -> 'degraded'
   *  - Any service in 'degraded' state -> 'degraded'
   *  - All services running -> 'operational'
   *  - No services at all -> 'operational' (nothing to be wrong)
   */
  const deriveAggregateStatus = (): 'operational' | 'degraded' | 'error' => {
    const hasError = services.some(s => s.status === 'error');
    const hasDegraded = services.some(s => s.status === 'degraded');
    if (hasError) return 'degraded';
    if (hasDegraded) return 'degraded';
    return 'operational';
  };
  const aggregateStatus = deriveAggregateStatus();
  const runningCount = services.filter(s => s.status === 'running' || s.status === 'degraded').length;
  const degradedCount = services.filter(s => s.status === 'degraded').length;
  const errorCount = services.filter(s => s.status === 'error').length;

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Core Services
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={`core-${i}`} variant="service" />
            ))}
          </div>
        </div>
        <div>
          <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            External Data Services
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={`external-${i}`} variant="service" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}>
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Error Loading Services
          </h3>
          <p className={`mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{error}</p>
          <button
            onClick={loadServices}
            className={`px-4 py-2 rounded-md font-medium transition-colors duration-200 ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Prepare modal props when a service is selected
  const modalProps = selectedService ? (() => {
    try {
      const serviceDef = getServiceDefinition(selectedService.service.service);
      const container = containers.find(c => c.service_name === selectedService.service.service);
      const serviceStatus = selectedService.service?.status || 'stopped';
      const status: 'healthy' | 'degraded' | 'unhealthy' | 'paused' = 
        serviceStatus === 'running' ? 'healthy' : 
          serviceStatus === 'error' ? 'unhealthy' :
            serviceStatus === 'degraded' ? 'degraded' : 'paused';
      const details = [
        { label: 'Service Name', value: selectedService.service.service || 'Unknown' },
        { label: 'Status', value: serviceStatus || 'unknown' },
        { label: 'Container Status', value: container?.status || 'unknown' },
        { label: 'Last Check', value: selectedService.service?.timestamp ? new Date(selectedService.service.timestamp).toLocaleString() : 'N/A' },
      ];
      return {
        title: serviceDef.name || selectedService.service.service || 'Service',
        service: selectedService.service.service || 'unknown',
        icon: selectedService.icon || '🔧',
        status,
        details,
      };
    } catch (err) {
      console.error('Error preparing modal props:', err);
      return null;
    }
  })() : null;

  return (
    <>
      {/* Service Details Modal */}
      {selectedService && modalProps && (
        <ServiceDetailsModal
          title={modalProps.title}
          service={modalProps.service}
          icon={modalProps.icon}
          status={modalProps.status}
          details={modalProps.details}
          isOpen={true}
          onClose={() => setSelectedService(null)}
          darkMode={darkMode}
          aiStats={aiStats}
          modelComparison={modelComparison}
        />
      )}

      <div className="space-y-8">
        {/* Header with Controls */}
        <div className={`rounded-lg shadow-md p-6 ${
          darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
        }`}>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
            <div>
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🔧 Service Management
              </h2>
              <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Monitoring {services.length} system services
              </p>
            </div>
          
            <div className="flex items-center space-x-4">
              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className={`px-3 py-2 rounded-md text-sm font-medium border transition-colors ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-gray-700'
                }`}
                aria-label="Filter services by status"
              >
                <option value="all">All Statuses</option>
                <option value="healthy">Healthy</option>
                <option value="degraded">Degraded</option>
                <option value="unhealthy">Unhealthy / Stopped</option>
              </select>

              {/* Auto-refresh Toggle */}
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-colors duration-200 ${
                  autoRefresh
                    ? darkMode
                      ? 'bg-green-700 hover:bg-green-600 text-white'
                      : 'bg-green-100 hover:bg-green-200 text-green-700'
                    : darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-white'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                <span>{autoRefresh ? '🔄' : '⏸️'}</span>
                <span>{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
              </button>
            
              {/* Manual Refresh */}
              <button
                onClick={loadServices}
                className={`px-4 py-2 rounded-md font-medium transition-colors duration-200 ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
              🔄 Refresh Now
              </button>
            </div>
          </div>
        
          {/* Status Summary */}
          {services.length > 0 && (
            <div className={`mt-4 flex items-center gap-4 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                aggregateStatus === 'operational'
                  ? darkMode ? 'bg-green-900/40 text-green-200' : 'bg-green-100 text-green-800'
                  : aggregateStatus === 'degraded'
                    ? darkMode ? 'bg-yellow-900/40 text-yellow-200' : 'bg-yellow-100 text-yellow-800'
                    : darkMode ? 'bg-red-900/40 text-red-200' : 'bg-red-100 text-red-800'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  aggregateStatus === 'operational' ? 'bg-green-500'
                    : aggregateStatus === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                {aggregateStatus === 'operational' ? 'All Operational' : aggregateStatus === 'degraded' ? 'Degraded' : 'Error'}
              </span>
              <span>{runningCount}/{services.length} running</span>
              {degradedCount > 0 && <span className="text-yellow-500">{degradedCount} degraded</span>}
              {errorCount > 0 && <span className="text-red-500">{errorCount} error</span>}
            </div>
          )}

          {/* Last Update Time */}
          <div className={`text-xs mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Updated {formatTimeAgo(lastUpdate)}
          </div>
        </div>

        {/* Core Services */}
        <div>
          <h3 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🏗️ Core Services ({coreServices.length})
          </h3>
          <div data-testid="service-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-in-list">
            {coreServices.map((service, index) => (
              <div key={service.service} style={{ animationDelay: `${index * 0.05}s` }}>
                <ServiceCard
                  key={service.service}
                  service={service}
                  icon={service.def.icon}
                  darkMode={darkMode}
                  onViewDetails={() => {
                    setSelectedService({ service, icon: service.def.icon });
                  }}
                  onConfigure={() => {
                    alert(`Configure ${service.service} - Use Configuration tab for now!`);
                  }}
                  onStart={() => handleContainerOperation(service.service, 'start')}
                  onStop={() => handleContainerOperation(service.service, 'stop')}
                  onRestart={() => handleContainerOperation(service.service, 'restart')}
                  containerStatus={getContainerStatus(service.service)}
                  isOperating={operatingServices.has(service.service)}
                />
              </div>
            ))}
          </div>
          {coreServices.length === 0 && (
            <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            No core services found
            </div>
          )}
        </div>

        {/* External Data Services */}
        <div>
          <h3 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🌐 External Data Services ({externalServices.length})
          </h3>
          <div data-testid="service-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-in-list">
            {externalServices.map((service, index) => (
              <div key={service.service} style={{ animationDelay: `${index * 0.05}s` }}>
                <ServiceCard
                  key={service.service}
                  service={service}
                  icon={service.def.icon}
                  darkMode={darkMode}
                  onViewDetails={() => {
                    setSelectedService({ service, icon: service.def.icon });
                  }}
                  onConfigure={() => {
                    alert(`Configure ${service.service} - Use Configuration tab for now!`);
                  }}
                  onStart={() => handleContainerOperation(service.service, 'start')}
                  onStop={() => handleContainerOperation(service.service, 'stop')}
                  onRestart={() => handleContainerOperation(service.service, 'restart')}
                  containerStatus={getContainerStatus(service.service)}
                  isOperating={operatingServices.has(service.service)}
                />
              </div>
            ))}
          </div>
          {externalServices.length === 0 && (
            <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            No external services found
            </div>
          )}
        </div>
      </div>
    </>
  );
};

