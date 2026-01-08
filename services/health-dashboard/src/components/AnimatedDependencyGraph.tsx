/**
 * Animated Dependency Graph with Real-Time Data Flow
 * 
 * Enhanced Dependencies tab showing animated data flow in real-time.
 * Uses SVG animations and CSS for smooth, performant visualizations.
 * 
 * Architecture: Epic 31 (October 2025) - Current as of November 2025
 * - enrichment-pipeline DEPRECATED - all normalization now inline in websocket-ingestion
 * - Weather enrichment REMOVED from websocket-ingestion - now standalone weather-api service (port 8009)
 * - Direct write path: websocket-ingestion → InfluxDB (no intermediate services)
 * - External services (weather-api, sports-api, etc.) write directly to InfluxDB
 * - AI Automation reads from InfluxDB (via data-api or direct query)
 * 
 * Research from Context7 KB:
 * - React Flow (/websites/reactflow_dev) - Animated edges and nodes
 * - Framer Motion (/grx7/framer-motion) - Smooth animations
 */

import React, { useState, useRef } from 'react';
import type { ServiceStatus } from '../types';

interface AnimatedDependencyGraphProps {
  services: ServiceStatus[];
  darkMode: boolean;
  realTimeData?: RealTimeMetrics;
  loading?: boolean;
  error?: string | null;
}

interface RealTimeMetrics {
  eventsPerHour: number;
  apiCallsActive: number;
  dataSourcesActive: string[];
  apiMetrics: ApiMetric[];
  inactiveApis: number;
  errorApis: number;
  totalApis: number;
  healthSummary: {
    healthy: number;
    unhealthy: number;
    total: number;
    health_percentage: number;
  };
  lastUpdate: Date;
}

interface ApiMetric {
  service: string;
  events_per_hour: number;
  uptime_seconds: number;
  status: 'active' | 'inactive' | 'error' | 'timeout' | 'not_configured';
  response_time_ms?: number;
  last_success?: string;
  error_message?: string;
  is_fallback?: boolean;
}

interface DataFlowPath {
  id: string;
  from: string;
  to: string;
  type: 'websocket' | 'api' | 'storage' | 'query';
  active: boolean;
  throughput?: number; // events/sec or calls/sec
  color: string;
}

interface ServiceNode {
  id: string;
  name: string;
  icon: string;
  type: 'source' | 'processor' | 'storage' | 'ui' | 'external';
  position: { x: number; y: number };
  layer: number;
  status?: 'running' | 'error' | 'degraded' | 'unknown';
  metrics?: {
    throughput?: number;
    latency?: number;
    errorRate?: number;
  };
  description?: string;
}

