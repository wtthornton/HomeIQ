/**
 * HA Agent Chat Page
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 * 
 * Chat interface for interacting with the HA AI Agent
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import {
  sendChatMessage,
  getConversation,
  createConversation,
  deleteConversation,
  listConversations,
  type ChatResponse,
  type Conversation,
  type Message,
  type ToolCall,
  HAIAgentAPIError,
} from '../services/haAiAgentApi';
import { ConversationSidebar } from '../components/ha-agent/ConversationSidebar';
import { DeleteConversationModal } from '../components/ha-agent/DeleteConversationModal';
import { ClearChatModal } from '../components/ha-agent/ClearChatModal';
import { ToolCallIndicator } from '../components/ha-agent/ToolCallIndicator';
import { AutomationPreview } from '../components/ha-agent/AutomationPreview';

interface ChatMessage extends Message {
  isLoading?: boolean;
  error?: string;
  toolCalls?: ToolCall[];
  responseTimeMs?: number;
}

export const HAAgentChat: React.FC = () => {
  const { darkMode } = useAppStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Open by default on desktop
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [clearChatModalOpen, setClearChatModalOpen] = useState(false);
  const [automationPreviewOpen, setAutomationPreviewOpen] = useState(false);
  const [previewAutomationYaml, setPreviewAutomationYaml] = useState<string>('');
  const [previewAutomationAlias, setPreviewAutomationAlias] = useState<string | undefined>();
  const [previewToolCall, setPreviewToolCall] = useState<ToolCall | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load conversation on mount or when conversation ID changes
  useEffect(() => {
    const loadConversation = async () => {
      if (currentConversationId) {
        try {
          setIsInitializing(true);
          const conversation = await getConversation(currentConversationId);
          setCurrentConversation(conversation);
          setMessages(
            conversation.messages?.map((msg) => ({
              ...msg,
              isLoading: false,
            })) || []
          );
        } catch (error) {
          console.error('Failed to load conversation:', error);
          toast.error('Failed to load conversation');
        } finally {
          setIsInitializing(false);
        }
      } else {
        setCurrentConversation(null);
        setIsInitializing(false);
      }
    };

    loadConversation();
  }, [currentConversationId]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      created_at: new Date().toISOString(),
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Add loading message
    const loadingMessage: ChatMessage = {
      message_id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    try {
      const response = await sendChatMessage({
        message: userMessage.content,
        conversation_id: currentConversationId || undefined,
      });

      // Update conversation ID if this was a new conversation
      if (!currentConversationId && response.conversation_id) {
        setCurrentConversationId(response.conversation_id);
        // Reload conversation to get full details
        try {
          const conversation = await getConversation(response.conversation_id);
          setCurrentConversation(conversation);
        } catch (error) {
          console.error('Failed to reload conversation:', error);
        }
      }

      // Remove loading message and add assistant response
      setMessages((prev) => {
        const filtered = prev.filter((msg) => !msg.isLoading);
        return [
          ...filtered,
          {
            message_id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.message,
            created_at: new Date().toISOString(),
            isLoading: false,
            toolCalls: response.tool_calls || [],
            responseTimeMs: response.metadata?.response_time_ms,
          },
        ];
      });

      // Show tool calls if any
      if (response.tool_calls && response.tool_calls.length > 0) {
        toast.success(`Agent executed ${response.tool_calls.length} action(s)`, {
          icon: '🔧',
        });
      }
    } catch (error) {
      console.error('Chat error:', error);

      // Remove loading message and add error message
      setMessages((prev) => {
        const filtered = prev.filter((msg) => !msg.isLoading);
        const lastMessage = filtered[filtered.length - 1];
        if (lastMessage && lastMessage.role === 'user') {
          return [
            ...filtered,
            {
              message_id: `error-${Date.now()}`,
              role: 'assistant',
              content: error instanceof HAIAgentAPIError
                ? `Error: ${error.detail || error.message}`
                : 'Sorry, I encountered an error. Please try again.',
              created_at: new Date().toISOString(),
              isLoading: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            },
          ];
        }
        return filtered;
      });

      toast.error(
        error instanceof HAIAgentAPIError
          ? error.detail || error.message
          : 'Failed to send message. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    if (messages.length > 0) {
      setClearChatModalOpen(true);
    } else {
      setCurrentConversationId(null);
      setCurrentConversation(null);
      setMessages([]);
      toast.success('New conversation started');
    }
  };

  const handleClearChat = () => {
    setCurrentConversationId(null);
    setCurrentConversation(null);
    setMessages([]);
    setClearChatModalOpen(false);
    toast.success('Chat cleared');
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    setSidebarOpen(false); // Close sidebar on mobile after selection
  };

  const handleDeleteConversation = (conversationId: string) => {
    setDeleteTargetId(conversationId);
    setDeleteModalOpen(true);
  };

  const confirmDeleteConversation = async () => {
    if (!deleteTargetId) return;

    try {
      await deleteConversation(deleteTargetId);
      
      // If deleting current conversation, clear it
      if (deleteTargetId === currentConversationId) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
        setMessages([]);
      }
      
      toast.success('Conversation deleted');
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      toast.error('Failed to delete conversation');
    } finally {
      setDeleteModalOpen(false);
      setDeleteTargetId(null);
    }
  };

  // Get conversation title for delete modal
  const getConversationTitle = (): string => {
    if (currentConversation?.messages && currentConversation.messages.length > 0) {
      const firstMessage = currentConversation.messages[0];
      if (firstMessage.role === 'user') {
        const title = firstMessage.content.trim();
        return title.length > 50 ? `${title.substring(0, 50)}...` : title;
      }
    }
    return currentConversation?.conversation_id.substring(0, 8) || 'this conversation';
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Detect automation YAML in message or tool calls
  const detectAutomation = (message: ChatMessage): { yaml: string; alias?: string; toolCall?: ToolCall } | null => {
    // Check tool calls for create_automation or test_automation_yaml
    if (message.toolCalls) {
      for (const toolCall of message.toolCalls) {
        if (toolCall.name === 'create_automation' || toolCall.name === 'test_automation_yaml') {
          const yaml = toolCall.arguments?.automation_yaml;
          const alias = toolCall.arguments?.alias;
          if (yaml) {
            return { yaml, alias, toolCall };
          }
        }
      }
    }

    // Check message content for YAML code blocks
    const yamlBlockMatch = message.content.match(/```yaml\n([\s\S]*?)```/);
    if (yamlBlockMatch) {
      const yaml = yamlBlockMatch[1].trim();
      // Try to extract alias from YAML
      const aliasMatch = yaml.match(/alias:\s*['"]?([^'\n"]+)['"]?/i);
      return { yaml, alias: aliasMatch ? aliasMatch[1] : undefined };
    }

    return null;
  };

  const handlePreviewAutomation = (message: ChatMessage) => {
    const automation = detectAutomation(message);
    if (automation) {
      setPreviewAutomationYaml(automation.yaml);
      setPreviewAutomationAlias(automation.alias);
      setPreviewToolCall(automation.toolCall);
      setAutomationPreviewOpen(true);
    }
  };

  const handleEditAutomation = (yaml: string) => {
    // Send message to agent asking to edit the automation
    setInputValue(`Please modify this automation:\n\`\`\`yaml\n${yaml}\n\`\`\``);
    setAutomationPreviewOpen(false);
    // Focus input after a brief delay
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  return (
    <div className={`min-h-[calc(100vh-12rem)] transition-colors ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} -mx-4 sm:-mx-6 lg:-mx-8 rounded-lg overflow-hidden`}>
      <div className="h-[calc(100vh-12rem)] flex">
        {/* Conversation Sidebar */}
        <ConversationSidebar
          darkMode={darkMode}
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div
          className={`border-b px-6 py-4 flex items-center justify-between ${
            darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
          }`}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className={`p-2 rounded-lg transition-colors ${
                darkMode
                  ? 'hover:bg-gray-700 text-gray-300'
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Toggle sidebar"
            >
              ☰
            </button>
            <div>
              <h1 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                🤖 HA AI Agent
              </h1>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Chat with your Home Assistant AI assistant
              </p>
            </div>
          </div>
          <button
            onClick={handleNewConversation}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-gray-700 text-white hover:bg-gray-600'
                : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
            }`}
          >
            New Chat
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isInitializing ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Loading conversation...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <div className="text-6xl mb-4">🤖</div>
                <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Welcome to HA AI Agent
                </h2>
                <p className={`mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  I can help you control your Home Assistant devices and create automations through natural conversation.
                  Try asking me to turn on lights, adjust temperatures, or create automations!
                </p>
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-gray-100'}`}>
                  <p className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Example questions:
                  </p>
                  <ul className={`text-sm space-y-1 text-left ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <li>• "Turn on the kitchen lights"</li>
                    <li>• "Set the living room temperature to 72°F"</li>
                    <li>• "Create an automation to turn on lights at sunset"</li>
                    <li>• "What devices are in the bedroom?"</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((message) => (
                  <motion.div
                    key={message.message_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        message.role === 'user'
                          ? darkMode
                            ? 'bg-blue-600 text-white'
                            : 'bg-blue-500 text-white'
                          : darkMode
                          ? 'bg-gray-700 text-gray-100'
                          : 'bg-gray-200 text-gray-900'
                      } ${message.error ? 'border border-red-500' : ''}`}
                    >
                      {message.isLoading ? (
                        <div className="flex items-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Thinking...</span>
                        </div>
                      ) : (
                        <div>
                          <p className="whitespace-pre-wrap break-words">{message.content}</p>
                          {message.error && (
                            <p className="text-xs mt-1 text-red-300">Error: {message.error}</p>
                          )}
                          {message.toolCalls && message.toolCalls.length > 0 && (
                            <ToolCallIndicator
                              toolCalls={message.toolCalls}
                              responseTimeMs={message.responseTimeMs}
                              darkMode={darkMode}
                            />
                          )}
                          {message.role === 'assistant' && detectAutomation(message) && (
                            <button
                              onClick={() => handlePreviewAutomation(message)}
                              className={`mt-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                darkMode
                                  ? 'bg-blue-700 text-white hover:bg-blue-600'
                                  : 'bg-blue-500 text-white hover:bg-blue-600'
                              }`}
                            >
                              ⚙️ Preview Automation
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div
          className={`border-t px-6 py-4 ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}
        >
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
              rows={1}
              className={`flex-1 resize-none rounded-lg px-4 py-2 border transition-colors ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                  : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              style={{
                minHeight: '44px',
                maxHeight: '120px',
              }}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className={`px-6 py-2 rounded-lg font-medium transition-colors min-h-[44px] ${
                !inputValue.trim() || isLoading
                  ? darkMode
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : darkMode
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Sending...</span>
                </div>
              ) : (
                'Send'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <DeleteConversationModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setDeleteTargetId(null);
        }}
        onConfirm={confirmDeleteConversation}
        conversationTitle={
          deleteTargetId === currentConversationId
            ? getConversationTitle()
            : `Conversation ${deleteTargetId?.substring(0, 8) || ''}`
        }
        darkMode={darkMode}
      />

      <ClearChatModal
        isOpen={clearChatModalOpen}
        onClose={() => setClearChatModalOpen(false)}
        onConfirm={handleClearChat}
        messageCount={messages.length}
        darkMode={darkMode}
      />

      {/* Automation Preview Modal */}
      {automationPreviewOpen && currentConversationId && (
        <AutomationPreview
          automationYaml={previewAutomationYaml}
          alias={previewAutomationAlias}
          toolCall={previewToolCall}
          darkMode={darkMode}
          onClose={() => setAutomationPreviewOpen(false)}
          onEdit={handleEditAutomation}
          conversationId={currentConversationId}
        />
      )}
    </div>
  );
};

