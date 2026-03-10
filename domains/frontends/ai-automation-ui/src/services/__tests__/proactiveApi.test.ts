/**
 * Proactive API Tests
 * Story 44.8: Proactive API client coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetchJSON = vi.fn();
vi.mock('../../lib/api-client', () => ({
  fetchJSON: (...args: unknown[]) => mockFetchJSON(...args),
  API_CONFIG: {
    DATA: 'http://localhost:8006/api',
    AI_AUTOMATION: 'http://localhost:8018/api',
    HA_AI_AGENT: 'http://localhost:8030/api',
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

import { proactiveApi } from '../proactiveApi';

describe('proactiveApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSuggestions', () => {
    it('fetches suggestions without filters', async () => {
      mockFetchJSON.mockResolvedValue({ suggestions: [], total: 0, limit: 50, offset: 0 });

      await proactiveApi.getSuggestions();

      expect(mockFetchJSON).toHaveBeenCalledWith('/api/proactive/suggestions');
    });

    it('appends filter params', async () => {
      mockFetchJSON.mockResolvedValue({ suggestions: [], total: 0, limit: 10, offset: 0 });

      await proactiveApi.getSuggestions({
        status: 'pending',
        context_type: 'weather',
        limit: 10,
        offset: 5,
      });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('status=pending');
      expect(url).toContain('context_type=weather');
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=5');
    });

    it('returns suggestion data', async () => {
      const suggestions = [{ id: 's1', prompt: 'Test', context_type: 'weather', status: 'pending' }];
      mockFetchJSON.mockResolvedValue({ suggestions, total: 1, limit: 50, offset: 0 });

      const result = await proactiveApi.getSuggestions();

      expect(result.suggestions).toHaveLength(1);
    });
  });

  describe('getSuggestion', () => {
    it('fetches suggestion by ID', async () => {
      mockFetchJSON.mockResolvedValue({ id: 's1', prompt: 'Test suggestion' });

      const result = await proactiveApi.getSuggestion('s1');

      expect(mockFetchJSON).toHaveBeenCalledWith('/api/proactive/suggestions/s1');
      expect(result.id).toBe('s1');
    });
  });

  describe('updateSuggestionStatus', () => {
    it('sends PATCH to update status', async () => {
      mockFetchJSON.mockResolvedValue({ id: 's1', status: 'approved' });

      const result = await proactiveApi.updateSuggestionStatus('s1', 'approved');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        '/api/proactive/suggestions/s1',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ status: 'approved' }),
        }),
      );
      expect(result.status).toBe('approved');
    });
  });

  describe('deleteSuggestion', () => {
    it('sends DELETE request', async () => {
      mockFetchJSON.mockResolvedValue({ success: true, message: 'Deleted' });

      const result = await proactiveApi.deleteSuggestion('s1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        '/api/proactive/suggestions/s1',
        expect.objectContaining({ method: 'DELETE' }),
      );
      expect(result.success).toBe(true);
    });
  });

  describe('getStats', () => {
    it('fetches suggestion stats', async () => {
      const stats = { total: 10, by_status: { pending: 5 }, by_context_type: { weather: 3 } };
      mockFetchJSON.mockResolvedValue(stats);

      const result = await proactiveApi.getStats();

      expect(mockFetchJSON).toHaveBeenCalledWith('/api/proactive/suggestions/stats/summary');
      expect(result.total).toBe(10);
    });
  });

  describe('triggerGeneration', () => {
    it('sends POST to trigger', async () => {
      mockFetchJSON.mockResolvedValue({ success: true, results: {} });

      const result = await proactiveApi.triggerGeneration();

      expect(mockFetchJSON).toHaveBeenCalledWith(
        '/api/proactive/suggestions/trigger',
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.success).toBe(true);
    });
  });

  describe('sendToAgent', () => {
    it('sends POST to send suggestion to agent', async () => {
      mockFetchJSON.mockResolvedValue({ id: 's1', status: 'sent' });

      const result = await proactiveApi.sendToAgent('s1');

      expect(mockFetchJSON).toHaveBeenCalledWith(
        '/api/proactive/suggestions/s1/send',
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.status).toBe('sent');
    });
  });

  describe('healthCheck', () => {
    it('fetches health status', async () => {
      mockFetchJSON.mockResolvedValue({ status: 'healthy' });

      const result = await proactiveApi.healthCheck();

      expect(result.status).toBe('healthy');
    });
  });
});
