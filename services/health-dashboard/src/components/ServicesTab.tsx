import React, { useState, useEffect } from 'react';
import { ServiceCard } from './ServiceCard';
import { ServiceDetailsModal } from './ServiceDetailsModal';
import { SkeletonCard } from './skeletons';
import { apiService, ContainerInfo } from '../services/api';
import type { ServiceStatus, ServiceDefinition } from '../types';

interface ServicesTabProps {
  darkMode: boolean;
}

// Service definitions with metadata
const SERVICE_DEFINITIONS: ServiceDefinition[] = [
  // Core Services
  { id: 'websocket-ingestion', name: 'WebSocket Ingestion', icon: '🏠', type: 'core', port: 8001, description: 'Home Assistant WebSocket client' },
  { id: 'enrichment-pipeline', name: 'Enrichment Pipeline', icon: '🔄', type: 'core', port: 8002, description: 'Multi-source data enrichment' },
  // { id: 'data-retention', name: 'Data Retention', icon: '💾', type: 'core', port: 8080, description: 'Storage optimization' }, // TODO: Enable when service is deployed
  { id: 'admin-api', name: 'Admin API', icon: '🔌', type: 'core', port: 8003, description: 'REST API gateway' },
  { id: 'health-dashboard', name: 'Health Dashboard', icon: '📊', type: 'core', port: 3000, description: 'Web UI' },
  { id: 'influxdb', name: 'InfluxDB', icon: '🗄️', type: 'core', port: 8086, description: 'Time-series database' },
  
  // External Data Services
  { id: 'weather-api', name: 'Weather API', icon: '☁️', type: 'external', description: 'Weather data integration' },
  { id: 'carbon-intensity-service', name: 'Carbon Intensity', icon: '🌱', type: 'external', description: 'Carbon footprint tracking' },
  { id: 'electricity-pricing-service', name: 'Electricity Pricing', icon: '⚡', type: 'external', description: 'Energy cost monitoring' },
  { id: 'air-quality-service', name: 'Air Quality', icon: '💨', type: 'external', description: 'Air quality monitoring' },
  { id: 'calendar-service', name: 'Calendar', icon: '📅', type: 'external', description: 'Event correlation' },
  { id: 'smart-meter-service', name: 'Smart Meter', icon: '📈', type: 'external', description: 'Energy consumption tracking' },
];

export const ServicesTab: React.FC<ServicesTabProps> = ({ darkMode }) => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [selectedService, setSelectedService] = useState<{ service: ServiceStatus; icon: string } | null>(null);
  const [operatingServices, setOperatingServices] = useState<Set<string>>(new Set());

  const loadServices = async () => {
    try {
      // Load both services and containers
      const [servicesResponse, containersData] = await Promise.all([
        fetch('/api/v1/services'),
        apiService.getContainers().catch(() => []) // Fallback to empty array if containers fail
      ]);
      
      if (!servicesResponse.ok) throw new Error('Failed to load services');
      
      const servicesData = await servicesResponse.json();
      setServices(servicesData.services || []);
      setContainers(containersData);
      setError('');
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load services');
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
    } catch (err: any) {
      alert(`Error ${operation}ing container: ${err.message}`);
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

  const coreServices = services
    .map(s => ({ ...s, def: getServiceDefinition(s.service) }))
    .filter(s => s.def.type === 'core');
  
  const externalServices = services
    .map(s => ({ ...s, def: getServiceDefinition(s.service) }))
    .filter(s => s.def.type === 'external');

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

  return (
    <>
      {/* Service Details Modal */}
      {selectedService && (
        <ServiceDetailsModal
          service={selectedService.service}
          icon={selectedService.icon}
          isOpen={true}
          onClose={() => setSelectedService(null)}
          darkMode={darkMode}
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
        
        {/* Last Update Time */}
        <div className={`text-xs mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Last updated: {lastUpdate.toLocaleTimeString('en-US', {
            hour12: true,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </div>
      </div>

      {/* Core Services */}
      <div>
        <h3 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🏗️ Core Services ({coreServices.length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-in-list">
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-in-list">
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

