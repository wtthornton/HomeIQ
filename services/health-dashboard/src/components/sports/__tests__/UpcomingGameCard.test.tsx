/**
 * Tests for UpcomingGameCard Component
 * 
 * Testing rendering, countdown timer, and accessibility
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import { UpcomingGameCard } from '../UpcomingGameCard';
import type { Game } from '../../../types/sports';

const mockGame: Game = {
  id: 'game-1',
  league: 'NFL',
  status: 'scheduled',
  startTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), // 2 hours from now
  homeTeam: {
    id: 'sf',
    name: 'San Francisco 49ers',
    abbreviation: 'SF',
    logo: '',
    colors: { primary: '#AA0000', secondary: '#B3995D' }
  },
  awayTeam: {
    id: 'dal',
    name: 'Dallas Cowboys',
    abbreviation: 'DAL',
    logo: '',
    colors: { primary: '#003594', secondary: '#869397' }
  },
  score: { home: 0, away: 0 },
  period: { current: 1, total: 4 }
};

describe('UpcomingGameCard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders game information correctly', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={false} />);
    
    expect(screen.getByText(/DAL @ SF/i)).toBeInTheDocument();
    expect(screen.getByText(/Dallas Cowboys at San Francisco 49ers/i)).toBeInTheDocument();
  });

  it('displays game start time', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={false} />);
    
    const timeElement = screen.getByLabelText(/Upcoming game:/i);
    expect(timeElement).toBeInTheDocument();
  });

  it('displays countdown timer', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={false} />);
    
    // Should show countdown (approximately 2 hours)
    expect(screen.getByText(/in \d+h/i)).toBeInTheDocument();
  });

  it('has proper ARIA label for accessibility', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={false} />);
    
    const card = screen.getByLabelText(/Upcoming game: Dallas Cowboys at San Francisco 49ers/i);
    expect(card).toBeInTheDocument();
  });

  it('displays notification button with proper label', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={false} />);
    
    const notifyButton = screen.getByLabelText(/Set notification for/i);
    expect(notifyButton).toBeInTheDocument();
  });

  it('supports dark mode styling', () => {
    render(<UpcomingGameCard game={mockGame} darkMode={true} />);
    
    const card = screen.getByLabelText(/Upcoming game:/i);
    expect(card.className).toContain('bg-gray-800');
  });
});
