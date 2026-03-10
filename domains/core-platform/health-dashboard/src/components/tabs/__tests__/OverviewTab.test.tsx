import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../../../tests/test-utils';
import { OverviewTab } from '../OverviewTab';

// Mock all hooks used by OverviewTab
vi.mock('../../../hooks/useHealth', () => ({
  useHealth: vi.fn(() => ({
    health: { status: 'healthy' },
    loading: false,
    error: null,
    lastUpdated: new Date(),
    refresh: vi.fn(),
  })),
}));

vi.mock('../../../hooks/useStatistics', () => ({
  useStatistics: vi.fn(() => ({
    statistics: {
      metrics: {
        'websocket-ingestion': {
          events_per_minute: 42,
          error_rate: 0.01,
        },
      },
    },
    loading: false,
    error: null,
    lastUpdated: new Date(),
    refresh: vi.fn(),
  })),
}));

vi.mock('../../../hooks/useDataSources', () => ({
  useDataSources: vi.fn(() => ({
    dataSources: {
      weather: { status: 'healthy' },
      sports: { status: 'healthy' },
    },
    loading: false,
    error: null,
  })),
}));

vi.mock('../../../hooks/useAlerts', () => ({
  useAlerts: vi.fn(() => ({
    alerts: [],
    summary: null,
    loading: false,
    error: null,
    lastUpdate: new Date(),
    refresh: vi.fn(),
    acknowledgeAlert: vi.fn(),
    resolveAlert: vi.fn(),
  })),
}));

vi.mock('../../../hooks/usePerformanceHistory', () => ({
  usePerformanceHistory: vi.fn(() => ({
    history: [],
    stats: { min: 0, max: 100, avg: 50 },
  })),
}));

vi.mock('../../../hooks/useDevices', () => ({
  useDevices: vi.fn(() => ({
    devices: [],
    entities: [],
    integrations: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
  })),
}));

vi.mock('../../../hooks/useRAGStatus', () => ({
  useRAGStatus: vi.fn(() => ({
    ragStatus: { overall: 'green' },
    loading: false,
  })),
}));

vi.mock('../../../hooks/useActivity', () => ({
  useActivity: vi.fn(() => ({
    activity: null,
    loading: false,
    error: null,
    isStale: false,
    refresh: vi.fn(),
  })),
}));

// Mock services/api — the enhanced health resolves immediately
vi.mock('../../../services/api', () => ({
  apiService: {
    getEnhancedHealth: vi.fn().mockResolvedValue({
      status: 'healthy',
      metrics: { uptime_human: '3d 2h' },
      dependencies: [
        { name: 'InfluxDB', status: 'healthy', response_time_ms: 15 },
        { name: 'WebSocket Ingestion', status: 'healthy', response_time_ms: 10 },
      ],
    }),
    getContainers: vi.fn().mockResolvedValue([]),
  },
  dataApi: {
    getEventsStats: vi.fn().mockResolvedValue({
      total_events: 100,
      event_types: { state_changed: 80 },
      top_entities: [],
    }),
  },
}));

// Mock sub-components that are complex
vi.mock('../../SystemStatusHero', () => ({
  SystemStatusHero: ({ overallStatus, darkMode }: { overallStatus: string; darkMode: boolean }) => (
    <div data-testid="system-status-hero">System Status: {overallStatus}</div>
  ),
}));

vi.mock('../../CoreSystemCard', () => ({
  CoreSystemCard: () => <div data-testid="core-system-card">Core System Card</div>,
}));

vi.mock('../../PerformanceSparkline', () => ({
  PerformanceSparkline: () => <div data-testid="performance-sparkline">Sparkline</div>,
}));

vi.mock('../../ServiceDetailsModal', () => ({
  ServiceDetailsModal: () => null,
  ServiceDetail: {},
}));

vi.mock('../../IntegrationDetailsModal', () => ({
  IntegrationDetailsModal: () => null,
}));

vi.mock('../../RAGStatusCard', () => ({
  RAGStatusCard: ({ onClick }: { onClick: () => void }) => (
    <div data-testid="rag-status-card" onClick={onClick}>RAG Status</div>
  ),
}));

