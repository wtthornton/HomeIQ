/**
 * TeamScheduleView Component
 * 
 * Calendar-style view of team's season schedule
 * Epic 21 Story 21.2 Phase 4
 */

import React, { useState, useEffect } from 'react';
import { dataApi } from '../../services/api';

interface TeamScheduleViewProps {
  teamId: string;
  teamName: string;
  league: 'NFL' | 'NHL';
  season?: number;
  darkMode?: boolean;
}

interface ScheduleGame {
  game_id: string;
  date: string;
  opponent: string;
  is_home: boolean;
  status: 'completed' | 'scheduled';
  result?: 'W' | 'L' | 'T';
  score?: string;
}

export const TeamScheduleView: React.FC<TeamScheduleViewProps> = ({
  teamId,
  teamName,
  league,
  season,
  darkMode = false
}) => {
  const [schedule, setSchedule] = useState<ScheduleGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<'all' | 'completed' | 'scheduled'>('all');

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  useEffect(() => {
    fetchSchedule();
  }, [teamId, season]);

  const fetchSchedule = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Query team schedule from InfluxDB
      const data = await dataApi.getTeamSchedule(teamId);
      
      if (data && data.games) {
        const formattedSchedule: ScheduleGame[] = data.games.map((game: any) => ({
          game_id: game.game_id,
          date: game.timestamp,
          opponent: game.home_team === teamId ? game.away_team : game.home_team,
          is_home: game.home_team === teamId,
          status: game.status === 'finished' ? 'completed' : 'scheduled',
          result: game.status === 'finished' ? determineResult(game, teamId) : undefined,
          score: game.status === 'finished' ? `${game.home_score}-${game.away_score}` : undefined
        }));
        setSchedule(formattedSchedule);
      } else {
        setSchedule([]);
      }
    } catch (err) {
      console.error('Error fetching schedule:', err);
      setError(err instanceof Error ? err.message : 'Failed to load schedule');
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

  const filteredSchedule = schedule.filter(game => {
    if (filterStatus === 'all') return true;
    return game.status === filterStatus;
  });

  const groupGamesByMonth = (games: ScheduleGame[]) => {
    const grouped: { [key: string]: ScheduleGame[] } = {};
    
    games.forEach(game => {
      const month = new Date(game.date).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long' 
      });
      if (!grouped[month]) {
        grouped[month] = [];
      }
      grouped[month].push(game);
    });
    
    return grouped;
  };

  if (loading) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64"></div>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className="text-red-500">⚠️ {error}</div>
      </div>
    );
  }

  if (schedule.length === 0) {
    return (
      <div className={`${cardBg} border ${borderColor} rounded-lg p-6`}>
        <div className={`text-center ${textSecondary}`}>
          <div className="text-4xl mb-2">📅</div>
          <p className="text-sm">No schedule available</p>
        </div>
      </div>
    );
  }

  const groupedGames = groupGamesByMonth(filteredSchedule);

  return (
    <div className={`${cardBg} border ${borderColor} rounded-lg overflow-hidden`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-lg font-bold ${textPrimary}`}>
            {teamName} - {season || 'Current'} Season Schedule
          </h3>
          <span className={`text-sm ${textSecondary}`}>
            {schedule.length} games
          </span>
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilterStatus('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'all'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
            }`}
          >
            All ({schedule.length})
          </button>
          <button
            onClick={() => setFilterStatus('completed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'completed'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Completed ({schedule.filter(g => g.status === 'completed').length})
          </button>
          <button
            onClick={() => setFilterStatus('scheduled')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'scheduled'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Upcoming ({schedule.filter(g => g.status === 'scheduled').length})
          </button>
        </div>
      </div>

      {/* Schedule List */}
      <div className="max-h-[600px] overflow-y-auto">
        {Object.entries(groupedGames).map(([month, games]) => (
          <div key={month} className="mb-4">
            {/* Month Header */}
            <div className={`px-6 py-2 sticky top-0 ${darkMode ? 'bg-gray-750' : 'bg-gray-100'} border-b ${borderColor}`}>
              <h4 className={`font-semibold ${textPrimary}`}>{month}</h4>
            </div>

            {/* Games for this month */}
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {games.map((game) => (
                <div key={game.game_id} className="px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Result Badge (if completed) */}
                      {game.status === 'completed' && game.result && (
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                            game.result === 'W'
                              ? 'bg-green-500 text-white'
                              : game.result === 'L'
                                ? 'bg-red-500 text-white'
                                : 'bg-gray-500 text-white'
                          }`}
                        >
                          {game.result}
                        </div>
                      )}
                      {game.status === 'scheduled' && (
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                          📅
                        </div>
                      )}

                      {/* Game Info */}
                      <div>
                        <div className={`font-medium ${textPrimary}`}>
                          {game.is_home ? 'vs' : '@'} {game.opponent}
                        </div>
                        <div className={`text-sm ${textSecondary}`}>
                          {new Date(game.date).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                          {game.status === 'completed' && game.score && ` • ${game.score}`}
                        </div>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div>
                      {game.status === 'completed' ? (
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'}`}>
                          Final
                        </span>
                      ) : (
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${darkMode ? 'bg-blue-900 text-blue-200' : 'bg-blue-100 text-blue-700'}`}>
                          Scheduled
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

