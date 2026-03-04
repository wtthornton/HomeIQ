/**
 * Scheduled Tasks API Client
 * Epic 27: Scheduled AI Tasks (Continuity)
 *
 * Endpoints on proactive-agent-service:
 * - GET    /api/v1/tasks                         — list tasks
 * - POST   /api/v1/tasks                         — create task
 * - GET    /api/v1/tasks/{id}                    — get task
 * - PUT    /api/v1/tasks/{id}                    — update task
 * - DELETE /api/v1/tasks/{id}                    — delete task
 * - PATCH  /api/v1/tasks/{id}/toggle             — toggle enabled
 * - POST   /api/v1/tasks/{id}/run                — run now
 * - GET    /api/v1/tasks/{id}/history             — execution history
 * - GET    /api/v1/tasks/templates                — list templates
 * - POST   /api/v1/tasks/templates/{id}/install   — install template
 * - GET    /api/v1/tasks/scheduler/status          — scheduler status
 */

import type {
  ScheduledTask,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskListResponse,
  ExecutionListResponse,
  TaskTemplate,
  SchedulerStatus,
  RunNowResponse,
} from '../types/scheduledTask';
import { fetchJSON } from '../lib/api-client';

const isProduction = import.meta.env.MODE === 'production';
const BASE = isProduction
  ? '/api/proactive/v1/tasks'
  : 'http://localhost:8031/api/v1/tasks';

export const taskApi = {
  /**
   * List scheduled tasks with optional enabled filter
   */
  async listTasks(params?: {
    enabled?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<TaskListResponse> {
    const qs = new URLSearchParams();
    if (params?.enabled !== undefined) qs.append('enabled', String(params.enabled));
    if (params?.limit !== undefined) qs.append('limit', String(params.limit));
    if (params?.offset !== undefined) qs.append('offset', String(params.offset));
    const query = qs.toString();
    return fetchJSON<TaskListResponse>(query ? `${BASE}?${query}` : BASE);
  },

  /**
   * Get a single task by ID
   */
  async getTask(id: number): Promise<ScheduledTask> {
    return fetchJSON<ScheduledTask>(`${BASE}/${id}`);
  },

  /**
   * Create a new scheduled task
   */
  async createTask(data: TaskCreateRequest): Promise<ScheduledTask> {
    return fetchJSON<ScheduledTask>(BASE, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing task
   */
  async updateTask(id: number, data: TaskUpdateRequest): Promise<ScheduledTask> {
    return fetchJSON<ScheduledTask>(`${BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a task and its execution history
   */
  async deleteTask(id: number): Promise<void> {
    await fetchJSON<void>(`${BASE}/${id}`, { method: 'DELETE' });
  },

  /**
   * Toggle a task's enabled/disabled state
   */
  async toggleTask(id: number): Promise<ScheduledTask> {
    return fetchJSON<ScheduledTask>(`${BASE}/${id}/toggle`, {
      method: 'PATCH',
    });
  },

  /**
   * Manually run a task now
   */
  async runNow(id: number): Promise<RunNowResponse> {
    return fetchJSON<RunNowResponse>(`${BASE}/${id}/run`, {
      method: 'POST',
      timeoutMs: 180_000, // 3 min — tasks can take a while
    });
  },

  /**
   * Get execution history for a task
   */
  async getHistory(
    taskId: number,
    params?: { limit?: number; offset?: number; status?: string },
  ): Promise<ExecutionListResponse> {
    const qs = new URLSearchParams();
    if (params?.limit !== undefined) qs.append('limit', String(params.limit));
    if (params?.offset !== undefined) qs.append('offset', String(params.offset));
    if (params?.status) qs.append('status', params.status);
    const query = qs.toString();
    const url = query
      ? `${BASE}/${taskId}/history?${query}`
      : `${BASE}/${taskId}/history`;
    return fetchJSON<ExecutionListResponse>(url);
  },

  /**
   * List available built-in templates
   */
  async listTemplates(): Promise<TaskTemplate[]> {
    return fetchJSON<TaskTemplate[]>(`${BASE}/templates`);
  },

  /**
   * Install a built-in template as a new task
   */
  async installTemplate(templateId: string): Promise<ScheduledTask> {
    return fetchJSON<ScheduledTask>(`${BASE}/templates/${templateId}/install`, {
      method: 'POST',
    });
  },

  /**
   * Get scheduler status and job info
   */
  async getSchedulerStatus(): Promise<SchedulerStatus> {
    return fetchJSON<SchedulerStatus>(`${BASE}/scheduler/status`);
  },
};

export default taskApi;
