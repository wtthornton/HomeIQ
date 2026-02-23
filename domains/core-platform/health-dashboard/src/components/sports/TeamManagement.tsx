/**
 * TeamManagement Component
 * 
 * Interface for managing selected teams after initial setup
 */

import React, { useState } from 'react';
import type { Team, League } from '../../types/sports';
import { calculateAPIUsage, getUsageColor } from '../../utils/apiUsageCalculator';

interface TeamManagementProps {
  nflTeams: string[];
  nhlTeams: string[];
  availableNFLTeams: Team[];
  availableNHLTeams: Team[];
  onAddTeam: (league: League, teamId: string) => void;
  onRemoveTeam: (league: League, teamId: string) => void;
  darkMode?: boolean;
}

export const TeamManagement: React.FC<TeamManagementProps> = ({
  nflTeams,
  nhlTeams,
  availableNFLTeams,
  availableNHLTeams,
  onAddTeam,
  onRemoveTeam,
  darkMode = false
}) => {
  const [showAddTeam, setShowAddTeam] = useState(false);
  const [addingLeague, setAddingLeague] = useState<League | null>(null);

  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const bgCard = darkMode ? 'bg-gray-800' : 'bg-white';
  const bgSecondary = darkMode ? 'bg-gray-700' : 'bg-gray-50';
  const borderColor = darkMode ? 'border-gray-600' : 'border-gray-300';

  const apiUsage = calculateAPIUsage(nflTeams, nhlTeams);

  const handleOpenAddTeam = (league: League) => {
    setAddingLeague(league);
    setShowAddTeam(true);
  };

  const handleAddTeamClick = (teamId: string) => {
    if (addingLeague) {
      onAddTeam(addingLeague, teamId);
      setShowAddTeam(false);
      setAddingLeague(null);
    }
  };

  const getTeamInfo = (teamId: string, league: League): Team | undefined => {
    return league === 'NFL'
      ? availableNFLTeams.find(t => t.id === teamId)
      : availableNHLTeams.find(t => t.id === teamId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
          ⚙️ Manage Tracked Teams
        </h2>
        <p className={textSecondary}>
          Add or remove teams from your dashboard
        </p>
      </div>

      {/* NFL Teams Section */}
      <div className={`${bgCard} rounded-xl p-6 shadow-md`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-xl font-semibold ${textPrimary}`}>
            🏈 NFL Teams ({nflTeams.length} selected)
          </h3>
          <button
            onClick={() => handleOpenAddTeam('NFL')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-blue-500 hover:bg-blue-600'
            } text-white`}
          >
            + Add Team
          </button>
        </div>

        {nflTeams.length > 0 ? (
          <div className="space-y-3">
            {nflTeams.map(teamId => {
              const team = getTeamInfo(teamId, 'NFL');
              if (!team) return null;

              return (
                <div
                  key={teamId}
                  className={`p-4 rounded-lg ${bgSecondary} flex items-center justify-between`}
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">🏈</div>
                    <div>
                      <div className={`font-semibold ${textPrimary}`}>
                        {team.name}
                      </div>
                      {team.record && (
                        <div className={`text-sm ${textSecondary}`}>
                          Record: {team.record.wins}-{team.record.losses}
                          {team.record.ties !== undefined && `-${team.record.ties}`}
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveTeam('NFL', teamId)}
                    className="px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    title="Remove team"
                  >
                    🗑️
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className={`text-center py-8 ${textSecondary}`}>
            No NFL teams selected. Click "+ Add Team" to get started.
          </div>
        )}
      </div>

      {/* NHL Teams Section */}
      <div className={`${bgCard} rounded-xl p-6 shadow-md`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-xl font-semibold ${textPrimary}`}>
            🏒 NHL Teams ({nhlTeams.length} selected)
          </h3>
          <button
            onClick={() => handleOpenAddTeam('NHL')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-blue-500 hover:bg-blue-600'
            } text-white`}
          >
            + Add Team
          </button>
        </div>

        {nhlTeams.length > 0 ? (
          <div className="space-y-3">
            {nhlTeams.map(teamId => {
              const team = getTeamInfo(teamId, 'NHL');
              if (!team) return null;

              return (
                <div
                  key={teamId}
                  className={`p-4 rounded-lg ${bgSecondary} flex items-center justify-between`}
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">🏒</div>
                    <div>
                      <div className={`font-semibold ${textPrimary}`}>
                        {team.name}
                      </div>
                      {team.record && (
                        <div className={`text-sm ${textSecondary}`}>
                          Record: {team.record.wins}-{team.record.losses}
                          {team.record.ties !== undefined && `-${team.record.ties}`}
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveTeam('NHL', teamId)}
                    className="px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    title="Remove team"
                  >
                    🗑️
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className={`text-center py-8 ${textSecondary}`}>
            No NHL teams selected. Click "+ Add Team" to get started.
          </div>
        )}
      </div>

      {/* API Usage Summary */}
      <div className={`${bgCard} rounded-xl p-6 shadow-md`}>
        <h3 className={`text-lg font-semibold ${textPrimary} mb-4`}>
          📊 Current API Usage
        </h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className={textSecondary}>Estimated calls today:</span>
            <span className={`font-bold ${getUsageColor(apiUsage.warning_level)}`}>
              {apiUsage.daily_calls} / 100
            </span>
          </div>
          <div className={`text-sm ${textSecondary}`}>
            {apiUsage.recommendation}
          </div>
        </div>
      </div>

      {/* Add Team Modal (Simple Version) */}
      {showAddTeam && addingLeague && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className={`${bgCard} rounded-xl p-6 max-w-4xl w-full max-h-[80vh] overflow-y-auto`}>
            <div className="flex justify-between items-center mb-6">
              <h3 className={`text-xl font-bold ${textPrimary}`}>
                Add {addingLeague} Team
              </h3>
              <button
                onClick={() => {
                  setShowAddTeam(false);
                  setAddingLeague(null);
                }}
                className={`text-2xl ${textSecondary} hover:${textPrimary}`}
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {(addingLeague === 'NFL' ? availableNFLTeams : availableNHLTeams)
                .filter(team => !(addingLeague === 'NFL' ? nflTeams : nhlTeams).includes(team.id))
                .map(team => (
                  <button
                    key={team.id}
                    onClick={() => handleAddTeamClick(team.id)}
                    className={`p-4 rounded-lg border ${borderColor} hover:border-blue-500 
                      hover:shadow-lg transition-all ${bgSecondary}`}
                  >
                    <div className="text-3xl mb-2">
                      {addingLeague === 'NFL' ? '🏈' : '🏒'}
                    </div>
                    <div className={`text-sm font-semibold ${textPrimary}`}>
                      {team.abbreviation}
                    </div>
                    <div className={`text-xs ${textSecondary} mt-1`}>
                      {team.name}
                    </div>
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

