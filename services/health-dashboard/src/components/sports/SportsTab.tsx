/**
 * SportsTab Component
 * 
 * Main sports tab integrating team selection, live games, and management
 * 
 * Accessibility improvements:
 * - ARIA labels for all interactive elements
 * - Keyboard navigation support
 * - Semantic HTML structure
 * - Screen reader friendly
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { SetupWizard } from './SetupWizard';
import { EmptyState } from './EmptyState';
import { TeamManagement } from './TeamManagement';
import { LiveGameCard } from './LiveGameCard';
import { UpcomingGameCard } from './UpcomingGameCard';
import { CompletedGameCard } from './CompletedGameCard';
import { GameDetailModal } from './GameDetailModal';
import { useTeamPreferences } from '../../hooks/useTeamPreferences';
import { useSportsData } from '../../hooks/useSportsData';
import { SkeletonCard } from '../skeletons';
import type { Team, Game } from '../../types/sports';

interface SportsTabProps {
  darkMode?: boolean;
}

export const SportsTab: React.FC<SportsTabProps> = ({ darkMode = false }) => {
  const {
    loading,
    setTeams,
    addTeam,
    removeTeam,
    hasAnyTeams,
    setupCompleted,
    nflTeams,
    nhlTeams
  } = useTeamPreferences();

  const [showSetup, setShowSetup] = useState(false);
  const [showManagement, setShowManagement] = useState(false);
  const [availableNFLTeams, setAvailableNFLTeams] = useState<Team[]>([]);
  const [availableNHLTeams, setAvailableNHLTeams] = useState<Team[]>([]);
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Filter and sort state
  const [leagueFilter, setLeagueFilter] = useState<'all' | 'NFL' | 'NHL'>('all');
  const [teamFilter, setTeamFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'date' | 'team'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const bgPrimary = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  // Memoize team IDs to prevent unnecessary re-renders
  const allTeamIds = useMemo(() => [...nflTeams, ...nhlTeams], [nflTeams, nhlTeams]);
  
  const {
    liveGames,
    upcomingGames,
    completedGames,
    loading: gamesLoading,
    error: gamesError,
    lastUpdate,
    refresh
  } = useSportsData({
    teamIds: allTeamIds,
    league: 'all',
    pollInterval: 30000
  });

  // Get all available teams for filter dropdown
  const allAvailableTeams = useMemo(() => {
    return [...availableNFLTeams, ...availableNHLTeams];
  }, [availableNFLTeams, availableNHLTeams]);

  // Filter and sort function for games
  const filterAndSortGames = useCallback((games: Game[]) => {
    // Apply filters
    let filtered = games.filter(game => {
      // League filter
      if (leagueFilter !== 'all' && game.league !== leagueFilter) {
        return false;
      }
      
      // Team filter
      if (teamFilter && game.homeTeam.id !== teamFilter && game.awayTeam.id !== teamFilter) {
        return false;
      }
      
      return true;
    });

    // Apply sorting
    filtered = [...filtered].sort((a, b) => {
      if (sortBy === 'date') {
        const dateA = new Date(a.startTime).getTime();
        const dateB = new Date(b.startTime).getTime();
        return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
      } else if (sortBy === 'team') {
        const nameA = `${a.awayTeam.name} vs ${a.homeTeam.name}`.toLowerCase();
        const nameB = `${b.awayTeam.name} vs ${b.homeTeam.name}`.toLowerCase();
        return sortOrder === 'asc' 
          ? nameA.localeCompare(nameB)
          : nameB.localeCompare(nameA);
      }
      return 0;
    });

    return filtered;
  }, [leagueFilter, teamFilter, sortBy, sortOrder]);

  // Memoize filtered and sorted games
  const filteredLiveGames = useMemo(
    () => filterAndSortGames(liveGames),
    [liveGames, filterAndSortGames]
  );
  const filteredUpcomingGames = useMemo(
    () => filterAndSortGames(upcomingGames),
    [upcomingGames, filterAndSortGames]
  );
  const filteredCompletedGames = useMemo(
    () => filterAndSortGames(completedGames),
    [completedGames, filterAndSortGames]
  );

  // Memoize game summary for header display (using filtered games)
  const gameSummary = useMemo(() => ({
    live: filteredLiveGames.length,
    upcoming: filteredUpcomingGames.length,
    teams: allTeamIds.length
  }), [filteredLiveGames.length, filteredUpcomingGames.length, allTeamIds.length]);

  // Check if setup is needed on mount
  useEffect(() => {
    if (!loading && !setupCompleted && !hasAnyTeams()) {
      setShowSetup(true);
    }
  }, [loading, setupCompleted, hasAnyTeams]);

  // Fetch available teams for management
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const nflResponse = await fetch('/api/sports/teams?league=NFL');
        const nflData = await nflResponse.json();
        setAvailableNFLTeams(nflData.teams || []);

        const nhlResponse = await fetch('/api/sports/teams?league=NHL');
        const nhlData = await nhlResponse.json();
        setAvailableNHLTeams(nhlData.teams || []);
      } catch (error) {
        console.error('Error fetching teams:', error);
      }
    };

    fetchTeams();
  }, []);

  // Memoize event handlers to prevent unnecessary re-renders
  const handleSetupComplete = useCallback((selectedNFL: string[], selectedNHL: string[]) => {
    setTeams(selectedNFL, selectedNHL);
    setShowSetup(false);
  }, [setTeams]);

  const handleSetupCancel = useCallback(() => {
    setShowSetup(false);
  }, []);

  const handleAddFirstTeam = useCallback(() => {
    setShowSetup(true);
  }, []);

  const handleViewGameDetails = useCallback((game: Game) => {
    setSelectedGame(game);
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedGame(null);
  }, []);

  const handleManageTeams = useCallback(() => {
    setShowManagement(false);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64 mb-6 shimmer"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={`sport-${i}`} variant="default" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Show setup wizard if needed
  if (showSetup) {
    return (
      <SetupWizard
        onComplete={handleSetupComplete}
        onCancel={handleSetupCancel}
        darkMode={darkMode}
      />
    );
  }

  // Show management interface
  if (showManagement) {
    return (
      <div className={`min-h-screen ${bgPrimary} p-6`} role="main" aria-label="Team Management">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={handleManageTeams}
            className={`mb-6 px-4 py-2 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textPrimary} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
            aria-label="Back to Sports view"
          >
            ← Back to Sports
          </button>

          <TeamManagement
            nflTeams={nflTeams}
            nhlTeams={nhlTeams}
            availableNFLTeams={availableNFLTeams}
            availableNHLTeams={availableNHLTeams}
            onAddTeam={addTeam}
            onRemoveTeam={removeTeam}
            darkMode={darkMode}
          />
        </div>
      </div>
    );
  }

  // Show empty state if no teams
  if (!hasAnyTeams()) {
    return (
      <div className={`min-h-screen ${bgPrimary}`}>
        <EmptyState onAddTeam={handleAddFirstTeam} darkMode={darkMode} />
      </div>
    );
  }

  // Main sports view with live games
  return (
    <div className={`min-h-screen ${bgPrimary} p-6`} role="main" aria-label="Sports Center">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <div>
            <h1 className={`text-3xl font-bold ${textPrimary} mb-2`}>
              <span aria-hidden="true">🏈</span> NFL & <span aria-hidden="true">🏒</span> NHL Sports Center
            </h1>
            <p className={textSecondary} aria-live="polite" aria-atomic="true">
              {gameSummary.live} Live • {gameSummary.upcoming} Upcoming • {gameSummary.teams} Teams
            </p>
          </div>
          
          <div className="flex gap-3" role="toolbar" aria-label="Sports actions">
            <button
              onClick={refresh}
              className={`px-4 py-2 rounded-lg font-medium ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
              } ${textPrimary} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
              aria-label="Refresh sports data"
              title="Refresh sports data"
            >
              <span aria-hidden="true">🔄</span>
              <span className="sr-only">Refresh</span>
            </button>
            {import.meta.env.VITE_HA_URL && (
              <button
                onClick={() => window.open(`${import.meta.env.VITE_HA_URL}/config/devices/dashboard`, '_blank')}
                className={`px-4 py-2 rounded-lg font-medium ${
                  darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
                } text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
                aria-label="Manage teams in Home Assistant (opens in new tab)"
                title="Manage teams in Home Assistant"
              >
                <span aria-hidden="true">⚙️</span> Manage Teams in HA
              </button>
            )}
          </div>
        </header>

        {/* Last Update Time */}
        {lastUpdate && (
          <div className={`text-xs ${textSecondary} text-right mb-4`} aria-live="polite" role="status">
            Last updated: <time dateTime={lastUpdate.toISOString()}>{lastUpdate.toLocaleTimeString()}</time>
          </div>
        )}

        {/* Loading State */}
        {gamesLoading && (
          <div className="text-center py-12" role="status" aria-live="polite" aria-label="Loading games">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" aria-hidden="true" />
            <p className={textSecondary}>Loading games...</p>
          </div>
        )}

        {/* Error State */}
        {gamesError && (
          <div 
            className={`${darkMode ? 'bg-red-900/20 border-red-500/30' : 'bg-red-50 border-red-200'} 
              border rounded-lg p-6 mb-6`}
            role="alert"
            aria-live="assertive"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl" aria-hidden="true">⚠️</span>
              <div className="flex-1">
                <div className={`font-semibold ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
                  Error loading games
                </div>
                <div className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
                  {gamesError}
                </div>
              </div>
              <button
                onClick={refresh}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                aria-label="Retry loading games"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Live Games Section */}
        {!gamesLoading && liveGames.length > 0 && (
          <section className="mb-8" aria-labelledby="live-games-heading">
            <h2 id="live-games-heading" className={`text-2xl font-bold ${textPrimary} mb-4 flex items-center gap-2`}>
              <span className="animate-pulse" aria-hidden="true">🟢</span>
              LIVE NOW ({liveGames.length})
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" role="list" aria-label="Live games">
              {liveGames.map(game => (
                <div key={game.id} role="listitem">
                  <LiveGameCard game={game} darkMode={darkMode} onViewDetails={handleViewGameDetails} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Upcoming Games Section */}
        {!gamesLoading && upcomingGames.length > 0 && (
          <section className="mb-8" aria-labelledby="upcoming-games-heading">
            <h2 id="upcoming-games-heading" className={`text-2xl font-bold ${textPrimary} mb-4`}>
              <span aria-hidden="true">📅</span> UPCOMING THIS WEEK ({upcomingGames.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" role="list" aria-label="Upcoming games">
              {upcomingGames.map(game => (
                <div key={game.id} role="listitem">
                  <UpcomingGameCard game={game} darkMode={darkMode} onViewDetails={handleViewGameDetails} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Completed Games Section */}
        {!gamesLoading && filteredCompletedGames.length > 0 && (
          <section className="mb-8" aria-labelledby="completed-games-heading">
            <h2 id="completed-games-heading" className={`text-2xl font-bold ${textPrimary} mb-4`}>
              <span aria-hidden="true">📜</span> COMPLETED ({filteredCompletedGames.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" role="list" aria-label="Completed games">
              {filteredCompletedGames.map(game => (
                <div key={game.id} role="listitem">
                  <CompletedGameCard game={game} darkMode={darkMode} onViewDetails={handleViewGameDetails} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* No Games State */}
        {!gamesLoading && !gamesError && 
         filteredLiveGames.length === 0 && filteredUpcomingGames.length === 0 && filteredCompletedGames.length === 0 && 
         (liveGames.length > 0 || upcomingGames.length > 0 || completedGames.length > 0) && (
          <div 
            className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-12 shadow-md text-center`}
            role="status"
            aria-live="polite"
          >
            <div className="text-6xl mb-4" aria-hidden="true">🔍</div>
            <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
              No Games Match Your Filters
            </h2>
            <p className={textSecondary}>
              Try adjusting your filters to see more games.
            </p>
            <button
              onClick={() => {
                setLeagueFilter('all');
                setTeamFilter('');
                setSortBy('date');
                setSortOrder('asc');
              }}
              className={`mt-4 px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
              } focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
              aria-label="Clear all filters"
            >
              Clear Filters
            </button>
          </div>
        )}

        {/* No Games State (no filters applied) */}
        {!gamesLoading && !gamesError && 
         liveGames.length === 0 && upcomingGames.length === 0 && completedGames.length === 0 && (
          <div 
            className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-12 shadow-md text-center`}
            role="status"
            aria-live="polite"
          >
            <div className="text-6xl mb-4" aria-hidden="true">😴</div>
            <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
              No Games Right Now
            </h2>
            <p className={textSecondary}>
              No scheduled games for your teams at this time.
            </p>
            <p className={`text-sm ${textSecondary} mt-4`}>
              We'll automatically refresh when games are scheduled.
            </p>
          </div>
        )}
      </div>

      {/* Game Detail Modal */}
      <GameDetailModal
        game={selectedGame}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        darkMode={darkMode}
      />
    </div>
  );
};

