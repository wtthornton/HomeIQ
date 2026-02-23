/**
 * Tests for SportsTab Component
 * 
 * Testing accessibility, rendering, and user interactions
 * Following Vitest patterns from Context7 KB
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { SportsTab } from '../SportsTab';
import { useTeamPreferences } from '../../../hooks/useTeamPreferences';
import { useSportsData } from '../../../hooks/useSportsData';

// Mock hooks
vi.mock('../../../hooks/useTeamPreferences');
vi.mock('../../../hooks/useSportsData');
vi.mock('../SetupWizard', () => ({
  SetupWizard: () => <div>Setup Wizard</div>
}));
vi.mock('../EmptyState', () => ({
  EmptyState: ({ onAddTeam }: { onAddTeam: () => void }) => (
    <div>
      <button onClick={onAddTeam}>Add Team</button>
      Empty State
    </div>
  )
}));
vi.mock('../TeamManagement', () => ({
  TeamManagement: () => <div>Team Management</div>
}));
vi.mock('../LiveGameCard', () => ({
  LiveGameCard: ({ game }: { game: any }) => <div>Live Game: {game.id}</div>
}));
vi.mock('../UpcomingGameCard', () => ({
  UpcomingGameCard: ({ game }: { game: any }) => <div>Upcoming Game: {game.id}</div>
}));
vi.mock('../CompletedGameCard', () => ({
  CompletedGameCard: ({ game }: { game: any }) => <div>Completed Game: {game.id}</div>
}));

const mockUseTeamPreferences = vi.mocked(useTeamPreferences);
const mockUseSportsData = vi.mocked(useSportsData);

const mockGame = {
  id: 'game-1',
  league: 'NFL' as const,
  status: 'live' as const,
  startTime: new Date().toISOString(),
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
  score: { home: 21, away: 14 },
  period: { current: 3, total: 4, timeRemaining: '12:34' }
};

describe('SportsTab Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    mockUseTeamPreferences.mockReturnValue({
      loading: false,
      setTeams: vi.fn(),
      addTeam: vi.fn(),
      removeTeam: vi.fn(),
      hasAnyTeams: () => true,
      setupCompleted: true,
      nflTeams: ['sf'],
      nhlTeams: []
    } as any);

    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders Sports Center heading', () => {
    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByRole('heading', { name: /NFL & NHL Sports Center/i })).toBeInTheDocument();
  });

  it('displays game summary with correct counts', () => {
    mockUseSportsData.mockReturnValue({
      liveGames: [mockGame],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText(/1 Live/i)).toBeInTheDocument();
    expect(screen.getByText(/0 Upcoming/i)).toBeInTheDocument();
  });

  it('shows loading state when teams are loading', () => {
    mockUseTeamPreferences.mockReturnValue({
      loading: true,
      setTeams: vi.fn(),
      addTeam: vi.fn(),
      removeTeam: vi.fn(),
      hasAnyTeams: () => false,
      setupCompleted: false,
      nflTeams: [],
      nhlTeams: []
    } as any);

    render(<SportsTab darkMode={false} />);
    
    // Should show skeleton/loading state
    expect(screen.queryByRole('heading', { name: /NFL & NHL Sports Center/i })).not.toBeInTheDocument();
  });

  it('shows setup wizard when no teams are selected', () => {
    mockUseTeamPreferences.mockReturnValue({
      loading: false,
      setTeams: vi.fn(),
      addTeam: vi.fn(),
      removeTeam: vi.fn(),
      hasAnyTeams: () => false,
      setupCompleted: false,
      nflTeams: [],
      nhlTeams: []
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText('Setup Wizard')).toBeInTheDocument();
  });

  it('shows empty state when no teams selected and setup not shown', () => {
    mockUseTeamPreferences.mockReturnValue({
      loading: false,
      setTeams: vi.fn(),
      addTeam: vi.fn(),
      removeTeam: vi.fn(),
      hasAnyTeams: () => false,
      setupCompleted: true,
      nflTeams: [],
      nhlTeams: []
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText('Empty State')).toBeInTheDocument();
  });

  it('displays live games when available', () => {
    mockUseSportsData.mockReturnValue({
      liveGames: [mockGame],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText(/LIVE NOW/i)).toBeInTheDocument();
    expect(screen.getByText(/Live Game: game-1/i)).toBeInTheDocument();
  });

  it('displays upcoming games when available', () => {
    const upcomingGame = { ...mockGame, id: 'game-2', status: 'scheduled' as const };
    
    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [upcomingGame],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText(/UPCOMING THIS WEEK/i)).toBeInTheDocument();
    expect(screen.getByText(/Upcoming Game: game-2/i)).toBeInTheDocument();
  });

  it('displays completed games when available', () => {
    const completedGame = { ...mockGame, id: 'game-3', status: 'final' as const };
    
    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [],
      completedGames: [completedGame],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByRole('heading', { name: /COMPLETED/i })).toBeInTheDocument();
    expect(screen.getByText(/Completed Game: game-3/i)).toBeInTheDocument();
  });

  it('displays no games state when no games are available', () => {
    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText(/No Games Right Now/i)).toBeInTheDocument();
  });

  it('displays error state when games fail to load', () => {
    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: 'Failed to fetch games',
      lastUpdate: null,
      refresh: vi.fn()
    } as any);

    render(<SportsTab darkMode={false} />);
    
    expect(screen.getByText(/Error loading games/i)).toBeInTheDocument();
    expect(screen.getByText(/Failed to fetch games/i)).toBeInTheDocument();
  });

  it('has refresh button with proper accessibility', () => {
    const mockRefresh = vi.fn();
    mockUseSportsData.mockReturnValue({
      liveGames: [],
      upcomingGames: [],
      completedGames: [],
      loading: false,
      error: null,
      lastUpdate: new Date(),
      refresh: mockRefresh
    } as any);

    render(<SportsTab darkMode={false} />);
    
    const refreshButton = screen.getByLabelText(/Refresh sports data/i);
    expect(refreshButton).toBeInTheDocument();
  });

  it('supports dark mode styling', () => {
    render(<SportsTab darkMode={true} />);
    
    const mainElement = screen.getByRole('main');
    expect(mainElement.className).toContain('bg-gray-900');
  });

  it('has proper ARIA labels for accessibility', () => {
    render(<SportsTab darkMode={false} />);
    
    const mainElement = screen.getByRole('main', { name: /Sports Center/i });
    expect(mainElement).toBeInTheDocument();
  });
});
