/**
 * Tests for LiveGameCard Component
 * 
 * Testing rendering, accessibility, and game display
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import { LiveGameCard } from '../LiveGameCard';
import type { Game } from '../../../types/sports';

const mockGame: Game = {
  id: 'game-1',
  league: 'NFL',
  status: 'live',
  startTime: new Date().toISOString(),
  homeTeam: {
    id: 'sf',
    name: 'San Francisco 49ers',
    abbreviation: 'SF',
    logo: '',
    colors: { primary: '#AA0000', secondary: '#B3995D' },
    record: { wins: 10, losses: 2 }
  },
  awayTeam: {
    id: 'dal',
    name: 'Dallas Cowboys',
    abbreviation: 'DAL',
    logo: '',
    colors: { primary: '#003594', secondary: '#869397' },
    record: { wins: 8, losses: 4 }
  },
  score: { home: 21, away: 14 },
  period: { current: 3, total: 4, timeRemaining: '12:34' },
  isFavorite: false
};

describe('LiveGameCard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders game information correctly', () => {
    render(<LiveGameCard game={mockGame} darkMode={false} />);
    
    expect(screen.getByText('San Francisco 49ers')).toBeInTheDocument();
    expect(screen.getByText('Dallas Cowboys')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();
    expect(screen.getByText('14')).toBeInTheDocument();
  });

  it('displays LIVE status indicator', () => {
    render(<LiveGameCard game={mockGame} darkMode={false} />);
    
    expect(screen.getByText(/LIVE/i)).toBeInTheDocument();
  });

  it('displays period information for NFL games', () => {
    render(<LiveGameCard game={mockGame} darkMode={false} />);
    
    expect(screen.getByText(/Q3/i)).toBeInTheDocument();
  });

  it('displays period information for NHL games', () => {
    const nhlGame = { ...mockGame, league: 'NHL' as const, period: { current: 2, total: 3, timeRemaining: '15:00' } };
    render(<LiveGameCard game={nhlGame} darkMode={false} />);
    
    expect(screen.getByText(/P2/i)).toBeInTheDocument();
  });

  it('has proper ARIA label for accessibility', () => {
    render(<LiveGameCard game={mockGame} darkMode={false} />);
    
    const card = screen.getByLabelText(/Live game: Dallas Cowboys vs San Francisco 49ers/i);
    expect(card).toBeInTheDocument();
  });

  it('displays action buttons with proper labels', () => {
    render(<LiveGameCard game={mockGame} darkMode={false} />);
    
    expect(screen.getByLabelText(/View full statistics for/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Watch/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Set notification for/i)).toBeInTheDocument();
  });

  it('supports dark mode styling', () => {
    render(<LiveGameCard game={mockGame} darkMode={true} />);
    
    const card = screen.getByLabelText(/Live game:/i);
    expect(card.className).toContain('bg-gray-800');
  });

  it('displays favorite indicator when game is favorited', () => {
    const favoritedGame = { ...mockGame, isFavorite: true };
    render(<LiveGameCard game={favoritedGame} darkMode={false} />);
    
    expect(screen.getByLabelText(/Favorite team/i)).toBeInTheDocument();
  });
});
