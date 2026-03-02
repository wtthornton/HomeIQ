import { fetchJSON } from '../lib/api-client';

export interface SettingsPayload {
  scheduleEnabled: boolean;
  scheduleTime: string;
  minConfidence: number;
  maxSuggestions: number;
  enabledCategories: {
    energy: boolean;
    comfort: boolean;
    security: boolean;
    convenience: boolean;
  };
  budgetLimit: number;
  notificationsEnabled: boolean;
  notificationEmail: string;
  softPromptEnabled: boolean;
  softPromptModelDir: string;
  softPromptConfidenceThreshold: number;
  guardrailEnabled: boolean;
  guardrailModelName: string;
  guardrailThreshold: number;
  enableParallelModelTesting?: boolean;
  parallelTestingModels?: {
    suggestion: string[];
    yaml: string[];
  };
}

export const defaultSettings: SettingsPayload = {
  scheduleEnabled: true,
  scheduleTime: '03:00',
  minConfidence: 70,
  maxSuggestions: 10,
  enabledCategories: {
    energy: true,
    comfort: true,
    security: true,
    convenience: true,
  },
  budgetLimit: 10,
  notificationsEnabled: false,
  notificationEmail: '',
  softPromptEnabled: true,
  softPromptModelDir: 'data/ask_ai_soft_prompt',
  softPromptConfidenceThreshold: 0.85,
  guardrailEnabled: true,
  guardrailModelName: 'unitary/toxic-bert',
  guardrailThreshold: 0.6,
  enableParallelModelTesting: false,
  parallelTestingModels: {
    suggestion: ['gpt-5.1'],
    yaml: ['gpt-5.1'],
  },
};

const API_BASE = '/api';

export async function getSettings(): Promise<SettingsPayload> {
  try {
    return await fetchJSON<SettingsPayload>(`${API_BASE}/settings`);
  } catch (error: unknown) {
    const err = error as { status?: number };
    if (err.status === 404) {
      return defaultSettings;
    }
    throw error;
  }
}

export async function updateSettings(payload: SettingsPayload): Promise<SettingsPayload> {
  return fetchJSON<SettingsPayload>(`${API_BASE}/settings`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export interface ModelComparisonMetrics {
  total_comparisons: number;
  task_type: string;
  days: number;
  summary: {
    cost_difference_usd: number;
    cost_savings_percentage: number;
    latency_difference_ms: number;
    model1_total_cost: number;
    model2_total_cost: number;
    model1_avg_latency_ms: number;
    model2_avg_latency_ms: number;
  };
  model_stats: {
    model1: {
      name: string;
      total_cost_usd: number;
      avg_cost_per_comparison: number;
      avg_latency_ms: number;
      approval_rate: number | null;
      yaml_validation_rate: number | null;
    };
    model2: {
      name: string;
      total_cost_usd: number;
      avg_cost_per_comparison: number;
      avg_latency_ms: number;
      approval_rate: number | null;
      yaml_validation_rate: number | null;
    };
  };
}

export interface ModelComparisonSummary {
  total_comparisons: number;
  recommendations: {
    suggestion: {
      recommendation: string;
      reason: string;
      total_comparisons: number;
      cost_savings_percentage: number;
      quality_difference_percentage: number;
    };
    yaml: {
      recommendation: string;
      reason: string;
      total_comparisons: number;
      cost_savings_percentage: number;
      quality_difference_percentage: number;
    };
  };
}

export async function getModelComparisonMetrics(
  taskType?: string,
  days: number = 7
): Promise<ModelComparisonMetrics> {
  const params = new URLSearchParams();
  if (taskType) params.append('task_type', taskType);
  params.append('days', days.toString());
  return fetchJSON<ModelComparisonMetrics>(`${API_BASE}/ask-ai/model-comparison/metrics?${params}`);
}

export async function getModelComparisonSummary(): Promise<ModelComparisonSummary> {
  return fetchJSON<ModelComparisonSummary>(`${API_BASE}/ask-ai/model-comparison/summary`);
}
