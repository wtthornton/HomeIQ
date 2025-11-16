/**
 * SportsTab Component
 * 
 * Main sports tab integrating team selection, live games, and management
 */

import React, { useState, useEffect } from 'react';
import { SetupWizard } from './SetupWizard';
import { EmptyState } from './EmptyState';
import { TeamManagement } from './TeamManagement';
import { LiveGameCard } from './LiveGameCard';
import { UpcomingGameCard } from './UpcomingGameCard';
import { CompletedGameCard } from './CompletedGameCard';
import { useTeamPreferences } from '../../hooks/useTeamPreferences';
import { useSportsData } from '../../hooks/useSportsData';
import { SkeletonCard } from '../skeletons';
import type { Team } from '../../types/sports';

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

  const bgPrimary = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  // Fetch sports data for selected teams
  const allTeamIds = [...nflTeams, ...nhlTeams];
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

  const handleSetupComplete = (selectedNFL: string[], selectedNHL: string[]) => {
    setTeams(selectedNFL, selectedNHL);
    setShowSetup(false);
  };

  const handleSetupCancel = () => {
    setShowSetup(false);
  };

  const handleAddFirstTeam = () => {
    setShowSetup(true);
  };

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
      <div className={`min-h-screen ${bgPrimary} p-6`}>
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => setShowManagement(false)}
            className={`mb-6 px-4 py-2 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textPrimary}`}
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
    <div className={`min-h-screen ${bgPrimary} p-6`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className={`text-3xl font-bold ${textPrimary} mb-2`}>
              🏈 NFL & 🏒 NHL Sports Center
            </h1>
            <p className={textSecondary}>
              {liveGames.length} Live • {upcomingGames.length} Upcoming • {allTeamIds.length} Teams
            </p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={refresh}
              className={`px-4 py-2 rounded-lg font-medium ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
              } ${textPrimary}`}
              title="Refresh now"
            >
              🔄
            </button>
              {import.meta.env.VITE_HA_URL && (
                <button
                  onClick={() => window.open(`${import.meta.env.VITE_HA_URL}/config/devices/dashboard`, '_blank')}
                  className={`px-4 py-2 rounded-lg font-medium ${
                    darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
                  } text-white`}
                  title="Manage teams in Home Assistant"
                >
                  ⚙️ Manage Teams in HA
                </button>
              )}
          </div>
        </div>

        {/* Last Update Time */}
        {lastUpdate && (
          <div className={`text-xs ${textSecondary} text-right mb-4`}>
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}

        {/* Loading State */}
        {gamesLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
            <p className={textSecondary}>Loading games...</p>
          </div>
        )}

        {/* Error State */}
        {gamesError && (
          <div className={`${darkMode ? 'bg-red-900/20 border-red-500/30' : 'bg-red-50 border-red-200'} 
            border rounded-lg p-6 mb-6`}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
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
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Live Games Section */}
        {!gamesLoading && liveGames.length > 0 && (
          <div className="mb-8">
            <h2 className={`text-2xl font-bold ${textPrimary} mb-4 flex items-center gap-2`}>
              <span className="animate-pulse">🟢</span>
              LIVE NOW ({liveGames.length})
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {liveGames.map(game => (
                <LiveGameCard key={game.id} game={game} darkMode={darkMode} />
              ))}
            </div>
          </div>
        )}

        {/* Upcoming Games Section */}
        {!gamesLoading && upcomingGames.length > 0 && (
          <div className="mb-8">
            <h2 className={`text-2xl font-bold ${textPrimary} mb-4`}>
              📅 UPCOMING THIS WEEK ({upcomingGames.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {upcomingGames.map(game => (
                <UpcomingGameCard key={game.id} game={game} darkMode={darkMode} />
              ))}
            </div>
          </div>
        )}

        {/* Completed Games Section */}
        {!gamesLoading && completedGames.length > 0 && (
          <div className="mb-8">
            <h2 className={`text-2xl font-bold ${textPrimary} mb-4`}>
              📜 COMPLETED ({completedGames.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {completedGames.map(game => (
                <CompletedGameCard key={game.id} game={game} darkMode={darkMode} />
              ))}
            </div>
          </div>
        )}

        {/* No Games State */}
        {!gamesLoading && !gamesError && 
         liveGames.length === 0 && upcomingGames.length === 0 && completedGames.length === 0 && (
          <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-12 shadow-md text-center`}>
            <div className="text-6xl mb-4">😴</div>
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
    </div>
  );
};

