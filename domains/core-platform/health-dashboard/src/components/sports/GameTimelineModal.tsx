/**
 * GameTimelineModal Component
 * 
 * Modal displaying score progression timeline for a game
 * Epic 21 Story 21.2 Phase 3
 */

import React, { useState, useEffect } from 'react';
import { dataApi } from '../../services/api';
import { ScoreTimelineChart } from './charts/ScoreTimelineChart';

interface GameTimelineModalProps {
  game: {
    game_id: string;
    league: string;
    home_team: string;
    away_team: string;
    home_score: number;
    away_score: number;
    timestamp: string;
  };
  onClose: () => void;
  darkMode?: boolean;
}

interface TimelinePoint {
  timestamp: string;
  home_score: number;
  away_score: number;
  quarter_period: string;
  time_remaining: string;
}

export const GameTimelineModal: React.FC<GameTimelineModalProps> = ({
  game,
  onClose,
  darkMode = false
}) => {
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const modalBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const overlayBg = darkMode ? 'bg-black bg-opacity-70' : 'bg-black bg-opacity-50';

  useEffect(() => {
    fetchGameTimeline();
  }, [game.game_id]);

  const fetchGameTimeline = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Query game timeline from InfluxDB
      const data = await dataApi.getGameTimeline(game.game_id);
      
      if (data && data.timeline) {
        setTimeline(data.timeline);
      } else {
        setTimeline([]);
      }
    } catch (err) {
      console.error('Error fetching game timeline:', err);
      setError(err instanceof Error ? err.message : 'Failed to load game timeline');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${overlayBg}`}
      onClick={onClose}
    >
      <div 
        className={`${modalBg} rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h2 className={`text-xl font-bold ${textPrimary}`}>
              Game Timeline
            </h2>
            <p className={`text-sm ${textSecondary}`}>
              {game.home_team} vs {game.away_team}
            </p>
          </div>
          <button
            onClick={onClose}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
              darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
            }`}
            aria-label="Close modal"
          >
            <span className="text-2xl">×</span>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Final Score */}
          <div className="mb-6">
            <div className="flex items-center justify-center gap-8 p-4 rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-750 dark:to-gray-700">
              <div className="text-center">
                <div className={`text-lg font-semibold ${textPrimary}`}>{game.home_team}</div>
                <div className="text-4xl font-bold mt-2">{game.home_score}</div>
              </div>
              <div className={`text-2xl font-bold ${textSecondary}`}>-</div>
              <div className="text-center">
                <div className={`text-lg font-semibold ${textPrimary}`}>{game.away_team}</div>
                <div className="text-4xl font-bold mt-2">{game.away_score}</div>
              </div>
            </div>
            <div className={`text-center text-sm ${textSecondary} mt-2`}>
              {new Date(game.timestamp).toLocaleString()}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className={textSecondary}>Loading timeline...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="text-center py-12">
              <div className="text-red-500 mb-4">⚠️</div>
              <p className="text-red-500">{error}</p>
            </div>
          )}

          {/* Timeline Chart */}
          {!loading && !error && timeline.length > 0 && (
            <div>
              <h3 className={`text-lg font-semibold ${textPrimary} mb-4`}>
                Score Progression
              </h3>
              <ScoreTimelineChart
                data={timeline.map((point, index) => {
                  // Format time label: prefer time_remaining, fallback to period, then index
                  let timeLabel = point.time_remaining || '';
                  if (!timeLabel && point.quarter_period) {
                    timeLabel = point.quarter_period;
                  }
                  if (!timeLabel) {
                    timeLabel = `Point ${index + 1}`;
                  }
                  
                  return {
                    time: timeLabel,
                    homeScore: point.home_score,
                    awayScore: point.away_score,
                    period: point.quarter_period || undefined
                  };
                })}
                homeTeamName={game.home_team}
                awayTeamName={game.away_team}
                darkMode={darkMode}
              />
              
              {/* Quarter/Period Breakdown */}
              <div className="mt-6">
                <h4 className={`text-md font-semibold ${textPrimary} mb-3`}>
                  Period Breakdown
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                  {(() => {
                    // Group timeline points by period
                    const periodMap = new Map<string, { start: TimelinePoint; end: TimelinePoint }>();
                    
                    timeline.forEach((point) => {
                      const period = point.quarter_period || 'Unknown';
                      if (!periodMap.has(period)) {
                        periodMap.set(period, { start: point, end: point });
                      } else {
                        const existing = periodMap.get(period)!;
                        existing.end = point;
                      }
                    });
                    
                    // Sort periods: Q1, Q2, Q3, Q4, OT, OT2, etc.
                    const sortedPeriods = Array.from(periodMap.entries()).sort((a, b) => {
                      const aPeriod = a[0].toUpperCase();
                      const bPeriod = b[0].toUpperCase();
                      
                      // Extract numbers for sorting
                      const aNum = parseInt(aPeriod.match(/\d+/)?.[0] || '999');
                      const bNum = parseInt(bPeriod.match(/\d+/)?.[0] || '999');
                      
                      if (aNum !== bNum) return aNum - bNum;
                      
                      // Handle OT (overtime) periods
                      if (aPeriod.includes('OT') && !bPeriod.includes('OT')) return 1;
                      if (!aPeriod.includes('OT') && bPeriod.includes('OT')) return -1;
                      
                      return aPeriod.localeCompare(bPeriod);
                    });
                    
                    return sortedPeriods.map(([period, { start, end }]) => (
                      <div
                        key={period}
                        className={`p-3 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600'
                            : 'bg-gray-50 border-gray-200'
                        }`}
                      >
                        <div className={`text-sm font-semibold ${textPrimary} mb-2`}>
                          {period}
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <div className={textSecondary}>
                            <div className="text-xs mb-1">{game.home_team}</div>
                            <div className="font-bold text-lg">{end.home_score}</div>
                          </div>
                          <div className={`text-lg font-bold ${textSecondary}`}>-</div>
                          <div className={textSecondary}>
                            <div className="text-xs mb-1">{game.away_team}</div>
                            <div className="font-bold text-lg">{end.away_score}</div>
                          </div>
                        </div>
                        {end.time_remaining && (
                          <div className={`text-xs mt-2 ${textSecondary}`}>
                            {end.time_remaining}
                          </div>
                        )}
                      </div>
                    ));
                  })()}
                </div>
              </div>
            </div>
          )}

          {/* No Data State */}
          {!loading && !error && timeline.length === 0 && (
            <div className={`text-center py-12 ${textSecondary}`}>
              <div className="text-4xl mb-4">📊</div>
              <p>No timeline data available for this game</p>
              <p className="text-sm mt-2">Timeline data may not be recorded for all games</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
            }`}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

