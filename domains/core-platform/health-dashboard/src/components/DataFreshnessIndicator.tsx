/**
 * Data Freshness Indicator Component
 * 
 * Shows when data was last updated and indicates if it's stale
 */

import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

export interface DataFreshnessIndicatorProps {
  lastUpdate: Date | null;
  isStale: boolean;
  loading: boolean;
  error: string | null;
  darkMode: boolean;
  className?: string;
}

export const DataFreshnessIndicator: React.FC<DataFreshnessIndicatorProps> = ({
  lastUpdate,
  isStale,
  loading,
  error,
  darkMode,
  className = ''
}) => {
  if (loading && !lastUpdate) {
    // Initial load - show loading spinner
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <LoadingSpinner variant="dots" size="sm" color="default" />
        <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Loading data...
        </span>
      </div>
    );
  }

  if (error) {
    // Error state - show error with last update if available
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <span className="text-red-500">⚠️</span>
        <span className={`text-xs ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
          {error}
        </span>
        {lastUpdate && (
          <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
            (Last: {lastUpdate.toLocaleTimeString()})
          </span>
        )}
      </div>
    );
  }

  if (!lastUpdate) {
    // No data yet
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <span className="text-yellow-500">⏳</span>
        <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          No data available
        </span>
      </div>
    );
  }

  // Calculate age
  const ageMs = Date.now() - lastUpdate.getTime();
  const ageSeconds = Math.floor(ageMs / 1000);
  const ageMinutes = Math.floor(ageSeconds / 60);
  const ageHours = Math.floor(ageMinutes / 60);

  let ageText: string;
  if (ageSeconds < 60) {
    ageText = `${ageSeconds}s ago`;
  } else if (ageMinutes < 60) {
    ageText = `${ageMinutes}m ago`;
  } else {
    ageText = `${ageHours}h ago`;
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {isStale ? (
        <>
          <span className="text-yellow-500 animate-pulse">⚠️</span>
          <span className={`text-xs font-medium ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
            Stale data
          </span>
        </>
      ) : (
        <>
          <span className="text-green-500">✓</span>
          <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Fresh
          </span>
        </>
      )}
      <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        {ageText} • {lastUpdate.toLocaleTimeString()}
      </span>
    </div>
  );
};

