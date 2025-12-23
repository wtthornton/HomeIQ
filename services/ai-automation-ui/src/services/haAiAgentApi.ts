/**
 * HA AI Agent Service API Client
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 * 
 * Connects to ha-ai-agent-service on port 8030
 */

import { API_CONFIG } from '../config/api';

const BASE_URL = API_CONFIG.HA_AI_AGENT;

// SECURITY: Never hardcode API keys. Always use environment variables.
// In production, VITE_API_KEY must be set via environment variables.
// If not set, throw an error to prevent insecure fallback.
const API_KEY = import.meta.env.VITE_API_KEY;
if (!API_KEY) {
  console.error('VITE_API_KEY environment variable is not set. API requests will fail.');
  // In development, we can allow requests without key for local testing
  // but log a warning. In production, this should be enforced.
  if (import.meta.env.MODE === 'production') {
    throw new Error('VITE_API_KEY is required in production mode. Please set the environment variable.');
  }
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  refresh_context?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  tool_calls: ToolCall[];
  metadata: {
    model: string;
    tokens_used: number;
    response_time_ms: number;
    iterations?: number;
    token_breakdown?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

export interface Conversation {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  state: 'active' | 'archived';
  message_count: number;
  messages?: Message[];
  metadata?: Record<string, any>;
}

export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
  limit: number;
  offset: number;
  has_more?: boolean;
}

export class HAIAgentAPIError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string
  ) {
    super(message);
    this.name = 'HAIAgentAPIError';
  }
}

/**
 * Add authentication headers to request options
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  // Only add auth headers if API_KEY is available
  const authHeaders: Record<string, string> = {};
  if (API_KEY) {
    authHeaders['Authorization'] = `Bearer ${API_KEY}`;
    authHeaders['X-HomeIQ-API-Key'] = API_KEY;
  }

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

/**
 * Fetch JSON with error handling
 * Handles 204 No Content responses (no body to parse)
 */
async function fetchJSON<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  // Add authentication headers to all requests
  const headers = withAuthHeaders({
    'Content-Type': 'application/json',
    ...options?.headers,
  });

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 204 No Content responses first (before checking response.ok)
  // 204 is considered "ok" but has no body
  if (response.status === 204) {
    // Consume the response body to avoid potential issues
    try {
      await response.text();
    } catch {
      // Ignore errors when consuming empty body
    }
    return undefined as T;
  }

  if (!response.ok) {
    let errorDetail: string | undefined;
    try {
      // Try to read the response body as text first
      const text = await response.text();
      if (text && text.trim()) {
        try {
          const errorBody = JSON.parse(text);
          errorDetail = errorBody.detail || errorBody.message || response.statusText;
        } catch {
          // If JSON parsing fails, use the text as-is or status text
          errorDetail = text || response.statusText;
        }
      } else {
        errorDetail = response.statusText;
      }
    } catch (error) {
      // If reading the body fails, use status text
      errorDetail = response.statusText || 'Unknown error';
    }

    throw new HAIAgentAPIError(response.status, `API Error: ${errorDetail}`, errorDetail);
  }

  // Check content-length header - if 0, no body to parse
  const contentLength = response.headers.get('content-length');
  if (contentLength === '0') {
    return undefined as T;
  }

  // Try to parse JSON, but handle empty responses gracefully
  try {
    const text = await response.text();
    // If body is empty, return undefined
    if (!text || text.trim() === '') {
      return undefined as T;
    }
    return JSON.parse(text) as T;
  } catch (error) {
    // If parsing fails and we expected content, throw
    // Otherwise, return undefined for empty responses
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      throw error;
    }
    return undefined as T;
  }
}

/**
 * Send a chat message to the HA AI Agent
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return fetchJSON<ChatResponse>(`${BASE_URL}/v1/chat`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get a conversation by ID
 */
export async function getConversation(
  conversationId: string
): Promise<Conversation> {
  return fetchJSON<Conversation>(`${BASE_URL}/v1/conversations/${conversationId}`);
}

/**
 * List conversations with optional filters
 */
export async function listConversations(params?: {
  state?: 'active' | 'archived';
  limit?: number;
  offset?: number;
  start_date?: string;
  end_date?: string;
}): Promise<ConversationListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.state) queryParams.append('state', params.state);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.start_date) queryParams.append('start_date', params.start_date);
  if (params?.end_date) queryParams.append('end_date', params.end_date);

  const url = `${BASE_URL}/v1/conversations${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<ConversationListResponse>(url);
}

/**
 * Create a new conversation
 */
export async function createConversation(initialMessage?: string): Promise<Conversation> {
  return fetchJSON<Conversation>(`${BASE_URL}/v1/conversations`, {
    method: 'POST',
    body: JSON.stringify({
      initial_message: initialMessage,
    }),
  });
}

/**
 * Delete a conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  await fetchJSON<void>(`${BASE_URL}/v1/conversations/${conversationId}`, {
    method: 'DELETE',
  });
}

/**
 * Execute a tool call directly
 */
export interface ExecuteToolCallRequest {
  tool_name: string;
  arguments: Record<string, any>;
}

export interface Enhancement {
  level: 'small' | 'medium' | 'large' | 'advanced' | 'fun';
  title: string;
  description: string;
  enhanced_yaml: string;
  changes: string[];
  source: 'llm' | 'pattern' | 'synergy' | 'fallback';
  pattern_id?: number;
  synergy_id?: string;
}

export interface ExecuteToolCallResponse {
  success: boolean;
  result?: any;
  error?: string;
  automation_id?: string;
  alias?: string;
  message?: string;
  enhancements?: Enhancement[];
  conversation_id?: string;
}

export async function executeToolCall(
  request: ExecuteToolCallRequest
): Promise<ExecuteToolCallResponse> {
  return fetchJSON<ExecuteToolCallResponse>(`${BASE_URL}/v1/tools/execute`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get prompt breakdown for debugging
 */
export interface PromptBreakdown {
  conversation_id: string;
  debug_id: string;  // Unique troubleshooting ID stored in DB
  base_system_prompt: string;
  injected_context: string;
  preview_context: string;
  complete_system_prompt: string;
  user_message: string;
  conversation_history: Array<{
    role: string;
    content: string;
  }>;
  full_assembled_messages: Array<{
    role: string;
    content: string;
    tool_calls?: any[];
  }>;
  token_counts: {
    system_tokens: number;
    history_tokens: number;
    new_message_tokens: number;
    total_tokens: number;
    max_input_tokens: number;
    within_budget: boolean;
  };
}

export async function getPromptBreakdown(
  conversationId: string,
  userMessage?: string,
  refreshContext: boolean = false
): Promise<PromptBreakdown> {
  const queryParams = new URLSearchParams();
  if (userMessage) queryParams.append('user_message', userMessage);
  if (refreshContext) queryParams.append('refresh_context', 'true');
  
  const url = `${BASE_URL}/v1/conversations/${conversationId}/debug/prompt${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<PromptBreakdown>(url);
}

