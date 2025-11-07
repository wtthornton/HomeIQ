import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '../../tests/test-utils';

import { EnvironmentHealthCard } from '../EnvironmentHealthCard';
import { useEnvironmentHealth } from '../../hooks/useEnvironmentHealth';
import { HealthStatus, IntegrationStatus, EnvironmentHealth } from '../../types/health';

vi.mock('../../hooks/useEnvironmentHealth');

const mockUseEnvironmentHealth = vi.mocked(useEnvironmentHealth);

const baseHealth: EnvironmentHealth = {
  health_score: 95,
  ha_status: HealthStatus.HEALTHY,
  ha_version: '2025.10.0',
  integrations: [
    {
      name: 'MQTT',
      type: 'mqtt',
      status: IntegrationStatus.HEALTHY,
      is_configured: true,
      is_connected: true,
      error_message: undefined,
      last_check: new Date().toISOString(),
      check_details: {
        broker: 'mqtt.local',
        port: 1883
      }
    }
  ],
  performance: {
    response_time_ms: 12.5,
    cpu_usage_percent: 3.4,
    memory_usage_mb: 256,
    uptime_seconds: 3600
  },
  issues_detected: [],
  timestamp: new Date().toISOString()
};

describe('EnvironmentHealthCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading indicator while data is loading', () => {
    mockUseEnvironmentHealth.mockReturnValue({
      health: null,
      loading: true,
      error: null,
      refetch: vi.fn()
    });

    render(<EnvironmentHealthCard />);

    expect(screen.getByText(/Loading health status/i)).toBeTruthy();
  });

  it('renders error state when hook returns an error', () => {
    mockUseEnvironmentHealth.mockReturnValue({
      health: null,
      loading: false,
      error: 'Setup service error 500: Internal Server Error',
      refetch: vi.fn()
    });

    render(<EnvironmentHealthCard />);

    expect(screen.getByText(/Error Loading Health Status/i)).toBeTruthy();
    expect(screen.getByText(/Setup service error 500/i)).toBeTruthy();
  });

  it('renders integration details including check details for healthy data', () => {
    mockUseEnvironmentHealth.mockReturnValue({
      health: baseHealth,
      loading: false,
      error: null,
      refetch: vi.fn()
    });

    render(<EnvironmentHealthCard />);

    expect(screen.getByText(/Environment Health/i)).toBeTruthy();
    expect(screen.getByText('MQTT')).toBeTruthy();
    expect(screen.getByText(/Broker/i)).toBeTruthy();
    expect(screen.getByText('mqtt.local')).toBeTruthy();
    expect(screen.getByText(/port/i)).toBeTruthy();
    expect(screen.getByText('1883')).toBeTruthy();
    expect(screen.getAllByText(/healthy/i).length).toBeGreaterThan(0);
  });

  it('formats warning and error integration statuses correctly', () => {
    const mixedHealth: EnvironmentHealth = {
      ...baseHealth,
      ha_status: HealthStatus.WARNING,
      integrations: [
        {
          ...baseHealth.integrations[0],
          name: 'MQTT',
          status: IntegrationStatus.HEALTHY
        },
        {
          ...baseHealth.integrations[0],
          name: 'Zigbee2MQTT',
          status: IntegrationStatus.WARNING,
          check_details: { bridge_state: 'offline' }
        },
        {
          ...baseHealth.integrations[0],
          name: 'Data API',
          status: IntegrationStatus.ERROR,
          check_details: { error_message: 'timeout' }
        }
      ]
    };

    mockUseEnvironmentHealth.mockReturnValue({
      health: mixedHealth,
      loading: false,
      error: null,
      refetch: vi.fn()
    });

    render(<EnvironmentHealthCard />);

    expect(screen.getAllByText(/warning/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/error/i).length).toBeGreaterThan(0);
  });
});

