/**
 * Network Graph View Component
 * Interactive force-directed graph visualization of device relationships
 * 
 * Phase 3: Interactive Network Graph
 */

import React, { useState, useMemo, useCallback, useRef, Component, ErrorInfo, ReactNode, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SynergyOpportunity } from '../../types';

// Global AFRAME stub to prevent errors from react-force-graph
// react-force-graph checks for AFRAME globally but we only use 2D graphs
if (typeof window !== 'undefined' && !(window as any).AFRAME) {
  (window as any).AFRAME = {
    registerComponent: () => {},
    registerSystem: () => {},
    registerPrimitive: () => {},
    scenes: [],
    version: '1.0.0'
  };
}

// Error Boundary Component for graph rendering errors
class GraphErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode; fallback: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('NetworkGraphView rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

// Dynamic import with state management
let ForceGraph2DComponent: any = null;
let loadPromise: Promise<any> | null = null;

const loadForceGraph = async (): Promise<any> => {
  if (ForceGraph2DComponent) {
    return ForceGraph2DComponent;
  }
  
  // Ensure AFRAME stub is available before importing react-force-graph
  if (typeof window !== 'undefined' && !(window as any).AFRAME) {
    (window as any).AFRAME = {
      registerComponent: () => {},
      registerSystem: () => {},
      registerPrimitive: () => {},
      scenes: [],
      version: '1.0.0'
    };
  }
  
  if (!loadPromise) {
    loadPromise = import('react-force-graph')
      .then((module: any) => {
        if (!module || !module.ForceGraph2D) {
          throw new Error('ForceGraph2D component not found in react-force-graph module');
        }
        ForceGraph2DComponent = module.ForceGraph2D;
        return ForceGraph2DComponent;
      })
      .catch((error: any) => {
        // Suppress AFRAME-related errors as we don't use 3D graphs
        const errorMessage = error?.message || String(error);
        if (errorMessage.includes('AFRAME')) {
          console.warn('AFRAME error suppressed (expected for 2D graphs):', errorMessage);
          // Set AFRAME stub and retry
          if (typeof window !== 'undefined' && !(window as any).AFRAME) {
            (window as any).AFRAME = {
              registerComponent: () => {},
              registerSystem: () => {},
              registerPrimitive: () => {},
              scenes: [],
              version: '1.0.0'
            };
          }
          // Retry the import
          loadPromise = null;
          return loadForceGraph();
        }
        console.error('Failed to load react-force-graph:', error);
        loadPromise = null; // Reset so we can retry
        throw error;
      });
  }
  
  return loadPromise;
};

interface NetworkGraphViewProps {
  synergies: SynergyOpportunity[];
  darkMode?: boolean;
  onSynergySelect?: (synergy: SynergyOpportunity | null) => void;
}

interface GraphNode {
  id: string;
  label: string;
  type: 'trigger' | 'action' | 'device';
  area?: string;
  synergyCount: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  impact: number;
  confidence: number;
  validated: boolean;
  synergyId: number;
}

export const NetworkGraphView: React.FC<NetworkGraphViewProps> = ({
  synergies,
  darkMode = false,
  onSynergySelect
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null);
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());
  const [highlightedLinks, setHighlightedLinks] = useState<Set<number>>(new Set());
  const [filterArea, setFilterArea] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [graphLoaded, setGraphLoaded] = useState(false);
  const [ForceGraph2D, setForceGraph2D] = useState<any>(null);
  const graphRef = useRef<any>();

  // Load the graph component on mount
  useEffect(() => {
    loadForceGraph()
      .then((GraphComponent: any) => {
        setForceGraph2D(() => GraphComponent);
        setGraphLoaded(true);
        setLoadError(null);
      })
      .catch((err: any) => {
        console.error('Error loading ForceGraph2D:', err);
        setLoadError(err?.message || 'Failed to load network graph library');
        setGraphLoaded(false);
      });
  }, []);
  
  // Transform synergies into graph format
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    const linkList: GraphLink[] = [];
    
    synergies.forEach(synergy => {
      // Skip if filtered
      if (filterArea && synergy.area !== filterArea) return;
      if (filterType && synergy.synergy_type !== filterType) return;
      
      const triggerEntity = synergy.opportunity_metadata?.trigger_entity || 
                           `trigger_${synergy.id}`;
      const actionEntity = synergy.opportunity_metadata?.action_entity || 
                          `action_${synergy.id}`;
      const triggerName = synergy.opportunity_metadata?.trigger_name || 
                         triggerEntity.split('.')[1] || triggerEntity;
      const actionName = synergy.opportunity_metadata?.action_name || 
                        actionEntity.split('.')[1] || actionEntity;
      
      // Add trigger node
      if (!nodeMap.has(triggerEntity)) {
        nodeMap.set(triggerEntity, {
          id: triggerEntity,
          label: triggerName,
          type: 'trigger',
          area: synergy.area,
          synergyCount: 0
        });
      }
      const triggerNode = nodeMap.get(triggerEntity)!;
      triggerNode.synergyCount++;
      
      // Add action node
      if (!nodeMap.has(actionEntity)) {
        nodeMap.set(actionEntity, {
          id: actionEntity,
          label: actionName,
          type: 'action',
          area: synergy.area,
          synergyCount: 0
        });
      }
      const actionNode = nodeMap.get(actionEntity)!;
      actionNode.synergyCount++;
      
      // Add link
      linkList.push({
        source: triggerEntity,
        target: actionEntity,
        impact: synergy.impact_score,
        confidence: synergy.confidence,
        validated: synergy.validated_by_patterns || false,
        synergyId: synergy.id
      });
    });
    
    return {
      nodes: Array.from(nodeMap.values()),
      links: linkList
    };
  }, [synergies, filterArea, filterType]);
  
  // Filter nodes/links by search query
  const filteredData = useMemo(() => {
    if (!searchQuery) {
      return { nodes, links };
    }
    
    const query = searchQuery.toLowerCase();
    const matchingNodeIds = new Set(
      nodes.filter(n => 
        n.label.toLowerCase().includes(query) || 
        n.id.toLowerCase().includes(query)
      ).map(n => n.id)
    );
    
    const filteredNodes = nodes.filter(n => matchingNodeIds.has(n.id));
    const filteredLinks = links.filter(l => 
      matchingNodeIds.has(l.source as string) || 
      matchingNodeIds.has(l.target as string)
    );
    
    return { nodes: filteredNodes, links: filteredLinks };
  }, [nodes, links, searchQuery]);
  
  // Get unique areas for filter
  const areas = useMemo(() => {
    const areaSet = new Set(synergies.map(s => s.area).filter(Boolean));
    return Array.from(areaSet).sort();
  }, [synergies]);
  
  // Get unique types for filter
  const types = useMemo(() => {
    const typeSet = new Set(synergies.map(s => s.synergy_type));
    return Array.from(typeSet);
  }, [synergies]);
  
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node.id);
    setSelectedLink(null);
    
    // Highlight connected nodes and links
    const connectedNodeIds = new Set([node.id]);
    const connectedLinkIds = new Set<number>();
    
    links.forEach(link => {
      if (link.source === node.id || link.target === node.id) {
        connectedNodeIds.add(link.source as string);
        connectedNodeIds.add(link.target as string);
        connectedLinkIds.add(link.synergyId);
      }
    });
    
    setHighlightedNodes(connectedNodeIds);
    setHighlightedLinks(connectedLinkIds);
    
    // Find and select a synergy for this node
    const relatedSynergy = synergies.find(s => 
      s.opportunity_metadata?.trigger_entity === node.id ||
      s.opportunity_metadata?.action_entity === node.id
    );
    onSynergySelect?.(relatedSynergy || null);
  }, [links, synergies, onSynergySelect]);
  
  const handleLinkClick = useCallback((link: GraphLink) => {
    setSelectedLink(link);
    setSelectedNode(null);
    
    const synergy = synergies.find(s => s.id === link.synergyId);
    onSynergySelect?.(synergy || null);
  }, [synergies, onSynergySelect]);
  
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedLink(null);
    setHighlightedNodes(new Set());
    setHighlightedLinks(new Set());
    onSynergySelect?.(null);
  }, [onSynergySelect]);
  
  // Node color by area
  const getNodeColor = (node: GraphNode) => {
    if (selectedNode === node.id) return '#3b82f6';
    if (highlightedNodes.has(node.id)) return '#10b981';
    
    // Color by area (simple hash)
    if (node.area) {
      const colors = [
        '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444'
      ];
      const hash = node.area.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return colors[hash % colors.length];
    }
    
    return darkMode ? '#6b7280' : '#9ca3af';
  };
  
  // Link color by confidence
  const getLinkColor = (link: GraphLink) => {
    if (selectedLink && selectedLink.synergyId === link.synergyId) return '#3b82f6';
    if (highlightedLinks.has(link.synergyId)) return '#10b981';
    
    if (link.confidence >= 0.8) return '#22c55e'; // green
    if (link.confidence >= 0.6) return '#eab308'; // yellow
    return '#ef4444'; // red
  };
  
  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className={`block text-xs font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Search Device
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search..."
              className={`w-full px-3 py-2 rounded-lg text-sm border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-gray-300 placeholder-gray-500'
                  : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            />
          </div>
          
          {/* Area Filter */}
          <div>
            <label className={`block text-xs font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Filter by Area
            </label>
            <select
              value={filterArea || ''}
              onChange={(e) => setFilterArea(e.target.value || null)}
              className={`w-full px-3 py-2 rounded-lg text-sm border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-gray-300'
                  : 'bg-white border-gray-300 text-gray-900'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            >
              <option value="">All Areas</option>
              {areas.map(area => (
                <option key={area} value={area}>{area}</option>
              ))}
            </select>
          </div>
          
          {/* Type Filter */}
          <div>
            <label className={`block text-xs font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Filter by Type
            </label>
            <select
              value={filterType || ''}
              onChange={(e) => setFilterType(e.target.value || null)}
              className={`w-full px-3 py-2 rounded-lg text-sm border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-gray-300'
                  : 'bg-white border-gray-300 text-gray-900'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            >
              <option value="">All Types</option>
              {types.map(type => (
                <option key={type} value={type}>{type.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          
          {/* Reset */}
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilterArea(null);
                setFilterType(null);
                setSearchQuery('');
                setSelectedNode(null);
                setSelectedLink(null);
                setHighlightedNodes(new Set());
                setHighlightedLinks(new Set());
              }}
              className={`w-full px-4 py-2 rounded-lg text-sm font-medium ${
                darkMode
                  ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
              }`}
            >
              Reset Filters
            </button>
          </div>
        </div>
      </div>
      
      {/* Graph Container */}
      <div className={`relative rounded-xl overflow-hidden ${darkMode ? 'bg-gray-900' : 'bg-gray-100'} shadow-lg`}>
        {loadError ? (
          <div className="flex items-center justify-center h-[600px]">
            <div className={`text-center p-6 rounded-xl ${darkMode ? 'bg-gray-800 text-gray-300' : 'bg-white text-gray-700'}`}>
              <div className="text-4xl mb-4">⚠️</div>
              <h3 className="text-lg font-semibold mb-2">Failed to load network graph</h3>
              <p className="text-sm mb-4">{loadError}</p>
              <button
                onClick={() => {
                  setLoadError(null);
                  window.location.reload();
                }}
                className={`px-4 py-2 rounded-xl text-sm font-medium ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                Retry
              </button>
            </div>
          </div>
        ) : filteredData.nodes.length === 0 ? (
          <div className="flex items-center justify-center h-[600px]">
            <div className={`text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <div className="text-4xl mb-4">📊</div>
              <p className="text-lg font-medium mb-2">No data to display</p>
              <p className="text-sm">No synergies available for network graph visualization.</p>
            </div>
          </div>
        ) : !graphLoaded || !ForceGraph2D ? (
          <div className="flex items-center justify-center h-[600px]">
            <div className={`text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p>Loading network graph...</p>
            </div>
          </div>
        ) : (
          <GraphErrorBoundary
            fallback={
              <div className="flex items-center justify-center h-[600px]">
                <div className={`text-center p-6 rounded-xl ${darkMode ? 'bg-gray-800 text-gray-300' : 'bg-white text-gray-700'}`}>
                  <div className="text-4xl mb-4">⚠️</div>
                  <h3 className="text-lg font-semibold mb-2">Graph rendering error</h3>
                  <p className="text-sm mb-4">An error occurred while rendering the network graph.</p>
                  <button
                    onClick={() => window.location.reload()}
                    className={`px-4 py-2 rounded-xl text-sm font-medium ${
                      darkMode
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                        : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
                    }`}
                  >
                    Refresh Page
                  </button>
                </div>
              </div>
            }
          >
            <ForceGraph2D
              ref={graphRef}
              graphData={filteredData}
              nodeLabel={(node: any) => {
                const graphNode = node as GraphNode;
                return `${graphNode.label}\n${graphNode.synergyCount} synergies`;
              }}
              nodeColor={(node: any) => getNodeColor(node as GraphNode)}
              nodeVal={(node: any) => {
                const graphNode = node as GraphNode;
                return Math.sqrt(graphNode.synergyCount) * 5 + 5;
              }}
              linkLabel={(link: any) => {
                const graphLink = link as GraphLink;
                return `Impact: ${Math.round(graphLink.impact * 100)}%\nConfidence: ${Math.round(graphLink.confidence * 100)}%`;
              }}
              linkColor={(link: any) => getLinkColor(link as GraphLink)}
              linkWidth={(link: any) => {
                const graphLink = link as GraphLink;
                return graphLink.impact * 3 + 1;
              }}
              linkDirectionalArrowLength={6}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(node: any) => handleNodeClick(node as GraphNode)}
              onLinkClick={(link: any) => handleLinkClick(link as GraphLink)}
              onBackgroundClick={handleBackgroundClick}
              cooldownTicks={100}
              onEngineStop={() => graphRef.current?.zoomToFit(400)}
              width={typeof window !== 'undefined' ? Math.max(window.innerWidth - 100, 800) : 800}
              height={600}
            />
          </GraphErrorBoundary>
        )}
      </div>
      
      {/* Selected Node/Link Info Panel */}
      <AnimatePresence>
        {(selectedNode || selectedLink) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            {selectedNode && (
              <div>
                <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Device: {nodes.find(n => n.id === selectedNode)?.label}
                </h3>
                <div className={`text-sm space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  <div>Area: {nodes.find(n => n.id === selectedNode)?.area || 'Unknown'}</div>
                  <div>Synergies: {nodes.find(n => n.id === selectedNode)?.synergyCount || 0}</div>
                </div>
              </div>
            )}
            {selectedLink && (
              <div>
                <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Synergy Connection
                </h3>
                <div className={`text-sm space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  <div>Impact: {Math.round(selectedLink.impact * 100)}%</div>
                  <div>Confidence: {Math.round(selectedLink.confidence * 100)}%</div>
                  <div>Validated: {selectedLink.validated ? 'Yes' : 'No'}</div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Stats */}
      <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {filteredData.nodes.length}
            </div>
            <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Devices
            </div>
          </div>
          <div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {filteredData.links.length}
            </div>
            <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Connections
            </div>
          </div>
          <div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {areas.length}
            </div>
            <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Areas
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

