/**
 * useConversationV2 Hook
 * 
 * React hook for managing v2 conversation API interactions.
 * Provides conversation state management and API methods.
 */

import { useState, useCallback, useRef } from 'react';
import apiV2, {
  ConversationResponse,
  ConversationTurnResponse,
  ConversationDetail,
  ConversationStartRequest,
  MessageRequest,
  ResponseType,
} from '../services/api-v2';
import toast from 'react-hot-toast';

interface UseConversationV2Options {
  userId?: string;
  onError?: (error: Error) => void;
  enableStreaming?: boolean;
}

export const useConversationV2 = (options: UseConversationV2Options = {}) => {
  const { userId = 'anonymous', onError, enableStreaming = false } = options;

  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [turns, setTurns] = useState<ConversationTurnResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationIdRef = useRef<string | null>(null);

  /**
   * Start a new conversation
   */
  const startConversation = useCallback(
    async (query: string, conversationType?: string) => {
      setIsLoading(true);
      try {
        const request: ConversationStartRequest = {
          query,
          user_id: userId,
          conversation_type: conversationType as any,
        };

        const response = await apiV2.startConversation(request);
        setConversation(response);
        conversationIdRef.current = response.conversation_id;

        // The start_conversation endpoint returns a turn response as well
        // We'll fetch the full conversation to get the turn
        const detail = await apiV2.getConversation(response.conversation_id);
        setTurns(detail.turns || []);

        return response;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        if (onError) {
          onError(err);
        } else {
          toast.error(`Failed to start conversation: ${err.message}`);
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, onError]
  );

  /**
   * Send a message in the current conversation
   */
  const sendMessage = useCallback(
    async (message: string, useStreaming = enableStreaming) => {
      if (!conversationIdRef.current) {
        throw new Error('No active conversation. Start a conversation first.');
      }

      if (useStreaming) {
        setIsStreaming(true);
        try {
          const turnResponses: ConversationTurnResponse[] = [];
          
          await apiV2.streamConversationTurn(
            conversationIdRef.current,
            message,
            (chunk) => {
              turnResponses.push(chunk);
              // Update turns with latest chunk
              setTurns((prev) => {
                const existingIndex = prev.findIndex(
                  (t) => t.turn_number === chunk.turn_number
                );
                if (existingIndex >= 0) {
                  // Update existing turn
                  const updated = [...prev];
                  updated[existingIndex] = chunk;
                  return updated;
                } else {
                  // Add new turn
                  return [...prev, chunk];
                }
              });
            },
            (error) => {
              if (onError) {
                onError(error);
              } else {
                toast.error(`Streaming error: ${error.message}`);
              }
            }
          );

          // Return the last chunk
          return turnResponses[turnResponses.length - 1] || null;
        } catch (error) {
          const err = error instanceof Error ? error : new Error(String(error));
          if (onError) {
            onError(err);
          } else {
            toast.error(`Failed to send message: ${err.message}`);
          }
          throw err;
        } finally {
          setIsStreaming(false);
        }
      } else {
        setIsLoading(true);
        try {
          const request: MessageRequest = { message };
          const response = await apiV2.sendMessage(
            conversationIdRef.current,
            request
          );

          setTurns((prev) => [...prev, response]);
          return response;
        } catch (error) {
          const err = error instanceof Error ? error : new Error(String(error));
          if (onError) {
            onError(err);
          } else {
            toast.error(`Failed to send message: ${err.message}`);
          }
          throw err;
        } finally {
          setIsLoading(false);
        }
      }
    },
    [enableStreaming, onError]
  );

  /**
   * Load an existing conversation
   */
  const loadConversation = useCallback(
    async (id: string) => {
      setIsLoading(true);
      try {
        const detail = await apiV2.getConversation(id);
        setConversation({
          conversation_id: detail.conversation_id,
          user_id: detail.user_id,
          conversation_type: detail.conversation_type,
          status: detail.status,
          initial_query: detail.initial_query,
          created_at: detail.created_at,
        });
        setTurns(detail.turns || []);
        conversationIdRef.current = id;
        return detail;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        if (onError) {
          onError(err);
        } else {
          toast.error(`Failed to load conversation: ${err.message}`);
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [onError]
  );

  /**
   * Get suggestions for the current conversation
   */
  const getSuggestions = useCallback(async () => {
    if (!conversationIdRef.current) {
      throw new Error('No active conversation.');
    }

    try {
      return await apiV2.getSuggestions(conversationIdRef.current);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      if (onError) {
        onError(err);
      } else {
        toast.error(`Failed to get suggestions: ${err.message}`);
      }
      throw err;
    }
  }, [onError]);

  /**
   * Clear the current conversation
   */
  const clearConversation = useCallback(() => {
    setConversation(null);
    setTurns([]);
    conversationIdRef.current = null;
  }, []);

  return {
    conversation,
    turns,
    isLoading,
    isStreaming,
    conversationId: conversationIdRef.current,
    startConversation,
    sendMessage,
    loadConversation,
    getSuggestions,
    clearConversation,
  };
};

