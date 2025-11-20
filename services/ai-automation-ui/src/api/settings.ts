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

const API_BASE = '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

/**
 * Add authentication headers to request options
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const authHeaders: Record<string, string> = {
    'Authorization': `Bearer ${API_KEY}`,
    'X-HomeIQ-API-Key': API_KEY,
  };

  if (headers instanceof Headers) {
    Object.entries(authHeaders).forEach(([key, value]) => {
      headers.set(key, value);
    });
    return headers;
  }

  if (Array.isArray(headers)) {
    // Filter out existing auth headers and add new ones
    const filtered = headers.filter(([key]) =>
      key.toLowerCase() !== 'authorization' && key.toLowerCase() !== 'x-homeiq-api-key'
    );
    return [...filtered, ...Object.entries(authHeaders)];
  }

  return {
    ...headers,
    ...authHeaders,
  };
}

async function handleResponse(response: Response): Promise<SettingsPayload> {
  if (response.ok) {
    return response.json() as Promise<SettingsPayload>;
  }

  if (response.status === 404) {
    return defaultSettings;
  }

  const message = await response.text();
  throw new Error(message || `Request failed with status ${response.status}`);
}

export async function getSettings(): Promise<SettingsPayload> {
  const headers = withAuthHeaders({
    Accept: 'application/json',
  });

  const response = await fetch(`${API_BASE}/settings`, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  return handleResponse(response);
}

export async function updateSettings(payload: SettingsPayload): Promise<SettingsPayload> {
  const headers = withAuthHeaders({
    'Content-Type': 'application/json',
    Accept: 'application/json',
  });

  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers,
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  return handleResponse(response);
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
  const headers = withAuthHeaders({
    Accept: 'application/json',
  });

  const params = new URLSearchParams();
  if (taskType) params.append('task_type', taskType);
  params.append('days', days.toString());

  const response = await fetch(`${API_BASE}/ask-ai/model-comparison/metrics?${params}`, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function getModelComparisonSummary(): Promise<ModelComparisonSummary> {
  const headers = withAuthHeaders({
    Accept: 'application/json',
  });

  const response = await fetch(`${API_BASE}/ask-ai/model-comparison/summary`, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json();
}