export const AnimatedDependencyGraph: React.FC<AnimatedDependencyGraphProps> = ({
  services,
  darkMode,
  realTimeData,
  loading = false,
  error = null,
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Helper function to format uptime
  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  // Helper function to get service category color
  const getServiceIcon = (serviceName: string): string => {
    if (serviceName.includes('admin') || serviceName.includes('data-api')) {
      return 'bg-blue-500'; // Core services
    } else if (serviceName.includes('websocket')) {
      return 'bg-green-500'; // Ingestion services
    } else if (serviceName.includes('weather') || serviceName.includes('sports') || serviceName.includes('air-quality')) {
      return 'bg-purple-500'; // External APIs
    } else if (serviceName.includes('carbon') || serviceName.includes('electricity') || serviceName.includes('energy')) {
      return 'bg-orange-500'; // Energy services
    } else if (serviceName.includes('calendar') || serviceName.includes('smart-meter')) {
      return 'bg-indigo-500'; // Integration services
    } else if (serviceName.includes('retention') || serviceName.includes('log-aggregator')) {
      return 'bg-gray-500'; // Storage/utility services
    } else {
      return 'bg-gray-400'; // Default
    }
  };

  // Define service nodes with optimized spacing to prevent line crossings
  // Epic 31 Architecture: Direct writes, no enrichment-pipeline
  const nodes: ServiceNode[] = [
    // Layer 1: External Sources (Spread horizontally across top)
    { id: 'external-apis', name: 'External APIs', icon: '🌐', type: 'external', position: { x: 60, y: 50 }, layer: 1, description: 'Air quality, carbon, pricing, electricity' },
    { id: 'espn-api', name: 'ESPN API', icon: '🏈🏒', type: 'external', position: { x: 180, y: 50 }, layer: 1, description: 'NFL/NHL game data' },
    { id: 'home-assistant', name: 'Home Assistant', icon: '🏠', type: 'source', position: { x: 300, y: 50 }, layer: 1, description: 'External event source (192.168.1.86:8123)' },
    { id: 'openweather', name: 'OpenWeather', icon: '☁️', type: 'external', position: { x: 420, y: 50 }, layer: 1, description: 'OpenWeatherMap API (external)' },
    
    // Layer 2: Ingestion Services (Spread horizontally, second row)
    { id: 'external-services', name: 'External Services', icon: '🔌', type: 'processor', position: { x: 60, y: 160 }, layer: 2, description: 'Periodic external data fetch & write' },
    { id: 'sports-api', name: 'Sports API', icon: '⚽', type: 'processor', position: { x: 180, y: 160 }, layer: 2, description: 'Team Tracker integration (port 8005)' },
    { id: 'websocket-ingestion', name: 'WebSocket Ingestion', icon: '📡', type: 'processor', position: { x: 300, y: 160 }, layer: 2, description: 'Event capture + inline normalization (Epic 31 - weather enrichment removed)' },
    { id: 'weather-api', name: 'Weather API', icon: '☁️', type: 'processor', position: { x: 420, y: 160 }, layer: 2, description: 'Standalone weather service (port 8009) - Epic 31' },
    
    // Layer 3: AI Processing (Right side)
    { id: 'ai-automation-service', name: 'AI Automation', icon: '🤖', type: 'processor', position: { x: 540, y: 160 }, layer: 3, description: 'Pattern detection + automation suggestions' },
    
    // Layer 4: AI Models (Right side, vertical stack)
    { id: 'openai-gpt4', name: 'OpenAI GPT-4o-mini', icon: '🧠', type: 'external', position: { x: 540, y: 280 }, layer: 4, description: 'Natural language generation' },
    { id: 'openvino-models', name: 'OpenVINO Models', icon: '⚡', type: 'processor', position: { x: 540, y: 400 }, layer: 4, description: 'Local ML: embeddings, reranking, classification' },
    
    // Layer 5: Storage (Spread horizontally, center-bottom)
    { id: 'influxdb', name: 'InfluxDB', icon: '🗄️', type: 'storage', position: { x: 180, y: 360 }, layer: 5, description: 'Time-series events (port 8086)' },
    { id: 'sqlite', name: 'SQLite', icon: '💾', type: 'storage', position: { x: 420, y: 360 }, layer: 5, description: 'Metadata & AI suggestions' },
    
    // Layer 6: Data Processing (Between storage and APIs)
    { id: 'data-retention', name: 'Data Retention', icon: '🔄', type: 'processor', position: { x: 300, y: 460 }, layer: 6, description: 'Data lifecycle management (port 8080)' },
    
    // Layer 7: API Gateway (Spread horizontally, second from bottom)
    { id: 'data-api', name: 'Data API', icon: '🔌', type: 'processor', position: { x: 180, y: 560 }, layer: 7, description: 'Feature data hub (port 8006)' },
    { id: 'admin-api', name: 'Admin API', icon: '⚙️', type: 'processor', position: { x: 420, y: 560 }, layer: 7, description: 'System monitoring (port 8003)' },
    
    // Layer 8: Main UI (Bottom center)
    { id: 'health-dashboard', name: 'Dashboard', icon: '📊', type: 'ui', position: { x: 300, y: 660 }, layer: 8, description: 'You are here! (port 3000)' },
  ];

  // Define data flow paths with AI automation integration (Epic 31 Architecture)
  // Epic 31: Direct writes to InfluxDB, no enrichment-pipeline
  const dataFlows: DataFlowPath[] = [
    // ===== PRIMARY DATA FLOWS (Epic 31: Direct write path) =====
    // Home Assistant → WebSocket Ingestion → InfluxDB (DIRECT, no enrichment-pipeline)
    { id: 'ha-ws', from: 'home-assistant', to: 'websocket-ingestion', type: 'websocket', active: true, throughput: (realTimeData?.eventsPerHour || 0) / 3600, color: '#3B82F6' },
    { id: 'ws-direct-influx', from: 'websocket-ingestion', to: 'influxdb', type: 'storage', active: true, color: '#10B981' },
    
    // External Services: Direct writes to InfluxDB (Epic 31 pattern - standalone services)
    // Weather API: Standalone service (Epic 31) - writes to weather_data bucket (NOT inline enrichment)
    { id: 'weather-api-fetch', from: 'openweather', to: 'weather-api', type: 'api', active: true, color: '#06B6D4' },
    { id: 'weather-api-influx', from: 'weather-api', to: 'influxdb', type: 'storage', active: true, color: '#06B6D4' },
    { id: 'external-fetch', from: 'external-apis', to: 'external-services', type: 'api', active: true, color: '#6B7280' },
    { id: 'external-influx', from: 'external-services', to: 'influxdb', type: 'storage', active: true, color: '#6B7280' },
    
    // Sports API Flow (Epic 31: Direct InfluxDB writes via Team Tracker)
    { id: 'ha-sports', from: 'home-assistant', to: 'sports-api', type: 'api', active: realTimeData?.dataSourcesActive?.includes('sports') || false, throughput: 0.5, color: '#8B5CF6' },
    { id: 'sports-influx', from: 'sports-api', to: 'influxdb', type: 'storage', active: true, color: '#8B5CF6' },
    
    // ===== AI PATTERN ANALYSIS FLOWS =====
    // AI Automation reads from InfluxDB (Epic 31: Direct query or via data-api)
    { id: 'influx-ai', from: 'influxdb', to: 'ai-automation-service', type: 'query', active: true, color: '#8B5CF6' },
    { id: 'data-api-ai', from: 'data-api', to: 'ai-automation-service', type: 'api', active: true, color: '#8B5CF6' },
    
    // AI Model Interactions
    { id: 'ai-openvino', from: 'ai-automation-service', to: 'openvino-models', type: 'api', active: true, color: '#8B5CF6' },
    { id: 'openvino-ai', from: 'openvino-models', to: 'ai-automation-service', type: 'api', active: true, color: '#8B5CF6' },
    { id: 'ai-openai', from: 'ai-automation-service', to: 'openai-gpt4', type: 'api', active: true, color: '#FF6B6B' },
    { id: 'openai-ai', from: 'openai-gpt4', to: 'ai-automation-service', type: 'api', active: true, color: '#FF6B6B' },
    { id: 'ai-sqlite', from: 'ai-automation-service', to: 'sqlite', type: 'storage', active: true, color: '#8B5CF6' },
    
    // ===== DATA PROCESSING & RETENTION =====
    { id: 'influx-retention', from: 'influxdb', to: 'data-retention', type: 'api', active: true, color: '#6366F1' },
    { id: 'retention-influx', from: 'data-retention', to: 'influxdb', type: 'api', active: true, color: '#6366F1' },
    
    // ===== HYBRID DATABASE QUERIES =====
    { id: 'influx-data', from: 'influxdb', to: 'data-api', type: 'query', active: true, color: '#3B82F6' },
    { id: 'sqlite-data', from: 'sqlite', to: 'data-api', type: 'query', active: true, color: '#10B981' },
    { id: 'influx-admin', from: 'influxdb', to: 'admin-api', type: 'query', active: true, color: '#F59E0B' },
    
    // ===== API GATEWAY TO DASHBOARD =====
    { id: 'data-dash', from: 'data-api', to: 'health-dashboard', type: 'api', active: true, color: '#3B82F6' },
    { id: 'admin-dash', from: 'admin-api', to: 'health-dashboard', type: 'api', active: true, color: '#F59E0B' },
  ];

  // Note: Pulse and active flows managed through CSS animations and real-time data

  const getServiceStatus = (nodeId: string): ServiceStatus | undefined => {
    return services.find(s => 
      s.service === nodeId || 
      s.service.toLowerCase().includes(nodeId.toLowerCase()) ||
      nodeId.toLowerCase().includes(s.service.toLowerCase())
    );
  };

  const getNodeColor = (node: ServiceNode): string => {
    const service = getServiceStatus(node.id);
    
    if (!service) {
      return darkMode ? '#374151' : '#E5E7EB'; // gray
    }
    
    switch (service.status) {
      case 'running':
        return darkMode ? '#10B981' : '#34D399'; // green
      case 'error':
        return darkMode ? '#EF4444' : '#F87171'; // red
      case 'degraded':
        return darkMode ? '#F59E0B' : '#FBBF24'; // yellow
      default:
        return darkMode ? '#374151' : '#E5E7EB'; // gray
    }
  };


  // Calculate path between two nodes using D3.js arc-based routing
  const calculatePath = (fromId: string, toId: string): string => {
    const from = nodes.find(n => n.id === fromId);
    const to = nodes.find(n => n.id === toId);
    
    if (!from || !to) return '';
    
    const startX = from.position.x;
    const startY = from.position.y + 30; // Offset from node center
    const endX = to.position.x;
    const endY = to.position.y - 30; // Offset from node center
    
    // Calculate distance and direction
    const dx = endX - startX;
    const dy = endY - startY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // For very short distances, use straight line
    if (distance < 50) {
      return `M ${startX} ${startY} L ${endX} ${endY}`;
    }
    
    // For vertical connections (same x-coordinate), use straight line
    if (Math.abs(dx) < 10) {
      return `M ${startX} ${startY} L ${endX} ${endY}`;
    }
    
    // For horizontal connections (same y-coordinate), use straight line
    if (Math.abs(dy) < 10) {
      return `M ${startX} ${startY} L ${endX} ${endY}`;
    }
    
    // For AI automation bidirectional flows, use arc routing
    if ((fromId === 'ai-automation-service' && (toId === 'openai-gpt4' || toId === 'openvino-models')) ||
        ((fromId === 'openai-gpt4' || fromId === 'openvino-models') && toId === 'ai-automation-service') ||
        (fromId === 'influxdb' && toId === 'ai-automation-service') ||
        (fromId === 'data-api' && toId === 'ai-automation-service')) {
      const midX = (startX + endX) / 2;
      const arcHeight = Math.abs(dy) * 0.6; // Increased arc height for better visibility
      const arcY = dy > 0 ? startY + arcHeight : startY - arcHeight;
      
      return `M ${startX} ${startY} 
              Q ${midX} ${arcY}, 
                 ${endX} ${endY}`;
    }
    
    // For external services parallel flows, use offset routing to prevent crossings
    if ((fromId === 'external-apis' || fromId === 'espn-api') && toId === 'external-services') {
      const offset = fromId === 'external-apis' ? -30 : 30;
      const midY = (startY + endY) / 2;
      
      return `M ${startX} ${startY} 
              L ${startX + offset} ${startY}
              L ${startX + offset} ${midY}
              L ${endX + offset} ${midY}
              L ${endX + offset} ${endY}
              L ${endX} ${endY}`;
    }
    
    // For long diagonal connections, use smooth curve
    const midX = (startX + endX) / 2;
    const midY = (startY + endY) / 2;
    
    // Add slight curve to avoid straight lines
    const curveOffset = Math.min(distance * 0.1, 30);
    const curveX = dx > 0 ? midX - curveOffset : midX + curveOffset;
    
    return `M ${startX} ${startY} 
            C ${curveX} ${startY}, 
               ${curveX} ${endY}, 
               ${endX} ${endY}`;
  };

  const renderDataFlow = (flow: DataFlowPath) => {
    const path = calculatePath(flow.from, flow.to);
    const isHighlighted = selectedNode === flow.from || selectedNode === flow.to;
    const opacity = !selectedNode || isHighlighted ? 1 : 0.2;

    return (
      <g key={flow.id} opacity={opacity}>
        {/* Base path */}
        <path
          d={path}
          fill="none"
          stroke={darkMode ? '#374151' : '#E5E7EB'}
          strokeWidth="2"
          strokeDasharray={flow.active ? undefined : '5,5'}
        />
        
        {/* Enhanced animated path overlay with stronger glow */}
        {flow.active && (
          <>
            {/* Base glow path */}
            <path
              d={path}
              fill="none"
              stroke={flow.color}
              strokeWidth="4"
              strokeLinecap="round"
              opacity="0.4"
              filter={`url(#glow-${flow.type})`}
            />
                
            {/* Animated main path */}
            <path
              d={path}
              fill="none"
              stroke={flow.color}
              strokeWidth="3"
              strokeLinecap="round"
              opacity="0.8"
              filter={`url(#glow-${flow.type})`}
            >
              <animate
                attributeName="stroke-dasharray"
                values="8,4;16,12"
                dur="1.2s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="stroke-dashoffset"
                from="0"
                to="24"
                dur="1.8s"
                repeatCount="indefinite"
              />
            </path>
                
            {/* Primary data particle with enhanced glow */}
            <circle r="5" fill={flow.color} filter={`url(#glow-${flow.type})`} opacity="0.9">
              <animateMotion
                dur={`${1.5 + Math.random() * 1.5}s`}
                repeatCount="indefinite"
                path={path}
              />
              <animate
                attributeName="r"
                values="4;6;4"
                dur="1.2s"
                repeatCount="indefinite"
              />
            </circle>
                
            {/* Secondary particles for high throughput */}
            {flow.throughput && flow.throughput > 0.1 && (
              <>
                <circle r="3" fill={flow.color} opacity="0.6">
                  <animateMotion
                    dur="2.5s"
                    repeatCount="indefinite"
                    path={path}
                    begin="0.5s"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.6;0.9;0.6"
                    dur="1.5s"
                    repeatCount="indefinite"
                  />
                </circle>
                {flow.throughput > 0.5 && (
                  <circle r="2.5" fill={flow.color} opacity="0.5">
                    <animateMotion
                      dur="3s"
                      repeatCount="indefinite"
                      path={path}
                      begin="1s"
                    />
                  </circle>
                )}
              </>
            )}
          </>
        )}
        
        {/* Throughput label */}
        {flow.throughput && flow.throughput > 0 && isHighlighted && (
          <text
            x={(nodes.find(n => n.id === flow.from)!.position.x + nodes.find(n => n.id === flow.to)!.position.x) / 2}
            y={(nodes.find(n => n.id === flow.from)!.position.y + nodes.find(n => n.id === flow.to)!.position.y) / 2}
            fill={darkMode ? '#fff' : '#000'}
            fontSize="12"
            textAnchor="middle"
            style={{ 
              pointerEvents: 'none',
              fontWeight: 600,
              textShadow: darkMode ? '0 0 4px rgba(0,0,0,0.8)' : '0 0 4px rgba(255,255,255,0.8)'
            }}
          >
            {(flow.throughput || 0).toFixed(1)}/s
          </text>
        )}
      </g>
    );
  };

  const renderNode = (node: ServiceNode) => {
    const isSelected = selectedNode === node.id;
    const isHovered = hoveredNode === node.id;
    const isHighlighted = !selectedNode || isSelected || 
      dataFlows.some(f => (f.from === selectedNode && f.to === node.id) || (f.to === selectedNode && f.from === node.id));
    
    const nodeColor = getNodeColor(node);
    const scale = isSelected ? 1.15 : isHovered ? 1.08 : 1;
    const opacity = !selectedNode || isHighlighted ? 1 : 0.3;

    return (
      <g
        key={node.id}
        transform={`translate(${node.position.x}, ${node.position.y}) scale(${scale})`}
        opacity={opacity}
        style={{ 
          cursor: 'pointer',
          transition: 'all 0.3s ease',
        }}
        onClick={() => setSelectedNode(isSelected ? null : node.id)}
        onMouseEnter={() => setHoveredNode(node.id)}
        onMouseLeave={() => setHoveredNode(null)}
      >
        {/* Enhanced node glow effect with pulsing */}
        <circle
          r="38"
          fill={nodeColor}
          opacity="0.15"
          filter="url(#node-glow)"
        >
          <animate
            attributeName="r"
            values="38;45;38"
            dur="2.5s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.15;0.25;0.15"
            dur="2.5s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* Node background with gradient */}
        <circle
          r="32"
          fill={darkMode ? '#1F2937' : '#FFFFFF'}
          stroke={nodeColor}
          strokeWidth={isSelected ? '4' : '3'}
          filter={isSelected ? 'url(#selected-glow)' : undefined}
          style={{
            boxShadow: isSelected ? `0 0 20px ${nodeColor}` : undefined,
          }}
        />
        
        {/* Inner glow ring */}
        <circle
          r="28"
          fill="none"
          stroke={nodeColor}
          strokeWidth="1"
          opacity="0.3"
        />
        
        {/* Node icon */}
        <text
          textAnchor="middle"
          dy=".3em"
          fontSize="24"
          style={{ pointerEvents: 'none' }}
        >
          {node.icon}
        </text>
        
        {/* Node label */}
        <text
          y="45"
          textAnchor="middle"
          fill={darkMode ? '#E5E7EB' : '#1F2937'}
          fontSize="12"
          fontWeight="600"
          style={{ pointerEvents: 'none' }}
        >
          {node.name}
        </text>
        
        {/* Status indicator */}
        {getServiceStatus(node.id) && (
          <circle
            cx="20"
            cy="-20"
            r="6"
            fill={nodeColor}
            stroke={darkMode ? '#1F2937' : '#FFFFFF'}
            strokeWidth="2"
          >
            <animate
              attributeName="r"
              values="6;8;6"
              dur="1.5s"
              repeatCount="indefinite"
            />
          </circle>
        )}
      </g>
    );
  };

  return (
    <div className="space-y-6">
      {/* Clean Slim Header */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} flex items-center gap-2`}>
              <span className="text-base">🏗️</span>
              Architecture Overview
            </h2>
            <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Real-time data flow from Home Assistant through processing to storage
            </p>
          </div>
          
          {/* Clean Live Metrics */}
          {realTimeData && (
            <div className={`px-4 py-3 rounded-lg border ${darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <div className={`text-lg font-semibold tracking-tight ${darkMode ? 'text-green-300' : 'text-green-600'}`}>
                    {(realTimeData.eventsPerHour || 0).toFixed(0)}
                  </div>
                  <div className={`text-xs font-medium tracking-wide uppercase ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    events/hour
                  </div>
                </div>
                <div className="text-center">
                  <div className={`text-lg font-semibold tracking-tight ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}>
                    {realTimeData.apiCallsActive}
                  </div>
                  <div className={`text-xs font-medium tracking-wide uppercase ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    active
                  </div>
                </div>
                <div className="text-center">
                  <div className={`text-lg font-semibold tracking-tight ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
                    {realTimeData.inactiveApis + realTimeData.errorApis}
                  </div>
                  <div className={`text-xs font-medium tracking-wide uppercase ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    issues
                  </div>
                </div>
                <div className="text-center">
                  <div className={`text-lg font-semibold tracking-tight ${darkMode ? 'text-purple-300' : 'text-purple-600'}`}>
                    {realTimeData.healthSummary.health_percentage}%
                  </div>
                  <div className={`text-xs font-medium tracking-wide uppercase ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    health
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Two Column Layout: Architecture Flow + Metrics Table */}
      <div className="flex gap-6">
        {/* Left Column: Compact Architecture Flow */}
        <div className={`w-1/3 p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h4 className={`text-sm font-medium mb-3 tracking-wide ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
            Data Flow
          </h4>
          
          {/* Compact Architecture Diagram */}
          <div className={`p-3 rounded-lg border ${darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
            <div className="space-y-3">
              {/* External Sources */}
              <div className="text-center">
                <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${darkMode ? 'bg-blue-900/30 text-blue-300 border border-blue-700/50' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mr-1.5"></span>
                  External APIs
                </div>
              </div>
              
              {/* Arrow */}
              <div className="flex justify-center">
                <div className={`w-0.5 h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}></div>
              </div>
              
              {/* Ingestion Layer (Epic 31: Direct write, no enrichment-pipeline, weather is standalone service) */}
              <div className="flex justify-center">
                <div className={`px-2 py-1 rounded text-xs font-medium ${darkMode ? 'bg-green-900/30 text-green-300 border border-green-700/50' : 'bg-green-50 text-green-700 border border-green-200'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 mr-1.5"></span>
                  WS Ingestion
                </div>
              </div>
              
              {/* Arrow */}
              <div className="flex justify-center">
                <div className={`w-0.5 h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}></div>
              </div>
              
              {/* Storage Layer */}
              <div className="flex justify-center space-x-2">
                <div className={`px-2 py-1 rounded text-xs font-medium ${darkMode ? 'bg-purple-900/30 text-purple-300 border border-purple-700/50' : 'bg-purple-50 text-purple-700 border border-purple-200'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mr-1.5"></span>
                  Influx
                </div>
                <div className={`px-2 py-1 rounded text-xs font-medium ${darkMode ? 'bg-purple-900/30 text-purple-300 border border-purple-700/50' : 'bg-purple-50 text-purple-700 border border-purple-200'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mr-1.5"></span>
                  SQLite
                </div>
              </div>
              
              {/* Arrow */}
              <div className="flex justify-center">
                <div className={`w-0.5 h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}></div>
              </div>
              
              {/* Output Layer */}
              <div className="text-center">
                <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${darkMode ? 'bg-gray-900/30 text-gray-300 border border-gray-700/50' : 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 mr-1.5"></span>
                  Dashboard
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Per-API Metrics Table */}
        <div className={`flex-1 p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h4 className={`text-sm font-medium mb-3 tracking-wide ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
            Per-API Metrics
          </h4>
          <div className="overflow-x-auto">
            <table className={`w-full text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              <thead>
                <tr className={`border-b ${darkMode ? 'border-gray-600 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}>
                  <th className="text-left py-2 px-1 font-medium text-xs tracking-wide">Service</th>
                  <th className="text-right py-2 px-1 font-medium text-xs tracking-wide">Events/hour</th>
                  <th className="text-right py-2 px-1 font-medium text-xs tracking-wide">Uptime</th>
                  <th className="text-center py-2 px-1 font-medium text-xs tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {realTimeData && realTimeData.apiMetrics && realTimeData.apiMetrics.map((metric, index) => (
                  <tr key={index} className={`border-b hover:${darkMode ? 'bg-gray-750' : 'bg-gray-50'} transition-colors ${darkMode ? 'border-gray-700' : 'border-gray-100'}`}>
                    <td className="py-2 px-1 font-mono text-xs">
                      <span className="inline-flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${getServiceIcon(metric.service)}`}></span>
                        {metric.service}
                      </span>
                    </td>
                    <td className="text-right py-2 px-1 text-xs font-mono">{(metric.events_per_hour || 0).toFixed(0)}</td>
                    <td className="text-right py-2 px-1 text-xs font-mono text-gray-500">{formatUptime(metric.uptime_seconds)}</td>
                    <td className="text-center py-2 px-1">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        metric.status === 'active' 
                          ? (darkMode ? 'bg-green-900/30 text-green-300 border border-green-700/50' : 'bg-green-50 text-green-700 border border-green-200')
                          : metric.status === 'inactive'
                            ? (darkMode ? 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/50' : 'bg-yellow-50 text-yellow-700 border border-yellow-200')
                            : metric.status === 'timeout'
                              ? (darkMode ? 'bg-orange-900/30 text-orange-300 border border-orange-700/50' : 'bg-orange-50 text-orange-700 border border-orange-200')
                              : metric.status === 'not_configured'
                                ? (darkMode ? 'bg-gray-900/30 text-gray-300 border border-gray-700/50' : 'bg-gray-50 text-gray-700 border border-gray-200')
                                : (darkMode ? 'bg-red-900/30 text-red-300 border border-red-700/50' : 'bg-red-50 text-red-700 border border-red-200')
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                          metric.status === 'active' ? 'bg-green-400' : 
                            metric.status === 'inactive' ? 'bg-yellow-400' :
                              metric.status === 'timeout' ? 'bg-orange-400' :
                                metric.status === 'not_configured' ? 'bg-gray-400' : 'bg-red-400'
                        }`}></span>
                        {metric.status}
                      </span>
                      {metric.error_message && (
                        <div className={`text-xs mt-1 ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
                          {metric.error_message}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Clean Slim Legend */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-blue-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>WebSocket/Query</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-green-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Primary Path</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-orange-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Enhancement Path</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-purple-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>AI Pattern Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-red-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>OpenAI GPT-4o-mini</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-cyan-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Weather API</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-gray-500"></div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>External APIs</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🗄️💾</span>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Hybrid Database</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="animate-pulse">●</div>
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Active Flow</span>
          </div>
        </div>
      </div>

      {/* Enhanced SVG Diagram Container with gradient background */}
      <div className={`p-8 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg overflow-x-auto relative`}>
        {/* Gradient background overlay */}
        <div className={`absolute inset-0 rounded-lg opacity-10 pointer-events-none ${
          darkMode 
            ? 'bg-gradient-to-br from-blue-900 via-purple-900 to-green-900' 
            : 'bg-gradient-to-br from-blue-50 via-purple-50 to-green-50'
        }`}></div>
        <svg
          ref={svgRef}
          width="1000"
          height="750"
          viewBox="0 0 1000 750"
          className="w-full relative z-10"
          style={{ minWidth: '1000px' }}
        >
          {/* Definitions for filters and effects */}
          <defs>
            {/* Enhanced glow filters for different flow types */}
            <filter id="glow-websocket" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-api" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-storage" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-query" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            {/* Enhanced node glow */}
            <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            {/* Enhanced selected node glow */}
            <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="10" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
          </defs>

          {/* Render all data flows first (so they appear behind nodes) */}
          {dataFlows.map(renderDataFlow)}

          {/* Render all nodes */}
          {nodes.map(renderNode)}
        </svg>
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} mb-2 flex items-center gap-2`}>
                <span className="text-2xl">{nodes.find(n => n.id === selectedNode)?.icon}</span>
                {nodes.find(n => n.id === selectedNode)?.name}
              </h3>
              <div className="space-y-2">
                <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'} italic`}>
                  {nodes.find(n => n.id === selectedNode)?.description}
                </p>
                <div className="grid grid-cols-3 gap-4 mt-3">
                  <div>
                    <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Type</p>
                    <p className={`text-sm font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {nodes.find(n => n.id === selectedNode)?.type}
                    </p>
                  </div>
                  <div>
                    <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Layer</p>
                    <p className={`text-sm font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {nodes.find(n => n.id === selectedNode)?.layer}
                    </p>
                  </div>
                  <div>
                    <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Connections</p>
                    <p className={`text-sm font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {dataFlows.filter(f => f.from === selectedNode || f.to === selectedNode).length} active
                    </p>
                  </div>
                </div>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mt-2`}>
                  <span className="font-semibold">Status:</span>{' '}
                  <span className={getServiceStatus(selectedNode)?.status === 'running' ? 'text-green-500' : 'text-gray-500'}>
                    {getServiceStatus(selectedNode)?.status || 'unknown'}
                  </span>
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className={`ml-4 px-4 py-2 rounded-lg transition-colors ${
                darkMode
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnimatedDependencyGraph;

