import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { Dashboard } from '../Dashboard';

describe('Dashboard User Interactions', () => {
  it('should toggle dark mode when theme button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);
    
    // Wait for dashboard to load (use heading role)
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });
    
    // Initially light mode (no dark class)
    expect(document.documentElement).not.toHaveClass('dark');
    
    // Find and click theme toggle
    const themeToggle = screen.getByTitle(/Switch to Dark Mode/i);
    await user.click(themeToggle);
    
    // Verify dark mode is applied
    expect(document.documentElement).toHaveClass('dark');
    
    // Click again to toggle back
    const lightModeToggle = screen.getByTitle(/Switch to Light Mode/i);
    await user.click(lightModeToggle);
    
    // Verify light mode is restored
    expect(document.documentElement).not.toHaveClass('dark');
  });

  it('should toggle auto-refresh when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);
    
    // Wait for dashboard to load
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });
    
    // Find auto-refresh toggle (initially ON)
    const autoRefreshToggle = screen.getByTitle(/Auto Refresh: ON/i);
    expect(autoRefreshToggle).toBeInTheDocument();
    
    // Click to turn OFF
    await user.click(autoRefreshToggle);
    
    // Verify it changed to OFF
    await waitFor(() => {
      expect(screen.getByTitle(/Auto Refresh: OFF/i)).toBeInTheDocument();
    });
  });

  it('should change time range when selector is used', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);
    
    // Wait for dashboard to load
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });
    
    // Find time range selector
    const timeSelector = screen.getByRole('combobox', { name: /Select time range/i });
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
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });
    
    // Test navigating to each tab
    const tabs = [
      'Overview',
      'Setup',
      'Services',
      'Dependencies',
      'Devices',
      'Events',
      'Logs',
      'Sports',
    ];
    
    for (const tabName of tabs) {
      const tab = screen.getByRole('button', { name: new RegExp(tabName, 'i') });
      await user.click(tab);

      // Verify tab is active (has blue background class in light mode)
      expect(tab).toHaveClass('bg-blue-100');
    }
  });
});

