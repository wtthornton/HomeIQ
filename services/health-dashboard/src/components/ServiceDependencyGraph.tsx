import React, { useState } from 'react';
import type { ServiceStatus, ServiceNode, ServiceDependency } from '../types';

interface ServiceDependencyGraphProps {
  services: ServiceStatus[];
  darkMode: boolean;
}

// Define service nodes with positioning
const SERVICE_NODES: ServiceNode[] = [
  // Layer 1: Source
  { id: 'home-assistant', name: 'Home Assistant', icon: '🏠', type: 'ui', layer: 1, position: 1 },
  
  // Layer 2: Ingestion
  { id: 'websocket-ingestion', name: 'WebSocket Ingestion', icon: '📡', type: 'core', layer: 2, position: 1 },
  
  // Layer 3: External Data Sources
  { id: 'weather-api', name: 'Weather API', icon: '☁️', type: 'external', layer: 3, position: 1 },
  { id: 'carbon-intensity-service', name: 'Carbon Intensity', icon: '🌱', type: 'external', layer: 3, position: 2 },
  { id: 'electricity-pricing-service', name: 'Electricity Pricing', icon: '⚡', type: 'external', layer: 3, position: 3 },
  { id: 'air-quality-service', name: 'Air Quality', icon: '💨', type: 'external', layer: 3, position: 4 },
  { id: 'calendar-service', name: 'Calendar', icon: '📅', type: 'external', layer: 3, position: 5 },
  { id: 'smart-meter-service', name: 'Smart Meter', icon: '📈', type: 'external', layer: 3, position: 6 },
  
  // Layer 4: Processing
  // NOTE: enrichment-pipeline removed (deprecated in Epic 31 - all normalization now inline in websocket-ingestion)
  
  // Layer 5: Storage & Services
  { id: 'influxdb', name: 'InfluxDB', icon: '🗄️', type: 'storage', layer: 5, position: 1 },
  { id: 'data-retention', name: 'Data Retention', icon: '💾', type: 'core', layer: 5, position: 2 },
  { id: 'admin-api', name: 'Admin API', icon: '🔌', type: 'core', layer: 5, position: 3 },
  { id: 'health-dashboard', name: 'Health Dashboard', icon: '📊', type: 'ui', layer: 5, position: 4 },
];

// Define service dependencies (Epic 31 Architecture)
const SERVICE_DEPENDENCIES: ServiceDependency[] = [
  // Main data flow (Epic 31: Direct write, no enrichment-pipeline)
  { from: 'home-assistant', to: 'websocket-ingestion', type: 'data_flow', description: 'WebSocket events' },
  { from: 'websocket-ingestion', to: 'influxdb', type: 'storage', description: 'Direct write (inline normalization)' },
  
  // External data sources (Epic 31: Direct writes to InfluxDB)
  { from: 'weather-api', to: 'influxdb', type: 'storage', description: 'Weather data' },
  { from: 'carbon-intensity-service', to: 'influxdb', type: 'storage', description: 'Carbon data' },
  { from: 'electricity-pricing-service', to: 'influxdb', type: 'storage', description: 'Pricing data' },
  { from: 'air-quality-service', to: 'influxdb', type: 'storage', description: 'Air quality' },
  { from: 'calendar-service', to: 'influxdb', type: 'storage', description: 'Calendar events' },
  { from: 'smart-meter-service', to: 'influxdb', type: 'storage', description: 'Energy data' },
  
  // Storage and admin
  { from: 'data-retention', to: 'influxdb', type: 'api_call', description: 'Data management' },
  { from: 'admin-api', to: 'influxdb', type: 'api_call', description: 'Queries' },
  { from: 'health-dashboard', to: 'admin-api', type: 'api_call', description: 'REST API' },
];

