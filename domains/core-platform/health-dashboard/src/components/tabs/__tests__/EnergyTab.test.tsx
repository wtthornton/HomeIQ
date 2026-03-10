import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../../../tests/test-utils';
import { EnergyTab } from '../EnergyTab';

vi.mock('../../../services/api', () => ({
  dataApi: {
    getEnergyStatistics: vi.fn(),
    getEnergyCorrelations: vi.fn(),
    getTopEnergyConsumers: vi.fn(),
  },
}));

import { dataApi } from '../../../services/api';

const mockDataApi = vi.mocked(dataApi);

const mockStatistics = {
  current_power_w: 1250,
  daily_kwh: 18.5,
  peak_power_w: 3200,
  peak_time: '2025-01-01T14:00:00Z',
  average_power_w: 900,
  total_correlations: 42,
};

const mockCorrelations = [
  {
    timestamp: '2025-01-01T12:00:00Z',
    entity_id: 'switch.living_room',
    domain: 'switch',
    state: 'on',
    previous_state: 'off',
    power_before_w: 800,
    power_after_w: 1200,
    power_delta_w: 400,
    power_delta_pct: 50,
  },
];

const mockConsumers = [
  {
    entity_id: 'climate.thermostat',
    domain: 'climate',
    average_power_on_w: 1500,
    average_power_off_w: 0,
    total_state_changes: 24,
    estimated_daily_kwh: 12.5,
    estimated_monthly_cost: 45.0,
  },
];

describe('EnergyTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDataApi.getEnergyStatistics.mockResolvedValue(mockStatistics as any);
    mockDataApi.getEnergyCorrelations.mockResolvedValue(mockCorrelations as any);
    mockDataApi.getTopEnergyConsumers.mockResolvedValue(mockConsumers as any);
  });

  it('shows loading state initially', () => {
    mockDataApi.getEnergyStatistics.mockReturnValue(new Promise(() => {}));
    mockDataApi.getEnergyCorrelations.mockReturnValue(new Promise(() => {}));
    mockDataApi.getTopEnergyConsumers.mockReturnValue(new Promise(() => {}));

    render(<EnergyTab darkMode={false} />);
    expect(screen.getByText('Loading energy data...')).toBeInTheDocument();
  });

  it('renders heading after data loads', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('Energy Monitoring & Correlations')).toBeInTheDocument();
    });
  });

  it('displays current power statistic', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('1250W')).toBeInTheDocument();
    });
  });

  it('displays daily energy statistic', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('18.5 kWh')).toBeInTheDocument();
    });
  });

  it('displays correlations count', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });

  it('shows error state on fetch failure', async () => {
    mockDataApi.getEnergyStatistics.mockRejectedValue(new Error('API down'));
    mockDataApi.getEnergyCorrelations.mockRejectedValue(new Error('API down'));
    mockDataApi.getTopEnergyConsumers.mockRejectedValue(new Error('API down'));

    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText(/Error: API down/)).toBeInTheDocument();
    });
  });

  it('displays top energy consumers section', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('Top Energy Consumers (Last 7 Days)')).toBeInTheDocument();
      expect(screen.getByText(/climate.thermostat/)).toBeInTheDocument();
    });
  });

  it('shows refresh button', async () => {
    render(<EnergyTab darkMode={false} />);
    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
  });
});
