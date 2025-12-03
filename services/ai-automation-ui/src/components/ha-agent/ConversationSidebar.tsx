/**
 * Conversation Sidebar Component
 * Epic AI-20 Story AI20.8: Conversation Management UI
 * 
 * Displays conversation history with search, filter, and management options
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { listConversations, deleteConversation, type Conversation } from '../../services/haAiAgentApi';
import toast from 'react-hot-toast';

interface ConversationSidebarProps {
  darkMode: boolean;
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  darkMode,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen,
  onToggle,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterState, setFilterState] = useState<'all' | 'active' | 'archived'>('all');

  // Load conversations
  useEffect(() => {
    const loadConversations = async () => {
      try {
        setIsLoading(true);
        const response = await listConversations({
          state: filterState === 'all' ? undefined : filterState,
          limit: 50,
        });
        setConversations(response.conversations);
      } catch (error) {
        console.error('Failed to load conversations:', error);
        toast.error('Failed to load conversations');
      } finally {
        setIsLoading(false);
      }
    };

    loadConversations();
  }, [filterState]);

  // Generate conversation title from first message
  const getConversationTitle = (conversation: Conversation): string => {
    if (conversation.messages && conversation.messages.length > 0) {
      const firstMessage = conversation.messages[0];
      if (firstMessage.role === 'user') {
        // Use first 50 characters of first user message
        const title = firstMessage.content.trim();
        return title.length > 50 ? `${title.substring(0, 50)}...` : title;
      }
    }
    return `Conversation ${conversation.conversation_id.substring(0, 8)}`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
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
  };

  // Filter conversations by search query
  const filteredConversations = conversations.filter((conv) => {
    if (!searchQuery) return true;
    const title = getConversationTitle(conv).toLowerCase();
    return title.includes(searchQuery.toLowerCase());
  });

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
                  <div className="p-2">
                    {filteredConversations.map((conversation) => {
                      const isActive = conversation.conversation_id === currentConversationId;
                      return (
                        <motion.div
                          key={conversation.conversation_id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
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
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{getConversationTitle(conversation)}</p>
                              <div className="flex items-center gap-2 mt-1 text-xs opacity-75">
                                <span>{conversation.message_count} messages</span>
                                <span>•</span>
                                <span>{formatDate(conversation.updated_at)}</span>
                              </div>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeleteConversation(conversation.conversation_id);
                              }}
                              className={`ml-2 p-1 rounded hover:opacity-75 ${
                                isActive ? 'text-white' : darkMode ? 'text-gray-400' : 'text-gray-600'
                              }`}
                              title="Delete conversation"
                            >
                              🗑️
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

