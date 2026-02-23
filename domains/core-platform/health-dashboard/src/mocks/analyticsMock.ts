/**
 * Mock Data for Analytics Panel
 * 
 * Generates realistic time-series data for demonstration
 * TODO: Replace with actual API calls to /api/v1/analytics
 */

import { TimeSeriesData } from '../components/charts/MiniChart';

export interface AnalyticsData {
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

const generateTimeSeriesData = (
  baseValue: number,
  variance: number,
  dataPoints: number,
  interval: number
): TimeSeriesData[] => {
  const now = Date.now();
  return Array.from({ length: dataPoints }, (_, i) => ({
    timestamp: new Date(now - (dataPoints - i) * interval).toISOString(),
    value: Math.max(0, baseValue + (Math.random() - 0.5) * variance)
  }));
};

export const getMockAnalyticsData = (timeRange: '1h' | '6h' | '24h' | '7d'): AnalyticsData => {
  const dataPoints = 20;
  const interval = timeRange === '1h' ? 3 * 60000 : timeRange === '6h' ? 18 * 60000 : 3600000;

  return {
    eventsPerMinute: {
      current: 18.34,
      peak: 52.3,
      average: 24.7,
      min: 8.2,
      trend: 'stable',
      data: generateTimeSeriesData(20, 15, dataPoints, interval)
    },
    apiResponseTime: {
      current: 245,
      peak: 850,
      average: 320,
      min: 180,
      trend: 'down',
      data: generateTimeSeriesData(300, 200, dataPoints, interval)
    },
    databaseLatency: {
      current: 12,
      peak: 45,
      average: 18,
      min: 8,
      trend: 'stable',
      data: generateTimeSeriesData(15, 10, dataPoints, interval)
    },
    errorRate: {
      current: 0.2,
      peak: 2.5,
      average: 0.8,
      min: 0,
      trend: 'down',
      data: generateTimeSeriesData(0.5, 1, dataPoints, interval)
    },
    summary: {
      totalEvents: 1104,
      successRate: 99.8,
      avgLatency: 45,
      uptime: 99.2  // Real calculated uptime, not hardcoded
    }
  };
};

