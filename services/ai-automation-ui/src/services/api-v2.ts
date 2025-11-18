/**
 * API v2 Service for AI Automation Backend
 * 
 * TypeScript client for v2 conversation API endpoints.
 * Provides type-safe access to conversation, automation, and action APIs.
 */

import type { Suggestion } from '../types';

// Use relative path - nginx will proxy to ai-automation-service
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

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

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const headers = withAuthHeaders({
      'Content-Type': 'application/json',
      ...options?.headers,
    });

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = response.statusText;
      try {
        const errorBody = await response.json();
        if (errorBody.detail) {
          errorMessage = typeof errorBody.detail === 'string' 
            ? errorBody.detail 
            : JSON.stringify(errorBody.detail);
        } else if (errorBody.message) {
          errorMessage = errorBody.message;
        }
      } catch {
        // If JSON parsing fails, use statusText
      }
      throw new APIError(response.status, errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${url}`, error);
    throw error;
  }
}

// Type definitions matching backend models

export enum ResponseType {
  AUTOMATION_GENERATED = "automation_generated",
  CLARIFICATION_NEEDED = "clarification_needed",
  ACTION_DONE = "action_done",
  INFORMATION_PROVIDED = "information_provided",
  ERROR = "error",
  NO_INTENT_MATCH = "no_intent_match",
}

export enum ConversationType {
  AUTOMATION = "automation",
  CLARIFICATION = "clarification",
  ACTION = "action",
  INFORMATION = "information",
}

export interface ConfidenceScore {
  overall: number;
  factors: Record<string, number>;
  explanation: string;
  breakdown?: Record<string, any>;
}

export interface AutomationSuggestion {
  suggestion_id: string;
  title: string;
  description: string;
  automation_yaml?: string;
  confidence: number;
  validated_entities: Record<string, string>;
  status: string;
}

export interface ClarificationQuestion {
  id: string;
  category: string;
  question_text: string;
  question_type: string;
  options?: string[];
  priority: number;
  related_entities?: string[];
}

export interface ConversationTurnResponse {
  conversation_id: string;
  turn_number: number;
  response_type: ResponseType;
  content: string;
  suggestions?: AutomationSuggestion[];
  clarification_questions?: ClarificationQuestion[];
  confidence?: ConfidenceScore;
  processing_time_ms: number;
  next_actions: string[];
  created_at: string;
}

export interface ConversationResponse {
  conversation_id: string;
  user_id: string;
  conversation_type: ConversationType;
  status: string;
  initial_query: string;
  created_at: string;
}

export interface ConversationDetail {
  conversation_id: string;
  user_id: string;
  conversation_type: ConversationType;
  status: string;
  initial_query: string;
  turns: ConversationTurnResponse[];
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface ConversationStartRequest {
  query: string;
  user_id?: string;
  conversation_type?: ConversationType;
  context?: Record<string, any>;
}

export interface MessageRequest {
  message: string;
  context?: Record<string, any>;
}

export interface ActionRequest {
  query: string;
  user_id?: string;
}

export interface ActionResult {
  success: boolean;
  action_type: string;
  entity_id?: string;
  result: Record<string, any>;
  message: string;
  execution_time_ms: number;
}

export interface AutomationGenerationRequest {
  suggestion_id: string;
  conversation_id: string;
  turn_id: number;
}

export interface AutomationGenerationResponse {
  suggestion_id: string;
  automation_yaml: string;
  validation_result: Record<string, any>;
  confidence: number;
}

export interface TestRequest {
  suggestion_id: string;
  automation_yaml: string;
}

export interface TestResult {
  success: boolean;
  state_changes: Record<string, any>;
  errors: string[];
  warnings: string[];
  execution_time_ms: number;
}

export interface DeploymentRequest {
  suggestion_id: string;
  automation_yaml: string;
  automation_id?: string;
}

export interface DeploymentResult {
  success: boolean;
  automation_id: string;
  message: string;
  deployed_at: string;
}

export interface AutomationSummary {
  suggestion_id: string;
  conversation_id: string;
  title: string;
  description: string;
  status: string;
  confidence: number;
  created_at: string;
  updated_at: string;
}

/**
 * v2 API Client
 */
export const apiV2 = {
  // ============================================
  // Conversation API
  // ============================================

  /**
   * Start a new conversation
   */
  async startConversation(request: ConversationStartRequest): Promise<ConversationResponse> {
    return fetchJSON<ConversationResponse>(`${API_BASE_URL}/v2/conversations`, {
      method: 'POST',
      body: JSON.stringify({
        query: request.query,
        user_id: request.user_id || 'anonymous',
        conversation_type: request.conversation_type,
        context: request.context,
      }),
    });
  },

  /**
   * Send a message in an existing conversation
   */
  async sendMessage(
    conversationId: string,
    request: MessageRequest
  ): Promise<ConversationTurnResponse> {
    return fetchJSON<ConversationTurnResponse>(
      `${API_BASE_URL}/v2/conversations/${conversationId}/message`,
      {
        method: 'POST',
        body: JSON.stringify({
          message: request.message,
          context: request.context,
        }),
      }
    );
  },

  /**
   * Get conversation details with full history
   */
  async getConversation(conversationId: string): Promise<ConversationDetail> {
    return fetchJSON<ConversationDetail>(
      `${API_BASE_URL}/v2/conversations/${conversationId}`
    );
  },

  /**
   * Get suggestions for a conversation
   */
  async getSuggestions(conversationId: string): Promise<AutomationSuggestion[]> {
    const response = await fetchJSON<{ suggestions: AutomationSuggestion[] }>(
      `${API_BASE_URL}/v2/conversations/${conversationId}/suggestions`
    );
    return response.suggestions || [];
  },

  /**
   * Stream conversation turn (Server-Sent Events)
   */
  async streamConversationTurn(
    conversationId: string,
    message: string,
    onChunk: (chunk: ConversationTurnResponse) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    try {
      const headers = withAuthHeaders({
        'Content-Type': 'application/json',
      });

      const response = await fetch(
        `${API_BASE_URL}/v2/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ message }),
        }
      );

      if (!response.ok) {
        throw new APIError(response.status, `Stream failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onChunk(data);
            } catch (e) {
              console.error('Failed to parse SSE chunk:', e);
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)));
      } else {
        throw error;
      }
    }
  },

  // ============================================
  // Action API
  // ============================================

  /**
   * Execute an immediate action (e.g., "turn on office lights")
   */
  async executeAction(request: ActionRequest): Promise<ActionResult> {
    return fetchJSON<ActionResult>(`${API_BASE_URL}/v2/actions/execute`, {
      method: 'POST',
      body: JSON.stringify({
        query: request.query,
        user_id: request.user_id || 'anonymous',
      }),
    });
  },

  // ============================================
  // Automation API
  // ============================================

  /**
   * Generate automation YAML from a suggestion
   */
  async generateAutomation(
    request: AutomationGenerationRequest
  ): Promise<AutomationGenerationResponse> {
    return fetchJSON<AutomationGenerationResponse>(
      `${API_BASE_URL}/v2/automations/generate`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    );
  },

  /**
   * Test an automation before deployment
   */
  async testAutomation(request: TestRequest): Promise<TestResult> {
    return fetchJSON<TestResult>(`${API_BASE_URL}/v2/automations/test`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  /**
   * Deploy an automation to Home Assistant
   */
  async deployAutomation(request: DeploymentRequest): Promise<DeploymentResult> {
    return fetchJSON<DeploymentResult>(`${API_BASE_URL}/v2/automations/deploy`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  /**
   * List all automations for a conversation
   */
  async listAutomations(conversationId?: string): Promise<AutomationSummary[]> {
    const url = conversationId
      ? `${API_BASE_URL}/v2/automations?conversation_id=${conversationId}`
      : `${API_BASE_URL}/v2/automations`;
    
    const response = await fetchJSON<{ automations: AutomationSummary[] }>(url);
    return response.automations || [];
  },
};

export default apiV2;

