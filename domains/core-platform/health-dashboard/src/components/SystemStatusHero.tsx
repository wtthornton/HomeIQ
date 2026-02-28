/**
 * System Status Hero Component
 * Phase 1: Critical Fixes - Overview Tab Redesign
 *
 * Displays the primary system status indicator with key performance metrics
 * at a glance. Answers "Is my system OK?" in 5 seconds or less.
 */

import React from 'react';
import { TrendIndicator } from './TrendIndicator';
import { LoadingSpinner } from './LoadingSpinner';

export interface SystemStatusHeroProps {
  overallStatus: 'operational' | 'degraded' | 'error';
  uptime: string;
  throughput: number; // events per minute
  latency: number; // milliseconds
  errorRate: number; // percentage
  lastUpdate: Date;
  darkMode: boolean;
  loading?: boolean; // Show loading indicators
  error?: string | null; // Error message when KPIs failed to load
  onRetry?: () => void; // Callback to retry fetching KPIs
  staleData?: boolean; // True when showing cached data after a failed refresh
  lastUpdated?: Date | null; // Timestamp of last successful data fetch
  trends?: {
    throughput?: number; // previous value for trend calculation
    latency?: number;
    errorRate?: number;
  };
}

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'operational':
      return {
        icon: '🟢',
        label: 'ALL SYSTEMS OPERATIONAL',
        bgClass: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700',
        textClass: 'text-green-800 dark:text-green-200',
        pulseClass: 'bg-green-500'
      };
    case 'degraded':
      return {
        icon: '🟡',
        label: 'DEGRADED PERFORMANCE',
        bgClass: 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-300 dark:border-yellow-700',
        textClass: 'text-yellow-800 dark:text-yellow-200',
        pulseClass: 'bg-yellow-500'
      };
    case 'error':
      return {
        icon: '🔴',
        label: 'SYSTEM ERROR',
        bgClass: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700',
        textClass: 'text-red-800 dark:text-red-200',
        pulseClass: 'bg-red-500'
      };
    default:
      return {
        icon: '⚪',
        label: 'UNKNOWN STATUS',
        bgClass: 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600',
        textClass: 'text-gray-800 dark:text-gray-200',
        pulseClass: 'bg-gray-500'
      };
  }
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

/** Renders a single KPI value, or "Unavailable" if errored, or a spinner if loading */
const KPIValue: React.FC<{
  loading: boolean;
  error: string | null;
  staleData: boolean;
  lastUpdated: Date | null;
  darkMode: boolean;
  children: React.ReactNode;
}> = ({ loading, error, staleData, lastUpdated, darkMode, children }) => {
  // First load: show spinner
  if (loading && !staleData) {
    return (
      <div className="flex items-center space-x-2">
        <LoadingSpinner variant="dots" size="sm" color="default" />
        <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Loading...</span>
      </div>
    );
  }

  // Error with no previous data: show Unavailable
  if (error && !staleData) {
    return (
      <span className={`text-sm font-medium ${darkMode ? 'text-orange-400' : 'text-orange-600'}`}>
        Unavailable
      </span>
    );
  }

  // Stale data: show value with "last updated X ago" hint
  if (staleData && lastUpdated) {
    return (
      <div className="flex flex-col items-end">
        <div className="flex items-center space-x-1">
          {children}
        </div>
        <span className={`text-[10px] ${darkMode ? 'text-orange-400' : 'text-orange-500'}`}>
          {formatTimeAgo(lastUpdated)}
        </span>
      </div>
    );
  }

  // Normal: show value
  return <>{children}</>;
};

