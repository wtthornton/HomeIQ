/**
 * UpcomingGameCard Component
 * 
 * Displays upcoming games with countdown timer
 */

import React, { useState, useEffect } from 'react';
import type { Game } from '../../types/sports';

interface UpcomingGameCardProps {
  game: Game;
  darkMode?: boolean;
}

export const UpcomingGameCard: React.FC<UpcomingGameCardProps> = ({
  game,
  darkMode = false
}) => {
  const [timeUntil, setTimeUntil] = useState('');

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  // Update countdown timer
  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date();
      const start = new Date(game.start_time);
      const diff = start.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeUntil('Starting soon');
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (hours > 24) {
        const days = Math.floor(hours / 24);
        setTimeUntil(`in ${days}d ${hours % 24}h`);
      } else {
        setTimeUntil(`in ${hours}h ${minutes}m`);
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [game.start_time]);

  return (
    <div className={`card-base card-hover content-fade-in ${cardBg} border ${borderColor} p-4`}>
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className={`text-sm font-semibold ${textSecondary}`}>
          {new Date(game.start_time).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
        <span className="text-sm font-semibold text-amber-500">
          ⏰ {timeUntil}
        </span>
      </div>

      {/* Matchup */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 flex-1">
          <span className="text-2xl">{game.league === 'NFL' ? '🏈' : '🏒'}</span>
          <div className="flex-1">
            <div className={`font-semibold ${textPrimary}`}>
              {game.away_team.abbreviation} @ {game.home_team.abbreviation}
            </div>
            <div className={`text-xs ${textSecondary}`}>
              {game.away_team.name} at {game.home_team.name}
            </div>
          </div>
        </div>

        <button 
          className={`ml-3 px-3 py-1 rounded ${
            darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
          } text-white text-sm transition-colors flex-shrink-0`}
        >
          🔔 Notify
        </button>
      </div>
    </div>
  );
};

