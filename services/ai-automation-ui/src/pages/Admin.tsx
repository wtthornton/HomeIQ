/**
 * Admin Page
 *
 * System administration and management interface.
 * Matches the styling of the suggestions page.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store';
import {
  getAdminConfig,
  getAdminOverview,
  getTrainingRuns,
  triggerTrainingRun,
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
      {/* Header */}
      <div className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'} pb-4`}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🔧 Admin Dashboard
            </h1>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              System administration and management
            </p>
          </div>
          <div className="text-sm text-gray-500">
            {overviewLoading ? 'Loading status…' : `System Status: ${overview?.systemStatus ?? 'unknown'}`}
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-blue-900/30 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">🔧</span>
          <div className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
            <strong>Admin Access:</strong> Manage system settings, view statistics, and monitor system health.
            Access to advanced features and configuration options.
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`rounded-lg p-4 border ${
              darkMode
                ? 'bg-gray-800 border-gray-700'
                : 'bg-white border-gray-200'
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
          className={`rounded-lg p-6 border ${
            darkMode
              ? 'bg-gray-800 border-gray-700'
              : 'bg-white border-gray-200'
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
          className={`rounded-lg p-6 border ${
            darkMode
              ? 'bg-gray-800 border-gray-700'
              : 'bg-white border-gray-200'
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
          <button
            type="button"
            onClick={() => trainingMutation.mutate()}
            disabled={trainingMutation.isPending || hasActiveTrainingRun}
            className={`px-4 py-2 text-xs rounded-lg font-bold shadow transition-colors ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-500 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {trainingMutation.isPending
              ? '🚧 Starting…'
              : hasActiveTrainingRun
                ? '⏳ Training In Progress'
                : '🚀 Start Training'}
          </button>
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
                        {run.errorMessage ? run.errorMessage.slice(-160) : run.baseModel ?? '—'}
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

      {/* Footer Info */}
      <div className={`rounded-lg p-6 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'} border`}>
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
      </div>
    </div>
  );
};

