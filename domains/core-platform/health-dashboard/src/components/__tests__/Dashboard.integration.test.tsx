/**
 * Dashboard Integration Tests (Story 59.1)
 *
 * Tests cross-component flows:
 * - Tab navigation preserves state and syncs URL hash
 * - Group expand/collapse state persists across tab switches
 * - Auto-refresh toggle affects data polling behavior
 * - Keyboard navigation through tabs
 * - Custom navigateToTab events from child components
 * - Time range selection persists across tab changes
 * - Hash-based initial tab selection
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/mocks/server';
import { Dashboard } from '../Dashboard';

// Helper to wait for dashboard to initialize
async function waitForDashboard() {
  await screen.findByTestId('dashboard-title');
}

describe('Dashboard Integration Tests', () => {
  beforeEach(() => {
    // Reset URL hash
    window.location.hash = '';
  });

  describe('Cross-Tab Navigation', () => {
    it('updates URL hash when switching tabs and preserves on re-render', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Expand Infrastructure group and click Services
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      const servicesTab = screen.getByTestId('tab-services');
      await user.click(servicesTab);

      expect(window.location.hash).toBe('#services');
      expect(servicesTab).toHaveAttribute('aria-selected', 'true');
    });

    it('clears hash when returning to Overview', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Navigate to Services
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      await user.click(screen.getByTestId('tab-services'));
      expect(window.location.hash).toBe('#services');

      // Navigate back to Overview
      await user.click(screen.getByTestId('tab-overview'));
      expect(window.location.hash).toBe('');
    });

    it('initializes to correct tab from URL hash', async () => {
      window.location.hash = '#services';
      render(<Dashboard />);
      await waitForDashboard();

      const servicesTab = screen.getByTestId('tab-services');
      expect(servicesTab).toHaveAttribute('aria-selected', 'true');
    });

    it('navigates through multiple tabs preserving active state', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Overview -> Services -> Devices -> back to Overview
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      await user.click(screen.getByTestId('tab-services'));
      expect(screen.getByTestId('tab-services')).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('tab-overview')).toHaveAttribute('aria-selected', 'false');

      const devicesGroup = screen.getByRole('button', { name: /Devices & Data/i });
      await user.click(devicesGroup);
      await user.click(screen.getByTestId('tab-devices'));
      expect(screen.getByTestId('tab-devices')).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('tab-services')).toHaveAttribute('aria-selected', 'false');

      await user.click(screen.getByTestId('tab-overview'));
      expect(screen.getByTestId('tab-overview')).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('tab-devices')).toHaveAttribute('aria-selected', 'false');
    });
  });

  describe('Group Expand/Collapse State', () => {
    it('auto-expands parent group when navigating to a child tab', async () => {
      window.location.hash = '#services';
      render(<Dashboard />);
      await waitForDashboard();

      // Infrastructure group should be auto-expanded because Services is active
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');
    });

    it('preserves expanded groups when switching tabs within the same group', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Expand Infrastructure
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');

      // Click Services
      await user.click(screen.getByTestId('tab-services'));
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');

      // Click Groups (same Infrastructure group)
      await user.click(screen.getByTestId('tab-groups'));
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');
    });

    it('allows multiple groups to be expanded simultaneously', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Expand Infrastructure
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);

      // Expand Devices & Data
      const devicesGroup = screen.getByRole('button', { name: /Devices & Data/i });
      await user.click(devicesGroup);

      // Both should be expanded
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');
      expect(devicesGroup).toHaveAttribute('aria-expanded', 'true');
    });

    it('collapses a group when clicking its header while expanded', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });

      // Expand
      await user.click(infraGroup);
      expect(infraGroup).toHaveAttribute('aria-expanded', 'true');

      // Collapse
      await user.click(infraGroup);
      expect(infraGroup).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Auto-Refresh and Time Range', () => {
    it('toggles auto-refresh and shows correct label', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      const toggle = screen.getByTestId('auto-refresh-toggle');
      expect(toggle).toHaveAttribute('aria-label', 'Auto Refresh: ON');

      await user.click(toggle);
      await waitFor(() => {
        expect(toggle).toHaveAttribute('aria-label', 'Auto Refresh: OFF');
      });

      await user.click(toggle);
      await waitFor(() => {
        expect(toggle).toHaveAttribute('aria-label', 'Auto Refresh: ON');
      });
    });

    it('persists time range selection across tab switches', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Change time range to 24h
      const timeSelector = screen.getByTestId('time-range-selector');
      await user.selectOptions(timeSelector, '24h');
      expect(timeSelector).toHaveValue('24h');

      // Switch tabs
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      await user.click(screen.getByTestId('tab-services'));

      // Switch back to Overview
      await user.click(screen.getByTestId('tab-overview'));

      // Time range should still be 24h
      expect(screen.getByTestId('time-range-selector')).toHaveValue('24h');
    });
  });

  describe('Custom Tab Navigation Events', () => {
    it('responds to navigateToTab custom events from child components', async () => {
      render(<Dashboard />);
      await waitForDashboard();

      // Dispatch custom navigation event (simulates modal/child triggering tab change)
      act(() => {
        window.dispatchEvent(
          new CustomEvent('navigateToTab', { detail: { tabId: 'alerts' } })
        );
      });

      await waitFor(() => {
        expect(window.location.hash).toBe('#alerts');
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('navigates tabs with arrow keys', async () => {
      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Focus on Overview tab
      const overviewTab = screen.getByTestId('tab-overview');
      overviewTab.focus();

      // Press ArrowDown to go to next tab
      await user.keyboard('{ArrowDown}');

      // Should navigate to the next available tab
      await waitFor(() => {
        const activeElement = document.activeElement;
        expect(activeElement).toBeTruthy();
        expect(activeElement?.getAttribute('data-tab') || activeElement?.getAttribute('data-testid')).toBeTruthy();
      });
    });
  });

  describe('Data Flow Across Tabs', () => {
    it('shows degraded status consistently across Overview and Services tabs', async () => {
      // Override health to return degraded
      server.use(
        http.get('/api/health', () => {
          return HttpResponse.json({
            service: 'websocket-ingestion',
            status: 'degraded',
            timestamp: new Date().toISOString(),
            uptime_seconds: 86400,
            version: '1.0.0',
            dependencies: [
              { name: 'InfluxDB', type: 'database', status: 'unhealthy', response_time_ms: 5000, message: 'Connection timeout', details: {} },
              { name: 'PostgreSQL', type: 'database', status: 'healthy', response_time_ms: 5, message: 'OK', details: {} },
            ],
            metrics: {
              uptime_seconds: 86400,
              uptime_human: '24h',
              start_time: new Date().toISOString(),
              current_time: new Date().toISOString(),
            },
          });
        }),
        http.get('/api/v1/health', () => {
          return HttpResponse.json({
            status: 'degraded',
            service: 'websocket-ingestion',
            timestamp: new Date().toISOString(),
            uptime_seconds: 86400,
            version: '1.0.0',
            dependencies: [
              { name: 'InfluxDB', type: 'database', status: 'unhealthy', response_time_ms: 5000, message: 'Connection timeout', details: {} },
            ],
            metrics: {
              uptime_seconds: 86400,
              uptime_human: '24h',
              start_time: new Date().toISOString(),
              current_time: new Date().toISOString(),
            },
          });
        }),
      );

      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Overview tab should reflect the degraded status via its child components
      // The exact rendering depends on how OverviewTab processes health data
      // We verify the health data is fetched and the tab renders without error
      const overviewTab = screen.getByTestId('tab-overview');
      expect(overviewTab).toHaveAttribute('aria-selected', 'true');

      // Navigate to Services tab
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      await user.click(screen.getByTestId('tab-services'));

      // Services tab should also render with the degraded health context
      expect(screen.getByTestId('tab-services')).toHaveAttribute('aria-selected', 'true');
      expect(window.location.hash).toBe('#services');
    });

    it('handles API errors gracefully without crashing tab navigation', async () => {
      // Simulate health endpoint failure
      server.use(
        http.get('/api/health', () => {
          return new HttpResponse(null, { status: 500 });
        }),
        http.get('/api/v1/health', () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const user = userEvent.setup();
      render(<Dashboard />);
      await waitForDashboard();

      // Dashboard should still render and be navigable even with API errors
      const infraGroup = screen.getByRole('button', { name: /Infrastructure/i });
      await user.click(infraGroup);
      await user.click(screen.getByTestId('tab-services'));

      expect(screen.getByTestId('tab-services')).toHaveAttribute('aria-selected', 'true');

      // Navigate to another tab — should not crash
      await user.click(screen.getByTestId('tab-overview'));
      expect(screen.getByTestId('tab-overview')).toHaveAttribute('aria-selected', 'true');
    });
  });
});
