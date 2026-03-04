/**
 * Scheduled Tasks Management Component
 * Epic 27: Scheduled AI Tasks (Continuity) - Story 27.4
 *
 * Provides task list, create/edit form, execution history viewer,
 * template installation, and manual "Run Now" trigger.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { taskApi } from '../services/taskApi';
import type {
  ScheduledTask,
  TaskTemplate,
  TaskExecution,
  TaskCreateRequest,
  TaskUpdateRequest,
  NotificationPreference,
} from '../types/scheduledTask';
import {
  cronToHuman,
  EXECUTION_STATUS_CONFIG,
  NOTIFICATION_PREF_CONFIG,
} from '../types/scheduledTask';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Status badge for execution results */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config = EXECUTION_STATUS_CONFIG[status as keyof typeof EXECUTION_STATUS_CONFIG];
  if (!config) return <span>{status}</span>;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
    >
      {config.label}
    </span>
  );
};

/** Relative time formatter */
function timeAgo(iso: string | null): string {
  if (!iso) return 'Never';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ---------------------------------------------------------------------------
// Task Form (Create / Edit)
// ---------------------------------------------------------------------------

interface TaskFormProps {
  initial?: ScheduledTask | null;
  onSubmit: (data: TaskCreateRequest | TaskUpdateRequest) => Promise<void>;
  onCancel: () => void;
}

const TaskForm: React.FC<TaskFormProps> = ({ initial, onSubmit, onCancel }) => {
  const [name, setName] = useState(initial?.name ?? '');
  const [cron, setCron] = useState(initial?.cron_expression ?? '0 7 * * *');
  const [prompt, setPrompt] = useState(initial?.prompt ?? '');
  const [notifPref, setNotifPref] = useState<NotificationPreference>(
    (initial?.notification_preference as NotificationPreference) ?? 'never',
  );
  const [cooldown, setCooldown] = useState(initial?.cooldown_minutes ?? 60);
  const [maxExec, setMaxExec] = useState(initial?.max_execution_seconds ?? 120);
  const [saving, setSaving] = useState(false);

  const cronPreview = useMemo(() => cronToHuman(cron), [cron]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSubmit({
        name,
        cron_expression: cron,
        prompt,
        notification_preference: notifPref,
        cooldown_minutes: cooldown,
        max_execution_seconds: maxExec,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="task-name" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
          Task Name
        </label>
        <input
          id="task-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={255}
          className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
          placeholder="e.g. Morning Briefing"
        />
      </div>

      <div>
        <label htmlFor="task-cron" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
          Schedule (Cron Expression)
        </label>
        <input
          id="task-cron"
          type="text"
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          required
          className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
          placeholder="0 7 * * *"
        />
        <p className="mt-1 text-xs text-[var(--text-tertiary)]">
          {cronPreview}
          <span className="ml-2 opacity-60">(min hour dom month dow)</span>
        </p>
      </div>

      <div>
        <label htmlFor="task-prompt" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
          Prompt
        </label>
        <textarea
          id="task-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
          rows={4}
          maxLength={5000}
          className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] resize-y"
          placeholder="What should the AI do at the scheduled time?"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label htmlFor="task-notif" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Notifications
          </label>
          <select
            id="task-notif"
            value={notifPref}
            onChange={(e) => setNotifPref(e.target.value as NotificationPreference)}
            className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
          >
            {Object.entries(NOTIFICATION_PREF_CONFIG).map(([key, cfg]) => (
              <option key={key} value={key}>
                {cfg.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="task-cooldown" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Cooldown (min)
          </label>
          <input
            id="task-cooldown"
            type="number"
            value={cooldown}
            onChange={(e) => setCooldown(Number(e.target.value))}
            min={0}
            max={10080}
            className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
          />
        </div>

        <div>
          <label htmlFor="task-timeout" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Timeout (sec)
          </label>
          <input
            id="task-timeout"
            type="number"
            value={maxExec}
            onChange={(e) => setMaxExec(Number(e.target.value))}
            min={10}
            max={600}
            className="w-full px-3 py-2 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm rounded border border-[var(--card-border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving || !name || !prompt}
          className="px-4 py-2 text-sm rounded bg-[var(--accent-primary)] text-[var(--bg-primary)] hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {saving ? 'Saving...' : initial ? 'Update Task' : 'Create Task'}
        </button>
      </div>
    </form>
  );
};

// ---------------------------------------------------------------------------
// Execution History Panel
// ---------------------------------------------------------------------------

interface HistoryPanelProps {
  taskId: number;
  taskName: string;
  onClose: () => void;
}

const HistoryPanel: React.FC<HistoryPanelProps> = ({ taskId, taskName, onClose }) => {
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await taskApi.getHistory(taskId, { limit: 20 });
        if (!cancelled) setExecutions(data.executions);
      } catch (err) {
        console.error('Failed to load execution history:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [taskId]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">
          History: {taskName}
        </h3>
        <button
          onClick={onClose}
          className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
        >
          Close
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-[var(--text-tertiary)]">Loading...</p>
      ) : executions.length === 0 ? (
        <p className="text-sm text-[var(--text-tertiary)]">No executions yet.</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {executions.map((ex) => (
            <div
              key={ex.id}
              className="p-3 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] text-sm"
            >
              <div className="flex items-center justify-between mb-1">
                <StatusBadge status={ex.status} />
                <span className="text-xs text-[var(--text-tertiary)]">
                  {new Date(ex.started_at).toLocaleString()}
                  {ex.duration_ms != null && ` (${(ex.duration_ms / 1000).toFixed(1)}s)`}
                </span>
              </div>
              {ex.response && (
                <p className="text-xs text-[var(--text-secondary)] line-clamp-3 mt-1">
                  {ex.response}
                </p>
              )}
              {ex.error && (
                <p className="text-xs text-red-400 mt-1">{ex.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

type ViewMode = 'list' | 'create' | 'edit' | 'templates' | 'history';

export const ScheduledTasks: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>('list');
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [historyTaskId, setHistoryTaskId] = useState<number | null>(null);
  const [historyTaskName, setHistoryTaskName] = useState('');
  const [runningTaskId, setRunningTaskId] = useState<number | null>(null);

  // Fetch tasks
  const loadTasks = useCallback(async () => {
    try {
      setError(null);
      const data = await taskApi.listTasks({ limit: 100 });
      setTasks(data.tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // Handlers
  const handleCreate = async (data: TaskCreateRequest | TaskUpdateRequest) => {
    await taskApi.createTask(data as TaskCreateRequest);
    setView('list');
    await loadTasks();
  };

  const handleUpdate = async (data: TaskCreateRequest | TaskUpdateRequest) => {
    if (!editingTask) return;
    await taskApi.updateTask(editingTask.id, data as TaskUpdateRequest);
    setView('list');
    setEditingTask(null);
    await loadTasks();
  };

  const handleToggle = async (task: ScheduledTask) => {
    try {
      await taskApi.toggleTask(task.id);
      await loadTasks();
    } catch (err) {
      console.error('Failed to toggle task:', err);
    }
  };

  const handleDelete = async (task: ScheduledTask) => {
    if (!window.confirm(`Delete "${task.name}"? This cannot be undone.`)) return;
    try {
      await taskApi.deleteTask(task.id);
      await loadTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  const handleRunNow = async (task: ScheduledTask) => {
    setRunningTaskId(task.id);
    try {
      await taskApi.runNow(task.id);
      await loadTasks();
    } catch (err) {
      console.error('Failed to run task:', err);
    } finally {
      setRunningTaskId(null);
    }
  };

  const handleInstallTemplate = async (templateId: string) => {
    try {
      await taskApi.installTemplate(templateId);
      setView('list');
      await loadTasks();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to install template';
      setError(msg);
    }
  };

  const openTemplates = async () => {
    try {
      const tpls = await taskApi.listTemplates();
      setTemplates(tpls);
      setView('templates');
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const openHistory = (task: ScheduledTask) => {
    setHistoryTaskId(task.id);
    setHistoryTaskName(task.name);
    setView('history');
  };

  const openEdit = (task: ScheduledTask) => {
    setEditingTask(task);
    setView('edit');
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            Scheduled Tasks
          </h2>
          <p className="text-sm text-[var(--text-tertiary)]">
            Automated AI tasks that run on a schedule
          </p>
        </div>
        {view === 'list' && (
          <div className="flex gap-2">
            <button
              onClick={openTemplates}
              className="px-3 py-1.5 text-sm rounded border border-[var(--card-border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] transition-colors"
            >
              Templates
            </button>
            <button
              onClick={() => setView('create')}
              className="px-3 py-1.5 text-sm rounded bg-[var(--accent-primary)] text-[var(--bg-primary)] hover:opacity-90 transition-opacity"
            >
              + New Task
            </button>
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-3 rounded border border-red-500/30 bg-red-500/10 text-sm text-red-400">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Views */}
      {view === 'create' && (
        <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--bg-secondary)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            Create New Task
          </h3>
          <TaskForm onSubmit={handleCreate} onCancel={() => setView('list')} />
        </div>
      )}

      {view === 'edit' && editingTask && (
        <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--bg-secondary)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            Edit Task
          </h3>
          <TaskForm
            initial={editingTask}
            onSubmit={handleUpdate}
            onCancel={() => { setView('list'); setEditingTask(null); }}
          />
        </div>
      )}

      {view === 'templates' && (
        <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--bg-secondary)] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Task Templates
            </h3>
            <button
              onClick={() => setView('list')}
              className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
            >
              Back to list
            </button>
          </div>
          {templates.map((tpl) => {
            const installed = tasks.some((t) => t.template_id === tpl.id);
            return (
              <div
                key={tpl.id}
                className="p-3 rounded border border-[var(--card-border)] bg-[var(--bg-primary)] flex items-start justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-[var(--text-primary)]">
                    {tpl.name}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)] mt-0.5">
                    {tpl.description}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)] mt-1 font-mono">
                    {cronToHuman(tpl.cron_expression)}
                  </div>
                </div>
                <button
                  onClick={() => handleInstallTemplate(tpl.id)}
                  disabled={installed}
                  className="px-3 py-1 text-xs rounded bg-[var(--accent-primary)] text-[var(--bg-primary)] hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {installed ? 'Installed' : 'Install'}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {view === 'history' && historyTaskId !== null && (
        <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--bg-secondary)]">
          <HistoryPanel
            taskId={historyTaskId}
            taskName={historyTaskName}
            onClose={() => { setView('list'); setHistoryTaskId(null); }}
          />
        </div>
      )}

      {/* Task list (always visible except when form is open) */}
      {view === 'list' && (
        <>
          {loading ? (
            <p className="text-sm text-[var(--text-tertiary)]">Loading tasks...</p>
          ) : tasks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[var(--text-tertiary)]">
                No scheduled tasks yet.
              </p>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">
                Create a custom task or install a template to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-4 rounded border border-[var(--card-border)] bg-[var(--bg-secondary)] flex items-center gap-4"
                >
                  {/* Toggle */}
                  <button
                    onClick={() => handleToggle(task)}
                    className={`w-10 h-5 rounded-full relative transition-colors flex-shrink-0 ${
                      task.enabled
                        ? 'bg-[var(--accent-primary)]'
                        : 'bg-[var(--card-border)]'
                    }`}
                    aria-label={task.enabled ? 'Disable task' : 'Enable task'}
                    title={task.enabled ? 'Disable' : 'Enable'}
                  >
                    <span
                      className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                        task.enabled ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </button>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-[var(--text-primary)] truncate">
                        {task.name}
                      </span>
                      {task.is_template && (
                        <span className="px-1.5 py-0.5 text-[10px] rounded bg-teal-500/20 text-teal-400">
                          Template
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-[var(--text-tertiary)]">
                      <span className="font-mono">{cronToHuman(task.cron_expression)}</span>
                      <span>Last run: {timeAgo(task.last_run_at)}</span>
                      <span>{task.run_count} runs</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleRunNow(task)}
                      disabled={runningTaskId === task.id || !task.enabled}
                      className="px-2 py-1 text-xs rounded border border-[var(--card-border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] transition-colors disabled:opacity-40"
                      title="Run now"
                    >
                      {runningTaskId === task.id ? 'Running...' : 'Run'}
                    </button>
                    <button
                      onClick={() => openHistory(task)}
                      className="px-2 py-1 text-xs rounded border border-[var(--card-border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] transition-colors"
                      title="View history"
                    >
                      History
                    </button>
                    <button
                      onClick={() => openEdit(task)}
                      className="px-2 py-1 text-xs rounded border border-[var(--card-border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] transition-colors"
                      title="Edit task"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(task)}
                      className="px-2 py-1 text-xs rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete task"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ScheduledTasks;
