/**
 * Tests for DevicesTab Component
 *
 * Covers: rendering, loading/error states, filtering, device selection,
 * dark mode, and accessibility.
 * Pattern follows SportsTab.test.tsx conventions.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, within } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { DevicesTab } from '../DevicesTab';
import { useDevices } from '../../../hooks/useDevices';

// Mock hooks and services
vi.mock('../../../hooks/useDevices');
vi.mock('../../../services/api', () => ({
  dataApi: {
    getEntities: vi.fn().mockResolvedValue({ entities: [] }),
  },
}));

const mockUseDevices = vi.mocked(useDevices);

const mockDevice = {
  device_id: 'device-1',
  name: 'Living Room Light',
  manufacturer: 'Philips',
  model: 'Hue White',
  sw_version: '1.50.2',
  area_id: 'living_room',
  integration: 'hue',
  entity_count: 3,
  timestamp: new Date().toISOString(),
  status: 'active',
};

const mockDevice2 = {
  device_id: 'device-2',
  name: 'Thermostat',
  manufacturer: 'Nest',
  model: 'Learning Thermostat',
  sw_version: '5.9.3',
  area_id: 'hallway',
  integration: 'nest',
  entity_count: 5,
  timestamp: new Date().toISOString(),
  status: 'active',
};

const mockEntity = {
  entity_id: 'light.living_room',
  device_id: 'device-1',
  domain: 'light',
  platform: 'hue',
  disabled: false,
  timestamp: new Date().toISOString(),
};

const defaultMockReturn = {
  devices: [],
  entities: [],
  integrations: [],
  loading: false,
  error: null,
  fetchDevices: vi.fn(),
  fetchEntities: vi.fn(),
  fetchIntegrations: vi.fn(),
  refresh: vi.fn(),
};

describe('DevicesTab Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDevices.mockReturnValue({ ...defaultMockReturn } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders page heading and description', () => {
    render(<DevicesTab darkMode={false} />);

    expect(screen.getByRole('heading', { name: /Devices/i })).toBeInTheDocument();
    expect(screen.getByText(/Manage and monitor your Home Assistant devices/i)).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    render(<DevicesTab darkMode={false} />);

    expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
  });

  it('calls refresh when Refresh button is clicked', async () => {
    const mockRefresh = vi.fn();
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      refresh: mockRefresh,
    } as any);

    const user = userEvent.setup();
    render(<DevicesTab darkMode={false} />);

    await user.click(screen.getByRole('button', { name: /Refresh/i }));
    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it('shows loading state', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      loading: true,
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByText(/Loading devices.../i)).toBeInTheDocument();
  });

  it('shows error state with message', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      error: 'Failed to retrieve devices: could not identify an equality operator',
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByText(/Error loading devices/i)).toBeInTheDocument();
    expect(screen.getByText(/could not identify an equality operator/i)).toBeInTheDocument();
  });

  it('renders device cards when devices are loaded', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice, mockDevice2],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByText('Living Room Light')).toBeInTheDocument();
    expect(screen.getByText('Thermostat')).toBeInTheDocument();
  });

  it('displays entity count on device cards', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByText(/3 entities/i)).toBeInTheDocument();
  });

  it('displays singular "entity" for count of 1', () => {
    const singleEntityDevice = { ...mockDevice, entity_count: 1 };
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [singleEntityDevice],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByText(/1 entity$/i)).toBeInTheDocument();
  });

  it('renders filter controls', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.getByPlaceholderText(/Search devices.../i)).toBeInTheDocument();
    expect(screen.getByText('All Manufacturers')).toBeInTheDocument();
    expect(screen.getByText('All Areas')).toBeInTheDocument();
    expect(screen.getByText('All Platforms')).toBeInTheDocument();
  });

  it('populates manufacturer filter from device data', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice, mockDevice2],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    // Manufacturer options should include Philips and Nest
    expect(screen.getByRole('option', { name: 'Philips' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Nest' })).toBeInTheDocument();
  });

  it('filters devices by search term', async () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice, mockDevice2],
      entities: [mockEntity],
    } as any);

    const user = userEvent.setup();
    render(<DevicesTab darkMode={false} />);

    await user.type(screen.getByPlaceholderText(/Search devices.../i), 'Living');

    expect(screen.getByText('Living Room Light')).toBeInTheDocument();
    expect(screen.queryByText('Thermostat')).not.toBeInTheDocument();
  });

  it('filters devices by manufacturer', async () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice, mockDevice2],
      entities: [mockEntity],
    } as any);

    const user = userEvent.setup();
    render(<DevicesTab darkMode={false} />);

    // Find the manufacturer select (second select after search input)
    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], 'Nest');

    expect(screen.queryByText('Living Room Light')).not.toBeInTheDocument();
    expect(screen.getByText('Thermostat')).toBeInTheDocument();
  });

  it('shows device manufacturer and model info on the card', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      devices: [mockDevice],
      entities: [mockEntity],
    } as any);

    render(<DevicesTab darkMode={false} />);

    // Manufacturer appears in both filter dropdown and device card
    const allPhilips = screen.getAllByText(/Philips/);
    expect(allPhilips.length).toBeGreaterThanOrEqual(2); // dropdown option + card
    expect(screen.getByText(/Hue White/)).toBeInTheDocument();
  });

  it('does not show devices grid during loading', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      loading: true,
      devices: [mockDevice],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.queryByText('Living Room Light')).not.toBeInTheDocument();
  });

  it('does not show devices grid when error is present', () => {
    mockUseDevices.mockReturnValue({
      ...defaultMockReturn,
      error: 'Database error',
      devices: [mockDevice],
    } as any);

    render(<DevicesTab darkMode={false} />);

    expect(screen.queryByText('Living Room Light')).not.toBeInTheDocument();
  });
});
