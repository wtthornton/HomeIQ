/**
 * Trend Indicator Component
 * Phase 2: Enhancements - Overview Tab Redesign
 * 
 * Displays a visual indicator showing if a metric is improving, degrading, or stable
 */

import React from 'react';

export interface TrendIndicatorProps {
  current: number;
  previous: number;
  darkMode?: boolean;
  showPercentage?: boolean;
  className?: string;
}

export const TrendIndicator: React.FC<TrendIndicatorProps> = ({
  current,
  previous,
  darkMode = false,
  showPercentage = true,
  className = ''
}) => {
  const calculateTrend = () => {
    // Null safety
    if (current == null || previous == null) {
      return { direction: 'stable', icon: '➡️', percentage: 0, color: 'text-gray-500' };
    }
    
    if (previous === 0) {
      return { direction: 'stable', icon: '➡️', percentage: 0, color: 'text-gray-500' };
    }

    const change = ((current - previous) / previous) * 100;
    
    if (Math.abs(change) < 5) {
      return {
        direction: 'stable',
        icon: '➡️',
        percentage: change,
        color: darkMode ? 'text-gray-400' : 'text-gray-500'
      };
    } else if (change > 0) {
      return {
        direction: 'up',
        icon: '↗️',
        percentage: change,
        color: darkMode ? 'text-green-400' : 'text-green-600'
      };
    } else {
      return {
        direction: 'down',
        icon: '↘️',
        percentage: change,
        color: darkMode ? 'text-red-400' : 'text-red-600'
      };
    }
  };

  const trend = calculateTrend();

  return (
    <div className={`inline-flex items-center space-x-1 ${trend.color} ${className}`}>
      <span className="text-sm">{trend.icon}</span>
      {showPercentage && (
        <span className="text-xs font-medium">
          {Math.abs(trend.percentage).toFixed(1)}%
        </span>
      )}
    </div>
  );
};

