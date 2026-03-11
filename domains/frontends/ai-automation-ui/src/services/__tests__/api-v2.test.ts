/**
 * API v2 Service Tests
 * Story 44.1: API client coverage for conversation, action, and automation APIs.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiV2 } from '../api-v2';

// Mock haAiAgentApi to avoid side effects from validateYAML delegation
vi.mock('../haAiAgentApi', () => ({
  validateYAML: vi.fn().mockResolvedValue({ valid: true, errors: [], warnings: [], score: 100 }),
}));

// Mock the api-client module so fetchJSON uses our controlled mock
const mockFetchJSON = vi.fn();
vi.mock('../../lib/api-client', () => ({
  fetchJSON: (...args: unknown[]) => mockFetchJSON(...args),
  withAuthHeaders: (h: Record<string, string> = {}) => ({ ...h, Authorization: 'Bearer test' }),
  APIError: class APIError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'APIError';
      this.status = status;
    }
  },
  API_CONFIG: {
    AI_AUTOMATION: 'http://localhost:8018/api',
    HA_AI_AGENT: 'http://localhost:8030/api',
    DATA: 'http://localhost:8006/api',
    BLUEPRINT_SUGGESTIONS: 'http://localhost:8039/api/blueprint-suggestions',
  },
}));

describe('apiV2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---- Conversation API ----

  describe('startConversation', () => {
    it('sends POST with query and default user_id', async () => {
      const mockResponse = {
        conversation_id: 'conv-1',
        user_id: 'anonymous',
        conversation_type: 'automation',
        status: 'active',
        initial_query: 'Turn on lights',
        created_at: '2026-03-10T00:00:00Z',
      };
      mockFetchJSON.mockResolvedValue(mockResponse);

      const result = await apiV2.startConversation({ query: 'Turn on lights' });

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('/v2/conversations'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"query":"Turn on lights"'),
        }),
      );
      expect(result.conversation_id).toBe('conv-1');
    });

    it('sends custom user_id and conversation_type', async () => {
      mockFetchJSON.mockResolvedValue({ conversation_id: 'conv-2' });

      await apiV2.startConversation({
        query: 'Test',
        user_id: 'user-42',
        conversation_type: 'action' as any,
      });

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.user_id).toBe('user-42');
      expect(body.conversation_type).toBe('action');
    });

    it('propagates API errors', async () => {
      mockFetchJSON.mockRejectedValue(new Error('Network error'));

      await expect(apiV2.startConversation({ query: 'fail' })).rejects.toThrow('Network error');
    });
  });

  describe('sendMessage', () => {
    it('sends POST with message to correct conversation URL', async () => {
      const mockTurn = {
        conversation_id: 'conv-1',
        turn_number: 2,
        response_type: 'information_provided',
        content: 'Here you go',
        processing_time_ms: 150,
        next_actions: [],
        created_at: '2026-03-10T00:00:00Z',
      };
      mockFetchJSON.mockResolvedValue(mockTurn);

      const result = await apiV2.sendMessage('conv-1', { message: 'hello' });

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('/v2/conversations/conv-1/message'),
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.turn_number).toBe(2);
    });

    it('includes optional context in request body', async () => {
      mockFetchJSON.mockResolvedValue({ turn_number: 1 });

      await apiV2.sendMessage('conv-1', {
        message: 'hi',
        context: { device: 'light.living_room' },
      });

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.context).toEqual({ device: 'light.living_room' });
    });
  });

  describe('getConversation', () => {
    it('fetches conversation details by ID', async () => {
      const detail = {
        conversation_id: 'conv-1',
        user_id: 'anon',
        conversation_type: 'automation',
        status: 'active',
        initial_query: 'test',
        turns: [],
        created_at: '2026-03-10T00:00:00Z',
        updated_at: '2026-03-10T00:00:00Z',
      };
      mockFetchJSON.mockResolvedValue(detail);

      const result = await apiV2.getConversation('conv-1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('/v2/conversations/conv-1'),
      );
      expect(result.conversation_id).toBe('conv-1');
    });
  });

  describe('getSuggestions', () => {
    it('returns suggestions array from nested response', async () => {
      mockFetchJSON.mockResolvedValue({
        suggestions: [{ suggestion_id: 's1', title: 'Test' }],
      });

      const result = await apiV2.getSuggestions('conv-1');

      expect(result).toHaveLength(1);
      expect(result[0].suggestion_id).toBe('s1');
    });

    it('returns empty array when suggestions field is missing', async () => {
      mockFetchJSON.mockResolvedValue({});

      const result = await apiV2.getSuggestions('conv-1');

      expect(result).toEqual([]);
    });
  });

  // ---- Action API ----

  describe('executeAction', () => {
    it('sends POST with query and default user_id', async () => {
      const actionResult = {
        success: true,
        action_type: 'turn_on',
        entity_id: 'light.office',
        result: {},
        message: 'Done',
        execution_time_ms: 50,
      };
      mockFetchJSON.mockResolvedValue(actionResult);

      const result = await apiV2.executeAction({ query: 'turn on office lights' });

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('/v2/actions/execute'),
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.success).toBe(true);
    });

    it('uses provided user_id', async () => {
      mockFetchJSON.mockResolvedValue({ success: true });

      await apiV2.executeAction({ query: 'test', user_id: 'user-1' });

      const body = JSON.parse(mockFetchJSON.mock.calls[0][1].body);
      expect(body.user_id).toBe('user-1');
    });
  });

  // ---- Automation API ----

  describe('generateAutomation', () => {
    it('sends POST with generation request', async () => {
      mockFetchJSON.mockResolvedValue({
        suggestion_id: 's1',
        automation_yaml: 'automation:',
        validation_result: {},
        confidence: 0.9,
      });

      const result = await apiV2.generateAutomation({
        suggestion_id: 's1',
        conversation_id: 'conv-1',
        turn_id: 1,
      });

      expect(result.confidence).toBe(0.9);
    });
  });

  describe('testAutomation', () => {
    it('sends POST and returns test result', async () => {
      mockFetchJSON.mockResolvedValue({
        success: true,
        state_changes: {},
        errors: [],
        warnings: [],
        execution_time_ms: 200,
      });

      const result = await apiV2.testAutomation({
        suggestion_id: 's1',
        automation_yaml: 'automation:',
      });

      expect(result.success).toBe(true);
      expect(result.errors).toEqual([]);
    });
  });

  describe('deployAutomation', () => {
    it('sends POST and returns deployment result', async () => {
      mockFetchJSON.mockResolvedValue({
        success: true,
        automation_id: 'auto-1',
        message: 'Deployed',
        deployed_at: '2026-03-10T00:00:00Z',
      });

      const result = await apiV2.deployAutomation({
        suggestion_id: 's1',
        automation_yaml: 'automation:',
      });

      expect(result.automation_id).toBe('auto-1');
    });
  });

  describe('listAutomations', () => {
    it('fetches all automations when no conversationId', async () => {
      mockFetchJSON.mockResolvedValue({
        automations: [{ suggestion_id: 's1' }],
      });

      const result = await apiV2.listAutomations();

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringMatching(/\/v2\/automations$/),
      );
      expect(result).toHaveLength(1);
    });

    it('filters by conversationId when provided', async () => {
      mockFetchJSON.mockResolvedValue({ automations: [] });

      await apiV2.listAutomations('conv-1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        expect.stringContaining('conversation_id=conv-1'),
      );
    });

    it('returns empty array when automations field is missing', async () => {
      mockFetchJSON.mockResolvedValue({});

      const result = await apiV2.listAutomations();

      expect(result).toEqual([]);
    });
  });

  describe('validateYAML', () => {
    it('delegates to haAiAgentApi validateYAML', async () => {
      const result = await apiV2.validateYAML('automation:');

      expect(result).toEqual({ valid: true, errors: [], warnings: [], score: 100 });
    });
  });
});
