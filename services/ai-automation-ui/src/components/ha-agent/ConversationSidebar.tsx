/**
 * Conversation Sidebar Component
 * Epic AI-20 Story AI20.8: Conversation Management UI
 * Epic AI-20.9: Better conversation naming, status badges, and source icons
 * 
 * Displays conversation history with search, filter, and management options.
 * Features:
 * - Conversation titles (auto-generated from first message or stored)
 * - Source indicators (user/proactive/pattern)
 * - Status badges (active/archived)
 * - Search and filter functionality
 * 
 * @security Input sanitization applied to all user-generated content
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { listConversations, type Conversation, type ConversationSource } from '../../services/haAiAgentApi';
import toast from 'react-hot-toast';

/** Filter state type for type safety */
type FilterState = 'all' | 'active' | 'archived';

/** Source icon configuration for type safety and maintainability */
const SOURCE_CONFIG: Record<ConversationSource | 'default', { icon: string; label: string; ariaLabel: string }> = {
  proactive: { icon: '💡', label: 'Proactive', ariaLabel: 'Created from proactive suggestion' },
  pattern: { icon: '📊', label: 'Pattern', ariaLabel: 'Created from pattern-based suggestion' },
  user: { icon: '👤', label: 'User', ariaLabel: 'Created by user' },
  default: { icon: '👤', label: 'User', ariaLabel: 'Created by user' },
};

/**
 * Sanitize text content to prevent XSS attacks
 * @param text - Raw text to sanitize
 * @returns Sanitized text safe for display
 */
