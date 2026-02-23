/**
 * Admin Page
 *
 * System administration and management interface.
 * Matches the styling of the suggestions page.
 */

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store';
import {
  getAdminConfig,
  getAdminOverview,
  getTrainingRuns,
  triggerTrainingRun,
  getGNNTrainingRuns,
  triggerGNNTrainingRun,
  getGNNTrainingStatus,
  deleteTrainingRun,
  clearOldTrainingRuns,
  type TrainingRunRecord,
} from '../api/admin';

const STATUS_BADGE_STYLES: Record<string, string> = {
  healthy: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  degraded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  offline: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  online: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

export const Admin: React.FC = () => {
  const { darkMode } = useAppStore();
  const queryClient = useQueryClient();
  const [expandedErrorRunId, setExpandedErrorRunId] = useState<number | null>(null);
  const [errorModalRun, setErrorModalRun] = useState<TrainingRunRecord | null>(null);

  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewError,
  } = useQuery({
    queryKey: ['admin-overview'],
    queryFn: getAdminOverview,
    retry: 1,
  });

  const {
    data: config,
    isLoading: configLoading,
    isError: configError,
  } = useQuery({
    queryKey: ['admin-config'],
    queryFn: getAdminConfig,
    retry: 1,
  });

  const {
    data: trainingRuns,
    isLoading: trainingRunsLoading,
    isFetching: trainingRunsFetching,
  } = useQuery({
    queryKey: ['training-runs'],
    queryFn: () => getTrainingRuns(25),
    refetchInterval: 60_000,
  });

  const {
    data: gnnTrainingRuns,
    isLoading: gnnTrainingRunsLoading,
    isFetching: gnnTrainingRunsFetching,
  } = useQuery({
    queryKey: ['gnn-training-runs'],
    queryFn: () => getGNNTrainingRuns(25),
    refetchInterval: 60_000,
  });

  const {
    data: gnnTrainingStatus,
  } = useQuery({
    queryKey: ['gnn-training-status'],
    queryFn: getGNNTrainingStatus,
    refetchInterval: 30_000,
  });

  const trainingMutation = useMutation({
    mutationFn: triggerTrainingRun,
    onSuccess: () => {
      toast.success('✅ Training job started');
      queryClient.invalidateQueries({ queryKey: ['training-runs'] });
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] });
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to trigger training';
      toast.error(`❌ ${message}`);
    },
  });

  const deleteTrainingMutation = useMutation({
    mutationFn: deleteTrainingRun,
    onSuccess: () => {
      toast.success('✅ Training run deleted')
      queryClient.invalidateQueries({ queryKey: ['training-runs'] })
      queryClient.invalidateQueries({ queryKey: ['gnn-training-runs'] })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to delete training run'
      toast.error(`❌ ${message}`)
    },
  })

  const clearOldRunsMutation = useMutation({
    mutationFn: (params: { trainingType?: string; olderThanDays?: number; keepRecent?: number }) =>
      clearOldTrainingRuns(params.trainingType, params.olderThanDays, params.keepRecent),
    onSuccess: (data) => {
      toast.success(`✅ Deleted ${data.deleted_count} old training run(s)`)
      queryClient.invalidateQueries({ queryKey: ['training-runs'] })
      queryClient.invalidateQueries({ queryKey: ['gnn-training-runs'] })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to clear old runs'
      toast.error(`❌ ${message}`)
    },
  })

  const gnnTrainingMutation = useMutation({
    mutationFn: () => triggerGNNTrainingRun(),
    onSuccess: () => {
      toast.success('✅ GNN training job started');
      queryClient.invalidateQueries({ queryKey: ['gnn-training-runs'] });
      queryClient.invalidateQueries({ queryKey: ['gnn-training-status'] });
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to trigger GNN training';
      toast.error(`❌ ${message}`);
    },
  });

  const stats = useMemo(() => ([
    {
      label: 'Total Suggestions',
      value: overview?.totalSuggestions ?? 0,
      icon: '💡',
      badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    },
    {
      label: 'Active Automations',
      value: overview?.activeAutomations ?? 0,
      icon: '🚀',
      badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    },
    {
      label: 'System Health',
      value: overview?.systemStatus ?? 'unknown',
      icon: '💚',
      badgeClass: STATUS_BADGE_STYLES[(overview?.systemStatus ?? '').toLowerCase()] ?? STATUS_BADGE_STYLES.healthy,
    },
    {
      label: 'API Status',
      value: overview?.apiStatus ?? 'unknown',
      icon: '🔌',
      badgeClass: STATUS_BADGE_STYLES[(overview?.apiStatus ?? '').toLowerCase()] ?? STATUS_BADGE_STYLES.online,
    },
  ]), [overview]);

  const modelStatusItems = useMemo(() => ([
    {
      label: 'Soft Prompt Fallback',
      detail: overview?.softPromptEnabled ? 'Enabled' : 'Disabled',
      status: overview?.softPromptEnabled
        ? overview?.softPromptLoaded ? 'Loaded' : 'Not Loaded'
        : '—',
      helper: overview?.softPromptModelId ?? 'N/A',
    },
    {
      label: 'Guardrail Checker',
      detail: overview?.guardrailEnabled ? 'Enabled' : 'Disabled',
      status: overview?.guardrailEnabled
        ? overview?.guardrailLoaded ? 'Ready' : 'Not Ready'
        : '—',
      helper: overview?.guardrailModelName ?? 'N/A',
    },
  ]), [overview]);

  const hasActiveTrainingRun = useMemo(
    () => trainingRuns?.some((run) => run.status === 'running') ?? false,
    [trainingRuns],
  );

  const hasActiveGNNTrainingRun = useMemo(
    () => gnnTrainingRuns?.some((run) => run.status === 'running') ?? false,
    [gnnTrainingRuns],
  );

  const configItems = useMemo(() => ([
    { label: 'Data API URL', value: config?.dataApiUrl ?? '—' },
    { label: 'Database Path', value: config?.databasePath ?? '—' },
    { label: 'Log Level', value: config?.logLevel ?? '—' },
    { label: 'Primary OpenAI Model', value: config?.openaiModel ?? '—' },
    { label: 'Soft Prompt Directory', value: config?.softPromptModelDir ?? '—' },
    { label: 'Guardrail Model', value: config?.guardrailModelName ?? '—' },
  ]), [config]);

  const hasError = overviewError || configError;

  return (
    <div className="space-y-6">
      {/* Header - Modern 2025 Design */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                🔧 Admin Dashboard
              </h1>
            </div>
            <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              System administration and management
            </p>
          </div>
          <div className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {overviewLoading ? 'Loading status…' : `System Status: ${overview?.systemStatus ?? 'unknown'}`}
          </div>
        </div>
      </motion.div>

      {/* Info Banner - Glassmorphism */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-4 ${darkMode ? 'bg-blue-900/40 border-blue-700/50' : 'bg-blue-50/80 border-blue-200/50'} border backdrop-blur-sm shadow-lg`}
      >
        <div className="flex items-start gap-3">
          <span className="text-2xl">🔧</span>
          <div className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
            <strong>Admin Access:</strong> Manage system settings, view statistics, and monitor system health.
            Access to advanced features and configuration options.
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`rounded-xl p-4 border ${
              darkMode
                ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
                : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{stat.icon}</span>
              <span className={`text-xs px-2 py-1 rounded ${stat.badgeClass}`}>
                {stat.value}
              </span>
            </div>
            <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {stat.label}
            </h3>
          </motion.div>
        ))}
      </div>

      {hasError && (
        <div className={`rounded-lg p-4 border ${darkMode ? 'bg-red-900/20 border-red-800 text-red-200' : 'bg-red-50 border-red-200 text-red-700'}`}>
          Unable to load some dashboard data. Please verify the backend service is reachable.
        </div>
      )}

      {/* Admin Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`rounded-xl p-6 border shadow-lg ${
            darkMode
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
          <h2 className={`text-lg font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            ⚙️ System Settings
          </h2>
          {configLoading ? (
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Loading configuration…</div>
          ) : (
            <dl className="space-y-3">
              {configItems.map((item) => (
                <div
                  key={item.label}
                  className={`px-4 py-3 rounded-lg ${
                    darkMode
                      ? 'bg-gray-700 text-gray-200'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  <dt className="text-xs uppercase tracking-wide opacity-70">{item.label}</dt>
                  <dd className="text-sm font-medium break-all">{item.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </motion.div>

        {/* System Monitoring */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`rounded-xl p-6 border shadow-lg ${
            darkMode
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
          <h2 className={`text-lg font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 System Monitoring
          </h2>
          {overviewLoading ? (
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Loading runtime status…</div>
          ) : (
            <dl className="space-y-3">
              {modelStatusItems.map((item) => (
                <div
                  key={item.label}
                  className={`px-4 py-3 rounded-lg ${
                    darkMode
                      ? 'bg-gray-700 text-gray-200'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <dt className="text-xs uppercase tracking-wide opacity-70">{item.label}</dt>
                      <dd className="text-sm font-medium">{item.detail}</dd>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded ${
                      item.status === 'Loaded' || item.status === 'Ready'
                        ? STATUS_BADGE_STYLES.healthy
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="text-xs mt-2 opacity-70 break-all">{item.helper}</p>
                </div>
              ))}
              <div
                className={`px-4 py-3 rounded-lg border ${
                  darkMode
                    ? 'bg-gray-800 border-gray-700 text-gray-300'
                    : 'bg-white border-gray-200 text-gray-600'
                }`}
              >
                <p className="text-xs uppercase tracking-wide opacity-70">Last Updated</p>
                <p className="text-sm font-medium">{overview?.updatedAt ? new Date(overview.updatedAt).toLocaleString() : '—'}</p>
              </div>
            </dl>
          )}
        </motion.div>
      </div>

      {/* Training & Model Maintenance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className={`rounded-lg p-6 border ${
          darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🛠️ Training & Model Maintenance
            </h2>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Manage local soft prompt fine-tuning jobs and review previous runs.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (
                  window.confirm(
                    'Delete training runs older than 30 days (keeping the 10 most recent)? This action cannot be undone.'
                  )
                ) {
                  clearOldRunsMutation.mutate({ trainingType: 'soft_prompt', olderThanDays: 30, keepRecent: 10 })
                }
              }}
              disabled={clearOldRunsMutation.isPending}
              className={`px-3 py-1.5 text-xs rounded ${
                darkMode
                  ? 'bg-yellow-900/30 text-yellow-300 hover:bg-yellow-900/50 disabled:opacity-50'
                  : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50'
              }`}
              title="Clear old training runs (keeps 10 most recent)"
            >
              🧹 Clear Old
            </button>
            <button
              type="button"
              onClick={() => trainingMutation.mutate()}
              disabled={trainingMutation.isPending || hasActiveTrainingRun}
              className={`px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
                darkMode
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
              } disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none`}
            >
              {trainingMutation.isPending
                ? '🚧 Starting…'
                : hasActiveTrainingRun
                  ? '⏳ Training In Progress'
                  : '🚀 Start Training'}
            </button>
          </div>
        </div>

        <div className={`rounded-lg border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          {trainingRunsLoading ? (
            <div className={`p-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Loading training history…
            </div>
          ) : trainingRuns && trainingRuns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className={`min-w-full text-sm ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                <thead className={darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}>
                  <tr>
                    <th className="px-4 py-2 text-left">Run</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Samples</th>
                    <th className="px-4 py-2 text-left">Loss</th>
                    <th className="px-4 py-2 text-left">Started</th>
                    <th className="px-4 py-2 text-left">Finished</th>
                    <th className="px-4 py-2 text-left">Notes</th>
                    <th className="px-4 py-2 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingRuns.map((run: TrainingRunRecord) => (
                    <tr
                      key={run.id}
                      className={darkMode ? 'odd:bg-gray-800 even:bg-gray-900/40' : 'odd:bg-white even:bg-gray-50'}
                    >
                      <td className="px-4 py-2 font-medium">{run.runIdentifier ?? `run-${run.id}`}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            run.status === 'completed'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                              : run.status === 'running'
                                ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                                : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{run.datasetSize ?? '—'}</td>
                      <td className="px-4 py-2">{run.finalLoss != null ? run.finalLoss.toFixed(4) : '—'}</td>
                      <td className="px-4 py-2">{run.startedAt ? new Date(run.startedAt).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2">{run.finishedAt ? new Date(run.finishedAt).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2 text-xs">
                        {run.errorMessage ? (
                          <div className="space-y-1">
                            <div className={`${darkMode ? 'text-red-300' : 'text-red-600'} font-mono text-[10px] break-words`}>
                              {expandedErrorRunId === run.id 
                                ? run.errorMessage 
                                : run.errorMessage.length > 160 
                                  ? `${run.errorMessage.slice(0, 160)}...` 
                                  : run.errorMessage}
                            </div>
                            {run.errorMessage.length > 160 && (
                              <button
                                onClick={() => setExpandedErrorRunId(expandedErrorRunId === run.id ? null : run.id)}
                                className={`text-xs underline ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-800'}`}
                              >
                                {expandedErrorRunId === run.id ? 'Show less' : 'Show full error'}
                              </button>
                            )}
                            <button
                              onClick={() => setErrorModalRun(run)}
                              className={`text-xs underline ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-800'}`}
                              title="View full error in modal"
                            >
                              📋 View in modal
                            </button>
                          </div>
                        ) : (
                          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                            {run.baseModel ?? '—'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => {
                            if (window.confirm(`Delete training run "${run.runIdentifier ?? `run-${run.id}`}"?`)) {
                              deleteTrainingMutation.mutate(run.id)
                            }
                          }}
                          disabled={deleteTrainingMutation.isPending || run.status === 'running'}
                          className={`px-2 py-1 text-xs rounded ${
                            darkMode
                              ? 'bg-red-900/30 text-red-300 hover:bg-red-900/50 disabled:opacity-50 disabled:cursor-not-allowed'
                              : 'bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed'
                          }`}
                          title={run.status === 'running' ? 'Cannot delete running training job' : 'Delete this training run'}
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={`p-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              No training runs recorded yet.
            </div>
          )}
          {trainingRunsFetching && !trainingRunsLoading && (
            <div className={`p-3 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Refreshing…
            </div>
          )}
        </div>
      </motion.div>

      {/* GNN Synergy Training Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className={`rounded-lg p-6 border ${
          darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🧠 GNN Synergy Training
            </h2>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Train Graph Neural Network model for synergy detection from {gnnTrainingStatus?.modelInfo?.training_date ? 'existing' : 'available'} synergies.
            </p>
            {gnnTrainingStatus?.modelExists && (
              <p className={`text-xs mt-1 ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                ✓ Model exists at {gnnTrainingStatus.modelPath.split('/').pop()}
                {gnnTrainingStatus.modelInfo?.training_date && ` (trained: ${new Date(gnnTrainingStatus.modelInfo.training_date).toLocaleDateString()})`}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => gnnTrainingMutation.mutate()}
            disabled={gnnTrainingMutation.isPending || hasActiveGNNTrainingRun}
            className={`px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
              darkMode
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg shadow-purple-500/30'
                : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg shadow-purple-400/30'
            } disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none`}
          >
            {gnnTrainingMutation.isPending
              ? '🚧 Starting…'
              : hasActiveGNNTrainingRun
                ? '⏳ Training In Progress'
                : '🚀 Start GNN Training'}
          </button>
        </div>

        <div className={`rounded-lg border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          {gnnTrainingRunsLoading ? (
            <div className={`p-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Loading GNN training history…
            </div>
          ) : gnnTrainingRuns && gnnTrainingRuns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className={`min-w-full text-sm ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                <thead className={darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}>
                  <tr>
                    <th className="px-4 py-2 text-left">Run</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Pairs</th>
                    <th className="px-4 py-2 text-left">Val Loss</th>
                    <th className="px-4 py-2 text-left">Val Acc</th>
                    <th className="px-4 py-2 text-left">Started</th>
                    <th className="px-4 py-2 text-left">Finished</th>
                    <th className="px-4 py-2 text-left">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {gnnTrainingRuns.map((run: TrainingRunRecord) => (
                    <tr
                      key={run.id}
                      className={darkMode ? 'odd:bg-gray-800 even:bg-gray-900/40' : 'odd:bg-white even:bg-gray-50'}
                    >
                      <td className="px-4 py-2 font-medium">{run.runIdentifier ?? `gnn-run-${run.id}`}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            run.status === 'completed'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                              : run.status === 'running'
                                ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                                : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{run.datasetSize ?? '—'}</td>
                      <td className="px-4 py-2">{run.finalLoss != null ? run.finalLoss.toFixed(4) : '—'}</td>
                      <td className="px-4 py-2">—</td>
                      <td className="px-4 py-2">{run.startedAt ? new Date(run.startedAt).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2">{run.finishedAt ? new Date(run.finishedAt).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2 text-xs">
                        {run.errorMessage ? (
                          <span className="text-red-500">{run.errorMessage.slice(-80)}</span>
                        ) : (
                          run.baseModel ?? '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={`p-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              No GNN training runs recorded yet.
            </div>
          )}
          {gnnTrainingRunsFetching && !gnnTrainingRunsLoading && (
            <div className={`p-3 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Refreshing…
            </div>
          )}
        </div>
      </motion.div>

      {/* Footer Info - Glassmorphism */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className={`rounded-xl p-6 ${darkMode ? 'bg-slate-900/60 border-gray-700/50' : 'bg-white/80 border-gray-200/50'} border backdrop-blur-sm shadow-lg`}
      >
        <div className={`text-sm space-y-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>
            <strong>🔧 Admin Functions:</strong> This page provides access to system administration features.
          </p>
          <p>
            <strong>📊 Monitoring:</strong> View system health, performance metrics, and activity logs.
          </p>
          <p>
            <strong>⚙️ Configuration:</strong> Manage system settings, API keys, and security options.
          </p>
          <p className="text-xs opacity-70">
            💡 For detailed system monitoring, visit the{' '}
            <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-400">
              health dashboard
            </a>
          </p>
        </div>
      </motion.div>

      {/* Error Message Modal */}
      {errorModalRun && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setErrorModalRun(null)}
        >
          <div 
            className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`flex items-center justify-between p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h2 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Training Run Error Details
              </h2>
              <button
                onClick={() => setErrorModalRun(null)}
                className={`text-2xl leading-none ${darkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`}
              >
                ×
              </button>
            </div>
            <div className="p-4 overflow-auto flex-1">
              <div className="space-y-4">
                <div>
                  <h3 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Run Information
                  </h3>
                  <div className={`text-xs space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <div><strong>Run ID:</strong> {errorModalRun.runIdentifier ?? `run-${errorModalRun.id}`}</div>
                    <div><strong>Status:</strong> {errorModalRun.status}</div>
                    <div><strong>Started:</strong> {errorModalRun.startedAt ? new Date(errorModalRun.startedAt).toLocaleString() : '—'}</div>
                    <div><strong>Finished:</strong> {errorModalRun.finishedAt ? new Date(errorModalRun.finishedAt).toLocaleString() : '—'}</div>
                    <div><strong>Base Model:</strong> {errorModalRun.baseModel ?? '—'}</div>
                    <div><strong>Samples:</strong> {errorModalRun.datasetSize ?? '—'}</div>
                    <div><strong>Final Loss:</strong> {errorModalRun.finalLoss != null ? errorModalRun.finalLoss.toFixed(4) : '—'}</div>
                  </div>
                </div>
                <div>
                  <h3 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Error Message
                  </h3>
                  <pre className={`text-xs p-3 rounded overflow-auto max-h-96 ${darkMode ? 'bg-gray-900 text-red-300' : 'bg-gray-100 text-red-700'} font-mono whitespace-pre-wrap break-words`}>
                    {errorModalRun.errorMessage || 'No error message available'}
                  </pre>
                </div>
              </div>
            </div>
            <div className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'} flex justify-end`}>
              <button
                onClick={() => {
                  if (errorModalRun.errorMessage) {
                    navigator.clipboard.writeText(errorModalRun.errorMessage);
                    toast.success('Error message copied to clipboard');
                  }
                }}
                className={`px-4 py-2 rounded text-sm ${darkMode ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
              >
                📋 Copy Error
              </button>
              <button
                onClick={() => setErrorModalRun(null)}
                className={`ml-2 px-4 py-2 rounded text-sm ${darkMode ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

