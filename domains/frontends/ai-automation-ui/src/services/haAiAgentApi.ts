/**
 * HA AI Agent Service API Client
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 *
 * Connects to ha-ai-agent-service on port 8030
 */

import { fetchJSON, API_CONFIG } from '../lib/api-client';

const BASE_URL = API_CONFIG.HA_AI_AGENT;

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  refresh_context?: boolean;
  hidden_context?: Record<string, any>;
  title?: string;
  source?: string;
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

export type ConversationSource = 'user' | 'proactive' | 'pattern';

export interface Conversation {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  state: 'active' | 'archived';
  title?: string | null;  // Epic AI-20.9: Conversation title
  source?: ConversationSource | null;  // Epic AI-20.9: Conversation origin
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

/** @deprecated Use APIError from lib/api-client instead */
export { APIError as HAIAgentAPIError } from '../lib/api-client';

/** Chat request timeout: HA AI Agent can take 60–120s for complex prompts (context assembly, multiple LLM rounds, tool execution) */
const CHAT_TIMEOUT_MS = 120_000;

/**
 * Send a chat message to the HA AI Agent
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return fetchJSON<ChatResponse>(`${BASE_URL}/v1/chat`, {
    method: 'POST',
    body: JSON.stringify(request),
    timeoutMs: CHAT_TIMEOUT_MS,
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

/**
 * Validate automation YAML (Epic 51, Story 51.9)
 * Uses HA AI Agent Service validation chain (graceful fallback when validation services unavailable).
 */
export interface ValidateYAMLResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  score: number;
  fixed_yaml?: string;
  fixes_applied?: string[];
  strategy_used?: string;
  services_unavailable?: string[];
}

export async function validateYAML(
  yamlContent: string,
  options?: {
    normalize?: boolean;
    validateEntities?: boolean;
    validateServices?: boolean;
  }
): Promise<ValidateYAMLResult> {
  return fetchJSON<ValidateYAMLResult>(`${BASE_URL}/v1/validation/validate`, {
    method: 'POST',
    body: JSON.stringify({
      yaml_content: yamlContent,
      normalize: options?.normalize ?? true,
      validate_entities: options?.validateEntities ?? true,
      validate_services: options?.validateServices ?? false,
    }),
  });
}