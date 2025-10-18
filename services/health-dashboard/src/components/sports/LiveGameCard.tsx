/**
 * LiveGameCard Component
 * 
 * Displays a live game with real-time score updates and animations
 */

import React, { useState, useEffect, useRef } from 'react';
import type { Game } from '../../types/sports';

interface LiveGameCardProps {
  game: Game;
  darkMode?: boolean;
}

export const LiveGameCard: React.FC<LiveGameCardProps> = ({
  game,
  darkMode = false
}) => {
  const [scoreChanged, setScoreChanged] = useState(false);
  const [pulse, setPulse] = useState(false);
  const prevScoreRef = useRef(game.score);

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  // Detect score changes and trigger animation
  useEffect(() => {
    const prev = prevScoreRef.current;
    const current = game.score;

    if (prev.home !== current.home || prev.away !== current.away) {
      setScoreChanged(true);
      setTimeout(() => setScoreChanged(false), 600);
    }

    prevScoreRef.current = current;
  }, [game.score]);

  // Pulse animation for live indicator
  useEffect(() => {
    if (game.status === 'live') {
      const interval = setInterval(() => setPulse(prev => !prev), 1000);
      return () => clearInterval(interval);
    }
  }, [game.status]);

  return (
    <div className={`card-base card-hover content-fade-in ${cardBg} border ${borderColor} overflow-hidden`}>
      
      {/* Header - Live Status */}
      <div className="bg-green-500 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 bg-white rounded-full ${pulse ? 'animate-pulse' : ''}`} />
          <span className="text-white font-bold uppercase text-sm">
            🟢 LIVE
          </span>
        </div>
        <div className="flex items-center space-x-3 text-white text-sm">
          <span>{game.league === 'NFL' ? `Q${game.period.current}` : `P${game.period.current}`}</span>
          <span className="font-mono">{game.period.timeRemaining || '--:--'}</span>
          {game.isFavorite && <span className="text-yellow-300">⭐</span>}
        </div>
      </div>

      {/* Game Content */}
      <div className="p-6">
        {/* Teams & Scores */}
        <div className="grid grid-cols-7 gap-4 items-center mb-6">
          {/* Away Team */}
          <div className="col-span-3 text-center">
            <div className="flex flex-col items-center space-y-2">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
                style={{ backgroundColor: `${game.away_team.colors.primary}20` }}
              >
                {game.league === 'NFL' ? '🏈' : '🏒'}
              </div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.away_team.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.away_team.record && 
                  `${game.away_team.record.wins}-${game.away_team.record.losses}`
                }
              </div>
              <div className={`text-4xl font-bold ${textPrimary} ${
                scoreChanged ? 'animate-bounce' : ''
              }`}>
                {game.score.away}
              </div>
            </div>
          </div>

          {/* VS Divider */}
          <div className="col-span-1 text-center">
            <div className={`text-2xl font-bold ${textSecondary}`}>vs</div>
          </div>

          {/* Home Team */}
          <div className="col-span-3 text-center">
            <div className="flex flex-col items-center space-y-2">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
                style={{ backgroundColor: `${game.home_team.colors.primary}20` }}
              >
                {game.league === 'NFL' ? '🏈' : '🏒'}
              </div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.home_team.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.home_team.record && 
                  `${game.home_team.record.wins}-${game.home_team.record.losses}`
                }
              </div>
              <div className={`text-4xl font-bold ${textPrimary} ${
                scoreChanged ? 'animate-bounce' : ''
              }`}>
                {game.score.home}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button 
            className={`flex-1 py-2 px-4 rounded-lg ${
              darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
            } text-white font-medium transition-colors`}
          >
            📊 Full Stats
          </button>
          <button 
            className={`flex-1 py-2 px-4 rounded-lg ${
              darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
            } ${textPrimary} font-medium transition-colors`}
          >
            📺 Watch
          </button>
          <button 
            className={`py-2 px-4 rounded-lg ${
              darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
            } ${textPrimary} transition-colors`}
          >
            🔔
          </button>
        </div>
      </div>
    </div>
  );
};

