/**
 * HA AI Agent Service API Client
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 * 
 * Connects to ha-ai-agent-service on port 8030
 */

import { API_CONFIG } from '../config/api';

const BASE_URL = API_CONFIG.HA_AI_AGENT;
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

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

