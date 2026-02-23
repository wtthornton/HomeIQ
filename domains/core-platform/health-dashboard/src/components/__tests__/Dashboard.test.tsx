import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { Dashboard } from '../Dashboard';

describe('Dashboard Component', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('displays dashboard heading when component loads', async () => {
    render(<Dashboard />);
    
    // Wait for dashboard title to appear (use heading role to be specific)
    expect(await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i })).toBeInTheDocument();
  });

  it('switches active tab when navigation button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    // Wait for dashboard to load
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });

    // Find and click the Services tab
    const servicesTab = screen.getByRole('button', { name: /Services/i });
    await user.click(servicesTab);

    // Verify the tab is now active (has blue background class in light mode)
    expect(servicesTab).toHaveClass('bg-blue-100');
  });

  it('toggles dark mode when theme button is clicked', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);
    
    // Wait for dashboard to load
    await screen.findByRole('heading', { name: /HA Ingestor Dashboard/i });
    
    // Find theme toggle button
    const themeToggle = screen.getByTitle(/Switch to Dark Mode/i);
    await user.click(themeToggle);
    
    // Verify dark mode is applied to document
    expect(document.documentElement).toHaveClass('dark');
  });
});

