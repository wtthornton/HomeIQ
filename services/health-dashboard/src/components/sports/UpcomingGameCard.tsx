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
  onViewDetails?: (game: Game) => void;
}

export const UpcomingGameCard: React.FC<UpcomingGameCardProps> = ({
  game,
  darkMode = false,
  onViewDetails
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
      const start = new Date(game.startTime);
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
  }, [game.startTime]);

  return (
    <article 
      className={`card-base card-hover content-fade-in ${cardBg} border ${borderColor} p-4`}
      aria-label={`Upcoming game: ${game.awayTeam.name} at ${game.homeTeam.name}, ${timeUntil}`}
    >
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <time 
          className={`text-sm font-semibold ${textSecondary}`}
          dateTime={game.startTime}
        >
          {new Date(game.startTime).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </time>
        <span className="text-sm font-semibold text-amber-500" aria-label={`Game starts ${timeUntil}`}>
          <span aria-hidden="true">⏰</span> {timeUntil}
        </span>
      </div>

      {/* Matchup */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 flex-1">
          <span className="text-2xl">{game.league === 'NFL' ? '🏈' : '🏒'}</span>
          <div className="flex-1">
            <div className={`font-semibold ${textPrimary}`}>
              {game.awayTeam.abbreviation} @ {game.homeTeam.abbreviation}
            </div>
            <div className={`text-xs ${textSecondary}`}>
              {game.awayTeam.name} at {game.homeTeam.name}
            </div>
          </div>
        </div>

        <button 
          className={`ml-3 px-3 py-1 rounded ${
            darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
          } text-white text-sm transition-colors flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
          aria-label={`Set notification for ${game.awayTeam.name} at ${game.homeTeam.name}`}
        >
          <span aria-hidden="true">🔔</span> Notify
        </button>
      </div>
    </article>
  );
};

