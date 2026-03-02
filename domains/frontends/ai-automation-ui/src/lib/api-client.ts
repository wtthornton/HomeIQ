/**
 * Consolidated API Client
 * Single source of truth for HTTP requests, auth headers, and error handling.
 * All API modules should use this instead of duplicating fetchJSON/withAuthHeaders.
 */

import { API_CONFIG } from '../config/api';

// SECURITY: Never hardcode API keys. Always use environment variables.
const API_KEY = import.meta.env.VITE_API_KEY;
if (!API_KEY && import.meta.env.MODE === 'production') {
  throw new Error('VITE_API_KEY is required in production mode. Please set the environment variable.');
}

const DEFAULT_TIMEOUT_MS = 10_000;

export class APIError extends Error {
  public response?: {
    data?: {
      detail?: string | { error?: string; message?: string; retry_after?: number };
    };
  };

  constructor(
    public status: number,
    message: string,
    errorBody?: unknown,
  ) {
    super(message);
    this.name = 'APIError';
    if (errorBody) {
      const body = errorBody as Record<string, unknown>;
      this.response = {
        data: {
          detail: (body.detail as string) || body,
        },
      };
    }
  }
}

/**
 * Add authentication headers to any HeadersInit variant.
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const authHeaders: Record<string, string> = {};
  if (API_KEY) {
    authHeaders['Authorization'] = `Bearer ${API_KEY}`;
    authHeaders['X-HomeIQ-API-Key'] = API_KEY;
  }

  if (headers instanceof Headers) {
    Object.entries(authHeaders).forEach(([key, value]) => {
      (headers as Headers).set(key, value);
    });
    return headers;
  }

  if (Array.isArray(headers)) {
    const filtered = (headers as [string, string][]).filter(
      ([key]) =>
        key.toLowerCase() !== 'authorization' &&
        key.toLowerCase() !== 'x-homeiq-api-key',
    );
    return [...filtered, ...Object.entries(authHeaders)];
  }

  return { ...headers, ...authHeaders };
}

export interface FetchJSONOptions extends RequestInit {
  /** Custom timeout in milliseconds (default 10 000) */
  timeoutMs?: number;
}

/**
 * Typed JSON fetch with auth, timeout, and structured error handling.
 */
export async function fetchJSON<T>(
  url: string,
  options?: FetchJSONOptions,
): Promise<T> {
  const headers = withAuthHeaders({
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  });

  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (options?.signal) {
    options.signal.addEventListener('abort', () => controller.abort(), {
      once: true,
    });
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === 'AbortError') {
      const err = new APIError(
        0,
        `Request timed out. The server at ${url} did not respond in time.`,
      );
      (err as unknown as Record<string, unknown>).isTimeout = true;
      throw err;
    }
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new APIError(
        0,
        `Network error: Unable to connect to ${url}. Please check your connection and ensure the server is running.`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let errorMessage = response.statusText;
    let errorBody: unknown = null;
    try {
      const text = await response.text();
      if (text && text.trim()) {
        const parsed = JSON.parse(text);
        errorBody = parsed;
        if (parsed.detail) {
          errorMessage =
            typeof parsed.detail === 'object' && parsed.detail.message
              ? parsed.detail.message
              : typeof parsed.detail === 'string'
                ? parsed.detail
                : JSON.stringify(parsed.detail);
        } else if (parsed.message) {
          errorMessage = parsed.message;
        }
      }
    } catch {
      // JSON parse failed, keep statusText
    }
    throw new APIError(response.status, errorMessage, errorBody);
  }

  // Empty body guard
  const contentLength = response.headers.get('content-length');
  if (contentLength === '0') {
    return undefined as T;
  }

  const text = await response.text();
  if (!text || text.trim() === '') {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

/** Re-export withAuthHeaders for the streaming use-case in api-v2 */
export { withAuthHeaders };
/** Re-export the config for convenience */
export { API_CONFIG };
