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
};

const API_BASE = '/api/v1';

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
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'include',
  });

  return handleResponse(response);
}

export async function updateSettings(payload: SettingsPayload): Promise<SettingsPayload> {
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  return handleResponse(response);
}

