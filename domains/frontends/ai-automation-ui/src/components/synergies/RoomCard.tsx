/**
 * Room Card Component
 * Displays a room/area with its synergies
 * 
 * Phase 2: Room Map View
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { SynergyOpportunity } from '../../types';

interface RoomCardProps {
  area: string;
  synergies: SynergyOpportunity[];
  darkMode?: boolean;
  onExpand?: () => void;
  isExpanded?: boolean;
  heatMapIntensity?: number; // 0-1 for heat map mode
}

export const RoomCard: React.FC<RoomCardProps> = ({
  area,
  synergies,
  darkMode = false,
  onExpand,
  isExpanded = false,
  heatMapIntensity = 0
}) => {
  const avgImpact = synergies.reduce((sum, s) => sum + s.impact_score, 0) / synergies.length;
  const typeCounts = synergies.reduce((acc, s) => {
    acc[s.synergy_type] = (acc[s.synergy_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      device_pair: '🔗',
      weather_context: '🌤️',
      energy_context: '⚡',
      event_context: '📅',
    };
    return icons[type] || '🔮';
  };
  
  // Heat map color calculation
  const getHeatMapColor = (intensity: number) => {
    if (intensity === 0) return darkMode ? 'bg-gray-800' : 'bg-gray-100';
    // Scale from light to dark: 0.1 = light, 1.0 = very dark
    const opacity = Math.max(0.1, Math.min(1.0, intensity));
    const red = Math.round(255 * (1 - opacity * 0.7));
    const green = Math.round(255 * (1 - opacity * 0.9));
    const blue = Math.round(255 * (1 - opacity * 0.5));
    return `rgb(${red}, ${green}, ${blue})`;
  };
  
  const heatMapStyle = heatMapIntensity > 0
    ? { backgroundColor: getHeatMapColor(heatMapIntensity) }
    : {};

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
        darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } ${isExpanded ? 'ring-2 ring-blue-500' : ''}`}
      style={heatMapStyle}
      onClick={onExpand}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Room Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {area}
        </h3>
        <div className={`text-2xl font-bold ${
          darkMode ? 'text-blue-400' : 'text-blue-600'
        }`}>
          {synergies.length}
        </div>
      </div>
      
      {/* Synergy Count Badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        {Object.entries(typeCounts).map(([type, count]) => (
          <span
            key={type}
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {getTypeIcon(type)} {count}
          </span>
        ))}
      </div>
      
      {/* Impact Score Indicator */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1">
          <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Avg Impact
          </span>
          <span className={`text-sm font-semibold ${
            avgImpact >= 0.75
              ? darkMode ? 'text-green-400' : 'text-green-600'
              : avgImpact >= 0.5
              ? darkMode ? 'text-yellow-400' : 'text-yellow-600'
              : darkMode ? 'text-red-400' : 'text-red-600'
          }`}>
            {Math.round(avgImpact * 100)}%
          </span>
        </div>
        <div className={`h-2 rounded-full overflow-hidden ${
          darkMode ? 'bg-gray-700' : 'bg-gray-200'
        }`}>
          <div
            className={`h-full ${
              avgImpact >= 0.75
                ? 'bg-green-500'
                : avgImpact >= 0.5
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${avgImpact * 100}%` }}
          />
        </div>
      </div>
      
      {/* Quick Stats */}
      <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {synergies.length} opportunit{synergies.length !== 1 ? 'ies' : 'y'}, {Math.round(avgImpact * 100)}% avg impact
      </div>
      
      {/* View Button */}
      <button
        className={`mt-3 w-full py-2 rounded-lg text-xs font-medium transition-colors ${
          darkMode
            ? 'bg-blue-600 hover:bg-blue-700 text-white'
            : 'bg-blue-500 hover:bg-blue-600 text-white'
        }`}
        onClick={(e) => {
          e.stopPropagation();
          onExpand?.();
        }}
      >
        {isExpanded ? '▼ Hide Synergies' : '▶ View Synergies'}
      </button>
    </motion.div>
  );
};

