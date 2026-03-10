import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { ConfigurationTab } from '../ConfigurationTab';

// Mock child components
vi.mock('../../ThresholdConfig', () => ({
  ThresholdConfig: ({ darkMode }: { darkMode: boolean }) => (
    <div data-testid="threshold-config">Threshold Config</div>
  ),
}));

vi.mock('../../ServiceControl', () => ({
  ServiceControl: () => <div data-testid="service-control">Service Control</div>,
}));

vi.mock('../../ConfigForm', () => ({
  ConfigForm: ({ service }: { service: string }) => (
    <div data-testid={`config-form-${service}`}>Config Form: {service}</div>
  ),
}));

vi.mock('../../ContainerManagement', () => ({
  ContainerManagement: () => <div data-testid="container-management">Container Management</div>,
}));

vi.mock('../../APIKeyManagement', () => ({
  APIKeyManagement: () => <div data-testid="api-key-management">API Key Management</div>,
}));

describe('ConfigurationTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the main configuration view', () => {
    render(<ConfigurationTab darkMode={false} />);
    expect(screen.getByText(/Integration Configuration/)).toBeInTheDocument();
  });

  it('renders threshold config section', () => {
    render(<ConfigurationTab darkMode={false} />);
    expect(screen.getByTestId('threshold-config')).toBeInTheDocument();
  });

  it('renders service control section', () => {
    render(<ConfigurationTab darkMode={false} />);
    expect(screen.getByTestId('service-control')).toBeInTheDocument();
  });

  it('shows all configuration cards', () => {
    render(<ConfigurationTab darkMode={false} />);
    expect(screen.getByText('Container Management')).toBeInTheDocument();
    expect(screen.getByText('API Key Management')).toBeInTheDocument();
    expect(screen.getByText('Home Assistant')).toBeInTheDocument();
    expect(screen.getByText('Weather API')).toBeInTheDocument();
    expect(screen.getByText('InfluxDB')).toBeInTheDocument();
  });

  it('navigates to websocket config when Home Assistant clicked', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('Home Assistant'));
    expect(screen.getByTestId('config-form-websocket')).toBeInTheDocument();
  });

  it('navigates to weather config when Weather API clicked', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('Weather API'));
    expect(screen.getByTestId('config-form-weather')).toBeInTheDocument();
  });

  it('navigates to influxdb config when InfluxDB clicked', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('InfluxDB'));
    expect(screen.getByTestId('config-form-influxdb')).toBeInTheDocument();
  });

  it('navigates to container management', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('Container Management'));
    expect(screen.getByTestId('container-management')).toBeInTheDocument();
  });

  it('navigates to API key management', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('API Key Management'));
    expect(screen.getByTestId('api-key-management')).toBeInTheDocument();
  });

  it('shows back button and returns to main view', async () => {
    const user = userEvent.setup();
    render(<ConfigurationTab darkMode={false} />);

    await user.click(screen.getByText('Home Assistant'));
    expect(screen.getByTestId('config-form-websocket')).toBeInTheDocument();

    await user.click(screen.getByText(/Back to Configuration/));
    expect(screen.getByText(/Integration Configuration/)).toBeInTheDocument();
  });
});
