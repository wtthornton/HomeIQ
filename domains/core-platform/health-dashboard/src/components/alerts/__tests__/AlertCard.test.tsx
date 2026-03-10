import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { AlertCard } from '../AlertCard';
import type { Alert } from '../../../types/alerts';

const mockAlert: Alert = {
  id: 'alert-1',
  name: 'High CPU',
  severity: 'critical',
  status: 'active',
  message: 'CPU usage above 90%',
  service: 'data-api',
  created_at: new Date().toISOString(),
  metadata: { cpu_percent: 95 },
};

describe('AlertCard', () => {
  const mockAcknowledge = vi.fn();
  const mockResolve = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders alert message', () => {
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.getByText('CPU usage above 90%')).toBeInTheDocument();
  });

  it('renders service name', () => {
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.getByText(/Service: data-api/)).toBeInTheDocument();
  });

  it('shows Acknowledge and Resolve buttons for active alerts', () => {
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.getByText('Acknowledge')).toBeInTheDocument();
    expect(screen.getByText('Resolve')).toBeInTheDocument();
  });

  it('calls onAcknowledge when Acknowledge clicked', async () => {
    const user = userEvent.setup();
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );

    await user.click(screen.getByText('Acknowledge'));
    expect(mockAcknowledge).toHaveBeenCalledWith('alert-1');
  });

  it('calls onResolve when Resolve clicked', async () => {
    const user = userEvent.setup();
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );

    await user.click(screen.getByText('Resolve'));
    expect(mockResolve).toHaveBeenCalledWith('alert-1');
  });

  it('only shows Resolve for acknowledged alerts', () => {
    const acknowledgedAlert: Alert = { ...mockAlert, status: 'acknowledged' };
    render(
      <AlertCard
        alert={acknowledgedAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
    expect(screen.getByText('Resolve')).toBeInTheDocument();
  });

  it('shows no action buttons for resolved alerts', () => {
    const resolvedAlert: Alert = { ...mockAlert, status: 'resolved' };
    render(
      <AlertCard
        alert={resolvedAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
    expect(screen.queryByText('Resolve')).not.toBeInTheDocument();
  });

  it('displays metadata when present', () => {
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={false}
      />
    );
    expect(screen.getByText(/cpu_percent/)).toBeInTheDocument();
  });

  it('renders in dark mode', () => {
    render(
      <AlertCard
        alert={mockAlert}
        onAcknowledge={mockAcknowledge}
        onResolve={mockResolve}
        darkMode={true}
      />
    );
    expect(screen.getByText('CPU usage above 90%')).toBeInTheDocument();
  });
});
