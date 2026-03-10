import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { EventsTab } from '../EventsTab';

// Mock dataApi
vi.mock('../../../services/api', () => ({
  dataApi: {
    getEvents: vi.fn().mockResolvedValue([
      {
        id: 'evt-1',
        entity_id: 'light.kitchen',
        event_type: 'state_changed',
        timestamp: '2025-01-01T12:00:00Z',
      },
    ]),
    getEventsStats: vi.fn().mockResolvedValue({
      total_events: 150,
      event_types: { state_changed: 100, automation_triggered: 50 },
      top_entities: [{ entity_id: 'light.kitchen', count: 25 }],
    }),
  },
}));

// Mock EventStreamViewer
vi.mock('../../EventStreamViewer', () => ({
  EventStreamViewer: ({ darkMode }: { darkMode: boolean }) => (
    <div data-testid="event-stream-viewer">Event Stream Viewer</div>
  ),
}));

describe('EventsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the events tab with real-time stream by default', () => {
    render(<EventsTab darkMode={false} />);
    expect(screen.getByTestId('event-stream')).toBeInTheDocument();
  });

  it('shows real-time stream button as active by default', () => {
    render(<EventsTab darkMode={false} />);
    expect(screen.getByText(/Real-Time Stream/)).toBeInTheDocument();
    expect(screen.getByText(/Historical Events/)).toBeInTheDocument();
  });

  it('renders EventStreamViewer in real-time mode', () => {
    render(<EventsTab darkMode={false} />);
    expect(screen.getByTestId('event-stream-viewer')).toBeInTheDocument();
  });

  it('switches to historical view when button clicked', async () => {
    const user = userEvent.setup();
    render(<EventsTab darkMode={false} />);

    await user.click(screen.getByText(/Historical Events/));
    // Historical view should now be visible with the heading
    expect(await screen.findByText('Historical Events', { selector: 'h3' })).toBeInTheDocument();
  });

  it('shows time range selector in historical mode', async () => {
    const user = userEvent.setup();
    render(<EventsTab darkMode={false} />);

    await user.click(screen.getByText(/Historical Events/));
    expect(screen.getByDisplayValue('Last Hour')).toBeInTheDocument();
  });

  it('does not show time range selector in real-time mode', () => {
    render(<EventsTab darkMode={false} />);
    expect(screen.queryByDisplayValue('Last Hour')).not.toBeInTheDocument();
  });

  it('does not show EventStreamViewer in historical mode', async () => {
    const user = userEvent.setup();
    render(<EventsTab darkMode={false} />);

    await user.click(screen.getByText(/Historical Events/));
    expect(screen.queryByTestId('event-stream-viewer')).not.toBeInTheDocument();
  });

  it('renders in dark mode without errors', () => {
    render(<EventsTab darkMode={true} />);
    expect(screen.getByTestId('event-stream')).toBeInTheDocument();
  });
});
