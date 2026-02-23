/**
 * TeamSelector Component
 * 
 * Grid display for team selection with search/filter
 */

import React, { useState, useMemo } from 'react';
import type { Team, League } from '../../types/sports';

interface TeamSelectorProps {
  league: League;
  teams: Team[];
  selectedTeams: string[];
  onTeamToggle: (teamId: string) => void;
  darkMode?: boolean;
}

export const TeamSelector: React.FC<TeamSelectorProps> = ({
  league,
  teams,
  selectedTeams,
  onTeamToggle,
  darkMode = false
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter teams based on search
  const filteredTeams = useMemo(() => {
    if (!searchQuery) return teams;
    
    const query = searchQuery.toLowerCase();
    return teams.filter(team =>
      team.name.toLowerCase().includes(query) ||
      team.abbreviation.toLowerCase().includes(query)
    );
  }, [teams, searchQuery]);

  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const bgPrimary = darkMode ? 'bg-gray-800' : 'bg-white';
  const bgSecondary = darkMode ? 'bg-gray-700' : 'bg-gray-50';
  const borderColor = darkMode ? 'border-gray-600' : 'border-gray-300';

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div>
        <input
          type="text"
          placeholder={`Search ${league} teams...`}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`w-full px-4 py-3 rounded-lg border ${borderColor} ${bgSecondary} ${textPrimary} 
            focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors`}
        />
      </div>

      {/* Selection Summary */}
      <div className={`flex items-center justify-between ${textSecondary} text-sm`}>
        <span>
          {selectedTeams.length} {league} team{selectedTeams.length !== 1 ? 's' : ''} selected
        </span>
        <span className="text-blue-500">
          💡 Recommended: 3-5 teams for best performance
        </span>
      </div>

      {/* Team Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {filteredTeams.map(team => {
          const isSelected = selectedTeams.includes(team.id);
          
          return (
            <button
              key={team.id}
              onClick={() => onTeamToggle(team.id)}
              className={`
                relative p-4 rounded-lg border-2 transition-all duration-200
                ${isSelected 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 scale-105' 
              : `${borderColor} ${bgPrimary} hover:border-blue-300`
            }
                hover:shadow-lg active:scale-95
                min-h-[120px] flex flex-col items-center justify-center
              `}
              style={{
                minWidth: '44px', // Touch-friendly
                minHeight: '44px'
              }}
            >
              {/* Selection Checkbox */}
              <div className="absolute top-2 right-2">
                <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                  isSelected
                    ? 'bg-blue-500 border-blue-500'
                    : `${borderColor}`
                }`}>
                  {isSelected && <span className="text-white text-sm">✓</span>}
                </div>
              </div>

              {/* Team Icon */}
              <div className="text-4xl mb-2">
                {league === 'NFL' ? '🏈' : '🏒'}
              </div>

              {/* Team Name */}
              <div className={`text-center ${textPrimary} font-semibold text-sm`}>
                {team.abbreviation}
              </div>
              <div className={`text-center ${textSecondary} text-xs mt-1`}>
                {team.name}
              </div>

              {/* Team Record */}
              {team.record && (
                <div className={`text-xs ${textSecondary} mt-1`}>
                  {team.record.wins}-{team.record.losses}
                  {team.record.ties !== undefined && `-${team.record.ties}`}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* No Results */}
      {filteredTeams.length === 0 && (
        <div className={`text-center py-12 ${textSecondary}`}>
          No teams found matching "{searchQuery}"
        </div>
      )}
    </div>
  );
};

