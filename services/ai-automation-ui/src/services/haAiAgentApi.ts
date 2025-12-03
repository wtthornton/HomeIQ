/**
 * HA AI Agent Service API Client
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 * 
 * Connects to ha-ai-agent-service on port 8030
 */

import { API_CONFIG } from '../config/api';

const BASE_URL = API_CONFIG.HA_AI_AGENT;

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
  total_count: number;
  limit: number;
  offset: number;
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
 * Fetch JSON with error handling
 */
async function fetchJSON<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail: string | undefined;
    try {
      const errorBody = await response.json();
      errorDetail = errorBody.detail || errorBody.message || response.statusText;
    } catch {
      errorDetail = response.statusText;
    }

    throw new HAIAgentAPIError(response.status, `API Error: ${errorDetail}`, errorDetail);
  }

  return response.json();
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

export interface ExecuteToolCallResponse {
  success: boolean;
  result?: any;
  error?: string;
  automation_id?: string;
  alias?: string;
  message?: string;
}

export async function executeToolCall(
  request: ExecuteToolCallRequest
): Promise<ExecuteToolCallResponse> {
  return fetchJSON<ExecuteToolCallResponse>(`${BASE_URL}/v1/tools/execute`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

