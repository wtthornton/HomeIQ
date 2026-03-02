import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../tests/test-utils';
import { AlertsPanel } from '../AlertsPanel';

// Mock the useAlerts hook
vi.mock('../../hooks/useAlerts', () => ({
  useAlerts: vi.fn(() => ({
    alerts: [
      {
        id: '1',
        name: 'High CPU',
        severity: 'critical',
        status: 'active',
        message: 'CPU usage above 90%',
        service: 'data-api',
        created_at: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'Disk Space',
        severity: 'warning',
        status: 'active',
        message: 'Disk usage above 80%',
        service: 'websocket-ingestion',
        created_at: new Date().toISOString(),
      },
    ],
    summary: { critical: 1, warning: 1, info: 0, total_active: 2, total_alerts: 2, alert_history_count: 5 },
    loading: false,
    error: null,
    lastUpdate: new Date(),
    refresh: vi.fn(),
    acknowledgeAlert: vi.fn().mockResolvedValue(true),
    resolveAlert: vi.fn().mockResolvedValue(true),
  })),
}));

describe('AlertsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the alert management heading', () => {
    render(<AlertsPanel darkMode={false} />);
    expect(screen.getByText(/Alert Management/)).toBeInTheDocument();
  });

  it('displays the correct number of filtered alerts', () => {
    render(<AlertsPanel darkMode={false} />);
    expect(screen.getByText('Alerts (2)')).toBeInTheDocument();
  });

  it('renders alert cards for each alert', () => {
    render(<AlertsPanel darkMode={false} />);
    expect(screen.getByText('CPU usage above 90%')).toBeInTheDocument();
    expect(screen.getByText('Disk usage above 80%')).toBeInTheDocument();
  });

  it('renders the refresh button', () => {
    render(<AlertsPanel darkMode={false} />);
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });
});
