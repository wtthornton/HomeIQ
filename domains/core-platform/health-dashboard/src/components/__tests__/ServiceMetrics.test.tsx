/**
 * ServiceMetrics Component Tests
 *
 * Unit tests for loading, error, metrics display, and refresh behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ServiceMetrics } from '../ServiceMetrics';

// Mock dependencies
vi.mock('../../hooks/useServiceMetrics');
vi.mock('../../config/serviceMetricsConfig');

import { useServiceMetrics } from '../../hooks/useServiceMetrics';
import { getServiceMetricsConfig } from '../../config/serviceMetricsConfig';

const mockUseServiceMetrics = vi.mocked(useServiceMetrics);
const mockGetConfig = vi.mocked(getServiceMetricsConfig);

const mockMetricsData = {
  serviceId: 'websocket-ingestion',
  timestamp: new Date().toISOString(),
  operational: { status: 'healthy' as const, uptime: 3600 },
  performance: { eventsPerMinute: 42 },
  errors: { errorRate: 0.5, circuitBreakerState: 'closed' as const },
  resources: { memoryMB: 128, cpuPercent: 15 },
  connection: { currentState: 'connected', connectionAttempts: 5, lastConnection: new Date().toISOString(), successfulConnections: 5, failedConnections: 0 },
  subscription: { isSubscribed: true, totalEvents: 12345, eventsPerMinute: 42, lastEvent: new Date().toISOString() },
  influxdb: { isConnected: true, lastWriteTime: new Date().toISOString(), writeErrors: 0 },
};

const mockConfig = {
  serviceId: 'websocket-ingestion',
  fetcher: vi.fn(),
  groups: [
    {
      title: 'Connection Status',
      metrics: [
        { key: 'connectionStatus', label: 'Connection Status', path: 'connection.currentState', type: 'status' as const },
      ],
    },
  ],
};

describe('ServiceMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetConfig.mockReturnValue(mockConfig as any);
  });

  it('should render loading state initially', () => {
    mockUseServiceMetrics.mockReturnValue({
      metrics: null,
      loading: true,
      error: null,
      lastUpdated: null,
      refresh: vi.fn(),
      clearCache: vi.fn(),
    });

    render(<ServiceMetrics serviceId="websocket-ingestion" darkMode={false} />);

    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
  });

  it('should render error state with retry button', () => {
    mockUseServiceMetrics.mockReturnValue({
      metrics: null,
      loading: false,
      error: 'Connection refused',
      lastUpdated: null,
      refresh: vi.fn(),
      clearCache: vi.fn(),
    });

    render(<ServiceMetrics serviceId="websocket-ingestion" darkMode={false} />);

    expect(screen.getByText('Error Loading Metrics')).toBeInTheDocument();
    expect(screen.getByText('Connection refused')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('should render metrics when available', () => {
    mockUseServiceMetrics.mockReturnValue({
      metrics: mockMetricsData as any,
      loading: false,
      error: null,
      lastUpdated: new Date(),
      refresh: vi.fn(),
      clearCache: vi.fn(),
    });

    render(<ServiceMetrics serviceId="websocket-ingestion" darkMode={false} />);

    expect(screen.getAllByText('Connection Status').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('should call refresh when refresh button clicked', async () => {
    const mockRefresh = vi.fn();
    mockUseServiceMetrics.mockReturnValue({
      metrics: mockMetricsData as any,
      loading: false,
      error: null,
      lastUpdated: new Date(),
      refresh: mockRefresh,
      clearCache: vi.fn(),
    });

    const user = userEvent.setup();
    render(<ServiceMetrics serviceId="websocket-ingestion" darkMode={false} />);

    await user.click(screen.getByText('Refresh'));
    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it('should show updating indicator during refresh', () => {
    mockUseServiceMetrics.mockReturnValue({
      metrics: mockMetricsData as any,
      loading: true,
      error: null,
      lastUpdated: new Date(),
      refresh: vi.fn(),
      clearCache: vi.fn(),
    });

    render(<ServiceMetrics serviceId="websocket-ingestion" darkMode={false} />);

    expect(screen.getByText('Updating...')).toBeInTheDocument();
    expect(screen.getByText('Refreshing...')).toBeInTheDocument();
  });
});
