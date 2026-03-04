/**
 * Scheduled Task Types
 * Epic 27: Scheduled AI Tasks (Continuity)
 */

export type NotificationPreference = 'always' | 'on_alert' | 'never';

export type TaskExecutionStatus = 'running' | 'completed' | 'failed' | 'timeout';

export interface ScheduledTask {
  id: number;
  name: string;
  cron_expression: string;
  prompt: string;
  enabled: boolean;
  notification_preference: NotificationPreference;
  cooldown_minutes: number;
  max_execution_seconds: number;
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  is_template: boolean;
  template_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  id: number;
  task_id: number;
  started_at: string;
  completed_at: string | null;
  status: TaskExecutionStatus;
  prompt: string;
  response: string | null;
  tools_used: string | null;
  error: string | null;
  duration_ms: number | null;
  notification_sent: boolean;
}

export interface TaskTemplate {
  id: string;
  name: string;
  cron_expression: string;
  prompt: string;
  notification_preference: NotificationPreference;
  cooldown_minutes: number;
  max_execution_seconds: number;
  description: string;
}

export interface TaskCreateRequest {
  name: string;
  cron_expression: string;
  prompt: string;
  enabled?: boolean;
  notification_preference?: NotificationPreference;
  cooldown_minutes?: number;
  max_execution_seconds?: number;
}

export interface TaskUpdateRequest {
  name?: string;
  cron_expression?: string;
  prompt?: string;
  enabled?: boolean;
  notification_preference?: NotificationPreference;
  cooldown_minutes?: number;
  max_execution_seconds?: number;
}

export interface TaskListResponse {
  tasks: ScheduledTask[];
  total: number;
}

export interface ExecutionListResponse {
  executions: TaskExecution[];
  total: number;
}

export interface SchedulerStatus {
  running: boolean;
  jobs: Array<{
    job_id: string;
    name: string;
    next_run_time: string | null;
  }>;
}

export interface RunNowResponse {
  execution_id: number;
  status: TaskExecutionStatus;
  duration_ms: number | null;
  response_preview: string;
}

// Notification preference display config
export const NOTIFICATION_PREF_CONFIG: Record<
  NotificationPreference,
  { label: string; description: string }
> = {
  always: {
    label: 'Always',
    description: 'Notify after every execution',
  },
  on_alert: {
    label: 'Alerts Only',
    description: 'Notify only when issues are detected',
  },
  never: {
    label: 'Never',
    description: 'No notifications',
  },
};

// Execution status display config
export const EXECUTION_STATUS_CONFIG: Record<
  TaskExecutionStatus,
  { label: string; color: string; bgColor: string }
> = {
  running: {
    label: 'Running',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
  },
  completed: {
    label: 'Completed',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
  },
  failed: {
    label: 'Failed',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
  },
  timeout: {
    label: 'Timeout',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
  },
};

/**
 * Convert a 5-field cron expression to a human-readable string.
 * Handles common patterns; falls back to raw expression for complex ones.
 */
export function cronToHuman(cron: string): string {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return cron;

  const [minute, hour, dom, month, dow] = parts;

  // Every minute
  if (cron === '* * * * *') return 'Every minute';

  // Daily at HH:MM
  if (dom === '*' && month === '*' && dow === '*') {
    if (minute !== '*' && hour !== '*') {
      const h = parseInt(hour, 10);
      const m = parseInt(minute, 10);
      const period = h >= 12 ? 'PM' : 'AM';
      const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
      return `Daily at ${h12}:${m.toString().padStart(2, '0')} ${period}`;
    }
  }

  // Weekly
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  if (dom === '*' && month === '*' && dow !== '*' && minute !== '*' && hour !== '*') {
    const dayIdx = parseInt(dow, 10);
    const dayName = dayNames[dayIdx] || dow;
    const h = parseInt(hour, 10);
    const m = parseInt(minute, 10);
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `Every ${dayName} at ${h12}:${m.toString().padStart(2, '0')} ${period}`;
  }

  return cron;
}
