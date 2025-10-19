/**
 * Animated Dependency Graph with Real-Time Data Flow
 * 
 * Enhanced Dependencies tab showing animated data flow in real-time.
 * Uses SVG animations and CSS for smooth, performant visualizations.
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
    } else if (serviceName.includes('websocket') || serviceName.includes('enrichment')) {
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
  const nodes: ServiceNode[] = [
    // Layer 1: External Sources (Spread horizontally across top)
    { id: 'external-apis', name: 'External APIs', icon: '🌐', type: 'external', position: { x: 80, y: 60 }, layer: 1, description: 'Air quality, carbon, pricing' },
    { id: 'espn-api', name: 'ESPN API', icon: '🏈🏒', type: 'external', position: { x: 200, y: 60 }, layer: 1, description: 'NFL/NHL game data' },
    { id: 'home-assistant', name: 'Home Assistant', icon: '🏠', type: 'source', position: { x: 320, y: 60 }, layer: 1, description: 'External event source' },
    { id: 'openweather', name: 'OpenWeather', icon: '☁️', type: 'external', position: { x: 440, y: 60 }, layer: 1, description: 'Weather enrichment' },
    
    // Layer 2: Ingestion (Spread horizontally, second row)
    { id: 'external-services', name: 'External Services', icon: '🔌', type: 'processor', position: { x: 80, y: 180 }, layer: 2, description: 'Periodic external data fetch' },
    { id: 'sports-data', name: 'Sports Data', icon: '⚡', type: 'processor', position: { x: 200, y: 180 }, layer: 2, description: 'ESPN cache + persistence' },
    { id: 'websocket-ingestion', name: 'WebSocket Ingestion', icon: '📡', type: 'processor', position: { x: 320, y: 180 }, layer: 2, description: 'Event capture + inline weather' },
    
    // Layer 3: Processing (Center, better horizontal spacing)
    { id: 'enrichment-pipeline', name: 'Enrichment Pipeline', icon: '🔄', type: 'processor', position: { x: 500, y: 180 }, layer: 3, description: 'Data normalization' },
    { id: 'ai-automation-service', name: 'AI Automation', icon: '🤖', type: 'processor', position: { x: 650, y: 180 }, layer: 3, description: 'Pattern detection + suggestions' },
    
    // Layer 4: AI Models (Right side, better vertical spacing for arcs)
    { id: 'openai-gpt4', name: 'OpenAI GPT-4o-mini', icon: '🧠', type: 'external', position: { x: 650, y: 300 }, layer: 4, description: 'Natural language generation' },
    { id: 'openvino-models', name: 'OpenVINO Models', icon: '⚡', type: 'processor', position: { x: 650, y: 420 }, layer: 4, description: 'Local ML: embeddings, reranking, classification' },
    
    // Layer 5: Storage (Spread horizontally across bottom)
    { id: 'influxdb', name: 'InfluxDB', icon: '🗄️', type: 'storage', position: { x: 200, y: 380 }, layer: 5, description: 'Time-series events' },
    { id: 'sqlite', name: 'SQLite', icon: '💾', type: 'storage', position: { x: 400, y: 380 }, layer: 5, description: 'Metadata & AI suggestions' },
    
    // Layer 6: API Gateway (Spread horizontally, second from bottom)
    { id: 'data-api', name: 'Data API', icon: '🔌', type: 'processor', position: { x: 200, y: 480 }, layer: 6, description: 'Feature data hub' },
    { id: 'admin-api', name: 'Admin API', icon: '⚙️', type: 'processor', position: { x: 400, y: 480 }, layer: 6, description: 'System monitoring' },
    
    // Layer 7: Main UI (Bottom center)
    { id: 'health-dashboard', name: 'Dashboard', icon: '📊', type: 'ui', position: { x: 300, y: 580 }, layer: 7, description: 'You are here!' },
  ];

  // Define data flow paths with AI automation integration
  const dataFlows: DataFlowPath[] = [
    // ===== LEFT SIDE: PRIMARY DATA FLOWS (Non-AI) =====
    // Primary HA Event Flow (Always Active)
    { id: 'ha-ws', from: 'home-assistant', to: 'websocket-ingestion', type: 'websocket', active: true, throughput: realTimeData?.eventsPerHour || 0, color: '#3B82F6' },
    { id: 'ws-direct-influx', from: 'websocket-ingestion', to: 'influxdb', type: 'storage', active: true, color: '#10B981' },
    
    // Enhancement Path (Optional)
    { id: 'ws-enrich', from: 'websocket-ingestion', to: 'enrichment-pipeline', type: 'api', active: true, color: '#F59E0B' },
    { id: 'enrich-db', from: 'enrichment-pipeline', to: 'influxdb', type: 'storage', active: true, color: '#F59E0B' },
    
    // Inline Weather Enrichment
    { id: 'weather-inline', from: 'openweather', to: 'websocket-ingestion', type: 'api', active: true, color: '#06B6D4' },
    
    // Sports Data Flow (Hybrid Pattern)
    { id: 'espn-sports', from: 'espn-api', to: 'sports-data', type: 'api', active: realTimeData?.dataSourcesActive?.includes('sports') || false, throughput: 0.5, color: '#8B5CF6' },
    { id: 'sports-influx', from: 'sports-data', to: 'influxdb', type: 'storage', active: true, color: '#8B5CF6' },
    { id: 'sports-sqlite', from: 'sports-data', to: 'sqlite', type: 'storage', active: true, color: '#8B5CF6' },
    
    // External API Services (Non-AI Data Sources)
    { id: 'external-fetch', from: 'external-apis', to: 'external-services', type: 'api', active: true, color: '#6B7280' },
    { id: 'external-influx', from: 'external-services', to: 'influxdb', type: 'storage', active: true, color: '#6B7280' },
    
    // ===== RIGHT SIDE: AI PATTERN ANALYSIS FLOWS =====
    // AI Pattern Analysis Flow
    { id: 'ws-ai-analysis', from: 'websocket-ingestion', to: 'ai-automation-service', type: 'api', active: true, color: '#8B5CF6' },
    { id: 'ai-openvino', from: 'ai-automation-service', to: 'openvino-models', type: 'api', active: true, color: '#8B5CF6' },
    { id: 'openvino-ai', from: 'openvino-models', to: 'ai-automation-service', type: 'api', active: true, color: '#8B5CF6' },
    { id: 'ai-openai', from: 'ai-automation-service', to: 'openai-gpt4', type: 'api', active: true, color: '#FF6B6B' },
    { id: 'openai-ai', from: 'openai-gpt4', to: 'ai-automation-service', type: 'api', active: true, color: '#FF6B6B' },
    { id: 'ai-sqlite', from: 'ai-automation-service', to: 'sqlite', type: 'storage', active: true, color: '#8B5CF6' },
    
    // Hybrid Database Queries
    { id: 'influx-data', from: 'influxdb', to: 'data-api', type: 'query', active: true, color: '#3B82F6' },
    { id: 'sqlite-data', from: 'sqlite', to: 'data-api', type: 'query', active: true, color: '#10B981' },
    
    // API Gateway Layer
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
        ((fromId === 'openai-gpt4' || fromId === 'openvino-models') && toId === 'ai-automation-service')) {
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
        
        {/* Animated path overlay */}
        {flow.active && (
          <>
            <path
              d={path}
              fill="none"
              stroke={flow.color}
              strokeWidth="3"
              strokeLinecap="round"
              opacity="0.6"
              filter={`url(#glow-${flow.type})`}
            >
              <animate
                attributeName="stroke-dasharray"
                values="10,5;20,15"
                dur="1s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="stroke-dashoffset"
                from="0"
                to="30"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </path>
            
            {/* Data particles */}
            <circle r="4" fill={flow.color} filter={`url(#glow-${flow.type})`}>
              <animateMotion
                dur={`${2 + Math.random() * 2}s`}
                repeatCount="indefinite"
                path={path}
              />
              <animate
                attributeName="r"
                values="3;5;3"
                dur="1s"
                repeatCount="indefinite"
              />
            </circle>
            
            {/* Additional particles for high throughput */}
            {flow.throughput && flow.throughput > 10 && (
              <circle r="3" fill={flow.color} opacity="0.7">
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
        {/* Node glow effect */}
        <circle
          r="35"
          fill={nodeColor}
          opacity="0.2"
          filter="url(#node-glow)"
        >
          <animate
            attributeName="r"
            values="35;40;35"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* Node background */}
        <circle
          r="30"
          fill={darkMode ? '#1F2937' : '#FFFFFF'}
          stroke={nodeColor}
          strokeWidth="3"
          filter={isSelected ? 'url(#selected-glow)' : undefined}
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

        {/* Clean Slim Legend */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
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
            <span className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Weather (Inline)</span>
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

      {/* Clean SVG Diagram Container */}
      <div className={`p-8 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg overflow-x-auto`}>
        <svg
          ref={svgRef}
          width="1000"
          height="650"
          viewBox="0 0 1000 650"
          className="w-full"
          style={{ minWidth: '1000px' }}
        >
          {/* Definitions for filters and effects */}
          <defs>
            {/* Glow filters for different flow types */}
            <filter id="glow-websocket">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-api">
              <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-storage">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="glow-query">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            {/* Node glow */}
            <filter id="node-glow">
              <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            {/* Selected node glow */}
            <filter id="selected-glow">
              <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
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