export const ServiceDependencyGraph: React.FC<ServiceDependencyGraphProps> = ({
  services,
  darkMode,
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const getServiceStatus = (nodeId: string): ServiceStatus | undefined => {
    return services.find(s => 
      s.service === nodeId || 
      s.service.toLowerCase().includes(nodeId.toLowerCase()) ||
      nodeId.toLowerCase().includes(s.service.toLowerCase())
    );
  };

  const getStatusColor = (nodeId: string) => {
    const service = getServiceStatus(nodeId);
    if (!service) return darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-100 border-gray-300';
    
    switch (service.status) {
      case 'running':
        return darkMode ? 'bg-green-900 border-green-700' : 'bg-green-100 border-green-500';
      case 'error':
        return darkMode ? 'bg-red-900 border-red-700' : 'bg-red-100 border-red-500';
      case 'degraded':
        return darkMode ? 'bg-yellow-900 border-yellow-700' : 'bg-yellow-100 border-yellow-500';
      default:
        return darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-100 border-gray-300';
    }
  };

  const isNodeHighlighted = (nodeId: string): boolean => {
    if (!selectedNode) return false;
    if (nodeId === selectedNode) return true;
    
    // Check if this node is in the dependency path
    const isSource = SERVICE_DEPENDENCIES.some(d => d.from === selectedNode && d.to === nodeId);
    const isTarget = SERVICE_DEPENDENCIES.some(d => d.to === selectedNode && d.from === nodeId);
    
    return isSource || isTarget;
  };

  const getConnectionOpacity = (from: string, to: string): string => {
    if (!selectedNode) return darkMode ? 'opacity-30' : 'opacity-20';
    if (from === selectedNode || to === selectedNode) return 'opacity-100';
    return 'opacity-10';
  };

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(selectedNode === nodeId ? null : nodeId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-md`}>
        <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🔗 Service Dependencies & Data Flow
        </h2>
        <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Click on any service to highlight its dependencies
        </p>
      </div>

      {/* Legend */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-md`}>
        <h3 className={`font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Legend
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-2">
            <div className={`w-4 h-4 rounded ${darkMode ? 'bg-green-900 border-2 border-green-700' : 'bg-green-100 border-2 border-green-500'}`} />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Running</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-4 h-4 rounded ${darkMode ? 'bg-yellow-900 border-2 border-yellow-700' : 'bg-yellow-100 border-2 border-yellow-500'}`} />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Degraded</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-4 h-4 rounded ${darkMode ? 'bg-red-900 border-2 border-red-700' : 'bg-red-100 border-2 border-red-500'}`} />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Error</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-4 h-4 rounded ${darkMode ? 'bg-gray-700 border-2 border-gray-600' : 'bg-gray-100 border-2 border-gray-300'}`} />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Unknown</span>
          </div>
        </div>
      </div>

      {/* Dependency Graph */}
      <div className={`p-8 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-md overflow-x-auto`}>
        <div className="min-w-max">
          {/* Layer 1: Home Assistant */}
          <div className="flex justify-center mb-8">
            <div
              onClick={() => handleNodeClick('home-assistant')}
              onMouseEnter={() => setHoveredNode('home-assistant')}
              onMouseLeave={() => setHoveredNode(null)}
              className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                getStatusColor('home-assistant')
              } ${isNodeHighlighted('home-assistant') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
            >
              <div className="flex flex-col items-center">
                <div className="text-3xl mb-2">🏠</div>
                <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Home Assistant
                </div>
              </div>
              {hoveredNode === 'home-assistant' && (
                <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                  darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                }`}>
                  <div className="text-xs">External event source</div>
                </div>
              )}
            </div>
          </div>

          {/* Arrow Down */}
          <div className="flex justify-center mb-4">
            <div className={`text-4xl ${getConnectionOpacity('home-assistant', 'websocket-ingestion')}`}>↓</div>
          </div>

          {/* Layer 2: WebSocket Ingestion */}
          <div className="flex justify-center mb-8">
            <div
              onClick={() => handleNodeClick('websocket-ingestion')}
              onMouseEnter={() => setHoveredNode('websocket-ingestion')}
              onMouseLeave={() => setHoveredNode(null)}
              className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                getStatusColor('websocket-ingestion')
              } ${isNodeHighlighted('websocket-ingestion') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
            >
              <div className="flex flex-col items-center">
                <div className="text-3xl mb-2">📡</div>
                <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  WebSocket<br/>Ingestion
                </div>
              </div>
              {hoveredNode === 'websocket-ingestion' && (
                <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                  darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                }`}>
                  <div className="text-xs">Captures HA events</div>
                </div>
              )}
            </div>
          </div>

          {/* External Services Row - Spread horizontally */}
          <div className="mb-8">
            <div className={`text-sm font-semibold mb-6 text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              External Data Sources
            </div>
            <div className="flex flex-wrap justify-center gap-6">
              {SERVICE_NODES.filter(n => n.type === 'external').map(node => (
                <div
                  key={node.id}
                  onClick={() => handleNodeClick(node.id)}
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className={`relative px-4 py-3 rounded-lg border-2 cursor-pointer transition-all ${
                    getStatusColor(node.id)
                  } ${isNodeHighlighted(node.id) ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
                >
                  <div className="flex flex-col items-center">
                    <div className="text-2xl mb-1">{node.icon}</div>
                    <div className={`text-xs font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {node.name}
                    </div>
                  </div>
                  {hoveredNode === node.id && (
                    <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                      darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                    }`}>
                      <div className="text-xs">External enrichment</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Arrows from External Services to Enrichment Pipeline */}
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-4">
              <div className={`text-2xl ${getConnectionOpacity('weather-api', 'enrichment-pipeline')}`}>↘</div>
              <div className={`text-2xl ${getConnectionOpacity('carbon-intensity-service', 'enrichment-pipeline')}`}>↓</div>
              <div className={`text-2xl ${getConnectionOpacity('electricity-pricing-service', 'enrichment-pipeline')}`}>↓</div>
              <div className={`text-2xl ${getConnectionOpacity('air-quality-service', 'enrichment-pipeline')}`}>↓</div>
              <div className={`text-2xl ${getConnectionOpacity('calendar-service', 'enrichment-pipeline')}`}>↓</div>
              <div className={`text-2xl ${getConnectionOpacity('smart-meter-service', 'enrichment-pipeline')}`}>↙</div>
            </div>
          </div>

          {/* Main Data Flow Arrow */}
          <div className="flex justify-center mb-4">
            <div className={`text-4xl ${getConnectionOpacity('websocket-ingestion', 'enrichment-pipeline')}`}>↓</div>
          </div>

          {/* Enrichment Pipeline - Centered */}
          <div className="flex justify-center mb-8">
            <div
              onClick={() => handleNodeClick('enrichment-pipeline')}
              onMouseEnter={() => setHoveredNode('enrichment-pipeline')}
              onMouseLeave={() => setHoveredNode(null)}
              className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                getStatusColor('enrichment-pipeline')
              } ${isNodeHighlighted('enrichment-pipeline') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
            >
              <div className="flex flex-col items-center">
                <div className="text-3xl mb-2">🔄</div>
                <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Enrichment<br/>Pipeline
                </div>
              </div>
              {hoveredNode === 'enrichment-pipeline' && (
                <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                  darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                }`}>
                  <div className="text-xs">Combines all data sources</div>
                </div>
              )}
            </div>
          </div>

          {/* Arrow Down */}
          <div className="flex justify-center mb-4">
            <div className={`text-4xl ${getConnectionOpacity('enrichment-pipeline', 'influxdb')}`}>↓</div>
          </div>

          {/* Storage and Services Row - Spread horizontally */}
          <div className="mb-8">
            <div className={`text-sm font-semibold mb-6 text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Storage & Services
            </div>
            <div className="flex flex-wrap justify-center gap-8">
              {/* InfluxDB */}
              <div
                onClick={() => handleNodeClick('influxdb')}
                onMouseEnter={() => setHoveredNode('influxdb')}
                onMouseLeave={() => setHoveredNode(null)}
                className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                  getStatusColor('influxdb')
                } ${isNodeHighlighted('influxdb') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
              >
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🗄️</div>
                  <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    InfluxDB
                  </div>
                </div>
                {hoveredNode === 'influxdb' && (
                  <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                    darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                  }`}>
                    <div className="text-xs">Time-series storage</div>
                  </div>
                )}
              </div>

              {/* Data Retention */}
              <div
                onClick={() => handleNodeClick('data-retention')}
                onMouseEnter={() => setHoveredNode('data-retention')}
                onMouseLeave={() => setHoveredNode(null)}
                className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                  getStatusColor('data-retention')
                } ${isNodeHighlighted('data-retention') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
              >
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">💾</div>
                  <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Data<br/>Retention
                  </div>
                </div>
                {hoveredNode === 'data-retention' && (
                  <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                    darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                  }`}>
                    <div className="text-xs">Data lifecycle management</div>
                  </div>
                )}
              </div>

              {/* Admin API */}
              <div
                onClick={() => handleNodeClick('admin-api')}
                onMouseEnter={() => setHoveredNode('admin-api')}
                onMouseLeave={() => setHoveredNode(null)}
                className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                  getStatusColor('admin-api')
                } ${isNodeHighlighted('admin-api') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
              >
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🔌</div>
                  <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Admin<br/>API
                  </div>
                </div>
                {hoveredNode === 'admin-api' && (
                  <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                    darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                  }`}>
                    <div className="text-xs">REST API gateway</div>
                  </div>
                )}
              </div>

              {/* Health Dashboard */}
              <div
                onClick={() => handleNodeClick('health-dashboard')}
                onMouseEnter={() => setHoveredNode('health-dashboard')}
                onMouseLeave={() => setHoveredNode(null)}
                className={`relative px-6 py-4 rounded-lg border-2 cursor-pointer transition-all ${
                  getStatusColor('health-dashboard')
                } ${isNodeHighlighted('health-dashboard') ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}`}
              >
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">📊</div>
                  <div className={`text-sm font-medium text-center ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Health<br/>Dashboard
                  </div>
                </div>
                {hoveredNode === 'health-dashboard' && (
                  <div className={`absolute top-full mt-2 left-1/2 transform -translate-x-1/2 z-10 px-3 py-2 rounded shadow-lg whitespace-nowrap ${
                    darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
                  }`}>
                    <div className="text-xs">Web UI (you are here!)</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Selected Service Info */}
        {selectedNode && (
          <div className={`mt-8 p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <div className="flex items-center justify-between">
              <div>
                <h4 className={`font-semibold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Selected: {SERVICE_NODES.find(n => n.id === selectedNode)?.name}
                </h4>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Dependencies highlighted in blue
                </p>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className={`px-4 py-2 rounded-md transition-colors ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-100 hover:bg-blue-200 text-blue-700'
                }`}
              >
                Clear Selection
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

