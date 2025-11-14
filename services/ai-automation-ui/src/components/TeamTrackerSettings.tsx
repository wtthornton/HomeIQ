/**
 * Team Tracker Settings Component
 * Manage Team Tracker integration and team configuration
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';

// API Base URL
const DEVICE_INTELLIGENCE_API = 'http://localhost:8028/api/team-tracker';

// Types
interface TeamTrackerStatus {
  is_installed: boolean;
  installation_status: string;
  version?: string;
  last_checked: string;
  configured_teams_count: number;
  active_teams_count: number;
}

interface Team {
  id: number;
  team_id: string;
  league_id: string;
  team_name: string;
  team_long_name?: string;
  entity_id?: string;
  sensor_name?: string;
  is_active: boolean;
  sport?: string;
  team_abbreviation?: string;
  team_logo?: string;
  configured_in_ha: boolean;
  last_detected?: string;
  user_notes?: string;
  priority: number;
  created_at: string;
  updated_at: string;
}

interface TeamFormData {
  team_id: string;
  league_id: string;
  team_name: string;
  team_long_name?: string;
  entity_id?: string;
  sensor_name?: string;
  is_active: boolean;
  sport?: string;
  user_notes?: string;
  priority: number;
}

// API Functions
const fetchStatus = async (): Promise<TeamTrackerStatus> => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/status`);
  if (!response.ok) throw new Error('Failed to fetch Team Tracker status');
  return response.json();
};

const fetchTeams = async (activeOnly: boolean = false): Promise<Team[]> => {
  const params = new URLSearchParams({ active_only: activeOnly.toString() });
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/teams?${params}`);
  if (!response.ok) throw new Error('Failed to fetch teams');
  return response.json();
};

const detectTeams = async () => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/detect`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to detect teams');
  return response.json();
};

const addTeam = async (team: TeamFormData): Promise<Team> => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/teams`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(team),
  });
  if (!response.ok) throw new Error('Failed to add team');
  return response.json();
};

const updateTeam = async ({ id, team }: { id: number; team: TeamFormData }): Promise<Team> => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/teams/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(team),
  });
  if (!response.ok) throw new Error('Failed to update team');
  return response.json();
};

const deleteTeam = async (id: number): Promise<void> => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/teams/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete team');
};

const syncFromHA = async () => {
  const response = await fetch(`${DEVICE_INTELLIGENCE_API}/sync-from-ha`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to sync from Home Assistant');
  return response.json();
};

// Main Component
export const TeamTrackerSettings: React.FC = () => {
  const { darkMode } = useAppStore();
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  // Queries
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['teamTrackerStatus'],
    queryFn: fetchStatus,
    refetchInterval: 30000, // Refresh every 30s
  });

  const { data: teams = [], isLoading: teamsLoading } = useQuery({
    queryKey: ['teamTrackerTeams', showInactive],
    queryFn: () => fetchTeams(!showInactive),
    enabled: status?.is_installed === true,
  });

  // Mutations
  const detectMutation = useMutation({
    mutationFn: detectTeams,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamTrackerStatus'] });
      queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
      toast.success('✅ Team Tracker entities detected!');
    },
    onError: () => toast.error('❌ Failed to detect Team Tracker entities'),
  });

  const syncMutation = useMutation({
    mutationFn: syncFromHA,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamTrackerStatus'] });
      queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
      toast.success('✅ Teams synchronized from Home Assistant!');
    },
    onError: () => toast.error('❌ Failed to sync teams'),
  });

  const addMutation = useMutation({
    mutationFn: addTeam,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
      toast.success('✅ Team added successfully!');
      setShowAddForm(false);
    },
    onError: () => toast.error('❌ Failed to add team'),
  });

  const updateMutation = useMutation({
    mutationFn: updateTeam,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
      toast.success('✅ Team updated successfully!');
      setEditingTeam(null);
    },
    onError: () => toast.error('❌ Failed to update team'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTeam,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
      toast.success('✅ Team deleted successfully!');
    },
    onError: () => toast.error('❌ Failed to delete team'),
  });

  const handleAddTeam = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const team: TeamFormData = {
      team_id: formData.get('team_id') as string,
      league_id: formData.get('league_id') as string,
      team_name: formData.get('team_name') as string,
      team_long_name: formData.get('team_long_name') as string || undefined,
      entity_id: formData.get('entity_id') as string || undefined,
      sport: formData.get('sport') as string || undefined,
      is_active: true,
      priority: 0,
    };
    addMutation.mutate(team);
  };

  const handleUpdateTeam = (team: Team, updates: Partial<TeamFormData>) => {
    updateMutation.mutate({
      id: team.id,
      team: {
        team_id: team.team_id,
        league_id: team.league_id,
        team_name: team.team_name,
        team_long_name: team.team_long_name,
        entity_id: team.entity_id,
        sensor_name: team.sensor_name,
        is_active: team.is_active,
        sport: team.sport,
        user_notes: team.user_notes,
        priority: team.priority,
        ...updates,
      },
    });
  };

  const handleDeleteTeam = (id: number, teamName: string) => {
    if (confirm(`Delete ${teamName}?`)) {
      deleteMutation.mutate(id);
    }
  };

  if (statusLoading) {
    return (
      <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Loading Team Tracker status...</p>
      </div>
    );
  }

  return (
    <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🏈 Team Tracker Integration
          </h2>
          <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Track sports teams for automation triggers
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
                : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300'
            }`}
          >
            {detectMutation.isPending ? 'Detecting...' : 'Detect Teams'}
          </button>
          {status?.is_installed && (
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-700'
                  : 'bg-green-500 hover:bg-green-600 text-white disabled:bg-gray-300'
              }`}
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync from HA'}
            </button>
          )}
        </div>
      </div>

      {/* Status Badge */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              status?.is_installed
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
            }`}
          >
            {status?.is_installed ? '✓ Installed' : '⚠ Not Installed'}
          </span>
          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {status?.configured_teams_count || 0} teams configured • {status?.active_teams_count || 0} active
          </span>
        </div>

        {!status?.is_installed && (
          <div className={`mt-4 p-4 rounded-lg border ${darkMode ? 'bg-yellow-900/20 border-yellow-800' : 'bg-yellow-50 border-yellow-200'}`}>
            <p className={`text-sm ${darkMode ? 'text-yellow-200' : 'text-yellow-800'}`}>
              <strong>Team Tracker not detected.</strong> Install it in Home Assistant:{' '}
              <a
                href="https://github.com/vasqued2/ha-teamtracker"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:no-underline"
              >
                GitHub Repository
              </a>
            </p>
          </div>
        )}
      </div>

      {/* Teams List */}
      {status?.is_installed && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Configured Teams
            </h3>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={showInactive}
                  onChange={(e) => setShowInactive(e.target.checked)}
                  className="rounded"
                />
                <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Show inactive</span>
              </label>
              <button
                onClick={() => setShowAddForm(true)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  darkMode
                    ? 'bg-purple-600 hover:bg-purple-700 text-white'
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
                }`}
              >
                + Add Team
              </button>
            </div>
          </div>

          {teamsLoading ? (
            <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Loading teams...</p>
          ) : teams.length === 0 ? (
            <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
              No teams configured. Click "Add Team" or "Detect Teams" to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {teams.map((team) => (
                <motion.div
                  key={team.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-lg border ${
                    darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                          {team.team_name}
                        </h4>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            darkMode ? 'bg-gray-600 text-gray-200' : 'bg-gray-200 text-gray-700'
                          }`}
                        >
                          {team.league_id}
                        </span>
                        {team.configured_in_ha && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            ✓ In HA
                          </span>
                        )}
                      </div>
                      {team.entity_id && (
                        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Entity: <code className={`px-1 py-0.5 rounded ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`}>{team.entity_id}</code>
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={team.is_active}
                          onChange={(e) => handleUpdateTeam(team, { is_active: e.target.checked })}
                          className="rounded"
                        />
                        <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Active</span>
                      </label>
                      <button
                        onClick={() => handleDeleteTeam(team.id, team.team_name)}
                        className={`p-2 rounded-lg transition-colors ${
                          darkMode
                            ? 'hover:bg-red-900/50 text-red-400'
                            : 'hover:bg-red-50 text-red-600'
                        }`}
                        title="Delete team"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {/* Add Team Form */}
          <AnimatePresence>
            {showAddForm && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                onClick={() => setShowAddForm(false)}
              >
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className={`w-full max-w-md rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <h3 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Add Team
                  </h3>
                  <form onSubmit={handleAddTeam} className="space-y-4">
                    <div>
                      <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Team Name *
                      </label>
                      <input
                        name="team_name"
                        required
                        placeholder="Dallas Cowboys"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      />
                    </div>
                    <div>
                      <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Team ID/Abbreviation *
                      </label>
                      <input
                        name="team_id"
                        required
                        placeholder="DAL"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      />
                    </div>
                    <div>
                      <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        League *
                      </label>
                      <select
                        name="league_id"
                        required
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      >
                        <option value="NFL">NFL</option>
                        <option value="NBA">NBA</option>
                        <option value="MLB">MLB</option>
                        <option value="NHL">NHL</option>
                        <option value="MLS">MLS</option>
                        <option value="NCAAF">NCAA Football</option>
                        <option value="NCAAB">NCAA Basketball</option>
                      </select>
                    </div>
                    <div>
                      <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Entity ID (optional)
                      </label>
                      <input
                        name="entity_id"
                        placeholder="sensor.team_tracker_cowboys"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      />
                    </div>
                    <div className="flex gap-3 mt-6">
                      <button
                        type="button"
                        onClick={() => setShowAddForm(false)}
                        className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                          darkMode
                            ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                            : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                        }`}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={addMutation.isPending}
                        className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                          darkMode
                            ? 'bg-purple-600 hover:bg-purple-700 text-white disabled:bg-gray-700'
                            : 'bg-purple-500 hover:bg-purple-600 text-white disabled:bg-gray-300'
                        }`}
                      >
                        {addMutation.isPending ? 'Adding...' : 'Add Team'}
                      </button>
                    </div>
                  </form>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};
