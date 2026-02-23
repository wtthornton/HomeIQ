import { beforeAll, afterEach, afterAll, vi } from 'vitest';
import { server } from './mocks/server';
import '@testing-library/jest-dom/vitest';

// Context7 pattern: Use environment variables in MSW setup
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';

// Mock WebSocket with environment-based URL
global.WebSocket = vi.fn().mockImplementation(() => {
  return {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    send: vi.fn(),
    close: vi.fn(),
    readyState: 1, // OPEN
  };
}) as any;

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