export const SystemStatusHero: React.FC<SystemStatusHeroProps> = ({
  overallStatus,
  uptime,
  throughput,
  latency,
  errorRate,
  lastUpdate,
  darkMode,
  loading = false,
  error = null,
  onRetry,
  staleData = false,
  lastUpdated = null,
  trends
}) => {
  const statusConfig = getStatusConfig(overallStatus);

  // KPI-level flags: show unavailable only when loading is done AND error exists AND no stale data
  const kpiError = error && !loading ? error : null;

  return (
    <div className="mb-8" role="region" aria-label="System status overview">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Primary Status Badge - Takes 60% on desktop */}
        <div className="lg:col-span-3">
          <div className={`
            rounded-xl shadow-lg p-8 border-2 transition-all-smooth animate-fade-in-scale
            ${statusConfig.bgClass}
          `}
          role="status"
          aria-live="polite"
          aria-label={`System status: ${statusConfig.label}`}
          >
            <div className="flex items-center justify-center space-x-4">
              {/* Status Icon with Pulse Animation */}
              <div className="relative">
                <span className="text-6xl animate-pulse">{statusConfig.icon}</span>
                {overallStatus === 'operational' && (
                  <span className={`absolute top-0 right-0 block h-4 w-4 rounded-full ${statusConfig.pulseClass} animate-ping opacity-75`}></span>
                )}
              </div>

              {/* Status Label */}
              <div>
                <h2 className={`text-3xl font-bold ${statusConfig.textClass}`}>
                  {statusConfig.label}
                </h2>
                <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Last updated: {lastUpdate.toLocaleTimeString('en-US', {
                    hour12: true,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  })}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Key Performance Indicators - Takes 40% on desktop */}
        <div className="lg:col-span-2">
          <div className={`
            rounded-xl shadow-lg p-6 h-full animate-fade-in-scale
            ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}
          `}
          role="complementary"
          aria-label="Key performance indicators"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-sm font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                KEY PERFORMANCE INDICATORS
              </h3>
              {/* Retry button when KPIs are unavailable or stale */}
              {(kpiError || staleData) && onRetry && (
                <button
                  onClick={onRetry}
                  className={`text-xs font-medium px-2 py-1 rounded transition-colors ${
                    darkMode
                      ? 'text-teal-400 hover:bg-teal-900/30'
                      : 'text-teal-600 hover:bg-teal-50'
                  }`}
                  aria-label="Retry loading KPI data"
                >
                  Retry
                </button>
              )}
            </div>

            <div className="space-y-3">
              {/* Uptime */}
              <div className="flex justify-between items-center">
                <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Uptime
                </span>
                <span className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {uptime}
                </span>
              </div>

              {/* Throughput */}
              <div className="flex justify-between items-center">
                <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Throughput
                </span>
                <KPIValue loading={loading} error={kpiError} staleData={staleData} lastUpdated={lastUpdated} darkMode={darkMode}>
                  <span className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {(throughput ?? 0).toLocaleString()} <span className="text-sm font-normal">evt/min</span>
                  </span>
                  {trends && trends.throughput !== undefined && (
                    <TrendIndicator
                      current={throughput ?? 0}
                      previous={trends.throughput}
                      darkMode={darkMode}
                      showPercentage={false}
                    />
                  )}
                </KPIValue>
              </div>

              {/* Latency */}
              <div className="flex justify-between items-center">
                <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Latency
                </span>
                <KPIValue loading={loading} error={kpiError} staleData={staleData} lastUpdated={lastUpdated} darkMode={darkMode}>
                  <span className={`text-lg font-bold ${
                    (latency ?? 0) < 50
                      ? 'text-green-600 dark:text-green-400'
                      : (latency ?? 0) < 100
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-red-600 dark:text-red-400'
                  }`}>
                    {(latency ?? 0).toFixed(1)} <span className="text-sm font-normal">ms avg</span>
                  </span>
                  {trends?.latency !== undefined && (
                    <TrendIndicator
                      current={latency}
                      previous={trends.latency}
                      darkMode={darkMode}
                      showPercentage={false}
                    />
                  )}
                </KPIValue>
              </div>

              {/* Error Rate */}
              <div className="flex justify-between items-center">
                <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Error Rate
                </span>
                <KPIValue loading={loading} error={kpiError} staleData={staleData} lastUpdated={lastUpdated} darkMode={darkMode}>
                  <span className={`text-lg font-bold ${
                    (errorRate ?? 0) < 1
                      ? 'text-green-600 dark:text-green-400'
                      : (errorRate ?? 0) < 5
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-red-600 dark:text-red-400'
                  }`}>
                    {(errorRate ?? 0).toFixed(2)} <span className="text-sm font-normal">%</span>
                  </span>
                </KPIValue>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Memoize for performance optimization
export default React.memo(SystemStatusHero);
