/**
 * Room Map View Component
 * Spatial visualization of synergies organized by room/area
 * 
 * Phase 2: Room Map View
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SynergyOpportunity } from '../../types';
import { RoomCard } from './RoomCard';

interface RoomMapViewProps {
  synergies: SynergyOpportunity[];
  darkMode?: boolean;
}

interface AreaStats {
  area: string;
  synergies: SynergyOpportunity[];
  avgImpact: number;
  typeCounts: Record<string, number>;
  complexityBreakdown: Record<string, number>;
}

export const RoomMapView: React.FC<RoomMapViewProps> = ({
  synergies,
  darkMode = false
}) => {
  const [expandedAreas, setExpandedAreas] = useState<Set<string>>(new Set());
  const [heatMapMode, setHeatMapMode] = useState(false);
  
  // Group synergies by area
  const areaStats = useMemo(() => {
    const grouped = synergies.reduce((acc, synergy) => {
      const area = synergy.area || 'Unassigned';
      if (!acc[area]) {
        acc[area] = {
          area,
          synergies: [],
          avgImpact: 0,
          typeCounts: {},
          complexityBreakdown: {}
        };
      }
      acc[area].synergies.push(synergy);
      return acc;
    }, {} as Record<string, AreaStats>);
    
    // Calculate stats for each area
    Object.values(grouped).forEach(stats => {
      stats.avgImpact = stats.synergies.reduce((sum, s) => sum + s.impact_score, 0) / stats.synergies.length;
      stats.typeCounts = stats.synergies.reduce((acc, s) => {
        acc[s.synergy_type] = (acc[s.synergy_type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
      stats.complexityBreakdown = stats.synergies.reduce((acc, s) => {
        acc[s.complexity] = (acc[s.complexity] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
    });
    
    return Object.values(grouped);
  }, [synergies]);
  
  // Calculate heat map intensity (normalized 0-1)
  const maxSynergies = Math.max(...areaStats.map(s => s.synergies.length), 1);
  const getHeatMapIntensity = (count: number) => count / maxSynergies;
  
  // Sort areas by synergy count (descending)
  const sortedAreas = [...areaStats].sort((a, b) => b.synergies.length - a.synergies.length);
  
  // Top areas for insights
  const topAreas = sortedAreas.slice(0, 3);
  const lowAreas = sortedAreas.filter(a => a.synergies.length <= 2).slice(0, 3);
  
  const toggleArea = (area: string) => {
    setExpandedAreas(prev => {
      const next = new Set(prev);
      if (next.has(area)) {
        next.delete(area);
      } else {
        next.add(area);
      }
      return next;
    });
  };
  
  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={heatMapMode}
              onChange={(e) => setHeatMapMode(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Show Heat Map
            </span>
          </label>
        </div>
        <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          {areaStats.length} {areaStats.length === 1 ? 'area' : 'areas'} with synergies
        </div>
      </div>
      
      {/* Spatial Insights Panel */}
      <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 ${darkMode ? 'bg-gray-800' : 'bg-white'} p-4 rounded-xl shadow-lg`}>
        <div>
          <h4 className={`text-sm font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🏆 Most Opportunities
          </h4>
          <div className="space-y-1">
            {topAreas.map((area, idx) => (
              <div key={area.area} className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {idx + 1}. {area.area} ({area.synergies.length})
              </div>
            ))}
          </div>
        </div>
        <div>
          <h4 className={`text-sm font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            ⚠️ Needs Attention
          </h4>
          <div className="space-y-1">
            {lowAreas.length > 0 ? (
              lowAreas.map((area) => (
                <div key={area.area} className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {area.area} ({area.synergies.length})
                </div>
              ))
            ) : (
              <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                All areas have good coverage
              </div>
            )}
          </div>
        </div>
        <div>
          <h4 className={`text-sm font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 Summary
          </h4>
          <div className="space-y-1 text-xs">
            <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
              Total: {synergies.length} synergies
            </div>
            <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
              Avg Impact: {Math.round(sortedAreas.reduce((sum, a) => sum + a.avgImpact, 0) / sortedAreas.length * 100)}%
            </div>
          </div>
        </div>
      </div>
      
      {/* Room Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {sortedAreas.map((areaStats) => (
          <div key={areaStats.area}>
            <RoomCard
              area={areaStats.area}
              synergies={areaStats.synergies}
              darkMode={darkMode}
              onExpand={() => toggleArea(areaStats.area)}
              isExpanded={expandedAreas.has(areaStats.area)}
              heatMapIntensity={heatMapMode ? getHeatMapIntensity(areaStats.synergies.length) : 0}
            />
            
            {/* Expanded Synergies List */}
            <AnimatePresence>
              {expandedAreas.has(areaStats.area) && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={`mt-2 p-3 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} border border-gray-300`}
                >
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {areaStats.synergies.map((synergy) => (
                      <div
                        key={synergy.id}
                        className={`p-2 rounded text-xs border ${
                          darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            {synergy.opportunity_metadata?.trigger_name || 'Trigger'} → {synergy.opportunity_metadata?.action_name || 'Action'}
                          </span>
                          <span className={`font-semibold ${
                            synergy.impact_score >= 0.75
                              ? darkMode ? 'text-green-400' : 'text-green-600'
                              : synergy.impact_score >= 0.5
                              ? darkMode ? 'text-yellow-400' : 'text-yellow-600'
                              : darkMode ? 'text-red-400' : 'text-red-600'
                          }`}>
                            {Math.round(synergy.impact_score * 100)}%
                          </span>
                        </div>
                        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          {synergy.complexity} complexity • {Math.round(synergy.confidence * 100)}% confidence
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
      
      {/* Empty State */}
      {areaStats.length === 0 && (
        <div className={`text-center py-12 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <div className="text-4xl mb-4">🏠</div>
          <div className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            No Areas with Synergies
          </div>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Synergies will be organized by room/area when available
          </p>
        </div>
      )}
    </div>
  );
};

