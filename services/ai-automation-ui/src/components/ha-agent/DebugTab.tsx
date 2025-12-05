/**
 * Debug Tab Component
 * Displays full prompt breakdown for debugging LLM interactions
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getPromptBreakdown, type PromptBreakdown } from '../../services/haAiAgentApi';
import toast from 'react-hot-toast';

interface DebugTabProps {
  conversationId: string | null;
  darkMode: boolean;
}

export const DebugTab: React.FC<DebugTabProps> = ({ conversationId, darkMode }) => {
  const [breakdown, setBreakdown] = useState<PromptBreakdown | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('system');
  const [refreshContext, setRefreshContext] = useState(false);

  useEffect(() => {
    if (conversationId) {
      loadBreakdown();
    } else {
      setBreakdown(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, refreshContext]);

  const loadBreakdown = async () => {
    if (!conversationId) return;

    setLoading(true);
    try {
      const data = await getPromptBreakdown(conversationId, undefined, refreshContext);
      setBreakdown(data);
    } catch (error) {
      console.error('Failed to load prompt breakdown:', error);
      const errorMessage = error instanceof Error 
        ? error.message 
        : 'Failed to load prompt breakdown';
      toast.error(errorMessage);
      setBreakdown(null);
    } finally {
      setLoading(false);
    }
  };

  const sections = [
    { id: 'system', label: 'System Prompt', icon: '⚙️' },
    { id: 'injected', label: 'Injected Context', icon: '💉' },
    { id: 'preview', label: 'Preview Context', icon: '👁️' },
    { id: 'complete', label: 'Complete System', icon: '📋' },
    { id: 'user', label: 'User Message', icon: '👤' },
    { id: 'history', label: 'Conversation History', icon: '💬' },
    { id: 'assembled', label: 'Full Assembled', icon: '🔧' },
    { id: 'tokens', label: 'Token Counts', icon: '🔢' },
  ];

  const renderContent = () => {
    if (!breakdown) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
              {conversationId ? 'Loading prompt breakdown...' : 'No conversation selected'}
            </p>
          </div>
        </div>
      );
    }

    switch (activeSection) {
      case 'system':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Base System Prompt
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.base_system_prompt.length} chars
              </span>
            </div>
            <pre className={`p-4 rounded-lg text-sm font-mono whitespace-pre-wrap ${
              darkMode ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
            }`}>
              {breakdown.base_system_prompt}
            </pre>
          </div>
        );

      case 'injected':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Injected Context (Tier 1)
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.injected_context.length} chars
              </span>
            </div>
            {breakdown.injected_context ? (
              <pre className={`p-4 rounded-lg text-sm font-mono whitespace-pre-wrap ${
                darkMode ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
              }`}>
                {breakdown.injected_context}
              </pre>
            ) : (
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>No injected context</p>
            )}
          </div>
        );

      case 'preview':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Pending Preview Context
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.preview_context.length} chars
              </span>
            </div>
            {breakdown.preview_context ? (
              <pre className={`p-4 rounded-lg text-sm font-mono whitespace-pre-wrap ${
                darkMode ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
              }`}>
                {breakdown.preview_context}
              </pre>
            ) : (
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>No pending preview</p>
            )}
          </div>
        );

      case 'complete':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Complete System Prompt (Base + Injected + Preview)
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.complete_system_prompt.length} chars
              </span>
            </div>
            <pre className={`p-4 rounded-lg text-sm font-mono whitespace-pre-wrap ${
              darkMode ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
            }`}>
              {breakdown.complete_system_prompt}
            </pre>
          </div>
        );

      case 'user':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                User Message
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.user_message.length} chars
              </span>
            </div>
            <pre className={`p-4 rounded-lg text-sm font-mono whitespace-pre-wrap ${
              darkMode ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
            }`}>
              {breakdown.user_message}
            </pre>
          </div>
        );

      case 'history':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Conversation History
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.conversation_history.length} messages
              </span>
            </div>
            <div className="space-y-2">
              {breakdown.conversation_history.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    darkMode ? 'bg-gray-800' : 'bg-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${
                      msg.role === 'user'
                        ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                        : darkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-200 text-gray-900'
                    }`}>
                      {msg.role}
                    </span>
                    <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {msg.content.length} chars
                    </span>
                  </div>
                  <pre className={`text-sm font-mono whitespace-pre-wrap ${
                    darkMode ? 'text-gray-300' : 'text-gray-800'
                  }`}>
                    {msg.content}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        );

      case 'assembled':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Full Assembled Messages (as sent to LLM)
              </h3>
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {breakdown.full_assembled_messages.length} messages
              </span>
            </div>
            <div className="space-y-2">
              {breakdown.full_assembled_messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    darkMode ? 'bg-gray-800' : 'bg-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${
                      msg.role === 'system'
                        ? darkMode ? 'bg-purple-600 text-white' : 'bg-purple-500 text-white'
                        : msg.role === 'user'
                        ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                        : msg.role === 'assistant'
                        ? darkMode ? 'bg-green-600 text-white' : 'bg-green-500 text-white'
                        : darkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-200 text-gray-900'
                    }`}>
                      {msg.role}
                    </span>
                    {msg.tool_calls && (
                      <span className={`text-xs px-2 py-1 rounded ${
                        darkMode ? 'bg-yellow-600 text-white' : 'bg-yellow-500 text-white'
                      }`}>
                        {msg.tool_calls.length} tool call(s)
                      </span>
                    )}
                    <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {msg.content?.length || 0} chars
                    </span>
                  </div>
                  <pre className={`text-sm font-mono whitespace-pre-wrap ${
                    darkMode ? 'text-gray-300' : 'text-gray-800'
                  }`}>
                    {msg.content || '[No content]'}
                  </pre>
                  {msg.tool_calls && msg.tool_calls.length > 0 && (
                    <details className="mt-2">
                      <summary className={`cursor-pointer text-sm font-semibold ${
                        darkMode ? 'text-yellow-400' : 'text-yellow-600'
                      }`}>
                        Tool Calls ({msg.tool_calls.length})
                      </summary>
                      <pre className={`mt-2 p-2 rounded text-xs font-mono overflow-auto ${
                        darkMode ? 'bg-gray-900 text-gray-300' : 'bg-gray-50 text-gray-800'
                      }`}>
                        {JSON.stringify(msg.tool_calls, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      case 'tokens':
        return (
          <div className="space-y-4">
            <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Token Counts
            </h3>
            <div className={`p-4 rounded-lg ${
              darkMode ? 'bg-gray-800' : 'bg-gray-100'
            }`}>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    System Tokens
                  </div>
                  <div className={`text-2xl font-bold ${
                    darkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {breakdown.token_counts.system_tokens.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    History Tokens
                  </div>
                  <div className={`text-2xl font-bold ${
                    darkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {breakdown.token_counts.history_tokens.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    New Message Tokens
                  </div>
                  <div className={`text-2xl font-bold ${
                    darkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {breakdown.token_counts.new_message_tokens.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Tokens
                  </div>
                  <div className={`text-2xl font-bold ${
                    breakdown.token_counts.within_budget
                      ? darkMode ? 'text-green-400' : 'text-green-600'
                      : darkMode ? 'text-red-400' : 'text-red-600'
                  }`}>
                    {breakdown.token_counts.total_tokens.toLocaleString()}
                  </div>
                </div>
                <div className="col-span-2">
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Max Input Tokens
                  </div>
                  <div className={`text-xl font-semibold ${
                    darkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {breakdown.token_counts.max_input_tokens.toLocaleString()}
                  </div>
                </div>
                <div className="col-span-2">
                  <div className={`flex items-center gap-2 ${
                    breakdown.token_counts.within_budget
                      ? darkMode ? 'text-green-400' : 'text-green-600'
                      : darkMode ? 'text-red-400' : 'text-red-600'
                  }`}>
                    <span className="text-2xl">
                      {breakdown.token_counts.within_budget ? '✅' : '⚠️'}
                    </span>
                    <span className="font-semibold">
                      {breakdown.token_counts.within_budget ? 'Within Budget' : 'Exceeds Budget'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`h-full flex flex-col ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      {/* Header */}
      <div className={`border-b px-6 py-4 flex items-center justify-between ${
        darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
      }`}>
        <div>
          <h2 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🔍 Debug: Prompt Breakdown
          </h2>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            View the full prompt sent to the LLM
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className={`flex items-center gap-2 text-sm ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            <input
              type="checkbox"
              checked={refreshContext}
              onChange={(e) => setRefreshContext(e.target.checked)}
              className="rounded"
            />
            Refresh Context
          </label>
          <button
            onClick={() => {
              if (conversationId && !loading) {
                loadBreakdown();
              }
            }}
            disabled={loading || !conversationId}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              loading || !conversationId
                ? darkMode
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : darkMode
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Section Tabs */}
      <div className={`border-b px-6 overflow-x-auto ${
        darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
      }`}>
        <div className="flex gap-2 py-2">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeSection === section.id
                  ? darkMode
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-500 text-white'
                  : darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {section.icon} {section.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Loading prompt breakdown...</p>
            </div>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="min-h-full"
          >
            {renderContent()}
          </motion.div>
        )}
      </div>
    </div>
  );
};

