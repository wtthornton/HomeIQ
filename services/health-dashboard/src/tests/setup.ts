import { beforeAll, afterEach, afterAll, vi, expect } from 'vitest';
import { server } from './mocks/server';
import { http, HttpResponse } from 'msw';

// Context7 pattern: Use environment variables in MSW setup
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';

// Configure MSW with environment-based URLs
server.use(
  http.get(`${API_BASE_URL}/api/health`, () => {
    return HttpResponse.json({ status: 'healthy', services: [] });
  }),
  http.get(`${API_BASE_URL}/api/services`, () => {
    return HttpResponse.json([]);
  })
);

// Mock WebSocket with environment-based URL
global.WebSocket = vi.fn().mockImplementation((url) => {
  expect(url).toBe(WS_URL);
  return {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    send: vi.fn(),
    close: vi.fn(),
    readyState: 1, // OPEN
  };
}) as any;

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

