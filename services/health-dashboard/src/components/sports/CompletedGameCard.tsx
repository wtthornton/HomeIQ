/**
 * CompletedGameCard Component
 * 
 * Displays completed games with final scores
 */

import React from 'react';
import type { Game } from '../../types/sports';

interface CompletedGameCardProps {
  game: Game;
  darkMode?: boolean;
  onViewDetails?: (game: Game) => void;
}

export const CompletedGameCard: React.FC<CompletedGameCardProps> = ({
  game,
  darkMode = false,
  onViewDetails
}) => {
  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  const winner = game.score.home > game.score.away ? 'home' : 'away';
  
  return (
    <div className={`card-base card-hover content-fade-in ${cardBg} border ${borderColor} p-4`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className={`text-sm font-semibold ${textSecondary} uppercase`}>
          Final
        </span>
        <span className={`text-xs ${textSecondary}`}>
          {new Date(game.startTime).toLocaleDateString()}
        </span>
      </div>

      {/* Matchup & Scores */}
      <div className="space-y-2">
        {/* Away Team */}
        <div className={`flex items-center justify-between p-2 rounded ${
          winner === 'away' ? (darkMode ? 'bg-green-900/30' : 'bg-green-50') : ''
        }`}>
          <div className="flex items-center space-x-3">
            <span className="text-xl">{game.league === 'NFL' ? '🏈' : '🏒'}</span>
            <div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.awayTeam.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.awayTeam.record && 
                  `${game.awayTeam.record.wins}-${game.awayTeam.record.losses}`
                }
              </div>
            </div>
          </div>
          <div className={`text-2xl font-bold ${textPrimary}`}>
            {game.score.away}
          </div>
        </div>

        {/* Home Team */}
        <div className={`flex items-center justify-between p-2 rounded ${
          winner === 'home' ? (darkMode ? 'bg-green-900/30' : 'bg-green-50') : ''
        }`}>
          <div className="flex items-center space-x-3">
            <span className="text-xl">{game.league === 'NFL' ? '🏈' : '🏒'}</span>
            <div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.homeTeam.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.homeTeam.record && 
                  `${game.homeTeam.record.wins}-${game.homeTeam.record.losses}`
                }
              </div>
            </div>
          </div>
          <div className={`text-2xl font-bold ${textPrimary}`}>
            {game.score.home}
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button 
        onClick={() => onViewDetails?.(game)}
        className={`w-full mt-3 py-2 px-4 rounded-lg ${
          darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'
        } ${textPrimary} text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
        aria-label={`View details for ${game.awayTeam.name} vs ${game.homeTeam.name}`}
      >
        <span aria-hidden="true">📊</span> View Details
      </button>
    </div>
  );
};

