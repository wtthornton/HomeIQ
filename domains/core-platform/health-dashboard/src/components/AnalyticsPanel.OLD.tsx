/**
 * AnalyticsPanel Component
 * 
 * System performance analytics with charts and trends
 * Epic 13.2: System Performance Analytics
 */

import React, { useState, useEffect } from 'react';
import { MiniChart } from './charts/MiniChart';
import type { AnalyticsData } from '../mocks/analyticsMock';
import { SkeletonCard } from './skeletons';

interface AnalyticsPanelProps {
  darkMode: boolean;
}

// Re-export AnalyticsData interface from mock for internal use
interface AnalyticsDataInternal {
  eventsPerMinute: {
    current: number;
    peak: number;
    average: number;
    min: number;
    trend: 'up' | 'down' | 'stable';
    data: TimeSeriesData[];
  };
  apiResponseTime: {
    current: number;
    peak: number;
    average: number;
    min: number;
    trend: 'up' | 'down' | 'stable';
    data: TimeSeriesData[];
  };
  databaseLatency: {
    current: number;
    peak: number;
    average: number;
    min: number;
    trend: 'up' | 'down' | 'stable';
    data: TimeSeriesData[];
  };
  errorRate: {
    current: number;
    peak: number;
    average: number;
    min: number;
    trend: 'up' | 'down' | 'stable';
    data: TimeSeriesData[];
  };
  summary: {
    totalEvents: number;
    successRate: number;
    avgLatency: number;
    uptime: number;
  };
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({ darkMode }) => {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchAnalytics = async () => {
    try {
      // Fetch real analytics data from data-api
      const response = await fetch(`/api/v1/analytics?range=${timeRange}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      setAnalytics(data);
      setError(null);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
      setLoading(false);
      console.error('Error fetching analytics:', err);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      default:
        return '➡️';
    }
  };

  const getTrendColor = (trend: string, inverted: boolean = false) => {
    const isGood = inverted ? trend === 'down' : trend === 'up';
    if (trend === 'stable') return darkMode ? 'text-gray-400' : 'text-gray-600';
    return isGood 
      ? (darkMode ? 'text-green-400' : 'text-green-600')
      : (darkMode ? 'text-yellow-400' : 'text-yellow-600');
  };


  if (loading) {
    return (
      <div className="space-y-6">
        {/* Key Metrics Skeletons */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={`metric-${i}`} variant="chart" />
          ))}
        </div>
        {/* Summary Stats Skeletons */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={`stat-${i}`} variant="default" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border border-red-200'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <h3 className={`font-semibold ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
              Error Loading Analytics
            </h3>
            <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
              {error}
            </p>
          </div>
          <button
            onClick={fetchAnalytics}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} flex items-center gap-2`}>
              <span>📈</span>
              System Performance Analytics
            </h2>
            <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Detailed metrics, trends, and performance analysis
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`text-right ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <p className="text-sm">Last updated</p>
              <p className="text-sm font-medium">{lastUpdate.toLocaleTimeString()}</p>
            </div>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              aria-label="Select time range for analytics"
              className={`px-4 py-2 rounded-lg border ${
                darkMode 
                  ? 'bg-gray-700 border-gray-600 text-white' 
                  : 'bg-white border-gray-300 text-gray-900'
              } transition-colors`}
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-2`}>
            Total Events
          </div>
          <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            {analytics.summary.totalEvents.toLocaleString()}
          </div>
          <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            events processed
          </div>
        </div>

        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-2`}>
            Success Rate
          </div>
          <div className={`text-3xl font-bold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
            {analytics.summary.successRate}%
          </div>
          <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            of all events
          </div>
        </div>

        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-2`}>
            Avg Latency
          </div>
          <div className={`text-3xl font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
            {analytics.summary.avgLatency}ms
          </div>
          <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            end-to-end
          </div>
        </div>

        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-2`}>
            System Uptime
          </div>
          <div className={`text-3xl font-bold ${darkMode ? 'text-purple-400' : 'text-purple-600'}`}>
            {analytics.summary.uptime}%
          </div>
          <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            availability
          </div>
        </div>
      </div>

      {/* Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Events Per Minute */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Events Processing Rate
              </h3>
              <span className={`text-sm ${getTrendColor(analytics.eventsPerMinute.trend)}`}>
                {getTrendIcon(analytics.eventsPerMinute.trend)} {analytics.eventsPerMinute.trend}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {(analytics.eventsPerMinute.current ?? 0).toFixed(1)}
              </span>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                events/min
              </span>
            </div>
          </div>
          <MiniChart 
            data={analytics.eventsPerMinute.data} 
            color="#3B82F6"
            ariaLabel="Events per minute over time" 
          />
          <div className={`mt-4 grid grid-cols-3 gap-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div>
              <div>Peak</div>
              <div className="font-medium">{(analytics.eventsPerMinute.peak ?? 0).toFixed(1)}</div>
            </div>
            <div>
              <div>Avg</div>
              <div className="font-medium">{(analytics.eventsPerMinute.average ?? 0).toFixed(1)}</div>
            </div>
            <div>
              <div>Min</div>
              <div className="font-medium">{(analytics.eventsPerMinute.min ?? 0).toFixed(1)}</div>
            </div>
          </div>
        </div>

        {/* API Response Time */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                API Response Time
              </h3>
              <span className={`text-sm ${getTrendColor(analytics.apiResponseTime.trend, true)}`}>
                {getTrendIcon(analytics.apiResponseTime.trend)} {analytics.apiResponseTime.trend}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {analytics.apiResponseTime.current.toFixed(0)}
              </span>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                ms
              </span>
            </div>
          </div>
          <MiniChart 
            data={analytics.apiResponseTime.data} 
            color="#10B981"
            ariaLabel="API response time over time" 
          />
          <div className={`mt-4 grid grid-cols-3 gap-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div>
              <div>Peak</div>
              <div className="font-medium">{analytics.apiResponseTime.peak.toFixed(0)}ms</div>
            </div>
            <div>
              <div>Avg</div>
              <div className="font-medium">{analytics.apiResponseTime.average.toFixed(0)}ms</div>
            </div>
            <div>
              <div>Min</div>
              <div className="font-medium">{analytics.apiResponseTime.min.toFixed(0)}ms</div>
            </div>
          </div>
        </div>

        {/* Database Latency */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Database Write Latency
              </h3>
              <span className={`text-sm ${getTrendColor(analytics.databaseLatency.trend, true)}`}>
                {getTrendIcon(analytics.databaseLatency.trend)} {analytics.databaseLatency.trend}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {analytics.databaseLatency.current.toFixed(0)}
              </span>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                ms
              </span>
            </div>
          </div>
          <MiniChart 
            data={analytics.databaseLatency.data} 
            color="#8B5CF6"
            ariaLabel="Database latency over time" 
          />
          <div className={`mt-4 grid grid-cols-3 gap-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div>
              <div>Peak</div>
              <div className="font-medium">{analytics.databaseLatency.peak.toFixed(0)}ms</div>
            </div>
            <div>
              <div>Avg</div>
              <div className="font-medium">{analytics.databaseLatency.average.toFixed(0)}ms</div>
            </div>
            <div>
              <div>Min</div>
              <div className="font-medium">{analytics.databaseLatency.min.toFixed(0)}ms</div>
            </div>
          </div>
        </div>

        {/* Error Rate */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Error Rate
              </h3>
              <span className={`text-sm ${getTrendColor(analytics.errorRate.trend, true)}`}>
                {getTrendIcon(analytics.errorRate.trend)} {analytics.errorRate.trend}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {analytics.errorRate.current.toFixed(1)}
              </span>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                %
              </span>
            </div>
          </div>
          <MiniChart 
            data={analytics.errorRate.data} 
            color="#EF4444"
            ariaLabel="Error rate percentage over time" 
          />
          <div className={`mt-4 grid grid-cols-3 gap-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div>
              <div>Peak</div>
              <div className="font-medium">{analytics.errorRate.peak.toFixed(1)}%</div>
            </div>
            <div>
              <div>Avg</div>
              <div className="font-medium">{analytics.errorRate.average.toFixed(1)}%</div>
            </div>
            <div>
              <div>Min</div>
              <div className="font-medium">{analytics.errorRate.min.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tip */}
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-blue-900/20 border border-blue-500/30' : 'bg-blue-50 border border-blue-200'}`}>
        <div className="flex items-start gap-3">
          <span className="text-xl">💡</span>
          <div className={darkMode ? 'text-blue-200' : 'text-blue-800'}>
            <p className="font-medium">Performance Tip</p>
            <p className="text-sm mt-1">
              View real-time metrics in the Overview tab. Use different time ranges to identify patterns and trends.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