vi.mock('../../RAGDetailsModal', () => ({
  RAGDetailsModal: () => null,
}));

vi.mock('../../DataFreshnessIndicator', () => ({
  DataFreshnessIndicator: () => <div data-testid="data-freshness">Data Freshness</div>,
}));

vi.mock('../../skeletons', () => ({
  SkeletonCard: () => <div data-testid="skeleton-card">Loading...</div>,
}));

// Import mocked hooks for manipulation
import { useHealth } from '../../../hooks/useHealth';
import { useStatistics } from '../../../hooks/useStatistics';
import { useDevices } from '../../../hooks/useDevices';
import { apiService } from '../../../services/api';

const mockUseHealth = vi.mocked(useHealth);
const mockUseStatistics = vi.mocked(useStatistics);
const mockUseDevices = vi.mocked(useDevices);
const mockApiService = vi.mocked(apiService);

describe('OverviewTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Re-setup default mock for apiService since clearAllMocks resets it
    mockApiService.getEnhancedHealth.mockResolvedValue({
      status: 'healthy',
      metrics: { uptime_human: '3d 2h' },
      dependencies: [
        { name: 'InfluxDB', status: 'healthy', response_time_ms: 15 },
        { name: 'WebSocket Ingestion', status: 'healthy', response_time_ms: 10 },
      ],
    } as any);
    mockApiService.getContainers.mockResolvedValue([]);
  });

  it('renders system status hero after data loads', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByTestId('system-status-hero')).toBeInTheDocument();
    });
  });

  it('shows operational status when all systems healthy', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText(/System Status: operational/)).toBeInTheDocument();
    });
  });

  it('renders RAG status card', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByTestId('rag-status-card')).toBeInTheDocument();
    });
  });

  it('renders in dark mode without errors', async () => {
    render(<OverviewTab darkMode={true} />);
    await waitFor(() => {
      expect(screen.getByTestId('system-status-hero')).toBeInTheDocument();
    });
  });

  it('renders core system cards after data loads', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('core-system-card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  it('does not render performance sparkline when feature is disabled', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByTestId('system-status-hero')).toBeInTheDocument();
    });
    // PerformanceSparkline is currently behind a {false &&} guard
    expect(screen.queryByTestId('performance-sparkline')).not.toBeInTheDocument();
  });

  it('does not show critical alerts banner when no critical alerts', async () => {
    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByTestId('system-status-hero')).toBeInTheDocument();
    });
    expect(screen.queryByText(/Critical Alert/i)).not.toBeInTheDocument();
  });

  it('shows degraded status when health endpoint has error', async () => {
    mockUseHealth.mockReturnValue({
      health: null,
      loading: false,
      error: 'Connection refused',
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);

    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText(/System Status: degraded/)).toBeInTheDocument();
    });
  });

  it('shows error details when health endpoint fails', async () => {
    mockUseHealth.mockReturnValue({
      health: null,
      loading: false,
      error: 'Connection refused',
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);

    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText(/Backend unavailable/)).toBeInTheDocument();
    });
  });

  it('shows Retry button when errors exist', async () => {
    mockUseHealth.mockReturnValue({
      health: null,
      loading: false,
      error: 'Connection refused',
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);

    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      const retryButtons = screen.getAllByText('Retry');
      expect(retryButtons.length).toBeGreaterThan(0);
    });
  });

  it('shows loading skeleton when initial data is loading', () => {
    mockUseHealth.mockReturnValue({
      health: null,
      loading: true,
      error: null,
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);
    mockUseStatistics.mockReturnValue({
      statistics: null,
      loading: true,
      error: null,
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);
    // Make the enhanced health never resolve
    mockApiService.getEnhancedHealth.mockReturnValue(new Promise(() => {}));

    render(<OverviewTab darkMode={false} />);
    const skeletons = screen.getAllByTestId('skeleton-card');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows degraded status when statistics endpoint fails', async () => {
    mockUseStatistics.mockReturnValue({
      statistics: null,
      loading: false,
      error: 'Stats unavailable',
      lastUpdated: null,
      refresh: vi.fn(),
    } as any);

    render(<OverviewTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText(/System Status: degraded/)).toBeInTheDocument();
    });
  });
});
