/**
 * API v2 Service for AI Automation Backend
 * 
 * TypeScript client for v2 conversation API endpoints.
 * Provides type-safe access to conversation, automation, and action APIs.
 */

// Removed unused import

// Use relative path - nginx will proxy to ai-automation-service
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

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
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:64',message:'fetchJSON called',data:{url,method:options?.method||'GET'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion
  try {
    const headers = withAuthHeaders({
      'Content-Type': 'application/json',
      ...options?.headers,
    });
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:71',message:'About to fetch',data:{url,headers:Object.keys(headers)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
    // #endregion

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:77',message:'About to execute fetch',data:{url,method:options?.method,hasBody:!!options?.body,bodyLength:options?.body ? (typeof options.body === 'string' ? options.body.length : JSON.stringify(options.body).length) : 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
    // #endregion
    const response = await fetch(url, {
      ...options,
      headers,
    });
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:82',message:'Fetch response received',data:{url,status:response.status,statusText:response.statusText,ok:response.ok,headers:Object.fromEntries(response.headers.entries())},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
    // #endregion

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

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:93',message:'Fetch successful',data:{url,status:response.status,ok:response.ok},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
    // #endregion
    return await response.json();
  } catch (error) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:96',message:'Fetch error caught',data:{url,errorType:error?.constructor?.name,errorMessage:error instanceof Error ? error.message : String(error),isTypeError:error instanceof TypeError,isFailedToFetch:error instanceof TypeError && error.message === 'Failed to fetch'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C,D'})}).catch(()=>{});
    // #endregion
    // Enhanced error logging with more context
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      console.error(`API request failed (network error): ${url}`, {
        error: error.message,
        url,
        message: 'This usually indicates a network connectivity issue, CORS problem, or the server is unreachable.',
        errorStack: error.stack
      });
      // Wrap in a more descriptive error
      const networkError = new Error(`Network error: Unable to connect to ${url}. Please check your connection and ensure the server is running. If accessing from browser, this may be a CORS issue - check browser console for CORS errors.`);
      (networkError as any).originalError = error;
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:104',message:'Network error wrapped',data:{url,originalMessage:error.message,newMessage:networkError.message,errorStack:error.stack},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
      // #endregion
      throw networkError;
    }
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

  /**
   * Validate automation YAML (Epic 51, Story 51.9)
   */
  async validateYAML(yamlContent: string, options?: {
    normalize?: boolean;
    validateEntities?: boolean;
    validateServices?: boolean;
  }): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
    score: number;
    fixed_yaml?: string;
    fixes_applied?: string[];
  }> {
    // Call yaml-validation-service directly (port 8037)
    const validationUrl = import.meta.env.VITE_VALIDATION_SERVICE_URL || 'http://localhost:8037';
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:491',message:'validateYAML called',data:{validationUrl,hasEnvVar:!!import.meta.env.VITE_VALIDATION_SERVICE_URL,envValue:import.meta.env.VITE_VALIDATION_SERVICE_URL,yamlLength:yamlContent.length,options},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B'})}).catch(()=>{});
    // #endregion
    const fullUrl = `${validationUrl}/api/v1/validation/validate`;
    const requestBody = {
      yaml_content: yamlContent,
      normalize: options?.normalize ?? true,
      validate_entities: options?.validateEntities ?? true,
      validate_services: options?.validateServices ?? false,
    };
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-v2.ts:497',message:'About to call fetchJSON',data:{fullUrl,validationUrl,requestBodyKeys:Object.keys(requestBody),yamlContentLength:requestBody.yaml_content.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B,D'})}).catch(()=>{});
    // #endregion
    return fetchJSON<{
      valid: boolean;
      errors: string[];
      warnings: string[];
      score: number;
      fixed_yaml?: string;
      fixes_applied?: string[];
    }>(fullUrl, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },
};

export default apiV2;

