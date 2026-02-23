/**
 * Performance Sparkline Component
 * Phase 2: Enhancements - Overview Tab Redesign
 * 
 * Displays a lightweight SVG sparkline chart showing performance trends
 * over time (e.g., events per minute over the last hour)
 */

import React, { useMemo } from 'react';

export interface DataPoint {
  timestamp: Date;
  value: number;
}

export interface PerformanceSparklineProps {
  data: DataPoint[];
  current: number;
  peak: number;
  average: number;
  unit: string;
  darkMode: boolean;
  height?: number;
  width?: number;
  onTimeRangeChange?: (range: string) => void;
  selectedTimeRange?: string;
}

export const PerformanceSparkline: React.FC<PerformanceSparklineProps> = ({
  data,
  current,
  peak,
  average,
  unit,
  darkMode,
  height = 80,
  width = 600,
  onTimeRangeChange,
  selectedTimeRange = '1h'
}) => {
  // Calculate SVG path for sparkline
  const { path, points } = useMemo(() => {
    if (data.length === 0) {
      return { path: '', points: [] };
    }

    const padding = 10;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Find min/max for scaling
    const values = data.map(d => d.value);
    const minValue = Math.min(...values, 0);
    const maxValue = Math.max(...values, 1);
    const valueRange = maxValue - minValue || 1;

    // Generate points
    const chartPoints = data.map((d, i) => {
      const x = padding + (i / (data.length - 1 || 1)) * chartWidth;
      const y = padding + chartHeight - ((d.value - minValue) / valueRange) * chartHeight;
      return { x, y, value: d.value };
    });

    // Generate SVG path
    if (chartPoints.length === 0) {
      return { path: '', points: [] };
    }

    const pathCommands = chartPoints
      .filter(point => point && point.x != null && point.y != null)
      .map((point, i) => {
        const command = i === 0 ? 'M' : 'L';
        return `${command} ${(point.x ?? 0).toFixed(2)},${(point.y ?? 0).toFixed(2)}`;
      }).join(' ');

    return { path: pathCommands, points: chartPoints };
  }, [data, height, width]);

  // Determine trend direction
  const trend = useMemo(() => {
    if (data.length < 2) return 'stable';
    const recent = data.slice(-5).map(d => d.value);
    const recentAvg = recent.reduce((sum, val) => sum + val, 0) / recent.length;
    const older = data.slice(-10, -5).map(d => d.value);
    const olderAvg = older.length > 0 
      ? older.reduce((sum, val) => sum + val, 0) / older.length 
      : recentAvg;
    
    if (recentAvg > olderAvg * 1.1) return 'up';
    if (recentAvg < olderAvg * 0.9) return 'down';
    return 'stable';
  }, [data]);

  const getTrendConfig = () => {
    switch (trend) {
      case 'up':
        return { icon: '📈', color: 'text-green-600 dark:text-green-400', label: 'Increasing' };
      case 'down':
        return { icon: '📉', color: 'text-red-600 dark:text-red-400', label: 'Decreasing' };
      default:
        return { icon: '➡️', color: 'text-gray-600 dark:text-gray-400', label: 'Stable' };
    }
  };

  const trendConfig = getTrendConfig();

  return (
    <div 
      className={`rounded-lg shadow p-6 animate-fade-in-scale ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}
      role="region"
      aria-label="Live performance metrics chart"
    >
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          📈 Live Performance Metrics
        </h3>
        <div className="flex items-center space-x-3">
          {/* Time Range Selector */}
          {onTimeRangeChange && (
            <select
              value={selectedTimeRange}
              onChange={(e) => onTimeRangeChange(e.target.value)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors focus-visible-ring ${
                darkMode 
                  ? 'bg-gray-700 border-gray-600 text-white hover:bg-gray-600' 
                  : 'bg-white border-gray-300 text-gray-900 hover:bg-gray-50'
              }`}
              aria-label="Select time range for performance chart"
            >
              <option value="15m">Last 15 min</option>
              <option value="1h">Last 1 hour</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
            </select>
          )}
          <div className={`flex items-center space-x-2 text-sm ${trendConfig.color}`}>
            <span aria-hidden="true">{trendConfig.icon}</span>
            <span className="font-medium">{trendConfig.label}</span>
          </div>
        </div>
      </div>

      {/* Sparkline Chart */}
      {data.length > 0 ? (
        <div className="relative">
          <svg
            width="100%"
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            className="w-full"
            preserveAspectRatio="none"
          >
            {/* Background grid lines */}
            <line
              x1="0"
              y1={height / 2}
              x2={width}
              y2={height / 2}
              stroke={darkMode ? '#374151' : '#E5E7EB'}
              strokeWidth="1"
              strokeDasharray="4"
            />

            {/* Area fill under the line */}
            {path && (
              <path
                d={`${path} L ${width - 10},${height - 10} L 10,${height - 10} Z`}
                fill={darkMode ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.15)'}
              />
            )}

            {/* Sparkline path with draw animation */}
            {path && (
              <path
                d={path}
                fill="none"
                stroke={darkMode ? '#3B82F6' : '#2563EB'}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="sparkline-path"
              />
            )}

            {/* Current value dot */}
            {points.length > 0 && (
              <circle
                cx={points[points.length - 1].x}
                cy={points[points.length - 1].y}
                r="4"
                fill={darkMode ? '#3B82F6' : '#2563EB'}
                stroke={darkMode ? '#1F2937' : '#FFFFFF'}
                strokeWidth="2"
              />
            )}
          </svg>
        </div>
      ) : (
        <div className={`h-${height} flex items-center justify-center ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          <p className="text-sm">No data available</p>
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div>
          <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} id="current-value-label">Current</p>
          <p className={`text-lg font-bold animate-count-up ${darkMode ? 'text-white' : 'text-gray-900'}`} aria-labelledby="current-value-label">
            {current.toLocaleString()} <span className="text-sm font-normal">{unit}</span>
          </p>
        </div>
        <div>
          <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} id="peak-value-label">Peak</p>
          <p className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`} aria-labelledby="peak-value-label">
            {peak.toLocaleString()} <span className="text-sm font-normal">{unit}</span>
          </p>
        </div>
        <div>
          <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} id="average-value-label">Average</p>
          <p className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`} aria-labelledby="average-value-label">
            {average.toLocaleString()} <span className="text-sm font-normal">{unit}</span>
          </p>
        </div>
      </div>
    </div>
  );
};

// Memoize for performance - only re-render when props change
export default React.memo(PerformanceSparkline);

