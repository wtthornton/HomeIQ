import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { Dashboard } from '../Dashboard';

describe('Dashboard Component', () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders the dashboard title', async () => {
    render(<Dashboard />);
    expect(await screen.findByTestId('dashboard-title')).toHaveTextContent('HomeIQ Health');
  });

  it('renders the sidebar navigation', async () => {
    render(<Dashboard />);
    expect(screen.getByLabelText('Dashboard navigation')).toBeInTheDocument();
  });

  it('renders the theme toggle button', async () => {
    render(<Dashboard />);
    const toggle = screen.getByTestId('theme-toggle');
    expect(toggle).toBeInTheDocument();
  });

  it('toggles dark mode when theme button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    const toggle = screen.getByTestId('theme-toggle');
    await user.click(toggle);

    expect(document.documentElement).toHaveClass('dark');
  });

  it('renders the auto-refresh toggle', async () => {
    render(<Dashboard />);
    const toggle = screen.getByTestId('auto-refresh-toggle');
    expect(toggle).toBeInTheDocument();
  });

  it('switches tab when a navigation item is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Expand the Infrastructure group
    const infraButton = screen.getByText('Infrastructure');
    await user.click(infraButton);

    // Click the Services tab
    const servicesTab = screen.getByTestId('tab-services');
    await user.click(servicesTab);

    // Verify URL hash updated
    expect(window.location.hash).toBe('#services');
  });

  it('renders the skip-to-content link for accessibility', () => {
    render(<Dashboard />);
    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
  });
});
