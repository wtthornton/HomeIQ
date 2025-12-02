/**
 * Filter Pills Component
 * Enhanced filter interface with pill buttons for better UX
 * Supports category, confidence, and status filters
 */

import React from 'react';
import { motion } from 'framer-motion';

export interface FilterOption {
  value: string;
  label: string;
  icon?: string;
  count?: number;
}

interface FilterPillsProps {
  type: 'category' | 'confidence' | 'status' | 'tags';
  options: FilterOption[];
  selected: string[];
  onSelectionChange: (selected: string[]) => void;
  darkMode?: boolean;
  showCounts?: boolean;
}

export const FilterPills: React.FC<FilterPillsProps> = ({
  type,
  options,
  selected,
  onSelectionChange,
  darkMode = false,
  showCounts = false
}) => {
  const toggleOption = (value: string) => {
    const newSelected = selected.includes(value)
      ? selected.filter(s => s !== value)
      : [...selected, value];
    onSelectionChange(newSelected);
  };

  const clearAll = () => {
    onSelectionChange([]);
  };

  const selectAll = () => {
    onSelectionChange(options.map(opt => opt.value));
  };

  const getTypeLabel = () => {
    switch (type) {
      case 'category': return 'Category';
      case 'confidence': return 'Confidence';
      case 'status': return 'Status';
      case 'tags': return 'Tags';
      default: return 'Filter';
    }
  };

  const getTypeIcon = () => {
    switch (type) {
      case 'category': return '🏷️';
      case 'confidence': return '🎯';
      case 'status': return '📊';
      case 'tags': return '🔖';
      default: return '🔍';
    }
  };

  const getPillColors = (isSelected: boolean, value: string) => {
    if (isSelected) {
      // Active state colors
      switch (type) {
        case 'confidence':
          if (value === 'high') return 'bg-green-500 text-white border-green-500';
          if (value === 'medium') return 'bg-yellow-500 text-white border-yellow-500';
          if (value === 'low') return 'bg-red-500 text-white border-red-500';
          break;
        case 'category':
          if (value === 'energy') return 'bg-green-500 text-white border-green-500';
          if (value === 'comfort') return 'bg-blue-500 text-white border-blue-500';
          if (value === 'security') return 'bg-red-500 text-white border-red-500';
          if (value === 'convenience') return 'bg-purple-500 text-white border-purple-500';
          break;
        case 'tags':
          // Tag-specific colors
          if (value === 'energy') return 'bg-green-500 text-white border-green-500';
          if (value === 'security') return 'bg-red-500 text-white border-red-500';
          if (value === 'comfort') return 'bg-blue-500 text-white border-blue-500';
          if (value === 'convenience') return 'bg-purple-500 text-white border-purple-500';
          if (value === 'lighting') return 'bg-yellow-500 text-white border-yellow-500';
          if (value === 'climate') return 'bg-cyan-500 text-white border-cyan-500';
          if (value === 'presence') return 'bg-orange-500 text-white border-orange-500';
          if (value === 'notification') return 'bg-blue-500 text-white border-blue-500';
          if (value === 'media') return 'bg-pink-500 text-white border-pink-500';
          if (value === 'ai-generated') return 'bg-purple-500 text-white border-purple-500';
          break;
        default:
          return darkMode 
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-blue-500 text-white border-blue-500';
      }
      return darkMode 
        ? 'bg-blue-600 text-white border-blue-600'
        : 'bg-blue-500 text-white border-blue-500';
    } else {
      // Inactive state colors
      return darkMode
        ? 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600 hover:border-gray-500'
        : 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200 hover:border-gray-300';
    }
  };

  return (
    <div className="space-y-3">
      {/* Filter Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getTypeIcon()}</span>
          <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {getTypeLabel()}
          </span>
          {selected.length > 0 && (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
            }`}>
              {selected.length} selected
            </span>
          )}
        </div>
        
        {/* Clear/Select All buttons */}
        <div className="flex gap-1">
          {selected.length > 0 && (
            <button
              onClick={clearAll}
              className={`px-2 py-1 text-xs font-medium rounded-xl transition-all ${
                darkMode 
                  ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/60'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100/80'
              }`}
            >
              Clear
            </button>
          )}
          {selected.length < options.length && (
            <button
              onClick={selectAll}
              className={`px-2 py-1 text-xs font-medium rounded-xl transition-all ${
                darkMode 
                  ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/60'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100/80'
              }`}
            >
              All
            </button>
          )}
        </div>
      </div>

      {/* Filter Pills */}
      <div className="flex flex-wrap gap-1">
        {options.map((option) => {
          const isSelected = selected.includes(option.value);
          return (
            <button
              key={option.value}
              onClick={() => toggleOption(option.value)}
              className={`
                px-3 py-1 text-sm font-medium border transition-all rounded-xl
                ${getPillColors(isSelected, option.value)}
                focus:outline-none focus:ring-1 focus:ring-blue-500
                ${isSelected ? 'shadow-lg' : ''}
              `}
              aria-pressed={isSelected}
              aria-label={`Filter by ${option.label}${option.count ? ` (${option.count} items)` : ''}`}
            >
              <span className="flex items-center gap-1">
                {option.icon && <span className="text-xs">{option.icon}</span>}
                <span>{option.label}</span>
                {showCounts && option.count !== undefined && (
                  <span className={`px-1 py-0.5 text-xs font-bold ${
                    isSelected 
                      ? 'bg-white/20 text-white'
                      : darkMode 
                        ? 'bg-gray-600 text-gray-200'
                        : 'bg-gray-200 text-gray-700'
                  }`}>
                    {option.count}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      {/* Filter Summary */}
      {selected.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} pt-1`}
        >
          Showing {selected.length} {type} filter{selected.length > 1 ? 's' : ''}: {selected.join(', ')}
        </motion.div>
      )}
    </div>
  );
};
