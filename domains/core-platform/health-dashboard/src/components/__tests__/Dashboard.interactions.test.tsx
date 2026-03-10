import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { Dashboard } from '../Dashboard';

describe('Dashboard User Interactions', () => {
  it('should toggle dark mode when theme button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Wait for dashboard to load
    await screen.findByTestId('dashboard-title');

    // Initially light mode (no dark class)
    expect(document.documentElement).not.toHaveClass('dark');

    // Find and click theme toggle using testid (desktop sidebar only)
    const themeToggle = screen.getByTestId('theme-toggle');
    await user.click(themeToggle);

    // Verify dark mode is applied
    expect(document.documentElement).toHaveClass('dark');

    // Click again to toggle back
    await user.click(themeToggle);

    // Verify light mode is restored
    expect(document.documentElement).not.toHaveClass('dark');
  });

  it('should toggle auto-refresh when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Wait for dashboard to load
    await screen.findByTestId('dashboard-title');

    // Find auto-refresh toggle using testid
    const autoRefreshToggle = screen.getByTestId('auto-refresh-toggle');
    expect(autoRefreshToggle).toBeInTheDocument();

    // Initially ON
    expect(autoRefreshToggle).toHaveAttribute('aria-label', 'Auto Refresh: ON');

    // Click to turn OFF
    await user.click(autoRefreshToggle);

    // Verify it changed to OFF
    await waitFor(() => {
      expect(autoRefreshToggle).toHaveAttribute('aria-label', 'Auto Refresh: OFF');
    });
  });

  it('should change time range when selector is used', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Wait for dashboard to load
    await screen.findByTestId('dashboard-title');

    // Find time range selector using testid
    const timeSelector = screen.getByTestId('time-range-selector');
    expect(timeSelector).toHaveValue('1h');

    // Change to 24h
    await user.selectOptions(timeSelector, '24h');

    // Verify selection changed
    expect(timeSelector).toHaveValue('24h');
  });

  it('should navigate through all main tabs', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Wait for dashboard to load
    await screen.findByTestId('dashboard-title');

    // Overview is a single-tab group, rendered as a direct button
    const overviewBtn = screen.getByRole('button', { name: /^Overview$/i });
    await user.click(overviewBtn);
    expect(overviewBtn.className).toContain('bg-primary');

    // For grouped nav items, we need to expand groups first then click sub-tabs
    // Expand Infrastructure group
    const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
    await user.click(infraGroup);

    // Click Services tab within Infrastructure group
    const servicesTab = screen.getByTestId('tab-services');
    await user.click(servicesTab);
    expect(servicesTab.className).toContain('bg-primary');

    // Expand Devices & Data group
    const devicesGroup = screen.getByRole('button', { name: /Devices & Data/i });
    await user.click(devicesGroup);

    // Click Devices tab
    const devicesTab = screen.getByTestId('tab-devices');
    await user.click(devicesTab);
    expect(devicesTab.className).toContain('bg-primary');
  });
});
