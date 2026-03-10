import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import { ServicesTab } from '../ServicesTab';

// The ServicesTab in tabs/ is a thin wrapper around ../ServicesTab
// Mock the actual ServicesTab component
vi.mock('../../ServicesTab', () => ({
  ServicesTab: ({ darkMode }: { darkMode: boolean }) => (
    <div data-testid="services-tab-inner" data-dark={darkMode}>
      <h2>Service Health Monitor</h2>
      <div data-testid="service-list">
        <div>websocket-ingestion: running</div>
        <div>data-api: running</div>
        <div>admin-api: degraded</div>
      </div>
    </div>
  ),
}));

describe('ServicesTab (wrapper)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the inner ServicesTab component', () => {
    render(<ServicesTab darkMode={false} />);
    expect(screen.getByTestId('services-tab-inner')).toBeInTheDocument();
  });

  it('passes darkMode prop to inner component', () => {
    render(<ServicesTab darkMode={true} />);
    expect(screen.getByTestId('services-tab-inner')).toHaveAttribute('data-dark', 'true');
  });

  it('renders service list', () => {
    render(<ServicesTab darkMode={false} />);
    expect(screen.getByTestId('service-list')).toBeInTheDocument();
  });

  it('displays service names', () => {
    render(<ServicesTab darkMode={false} />);
    expect(screen.getByText(/websocket-ingestion/)).toBeInTheDocument();
    expect(screen.getByText(/data-api/)).toBeInTheDocument();
  });

  it('shows heading', () => {
    render(<ServicesTab darkMode={false} />);
    expect(screen.getByText('Service Health Monitor')).toBeInTheDocument();
  });

  it('renders in light mode without errors', () => {
    render(<ServicesTab darkMode={false} />);
    expect(screen.getByTestId('services-tab-inner')).toHaveAttribute('data-dark', 'false');
  });
});
