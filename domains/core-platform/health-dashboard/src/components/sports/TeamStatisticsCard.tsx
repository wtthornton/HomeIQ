/**
 * TeamStatisticsCard Component
 * 
 * Displays season statistics for a team from InfluxDB historical data
 * Epic 21 Story 21.2 Phase 3
 */

import React, { useState, useEffect } from 'react';
import { dataApi } from '../../services/api';

interface TeamStatisticsCardProps {
  teamId: string;
  teamName: string;
  league: 'NFL' | 'NHL';
  season?: number;
  darkMode?: boolean;
}

interface TeamStats {
  wins: number;
  losses: number;
  ties: number;
  win_percentage: number;
  total_games: number;
  recent_games: Array<{
    game_id: string;
    opponent: string;
    score: string;
    result: 'W' | 'L' | 'T';
    date: string;
  }>;
}

export const TeamStatisticsCard: React.FC<TeamStatisticsCardProps> = ({
  teamId,
  teamName,
  league,
  season,
  darkMode = false
}) => {
  const [stats, setStats] = useState<TeamStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  useEffect(() => {
    fetchTeamStats();
  }, [teamId, season]);

  const fetchTeamStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Query historical data from InfluxDB via data-api
      const data = await dataApi.getSportsHistory(teamId, season);
      
      if (data && data.total_games > 0) {
        setStats({
          wins: data.wins || 0,
          losses: data.losses || 0,
          ties: data.ties || 0,
          win_percentage: data.win_percentage || 0,
          total_games: data.total_games || 0,
          recent_games: (data.games || []).slice(0, 5).map((game: any) => ({
            game_id: game.game_id,
            opponent: game.home_team === teamId ? game.away_team : game.home_team,
            score: `${game.home_score}-${game.away_score}`,
            result: determineResult(game, teamId),
            date: new Date(game.timestamp).toLocaleDateString()
          }))
        });
      } else {
        setStats(null);
      }
    } catch (err) {
      console.error('Error fetching team statistics:', err);
      setError(err instanceof Error ? err.message : 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  const determineResult = (game: any, teamId: string): 'W' | 'L' | 'T' => {
    const isHome = game.home_team === teamId;
    const teamScore = isHome ? game.home_score : game.away_score;
    const opponentScore = isHome ? game.away_score : game.home_score;
    
    if (teamScore > opponentScore) return 'W';
    if (teamScore < opponentScore) return 'L';
    return 'T';
  };

  if (loading) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
          </div>
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

  if (!stats) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className={`text-center ${textSecondary}`}>
          <div className="text-4xl mb-2">📊</div>
          <p className="text-sm">No statistics available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-lg font-bold ${textPrimary}`}>
          {teamName} - {season || 'Current'} Season
        </h3>
        <span className={`text-sm ${textSecondary}`}>
          {league}
        </span>
      </div>

      {/* Record */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div className={`text-2xl font-bold ${textPrimary}`}>{stats.wins}</div>
          <div className={`text-xs ${textSecondary}`}>Wins</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold ${textPrimary}`}>{stats.losses}</div>
          <div className={`text-xs ${textSecondary}`}>Losses</div>
        </div>
        {stats.ties > 0 && (
          <div className="text-center">
            <div className={`text-2xl font-bold ${textPrimary}`}>{stats.ties}</div>
            <div className={`text-xs ${textSecondary}`}>Ties</div>
          </div>
        )}
        <div className="text-center">
          <div className={`text-2xl font-bold ${textPrimary}`}>
            {(stats.win_percentage * 100).toFixed(1)}%
          </div>
          <div className={`text-xs ${textSecondary}`}>Win %</div>
        </div>
      </div>

      {/* Recent Games */}
      {stats.recent_games.length > 0 && (
        <div>
          <h4 className={`text-sm font-semibold ${textPrimary} mb-2`}>
            Last 5 Games
          </h4>
          <div className="space-y-2">
            {stats.recent_games.map((game) => (
              <div
                key={game.game_id}
                className={`flex items-center justify-between text-sm p-2 rounded ${
                  darkMode ? 'bg-gray-750' : 'bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      game.result === 'W'
                        ? 'bg-green-500 text-white'
                        : game.result === 'L'
                          ? 'bg-red-500 text-white'
                          : 'bg-gray-500 text-white'
                    }`}
                  >
                    {game.result}
                  </span>
                  <span className={textPrimary}>vs {game.opponent}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={textSecondary}>{game.score}</span>
                  <span className={`text-xs ${textSecondary}`}>{game.date}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

