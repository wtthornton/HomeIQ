/**
 * HA AI Agent API Tests
 * Story 44.1: Chat API client coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetchJSON = vi.fn();
vi.mock('../../lib/api-client', () => ({
  fetchJSON: (...args: unknown[]) => mockFetchJSON(...args),
  API_CONFIG: {
    HA_AI_AGENT: 'http://localhost:8030/api',
    AI_AUTOMATION: 'http://localhost:8018/api',
    DATA: 'http://localhost:8006/api',
    BLUEPRINT_SUGGESTIONS: 'http://localhost:8039/api/blueprint-suggestions',
  },
  APIError: class APIError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'APIError';
      this.status = status;
    }
  },
}));

import {
  sendChatMessage,
  getConversation,
  listConversations,
  createConversation,
  deleteConversation,
  executeToolCall,
  getPromptBreakdown,
  validateYAML,
} from '../haAiAgentApi';

describe('haAiAgentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('sendChatMessage', () => {
    it('sends POST to /v1/chat with message', async () => {
      const chatResponse = {
        message: 'Hello!',
        conversation_id: 'conv-1',
        tool_calls: [],
        metadata: { model: 'gpt-4', tokens_used: 100, response_time_ms: 500 },
      };
      mockFetchJSON.mockResolvedValue(chatResponse);

      const result = await sendChatMessage({ message: 'Hi' });

      expect(mockFetchJSON).toHaveBeenCalledWith(
        'http://localhost:8030/api/v1/chat',
        expect.objectContaining({
          method: 'POST',
          timeoutMs: 120_000,
        }),
      );
      expect(result.message).toBe('Hello!');
    });

    it('includes optional conversation_id and hidden_context', async () => {
      mockFetchJSON.mockResolvedValue({ message: 'ok', conversation_id: 'c1', tool_calls: [], metadata: {} });

      await sendChatMessage({
        message: 'test',
        conversation_id: 'c1',
        hidden_context: { device: 'light.kitchen' },
      });

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.conversation_id).toBe('c1');
      expect(body.hidden_context).toEqual({ device: 'light.kitchen' });
    });

    it('propagates errors from fetchJSON', async () => {
      mockFetchJSON.mockRejectedValue(new Error('Timeout'));

      await expect(sendChatMessage({ message: 'fail' })).rejects.toThrow('Timeout');
    });
  });

  describe('getConversation', () => {
    it('fetches conversation by ID', async () => {
      const conv = { conversation_id: 'c1', state: 'active', message_count: 5 };
      mockFetchJSON.mockResolvedValue(conv);

      const result = await getConversation('c1');

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8030/api/v1/conversations/c1');
      expect(result.state).toBe('active');
    });
  });

  describe('listConversations', () => {
    it('fetches conversations without params', async () => {
      mockFetchJSON.mockResolvedValue({ conversations: [], total: 0, limit: 50, offset: 0 });

      await listConversations();

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8030/api/v1/conversations');
    });

    it('appends query params when provided', async () => {
      mockFetchJSON.mockResolvedValue({ conversations: [], total: 0, limit: 10, offset: 0 });

      await listConversations({ state: 'active', limit: 10, offset: 5 });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('state=active');
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=5');
    });

    it('includes date params', async () => {
      mockFetchJSON.mockResolvedValue({ conversations: [], total: 0, limit: 50, offset: 0 });

      await listConversations({ start_date: '2026-01-01', end_date: '2026-03-10' });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('start_date=2026-01-01');
      expect(url).toContain('end_date=2026-03-10');
    });
  });

  describe('createConversation', () => {
    it('sends POST to create conversation', async () => {
      mockFetchJSON.mockResolvedValue({ conversation_id: 'new-1', state: 'active', message_count: 0 });

      await createConversation('Hello bot');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        'http://localhost:8030/api/v1/conversations',
        expect.objectContaining({ method: 'POST' }),
      );
      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.initial_message).toBe('Hello bot');
    });

    it('sends undefined initial_message when omitted', async () => {
      mockFetchJSON.mockResolvedValue({ conversation_id: 'new-2' });

      await createConversation();

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.initial_message).toBeUndefined();
    });
  });

  describe('deleteConversation', () => {
    it('sends DELETE request', async () => {
      mockFetchJSON.mockResolvedValue(undefined);

      await deleteConversation('c1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        'http://localhost:8030/api/v1/conversations/c1',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
  });

  describe('executeToolCall', () => {
    it('sends POST to /v1/tools/execute', async () => {
      mockFetchJSON.mockResolvedValue({ success: true, result: { state: 'on' } });

      const result = await executeToolCall({
        tool_name: 'turn_on',
        arguments: { entity_id: 'light.office' },
      });

      expect(mockFetchJSON).toHaveBeenCalledWith(
        'http://localhost:8030/api/v1/tools/execute',
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.success).toBe(true);
    });
  });

  describe('getPromptBreakdown', () => {
    it('fetches prompt debug info for conversation', async () => {
      mockFetchJSON.mockResolvedValue({ conversation_id: 'c1', debug_id: 'd1' });

      const result = await getPromptBreakdown('c1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('/v1/conversations/c1/debug/prompt'),
      );
      expect(result.debug_id).toBe('d1');
    });

    it('appends user_message and refresh_context params', async () => {
      mockFetchJSON.mockResolvedValue({ conversation_id: 'c1', debug_id: 'd2' });

      await getPromptBreakdown('c1', 'test message', true);

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('user_message=test+message');
      expect(url).toContain('refresh_context=true');
    });
  });

  describe('validateYAML', () => {
    it('sends POST to /v1/validation/validate', async () => {
      mockFetchJSON.mockResolvedValue({ valid: true, errors: [], warnings: [], score: 95 });

      const result = await validateYAML('automation:');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        'http://localhost:8030/api/v1/validation/validate',
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.valid).toBe(true);
    });

    it('passes options with defaults', async () => {
      mockFetchJSON.mockResolvedValue({ valid: true, errors: [], warnings: [], score: 100 });

      await validateYAML('test:', { normalize: false, validateEntities: false, validateServices: true });

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.normalize).toBe(false);
      expect(body.validate_entities).toBe(false);
      expect(body.validate_services).toBe(true);
    });
  });
});
