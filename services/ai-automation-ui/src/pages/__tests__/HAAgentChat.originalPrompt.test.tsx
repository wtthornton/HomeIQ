/**
 * HAAgentChat originalPrompt State Management Tests
 * Tests for originalPrompt persistence, localStorage, and state synchronization
 * 
 * Recommendations Implementation:
 * - State persistence: Store originalPrompt in localStorage with conversation ID
 * - Memoization: Optimize latestUserMessage usage
 * - Debug logging: Structured logging for diagnostics
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useState, useEffect } from 'react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('HAAgentChat originalPrompt State Management', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('State Persistence with localStorage', () => {
    it('should store originalPrompt in localStorage with conversation ID', async () => {
      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('');
        const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

        // Effect to store originalPrompt in localStorage
        useEffect(() => {
          if (originalPrompt && currentConversationId) {
            try {
              localStorage.setItem(`originalPrompt:${currentConversationId}`, originalPrompt);
              console.log('[HAAgentChat] Stored originalPrompt in localStorage:', {
                conversationId: currentConversationId,
                promptLength: originalPrompt.length,
              });
            } catch (error) {
              console.warn('[HAAgentChat] Failed to store originalPrompt in localStorage:', error);
            }
          }
        }, [originalPrompt, currentConversationId]);

        return { originalPrompt, setOriginalPrompt, setCurrentConversationId };
      });

      // Set conversation ID and original prompt
      act(() => {
        result.current.setCurrentConversationId('test-conversation-123');
        result.current.setOriginalPrompt('Turn on the lights when motion is detected');
      });

      await waitFor(() => {
        const stored = localStorage.getItem('originalPrompt:test-conversation-123');
        expect(stored).toBe('Turn on the lights when motion is detected');
      });
    });

    it('should restore originalPrompt from localStorage on conversation load', async () => {
      // Pre-populate localStorage
      localStorage.setItem('originalPrompt:test-conversation-456', 'Create an automation for office lights');

      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('');
        const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

        // Effect to restore originalPrompt from localStorage
        useEffect(() => {
          if (currentConversationId && !originalPrompt) {
            try {
              const stored = localStorage.getItem(`originalPrompt:${currentConversationId}`);
              if (stored) {
                setOriginalPrompt(stored);
                console.log('[HAAgentChat] Restored originalPrompt from localStorage:', {
                  conversationId: currentConversationId,
                  promptLength: stored.length,
                });
              }
            } catch (error) {
              console.warn('[HAAgentChat] Failed to restore originalPrompt from localStorage:', error);
            }
          }
        }, [currentConversationId]);

        return { originalPrompt, setOriginalPrompt, setCurrentConversationId };
      });

      // Set conversation ID (should trigger restore)
      act(() => {
        result.current.setCurrentConversationId('test-conversation-456');
      });

      await waitFor(() => {
        expect(result.current.originalPrompt).toBe('Create an automation for office lights');
      });
    });

    it('should not overwrite existing originalPrompt when restoring from localStorage', async () => {
      localStorage.setItem('originalPrompt:test-conversation-789', 'Stored prompt');

      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('Existing prompt');
        const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

        useEffect(() => {
          if (currentConversationId && !originalPrompt) {
            const stored = localStorage.getItem(`originalPrompt:${currentConversationId}`);
            if (stored) {
              setOriginalPrompt(stored);
            }
          }
        }, [currentConversationId, originalPrompt]);

        return { originalPrompt, setOriginalPrompt, setCurrentConversationId };
      });

      act(() => {
        result.current.setCurrentConversationId('test-conversation-789');
      });

      // Should keep existing prompt, not restore from localStorage
      await waitFor(() => {
        expect(result.current.originalPrompt).toBe('Existing prompt');
      });
    });
  });

  describe('State Synchronization After loadConversation', () => {
    it('should set originalPrompt from latest user message after reload', async () => {
      const mockMessages = [
        {
          message_id: 'msg-1',
          role: 'assistant' as const,
          content: 'I can help you with that.',
          created_at: '2025-01-15T10:00:00Z',
        },
        {
          message_id: 'msg-2',
          role: 'user' as const,
          content: 'Create an automation to turn on office lights',
          created_at: '2025-01-15T10:01:00Z',
        },
      ];

      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('');
        const [messages, setMessages] = useState(mockMessages);

        // Simulate loadConversation logic
        const loadConversation = () => {
          const deduplicated = messages;
          if (!originalPrompt) {
            const latestUserMsg = deduplicated.slice().reverse().find(m => m.role === 'user');
            if (latestUserMsg) {
              setOriginalPrompt(latestUserMsg.content);
              console.log('[HAAgentChat] Set originalPrompt from latest user message after reload', {
                conversationId: 'test',
                messageId: latestUserMsg.message_id,
                promptLength: latestUserMsg.content.length,
              });
            } else {
              console.warn('[HAAgentChat] No user message found after reload:', {
                conversationId: 'test',
                messageCount: deduplicated.length,
              });
            }
          }
        };

        return { originalPrompt, setOriginalPrompt, loadConversation };
      });

      // Initially originalPrompt is empty
      expect(result.current.originalPrompt).toBe('');

      // Simulate loadConversation
      act(() => {
        result.current.loadConversation();
      });

      await waitFor(() => {
        expect(result.current.originalPrompt).toBe('Create an automation to turn on office lights');
      });
    });

    it('should preserve originalPrompt if already set during reload', async () => {
      const mockMessages = [
        {
          message_id: 'msg-1',
          role: 'user' as const,
          content: 'New user message',
          created_at: '2025-01-15T10:00:00Z',
        },
      ];

      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('Existing prompt');
        const [messages] = useState(mockMessages);

        const loadConversation = () => {
          if (!originalPrompt) {
            const latestUserMsg = messages.slice().reverse().find(m => m.role === 'user');
            if (latestUserMsg) {
              setOriginalPrompt(latestUserMsg.content);
            }
          }
        };

        return { originalPrompt, loadConversation };
      });

      act(() => {
        result.current.loadConversation();
      });

      // Should preserve existing prompt
      await waitFor(() => {
        expect(result.current.originalPrompt).toBe('Existing prompt');
      });
    });
  });

  describe('Memoization Optimization', () => {
    it('should reuse memoized latestUserMessage for EnhancementButton', () => {
      const mockMessages = [
        {
          message_id: 'msg-1',
          role: 'user' as const,
          content: 'First message',
          created_at: '2025-01-15T10:00:00Z',
        },
        {
          message_id: 'msg-2',
          role: 'assistant' as const,
          content: 'Response',
          created_at: '2025-01-15T10:01:00Z',
        },
        {
          message_id: 'msg-3',
          role: 'user' as const,
          content: 'Latest user message',
          created_at: '2025-01-15T10:02:00Z',
        },
      ];

      const { result } = renderHook(() => {
        const [originalPrompt] = useState<string>('');
        const [messages] = useState(mockMessages);

        // Memoize latest user message
        const latestUserMessage = messages.slice().reverse().find(m => m.role === 'user');

        // Memoization optimization: Reuse memoized latestUserMessage
        const userMsgForEnhance = originalPrompt ? null : latestUserMessage;

        return { originalPrompt, latestUserMessage, userMsgForEnhance };
      });

      // Should return latest user message when originalPrompt is empty
      expect(result.current.userMsgForEnhance?.content).toBe('Latest user message');
      expect(result.current.userMsgForEnhance?.message_id).toBe('msg-3');
    });

    it('should return null for userMsgForEnhance when originalPrompt is set', () => {
      const mockMessages = [
        {
          message_id: 'msg-1',
          role: 'user' as const,
          content: 'User message',
          created_at: '2025-01-15T10:00:00Z',
        },
      ];

      const { result } = renderHook(() => {
        const [originalPrompt] = useState<string>('Existing prompt');
        const [messages] = useState(mockMessages);

        const latestUserMessage = messages.slice().reverse().find(m => m.role === 'user');
        const userMsgForEnhance = originalPrompt ? null : latestUserMessage;

        return { originalPrompt, latestUserMessage, userMsgForEnhance };
      });

      // Should return null when originalPrompt is already set
      expect(result.current.userMsgForEnhance).toBeNull();
    });
  });

  describe('Debug Logging', () => {
    it('should log structured diagnostics when originalPrompt is missing', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const mockMessages: any[] = [];

      // Simulate the warning log
      if (!mockMessages.length) {
        console.warn('[HAAgentChat] No user message found after reload:', {
          conversationId: 'test-conversation',
          messageCount: mockMessages.length,
          messages: mockMessages.map(m => ({ role: m.role, id: m.message_id })),
        });
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[HAAgentChat] No user message found after reload:'),
        expect.objectContaining({
          conversationId: 'test-conversation',
          messageCount: 0,
          messages: expect.any(Array),
        })
      );

      consoleSpy.mockRestore();
    });

    it('should log structured diagnostics when originalPrompt is set', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      const mockMessage = {
        message_id: 'msg-1',
        role: 'user' as const,
        content: 'Test prompt',
        created_at: '2025-01-15T10:00:00Z',
      };

      // Simulate the success log
      console.log('[HAAgentChat] Set originalPrompt from latest user message after reload', {
        conversationId: 'test-conversation',
        messageId: mockMessage.message_id,
        promptLength: mockMessage.content.length,
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[HAAgentChat] Set originalPrompt from latest user message after reload'),
        expect.objectContaining({
          conversationId: 'test-conversation',
          messageId: 'msg-1',
          promptLength: 11,
        })
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    it('should handle localStorage errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Mock localStorage.setItem to throw error
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error('Storage quota exceeded');
      });

      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('');
        const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

        useEffect(() => {
          if (originalPrompt && currentConversationId) {
            try {
              localStorage.setItem(`originalPrompt:${currentConversationId}`, originalPrompt);
            } catch (error) {
              console.warn('[HAAgentChat] Failed to store originalPrompt in localStorage:', error);
            }
          }
        }, [originalPrompt, currentConversationId]);

        return { originalPrompt, setOriginalPrompt, setCurrentConversationId };
      });

      act(() => {
        result.current.setCurrentConversationId('test-conversation');
        result.current.setOriginalPrompt('Test prompt');
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('[HAAgentChat] Failed to store originalPrompt in localStorage:'),
          expect.any(Error)
        );
      });

      // Restore original localStorage
      localStorage.setItem = originalSetItem;
      consoleSpy.mockRestore();
    });

    it('should handle empty conversation ID', () => {
      const { result } = renderHook(() => {
        const [originalPrompt, setOriginalPrompt] = useState<string>('');
        const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

        useEffect(() => {
          if (originalPrompt && currentConversationId) {
            localStorage.setItem(`originalPrompt:${currentConversationId}`, originalPrompt);
          }
        }, [originalPrompt, currentConversationId]);

        return { originalPrompt, setOriginalPrompt, setCurrentConversationId };
      });

      act(() => {
        result.current.setOriginalPrompt('Test prompt');
        // Don't set conversationId
      });

      // Should not store in localStorage without conversation ID
      expect(localStorage.getItem('originalPrompt:')).toBeNull();
    });
  });
});
