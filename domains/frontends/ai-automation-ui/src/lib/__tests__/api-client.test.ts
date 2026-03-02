/**
 * API Client Tests
 * Tests for the consolidated fetchJSON, APIError, and withAuthHeaders.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Stub env BEFORE importing the module so API_KEY is captured at module load
vi.stubEnv('VITE_API_KEY', 'test-api-key');

// Dynamic import after env stub to ensure module picks up the key
const loadModule = async () => {
  vi.resetModules();
  return import('../api-client');
};

describe('APIError', () => {
  it('creates error with status and message', async () => {
    const { APIError } = await loadModule();
    const error = new APIError(404, 'Not Found');
    expect(error.status).toBe(404);
    expect(error.message).toBe('Not Found');
    expect(error.name).toBe('APIError');
  });

  it('attaches error body as response.data', async () => {
    const { APIError } = await loadModule();
    const body = { detail: 'Something went wrong' };
    const error = new APIError(500, 'Server Error', body);
    expect(error.response?.data?.detail).toBe('Something went wrong');
  });

  it('is an instance of Error', async () => {
    const { APIError } = await loadModule();
    const error = new APIError(400, 'Bad Request');
    expect(error).toBeInstanceOf(Error);
  });
});

describe('withAuthHeaders', () => {
  it('adds auth headers to plain object', async () => {
    const { withAuthHeaders } = await loadModule();
    const result = withAuthHeaders({ 'Content-Type': 'application/json' });
    expect(result).toEqual({
      'Content-Type': 'application/json',
      Authorization: 'Bearer test-api-key',
      'X-HomeIQ-API-Key': 'test-api-key',
    });
  });

  it('adds auth headers to empty object', async () => {
    const { withAuthHeaders } = await loadModule();
    const result = withAuthHeaders({});
    expect(result).toEqual({
      Authorization: 'Bearer test-api-key',
      'X-HomeIQ-API-Key': 'test-api-key',
    });
  });

  it('adds auth headers when called with no argument', async () => {
    const { withAuthHeaders } = await loadModule();
    const result = withAuthHeaders();
    expect(result).toEqual({
      Authorization: 'Bearer test-api-key',
      'X-HomeIQ-API-Key': 'test-api-key',
    });
  });
});

describe('fetchJSON', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it('returns parsed JSON for successful response', async () => {
    const { fetchJSON } = await loadModule();
    const mockData = { id: 1, name: 'test' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-length': '100' }),
      text: () => Promise.resolve(JSON.stringify(mockData)),
    });

    const result = await fetchJSON<typeof mockData>('http://test.com/api');
    expect(result).toEqual(mockData);
  });

  it('returns undefined for 204 No Content', async () => {
    const { fetchJSON } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      headers: new Headers(),
    });

    const result = await fetchJSON('http://test.com/api');
    expect(result).toBeUndefined();
  });

  it('returns undefined for empty body with content-length 0', async () => {
    const { fetchJSON } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-length': '0' }),
    });

    const result = await fetchJSON('http://test.com/api');
    expect(result).toBeUndefined();
  });

  it('throws APIError for non-ok response', async () => {
    const { fetchJSON, APIError } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve(JSON.stringify({ detail: 'Resource not found' })),
    });

    await expect(fetchJSON('http://test.com/api')).rejects.toThrow(APIError);
    try {
      await fetchJSON('http://test.com/api');
    } catch (err) {
      expect((err as InstanceType<typeof APIError>).status).toBe(404);
      expect((err as InstanceType<typeof APIError>).message).toBe('Resource not found');
    }
  });

  it('throws APIError with isTimeout for aborted requests', async () => {
    const { fetchJSON, APIError } = await loadModule();
    globalThis.fetch = vi.fn().mockImplementation(() => {
      const err = new DOMException('The operation was aborted', 'AbortError');
      return Promise.reject(err);
    });

    await expect(fetchJSON('http://test.com/api')).rejects.toThrow(APIError);
    try {
      await fetchJSON('http://test.com/api');
    } catch (err) {
      expect((err as any).isTimeout).toBe(true);
    }
  });

  it('throws APIError for network errors', async () => {
    const { fetchJSON, APIError } = await loadModule();
    globalThis.fetch = vi.fn().mockRejectedValue(
      new TypeError('Failed to fetch'),
    );

    await expect(fetchJSON('http://test.com/api')).rejects.toThrow(APIError);
    try {
      await fetchJSON('http://test.com/api');
    } catch (err) {
      expect((err as InstanceType<typeof APIError>).status).toBe(0);
      expect((err as InstanceType<typeof APIError>).message).toContain('Network error');
    }
  });

  it('sends auth headers with requests', async () => {
    const { fetchJSON } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-length': '2' }),
      text: () => Promise.resolve('{}'),
    });

    await fetchJSON('http://test.com/api');
    const calledHeaders = (globalThis.fetch as any).mock.calls[0][1].headers;
    expect(calledHeaders).toHaveProperty('Authorization', 'Bearer test-api-key');
    expect(calledHeaders).toHaveProperty('X-HomeIQ-API-Key', 'test-api-key');
  });

  it('sends body as JSON for POST requests', async () => {
    const { fetchJSON } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-length': '2' }),
      text: () => Promise.resolve('{}'),
    });

    await fetchJSON('http://test.com/api', {
      method: 'POST',
      body: JSON.stringify({ key: 'value' }),
    });

    const calledBody = (globalThis.fetch as any).mock.calls[0][1].body;
    expect(calledBody).toBe('{"key":"value"}');
  });

  it('handles error response with nested detail object', async () => {
    const { fetchJSON, APIError } = await loadModule();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      text: () => Promise.resolve(JSON.stringify({
        detail: { message: 'Validation failed', error_code: 'VALIDATION_ERROR' },
      })),
    });

    try {
      await fetchJSON('http://test.com/api');
    } catch (err) {
      expect((err as InstanceType<typeof APIError>).message).toBe('Validation failed');
    }
  });
});
