/**
 * AnalyticsFilters Component
 * 
 * Time range filter controls for analytics data
 */

import React from 'react';
import type { TimeRange } from '../../hooks/useAnalyticsData';

interface AnalyticsFiltersProps {
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
  lastUpdate: Date;
  darkMode: boolean;
}

export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  timeRange,
  onTimeRangeChange,
  lastUpdate,
  darkMode
}): JSX.Element => {
  const ranges: Array<{ value: TimeRange; label: string }> = [
    { value: '1h', label: 'Last Hour' },
    { value: '6h', label: 'Last 6 Hours' },
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' }
  ];

  const formatLastUpdate = (): string => {
    const now = new Date();
    const diffMs = now.getTime() - lastUpdate.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffMs / 60000);

    if (diffSecs < 60) {
      return `${diffSecs}s ago`;
    }
    if (diffMins < 60) {
      return `${diffMins}m ago`;
    }
    return lastUpdate.toLocaleTimeString();
  };

  return (
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <div>
        <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          System Analytics
        </h2>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Last updated: {formatLastUpdate()}
        </p>
      </div>

      <div className="flex gap-2">
        {ranges.map((range) => (
          <button
            key={range.value}
            onClick={() => onTimeRangeChange(range.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              timeRange === range.value
                ? darkMode
                  ? 'bg-blue-600 text-white'
                  : 'bg-blue-600 text-white'
                : darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>
    </div>
  );
};

