import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import { GroupsTab } from '../GroupsTab';

// The GroupsTab in tabs/ is a thin wrapper around ../GroupsTab
// Mock the actual GroupsTab component
vi.mock('../../GroupsTab', () => ({
  GroupsTab: ({ darkMode }: { darkMode: boolean }) => (
    <div data-testid="groups-tab-inner" data-dark={darkMode}>
      <h2>Domain Groups</h2>
      <div data-testid="group-list">
        <div>core-platform: 6 services</div>
        <div>data-collectors: 8 services</div>
        <div>ml-engine: 3 services</div>
      </div>
    </div>
  ),
}));

describe('GroupsTab (wrapper)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the inner GroupsTab component', () => {
    render(<GroupsTab darkMode={false} />);
    expect(screen.getByTestId('groups-tab-inner')).toBeInTheDocument();
  });

  it('passes darkMode prop to inner component', () => {
    render(<GroupsTab darkMode={true} />);
    expect(screen.getByTestId('groups-tab-inner')).toHaveAttribute('data-dark', 'true');
  });

  it('renders group list', () => {
    render(<GroupsTab darkMode={false} />);
    expect(screen.getByTestId('group-list')).toBeInTheDocument();
  });

  it('displays group names', () => {
    render(<GroupsTab darkMode={false} />);
    expect(screen.getByText(/core-platform/)).toBeInTheDocument();
    expect(screen.getByText(/data-collectors/)).toBeInTheDocument();
    expect(screen.getByText(/ml-engine/)).toBeInTheDocument();
  });

  it('shows heading', () => {
    render(<GroupsTab darkMode={false} />);
    expect(screen.getByText('Domain Groups')).toBeInTheDocument();
  });

  it('renders in light mode', () => {
    render(<GroupsTab darkMode={false} />);
    expect(screen.getByTestId('groups-tab-inner')).toHaveAttribute('data-dark', 'false');
  });

  it('renders in dark mode', () => {
    render(<GroupsTab darkMode={true} />);
    expect(screen.getByTestId('groups-tab-inner')).toHaveAttribute('data-dark', 'true');
  });
});