const sanitizeText = (text: string): string => {
  return text
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

/** Props for ConversationSidebar component */
interface ConversationSidebarProps {
  /** Whether dark mode is enabled */
  darkMode: boolean;
  /** Currently selected conversation ID */
  currentConversationId: string | null;
  /** Callback when a conversation is selected */
  onSelectConversation: (conversationId: string) => void;
  /** Callback to create a new conversation */
  onNewConversation: () => void;
  /** Callback when a conversation is deleted */
  onDeleteConversation: (conversationId: string) => void;
  /** Whether the sidebar is open */
  isOpen: boolean;
  /** Callback to toggle sidebar visibility */
  onToggle: () => void;
  /** Trigger to refresh conversation list */
  refreshTrigger?: number;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  darkMode,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen,
  onToggle,
  refreshTrigger = 0,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterState, setFilterState] = useState<FilterState>('all');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Load conversations with proper error handling
  useEffect(() => {
    const controller = new AbortController();
    
    const loadConversations = async (): Promise<void> => {
      try {
        setIsLoading(true);
        const response = await listConversations({
          state: filterState === 'all' ? undefined : filterState,
          limit: 50,
        });
        if (!controller.signal.aborted) {
          setConversations(response.conversations);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error('Failed to load conversations:', error);
          toast.error('Failed to load conversations');
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    loadConversations();
    
    return () => {
      controller.abort();
    };
  }, [filterState, refreshTrigger]);

  /**
   * Generate conversation title from stored title or first message
   * @security Applies sanitization to prevent XSS
   */
  const getConversationTitle = useCallback((conversation: Conversation): string => {
    // Epic AI-20.9: Use stored title if available
    if (conversation.title) {
      return sanitizeText(conversation.title);
    }
    // Fallback: Try to use first user message
    if (conversation.messages && conversation.messages.length > 0) {
      const firstMessage = conversation.messages[0];
      if (firstMessage.role === 'user') {
        // Use first 50 characters of first user message, sanitized
        const title = sanitizeText(firstMessage.content.trim());
        return title.length > 50 ? `${title.substring(0, 50)}...` : title;
      }
    }
    // Final fallback: Use conversation ID (no sanitization needed - UUID format)
    return `Conversation ${conversation.conversation_id.substring(0, 8)}`;
  }, []);

  /**
   * Get source configuration with type safety
   * Epic AI-20.9: Source icons for conversation origin
   */
  const getSourceConfig = useCallback((source: string | null | undefined) => {
    const key = (source as ConversationSource) || 'default';
    return SOURCE_CONFIG[key] ?? SOURCE_CONFIG.default;
  }, []);

  /**
   * Handle delete with confirmation
   * @security Prevents accidental deletion with confirmation state
   */
  const handleDelete = useCallback((e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    
    if (deletingId === conversationId) {
      // Second click - actually delete
      onDeleteConversation(conversationId);
      setDeletingId(null);
    } else {
      // First click - enter confirmation mode
      setDeletingId(conversationId);
      // Auto-reset after 3 seconds
      setTimeout(() => setDeletingId(null), 3000);
    }
  }, [deletingId, onDeleteConversation]);

  /**
   * Format date for display with relative time
   */
  const formatDate = useCallback((dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }, []);

  /**
   * Filter conversations by search query
   * @performance Uses useMemo to prevent unnecessary re-filtering
   */
  const filteredConversations = useMemo(() => {
    if (!searchQuery) return conversations;
    const query = searchQuery.toLowerCase();
    return conversations.filter((conv) => {
      const title = getConversationTitle(conv).toLowerCase();
      return title.includes(query);
    });
  }, [conversations, searchQuery, getConversationTitle]);

  return (
    <>
      {/* Mobile toggle button - only show when sidebar is closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className={`md:hidden fixed top-20 left-4 z-40 p-2 rounded-lg ${
            darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
          } shadow-lg`}
        >
          ☰
        </button>
      )}

      {/* Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Overlay for mobile */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
            />

            {/* Sidebar content */}
            <motion.div
              initial={false}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className={`fixed left-0 top-0 h-full w-80 z-40 flex flex-col ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              } border-r shadow-xl md:relative md:z-auto md:shadow-none`}
            >
              {/* Header */}
              <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Conversations
                  </h2>
                  <button
                    onClick={onToggle}
                    className={`md:hidden p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
                  >
                    ✕
                  </button>
                </div>

                {/* New Conversation Button */}
                <button
                  onClick={onNewConversation}
                  className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  + New Conversation
                </button>

                {/* Search */}
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full mt-3 px-3 py-2 rounded-lg border ${
                    darkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                  } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                />

                {/* Filter buttons */}
                <div className="flex gap-2 mt-3">
                  {(['all', 'active', 'archived'] as const).map((state) => (
                    <button
                      key={state}
                      onClick={() => setFilterState(state)}
                      className={`flex-1 px-3 py-1 rounded text-sm font-medium transition-colors ${
                        filterState === state
                          ? darkMode
                            ? 'bg-blue-600 text-white'
                            : 'bg-blue-500 text-white'
                          : darkMode
                          ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {state.charAt(0).toUpperCase() + state.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Conversation List */}
              <div className="flex-1 overflow-y-auto">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                  </div>
                ) : filteredConversations.length === 0 ? (
                  <div className={`p-4 text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {searchQuery ? 'No conversations found' : 'No conversations yet'}
                  </div>
                ) : (
                  <div className="p-2" role="listbox" aria-label="Conversations">
                    {filteredConversations.map((conversation) => {
                      const isActive = conversation.conversation_id === currentConversationId;
                      const isDeleting = deletingId === conversation.conversation_id;
                      const sourceConfig = getSourceConfig(conversation.source);
                      
                      return (
                        <motion.div
                          key={conversation.conversation_id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          role="option"
                          aria-selected={isActive}
                          aria-label={`${getConversationTitle(conversation)}, ${sourceConfig.ariaLabel}`}
                          className={`mb-2 rounded-lg p-3 cursor-pointer transition-colors ${
                            isActive
                              ? darkMode
                                ? 'bg-blue-600 text-white'
                                : 'bg-blue-500 text-white'
                              : darkMode
                              ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                              : 'bg-gray-50 hover:bg-gray-100 text-gray-900'
                          }`}
                          onClick={() => onSelectConversation(conversation.conversation_id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              onSelectConversation(conversation.conversation_id);
                            }
                          }}
                          tabIndex={0}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              {/* Title with source icon */}
                              <div className="flex items-center gap-1.5">
                                <span 
                                  title={sourceConfig.ariaLabel}
                                  aria-label={sourceConfig.ariaLabel}
                                  className="text-sm flex-shrink-0"
                                  role="img"
                                >
                                  {sourceConfig.icon}
                                </span>
                                <p className="font-medium truncate">{getConversationTitle(conversation)}</p>
                              </div>
                              {/* Metadata row: status badge, message count, time */}
                              <div className="flex items-center gap-2 mt-1 text-xs opacity-75">
                                {/* Status badge */}
                                <span 
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                    conversation.state === 'active'
                                      ? isActive
                                        ? 'bg-green-500/30 text-green-200'
                                        : darkMode
                                          ? 'bg-green-500/20 text-green-400'
                                          : 'bg-green-100 text-green-700'
                                      : isActive
                                        ? 'bg-gray-500/30 text-gray-300'
                                        : darkMode
                                          ? 'bg-gray-600 text-gray-400'
                                          : 'bg-gray-200 text-gray-600'
                                  }`}
                                  aria-label={conversation.state === 'active' ? 'Active conversation' : 'Archived conversation'}
                                  role="status"
                                >
                                  {conversation.state === 'active' ? '🟢' : '📦'}
                                </span>
                                <span aria-label={`${conversation.message_count} messages`}>
                                  {conversation.message_count} msgs
                                </span>
                                <span aria-hidden="true">•</span>
                                <span aria-label={`Last updated ${formatDate(conversation.updated_at)}`}>
                                  {formatDate(conversation.updated_at)}
                                </span>
                              </div>
                            </div>
                            {/* Delete button with confirmation UX */}
                            <button
                              onClick={(e) => handleDelete(e, conversation.conversation_id)}
                              className={`ml-2 p-1.5 rounded transition-all ${
                                isDeleting
                                  ? 'bg-red-500 text-white animate-pulse'
                                  : isActive 
                                    ? 'text-white hover:bg-white/20' 
                                    : darkMode 
                                      ? 'text-gray-400 hover:bg-gray-600' 
                                      : 'text-gray-600 hover:bg-gray-200'
                              }`}
                              title={isDeleting ? 'Click again to confirm delete' : 'Delete conversation'}
                              aria-label={isDeleting ? 'Confirm delete' : 'Delete conversation'}
                            >
                              {isDeleting ? '⚠️' : '🗑️'}
                            </button>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

