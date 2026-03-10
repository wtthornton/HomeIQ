/**
 * DevicePicker Component Tests
 * Story 44.4: Device picker coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DevicePicker } from '../DevicePicker';

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => {
        const { initial, animate, exit, transition, whileHover, whileTap, ...htmlProps } = props;
        return <div {...htmlProps}>{children}</div>;
      },
    },
  };
});

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

// Mock deviceApi
const mockListDevices = vi.fn();
const mockGetDevice = vi.fn();
const mockGetDeviceCapabilities = vi.fn();
vi.mock('../../../services/deviceApi', () => ({
  listDevices: (...args: unknown[]) => mockListDevices(...args),
  getDevice: (...args: unknown[]) => mockGetDevice(...args),
  getDeviceCapabilities: (...args: unknown[]) => mockGetDeviceCapabilities(...args),
  DeviceAPIError: class extends Error {
    status = 0;
  },
}));

const mockDevices = [
  {
    device_id: 'd1',
    name: 'Kitchen Light',
    manufacturer: 'Philips',
    model: 'Hue Bulb',
    area_id: 'kitchen',
    device_type: 'light',
    entity_count: 3,
    status: 'active' as const,
    timestamp: '2026-01-01',
  },
  {
    device_id: 'd2',
    name: 'Thermostat',
    manufacturer: 'Nest',
    model: 'Learning',
    area_id: 'living_room',
    device_type: 'thermostat',
    entity_count: 1,
    status: 'active' as const,
    timestamp: '2026-01-01',
  },
];

const defaultProps = {
  darkMode: false,
  selectedDeviceId: null,
  onSelectDevice: vi.fn(),
  isOpen: true,
  onToggle: vi.fn(),
};

describe('DevicePicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListDevices.mockResolvedValue({ devices: mockDevices, count: 2, limit: 100 });
    mockGetDevice.mockResolvedValue(mockDevices[0]);
    mockGetDeviceCapabilities.mockResolvedValue({ device_id: 'd1', capabilities: [] });
  });

  it('renders Select Device heading when open', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Select Device')).toBeInTheDocument();
    });
  });

  it('renders device list from API', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Kitchen Light')).toBeInTheDocument();
      // "Thermostat" appears both in device list and in device type dropdown option
      const items = screen.getAllByTestId('device-item');
      expect(items).toHaveLength(2);
    });
  });

  it('shows search input', async () => {
    render(<DevicePicker {...defaultProps} />);
    expect(screen.getByPlaceholderText('Search devices...')).toBeInTheDocument();
  });

  it('shows device type filter dropdown', async () => {
    render(<DevicePicker {...defaultProps} />);
    expect(screen.getByText('All Device Types')).toBeInTheDocument();
  });

  it('shows manufacturer and area info', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText(/Philips Hue Bulb/)).toBeInTheDocument();
      expect(screen.getByText(/kitchen/)).toBeInTheDocument();
    });
  });

  it('shows entity count', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('3 entities')).toBeInTheDocument();
      expect(screen.getByText('1 entity')).toBeInTheDocument();
    });
  });

  it('calls onSelectDevice and onToggle when device clicked', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      screen.getByText('Kitchen Light');
    });
    const items = screen.getAllByTestId('device-item');
    fireEvent.click(items[0]);
    expect(defaultProps.onSelectDevice).toHaveBeenCalledWith('d1');
    expect(defaultProps.onToggle).toHaveBeenCalled();
  });

  it('shows empty state when no devices', async () => {
    mockListDevices.mockResolvedValue({ devices: [], count: 0, limit: 100 });

    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('No devices available')).toBeInTheDocument();
    });
  });

  it('shows Clear Selection button when device selected', async () => {
    render(<DevicePicker {...defaultProps} selectedDeviceId="d1" />);
    await waitFor(() => {
      expect(screen.getByText('Clear Selection')).toBeInTheDocument();
    });
  });

  it('renders device list with correct aria roles', async () => {
    render(<DevicePicker {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: 'Devices' })).toBeInTheDocument();
    });
  });
});
