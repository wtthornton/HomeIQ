/**
 * RecentGamesList Component
 * 
 * Displays a list of recent games with clickable rows to view game timeline
 * Epic 21 Story 21.2 Phase 3
 */

import React, { useState, useEffect } from 'react';
import { dataApi } from '../../services/api';
import { GameTimelineModal } from './GameTimelineModal';

interface RecentGamesListProps {
  teamId: string;
  teamName: string;
  league: 'NFL' | 'NHL';
  limit?: number;
  darkMode?: boolean;
}

interface Game {
  game_id: string;
  league: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  status: string;
  timestamp: string;
}

export const RecentGamesList: React.FC<RecentGamesListProps> = ({
  teamId,
  teamName,
  league,
  limit = 10,
  darkMode = false
}) => {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);
  const [showTimelineModal, setShowTimelineModal] = useState(false);

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';
  const hoverBg = darkMode ? 'hover:bg-gray-750' : 'hover:bg-gray-50';

  useEffect(() => {
    fetchRecentGames();
  }, [teamId, limit]);

  const fetchRecentGames = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Query historical games from InfluxDB
      const data = await dataApi.getSportsHistory(teamId, undefined);
      
      if (data && data.games) {
        setGames(data.games.slice(0, limit));
      } else {
        setGames([]);
      }
    } catch (err) {
      console.error('Error fetching recent games:', err);
      setError(err instanceof Error ? err.message : 'Failed to load recent games');
    } finally {
      setLoading(false);
    }
  };

  const handleGameClick = (game: Game) => {
    setSelectedGame(game);
    setShowTimelineModal(true);
  };

  const handleCloseModal = () => {
    setShowTimelineModal(false);
    setSelectedGame(null);
  };

  if (loading) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className="animate-pulse space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className="text-red-500 text-sm">⚠️ {error}</div>
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className={`text-center ${textSecondary}`}>
          <div className="text-4xl mb-2">📅</div>
          <p className="text-sm">No recent games found</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`${cardBg} border ${borderColor} rounded-lg overflow-hidden`}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className={`text-lg font-bold ${textPrimary}`}>
            Recent Games - {teamName}
          </h3>
          <p className={`text-sm ${textSecondary}`}>
            Click any game to view score timeline
          </p>
        </div>

        {/* Games List */}
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {games.map((game) => {
            const isHome = game.home_team === teamId;
            const opponent = isHome ? game.away_team : game.home_team;
            const teamScore = isHome ? game.home_score : game.away_score;
            const opponentScore = isHome ? game.away_score : game.home_score;
            const won = teamScore > opponentScore;
            const tied = teamScore === opponentScore;

            return (
              <div
                key={game.game_id}
                onClick={() => handleGameClick(game)}
                className={`px-6 py-4 cursor-pointer transition-colors ${hoverBg}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {/* Result Badge */}
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                        won
                          ? 'bg-green-500 text-white'
                          : tied
                            ? 'bg-gray-500 text-white'
                            : 'bg-red-500 text-white'
                      }`}
                    >
                      {won ? 'W' : tied ? 'T' : 'L'}
                    </div>

                    {/* Teams & Score */}
                    <div>
                      <div className={`font-semibold ${textPrimary}`}>
                        {teamName} vs {opponent}
                      </div>
                      <div className={`text-sm ${textSecondary}`}>
                        Final: {teamScore} - {opponentScore}
                      </div>
                    </div>
                  </div>

                  {/* Date & Arrow */}
                  <div className="flex items-center gap-3">
                    <span className={`text-sm ${textSecondary}`}>
                      {new Date(game.timestamp).toLocaleDateString()}
                    </span>
                    <span className={textSecondary}>→</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Timeline Modal */}
      {showTimelineModal && selectedGame && (
        <GameTimelineModal
          game={selectedGame}
          onClose={handleCloseModal}
          darkMode={darkMode}
        />
      )}
    </>
  );
};

