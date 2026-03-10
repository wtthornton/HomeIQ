/**
 * useConversationV2 Hook Tests
 * Story 44.5: Conversation hook coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useConversationV2 } from '../useConversationV2';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}));

// Mock api-v2
const mockStartConversation = vi.fn();
const mockSendMessage = vi.fn();
const mockGetConversation = vi.fn();
const mockGetSuggestions = vi.fn();
const mockStreamConversationTurn = vi.fn();

vi.mock('../../services/api-v2', () => ({
  default: {
    startConversation: (...args: unknown[]) => mockStartConversation(...args),
    sendMessage: (...args: unknown[]) => mockSendMessage(...args),
    getConversation: (...args: unknown[]) => mockGetConversation(...args),
    getSuggestions: (...args: unknown[]) => mockGetSuggestions(...args),
    streamConversationTurn: (...args: unknown[]) => mockStreamConversationTurn(...args),
  },
  // Re-export types
  ConversationResponse: {},
  ConversationTurnResponse: {},
  ConversationStartRequest: {},
  MessageRequest: {},
}));

describe('useConversationV2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with null conversation and empty turns', () => {
    const { result } = renderHook(() => useConversationV2());

    expect(result.current.conversation).toBeNull();
    expect(result.current.turns).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.conversationId).toBeNull();
  });

  describe('startConversation', () => {
    it('starts a conversation and loads turns', async () => {
      const convResponse = {
        conversation_id: 'conv-1',
        user_id: 'anonymous',
        conversation_type: 'automation',
        status: 'active',
        initial_query: 'Turn on lights',
        created_at: '2026-03-10T00:00:00Z',
      };
      const detailResponse = {
        ...convResponse,
        turns: [{ turn_number: 1, content: 'Hello', response_type: 'information_provided' }],
        updated_at: '2026-03-10T00:00:00Z',
      };

      mockStartConversation.mockResolvedValue(convResponse);
      mockGetConversation.mockResolvedValue(detailResponse);

      const { result } = renderHook(() => useConversationV2());

      await act(async () => {
        await result.current.startConversation('Turn on lights');
      });

      expect(result.current.conversation).toEqual(convResponse);
      expect(result.current.turns).toHaveLength(1);
      expect(mockStartConversation).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'Turn on lights', user_id: 'anonymous' }),
      );
    });

    it('uses custom userId', async () => {
      mockStartConversation.mockResolvedValue({ conversation_id: 'c1' });
      mockGetConversation.mockResolvedValue({ conversation_id: 'c1', turns: [] });

      const { result } = renderHook(() => useConversationV2({ userId: 'user-42' }));

      await act(async () => {
        await result.current.startConversation('test');
      });

      expect(mockStartConversation).toHaveBeenCalledWith(
        expect.objectContaining({ user_id: 'user-42' }),
      );
    });

    it('calls onError callback on failure', async () => {
      const onError = vi.fn();
      mockStartConversation.mockRejectedValue(new Error('API failed'));

      const { result } = renderHook(() => useConversationV2({ onError }));

      await act(async () => {
        try {
          await result.current.startConversation('fail');
        } catch {
          // expected
        }
      });

      expect(onError).toHaveBeenCalledWith(expect.any(Error));
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('sendMessage', () => {
    it('throws if no active conversation', async () => {
      const { result } = renderHook(() => useConversationV2());

      await expect(
        act(async () => {
          await result.current.sendMessage('hello');
        }),
      ).rejects.toThrow('No active conversation');
    });

    it('sends message and appends turn', async () => {
      mockStartConversation.mockResolvedValue({ conversation_id: 'c1' });
      mockGetConversation.mockResolvedValue({ conversation_id: 'c1', turns: [] });

      const turnResponse = {
        turn_number: 2,
        content: 'Response',
        response_type: 'information_provided',
      };
      mockSendMessage.mockResolvedValue(turnResponse);

      const { result } = renderHook(() => useConversationV2());

      await act(async () => {
        await result.current.startConversation('initial');
      });

      await act(async () => {
        await result.current.sendMessage('hello');
      });

      expect(result.current.turns).toContainEqual(turnResponse);
      expect(mockSendMessage).toHaveBeenCalledWith('c1', { message: 'hello' });
    });

    it('handles send message error', async () => {
      const onError = vi.fn();
      mockStartConversation.mockResolvedValue({ conversation_id: 'c1' });
      mockGetConversation.mockResolvedValue({ conversation_id: 'c1', turns: [] });
      mockSendMessage.mockRejectedValue(new Error('Send failed'));

      const { result } = renderHook(() => useConversationV2({ onError }));

      await act(async () => {
        await result.current.startConversation('test');
      });

      await expect(
        act(async () => {
          await result.current.sendMessage('fail');
        }),
      ).rejects.toThrow('Send failed');

      expect(onError).toHaveBeenCalled();
    });
  });

  describe('loadConversation', () => {
    it('loads existing conversation by ID', async () => {
      const detail = {
        conversation_id: 'c1',
        user_id: 'anon',
        conversation_type: 'automation',
        status: 'active',
        initial_query: 'test',
        turns: [{ turn_number: 1, content: 'hi' }],
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      };
      mockGetConversation.mockResolvedValue(detail);

      const { result } = renderHook(() => useConversationV2());

      await act(async () => {
        await result.current.loadConversation('c1');
      });

      expect(result.current.conversation).toBeTruthy();
      expect(result.current.turns).toHaveLength(1);
    });
  });

  describe('getSuggestions', () => {
    it('throws if no active conversation', async () => {
      const { result } = renderHook(() => useConversationV2());

      await expect(
        act(async () => {
          await result.current.getSuggestions();
        }),
      ).rejects.toThrow('No active conversation');
    });

    it('returns suggestions for active conversation', async () => {
      mockStartConversation.mockResolvedValue({ conversation_id: 'c1' });
      mockGetConversation.mockResolvedValue({ conversation_id: 'c1', turns: [] });
      mockGetSuggestions.mockResolvedValue([{ suggestion_id: 's1' }]);

      const { result } = renderHook(() => useConversationV2());

      await act(async () => {
        await result.current.startConversation('test');
      });

      let suggestions: unknown;
      await act(async () => {
        suggestions = await result.current.getSuggestions();
      });

      expect(suggestions).toHaveLength(1);
    });
  });

  describe('clearConversation', () => {
    it('resets state to initial', async () => {
      mockStartConversation.mockResolvedValue({ conversation_id: 'c1' });
      mockGetConversation.mockResolvedValue({ conversation_id: 'c1', turns: [{ turn_number: 1 }] });

      const { result } = renderHook(() => useConversationV2());

      await act(async () => {
        await result.current.startConversation('test');
      });

      expect(result.current.conversation).toBeTruthy();

      act(() => {
        result.current.clearConversation();
      });

      expect(result.current.conversation).toBeNull();
      expect(result.current.turns).toEqual([]);
    });
  });
});
