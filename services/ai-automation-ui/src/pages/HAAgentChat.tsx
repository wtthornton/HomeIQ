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
  deleteConversation,
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
import { AutomationProposal } from '../components/ha-agent/AutomationProposal';
import { ProposalErrorBoundary } from '../components/ha-agent/ProposalErrorBoundary';
import { MessageContent } from '../components/ha-agent/MessageContent';
import { MarkdownErrorBoundary } from '../components/ha-agent/MarkdownErrorBoundary';
import { CTAActionButtons } from '../components/ha-agent/CTAActionButtons';
import { EnhancementButton } from '../components/ha-agent/EnhancementButton';
import { SendButton } from '../components/ha-agent/SendButton';
import { DebugTab } from '../components/ha-agent/DebugTab';
import { startTracking, endTracking, createReport } from '../utils/performanceTracker';
import { parseProposal } from '../utils/proposalParser';

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
  const [previewToolCall, setPreviewToolCall] = useState<ToolCall | undefined>(undefined);
  const [originalPrompt, setOriginalPrompt] = useState<string>('');
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState<'chat' | 'debug'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Helper function to deduplicate messages using a Set-based approach (2025 pattern)
  // Deduplicates by message_id first (most reliable), then by content+role to catch API duplicates
  const deduplicateMessages = (messages: ChatMessage[]): ChatMessage[] => {
    const seenById = new Set<string>();
    const seenByContent = new Set<string>();
    const uniqueMessages: ChatMessage[] = [];
    
    for (const msg of messages) {
      // Skip empty loading messages
      if (!msg.content.trim() && msg.isLoading) {
        continue;
      }
      
      const normalizedContent = msg.content.trim();
      const isTemp = msg.message_id.startsWith('temp-') || msg.message_id.startsWith('loading-');
      
      // For real messages (from API), check both message_id and content+role
      if (!isTemp && msg.message_id) {
        const idKey = `id:${msg.message_id}`;
        const contentKey = `content:${msg.role}:${normalizedContent}`;
        
        // Skip if we've seen this message_id OR this exact content+role combination
        if (seenById.has(idKey) || seenByContent.has(contentKey)) {
          continue;
        }
        
        seenById.add(idKey);
        seenByContent.add(contentKey);
        uniqueMessages.push(msg);
      } else {
        // For temp/loading messages, use content+role+timestamp to allow same content at different times
        const timestamp = new Date(msg.created_at).getTime();
        const contentKey = `content:${msg.role}:${normalizedContent}:${timestamp}`;
        
        if (!seenByContent.has(contentKey)) {
          seenByContent.add(contentKey);
          uniqueMessages.push(msg);
        }
      }
    }
    
    // Sort by creation time to maintain chronological order
    return uniqueMessages.sort((a, b) => 
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  };

  // Load conversation function
  const loadConversation = async () => {
    if (currentConversationId) {
      try {
        setIsInitializing(true);
        const conversation = await getConversation(currentConversationId);
        setCurrentConversation(conversation);
        const loadedMessages = conversation.messages?.map((msg) => ({
          ...msg,
          isLoading: false,
        })) || [];
        
        // When loading a conversation, replace all messages (don't merge)
        // Deduplicate to prevent duplicates from API or previous state
        const deduplicated = deduplicateMessages(loadedMessages);
        console.log(`[HAAgentChat] Loaded ${loadedMessages.length} messages, deduplicated to ${deduplicated.length}`);
        setMessages(deduplicated);
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

  // Load conversation on mount or when conversation ID changes
  useEffect(() => {
    loadConversation();
  }, [currentConversationId]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    // Start performance tracking
    const operationId = `send_message_${Date.now()}`;
    const uiUpdateId = startTracking('ui_update', { operation: 'add_user_message' });
    const apiCallId = startTracking('api_call', { 
      operation: 'sendChatMessage',
      conversation_id: currentConversationId || 'new',
    });

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
    endTracking(uiUpdateId, { message_length: userMessage.content.length });

    // Add loading message
    const loadingId = startTracking('ui_update', { operation: 'add_loading_message' });
    const loadingMessage: ChatMessage = {
      message_id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);
    endTracking(loadingId);

    try {
      const response = await sendChatMessage({
        message: userMessage.content,
        conversation_id: currentConversationId || undefined,
      });
      
      endTracking(apiCallId, {
        success: true,
        response_time_ms: response.metadata?.response_time_ms,
        tokens_used: response.metadata?.tokens_used,
        tool_calls_count: response.tool_calls?.length || 0,
        iterations: response.metadata?.iterations || 1,
      });

      // Update conversation ID if this was a new conversation
      if (!currentConversationId && response.conversation_id) {
        setCurrentConversationId(response.conversation_id);
        // Reload conversation to get full details - this will replace messages via useEffect
        const reloadId = startTracking('api_call', { operation: 'getConversation' });
        try {
          const conversation = await getConversation(response.conversation_id);
          endTracking(reloadId, { success: true, message_count: conversation.message_count });
          setCurrentConversation(conversation);
          // Messages will be replaced by the useEffect when currentConversationId changes
          // Don't add messages here - let the useEffect handle it to avoid duplicates
          setIsLoading(false);
          
          // Create performance report
          createReport(operationId, [uiUpdateId, loadingId, apiCallId, reloadId]);
          return; // Exit early to let useEffect handle message loading
        } catch (error) {
          endTracking(reloadId, { success: false, error: error instanceof Error ? error.message : 'Unknown' });
          console.error('Failed to reload conversation:', error);
          // Fall through to add message manually if reload fails
        }
      }

      // Remove loading message and add assistant response
      // Only add if conversation wasn't just reloaded (which would have returned early)
      const responseUpdateId = startTracking('ui_update', { operation: 'add_assistant_response' });
      setMessages((prev) => {
        const filtered = prev.filter((msg) => !msg.isLoading);
        const assistantMessage: ChatMessage = {
          message_id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.message,
          created_at: new Date().toISOString(),
          isLoading: false,
          toolCalls: response.tool_calls || [],
          responseTimeMs: response.metadata?.response_time_ms,
        };
        
        // Check if this message already exists (by message_id or content)
        const alreadyExists = filtered.some(
          m => (m.message_id === assistantMessage.message_id && assistantMessage.message_id) ||
               (m.role === 'assistant' && m.content.trim() === assistantMessage.content.trim() && 
                !m.message_id.startsWith('temp-') && !m.message_id.startsWith('loading-'))
        );
        
        if (alreadyExists) {
          // Message already exists, just remove loading
          return filtered;
        }
        
        // Deduplicate to prevent adding the same message twice
        return deduplicateMessages([...filtered, assistantMessage]);
      });
      endTracking(responseUpdateId, { 
        response_length: response.message.length,
        tool_calls_count: response.tool_calls?.length || 0,
      });

      // Show tool calls if any
      if (response.tool_calls && response.tool_calls.length > 0) {
        toast.success(`Agent executed ${response.tool_calls.length} action(s)`, {
          icon: '🔧',
        });
      }
      
      // Create performance report
      createReport(operationId, [uiUpdateId, loadingId, apiCallId, responseUpdateId]);
    } catch (error) {
      console.error('Chat error:', error);
      endTracking(apiCallId, { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error',
      });

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
      
      // Create performance report even on error
      const errorUpdateId = startTracking('ui_update', { operation: 'add_error_message' });
      endTracking(errorUpdateId);
      createReport(operationId, [uiUpdateId, loadingId, apiCallId, errorUpdateId]);
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
      
      // Refresh conversation list in sidebar
      setSidebarRefreshTrigger(prev => prev + 1);
      
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
    // Check tool calls for preview_automation_from_prompt, create_automation_from_prompt, or test_automation_yaml
    if (message.toolCalls) {
      for (const toolCall of message.toolCalls) {
        if (toolCall.name === 'preview_automation_from_prompt' || 
            toolCall.name === 'create_automation_from_prompt' || 
            toolCall.name === 'test_automation_yaml') {
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
      setPreviewToolCall(automation.toolCall ?? undefined);
      setAutomationPreviewOpen(true);
      
      // Extract original prompt from conversation - get the most recent user message
      const userMessage = messages.slice().reverse().find(m => m.role === 'user');
      if (userMessage) {
        setOriginalPrompt(userMessage.content);
      }
    }
  };
  
  const handleEnhancementSelected = (enhancement: { enhanced_yaml: string; title?: string }) => {
    // Detect if this is a prompt enhancement (no YAML structure) or YAML enhancement
    const isPromptEnhancement = !previewAutomationYaml && 
                                 enhancement.enhanced_yaml && 
                                 !enhancement.enhanced_yaml.includes('alias:') &&
                                 !enhancement.enhanced_yaml.includes('trigger:') &&
                                 !enhancement.enhanced_yaml.includes('action:');
    
    if (isPromptEnhancement) {
      // Prompt enhancement: Insert enhanced prompt into input field
      setInputValue(enhancement.enhanced_yaml);
      toast.success(`Enhanced prompt applied: ${enhancement.title}`, { icon: '✨' });
      // Focus input after a brief delay
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    } else {
      // YAML enhancement: Apply YAML to preview (existing behavior)
      setPreviewAutomationYaml(enhancement.enhanced_yaml);
      if (enhancement.title) {
        setPreviewAutomationAlias(enhancement.title);
      }
      toast.success(`Enhancement applied: ${enhancement.title}`, { icon: '✅' });
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
          refreshTrigger={sidebarRefreshTrigger}
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
          <div className="flex items-center gap-2">
            {/* Tab Switcher */}
            <div className={`flex rounded-lg p-1 ${
              darkMode ? 'bg-gray-700' : 'bg-gray-200'
            }`}>
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'chat'
                    ? darkMode
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-500 text-white'
                    : darkMode
                    ? 'text-gray-300 hover:bg-gray-600'
                    : 'text-gray-700 hover:bg-gray-300'
                }`}
              >
                💬 Chat
              </button>
              <button
                onClick={() => setActiveTab('debug')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'debug'
                    ? darkMode
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-500 text-white'
                    : darkMode
                    ? 'text-gray-300 hover:bg-gray-600'
                    : 'text-gray-700 hover:bg-gray-300'
                }`}
              >
                🔍 Debug
              </button>
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
        </div>

        {/* Tab Content */}
        {activeTab === 'chat' ? (
          <>
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
                          {(() => {
                            // Check if this is a proposal message
                            const proposal = parseProposal(message.content);
                            
                            if (proposal.hasProposal && proposal.sections.length > 0) {
                              // Render structured proposal
                              return (
                                <>
                                  <div className="mb-3">
                                    <p className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                      Here's what I'll create for you:
                                    </p>
                                    <ProposalErrorBoundary>
                                      <AutomationProposal sections={proposal.sections} darkMode={darkMode} />
                                    </ProposalErrorBoundary>
                                  </div>
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
                                  {detectAutomation(message) && (
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
                                  {currentConversationId && (
                                    <CTAActionButtons
                                      messageContent={message.content}
                                      automationYaml={detectAutomation(message)?.yaml}
                                      conversationId={currentConversationId}
                                      darkMode={darkMode}
                                      onSuccess={(automationId) => {
                                        toast.success(`Automation ${automationId} created successfully!`);
                                        // Refresh conversation to show new message
                                        if (currentConversationId) {
                                          loadConversation();
                                        }
                                      }}
                                    />
                                  )}
                                </>
                              );
                            }
                            
                            // Regular message rendering with markdown
                            const automation = detectAutomation(message);
                            return (
                              <>
                                <MarkdownErrorBoundary content={message.content} darkMode={darkMode}>
                                  <MessageContent content={message.content} darkMode={darkMode} />
                                </MarkdownErrorBoundary>
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
                                {message.role === 'assistant' && automation && (
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
                                {message.role === 'assistant' && currentConversationId && (
                                  <CTAActionButtons
                                    messageContent={message.content}
                                    automationYaml={automation?.yaml}
                                    conversationId={currentConversationId}
                                    darkMode={darkMode}
                                    onSuccess={(automationId) => {
                                      toast.success(`Automation ${automationId} created successfully!`);
                                      // Refresh conversation to show new message
                                      if (currentConversationId) {
                                        loadConversation();
                                      }
                                    }}
                                  />
                                )}
                              </>
                            );
                          })()}
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
            {(() => {
              // Show button if there's a conversation
              if (!currentConversationId) return null;
              
              // Check for automation in messages or in preview
              const hasAutomation = messages.some(m => detectAutomation(m));
              const hasPreviewYaml = !!previewAutomationYaml;
              
              // Check if any assistant message mentions automation creation (even without YAML yet)
              const hasAutomationMention = messages.some(m => 
                m.role === 'assistant' && 
                (m.content.toLowerCase().includes('automation') || 
                 m.content.toLowerCase().includes('create') ||
                 m.content.toLowerCase().includes('here\'s what i\'ll create'))
              );
              
              // Show button if there's an automation detected, preview is open, preview YAML exists, or automation is mentioned
              if (!hasAutomation && !automationPreviewOpen && !hasPreviewYaml && !hasAutomationMention) return null;
              
              // Get the latest automation from messages
              const latestAutomation = messages.slice().reverse().find(m => detectAutomation(m));
              const automation = latestAutomation ? detectAutomation(latestAutomation) : null;
              // Get the most recent user message (not just the first one)
              const userMsg = messages.slice().reverse().find(m => m.role === 'user');
              
              // If we don't have YAML yet but have a mention, try to get it from the most recent assistant message
              let automationYaml = previewAutomationYaml || automation?.yaml || '';
              if (!automationYaml && hasAutomationMention) {
                // Try to extract YAML from the most recent assistant message
                const latestAssistant = messages.slice().reverse().find(m => m.role === 'assistant');
                if (latestAssistant) {
                  const detected = detectAutomation(latestAssistant);
                  if (detected) {
                    automationYaml = detected.yaml;
                  }
                }
              }
              
              return (
                <EnhancementButton
                  automationYaml={automationYaml || undefined}  // Optional - pass only if available
                  originalPrompt={originalPrompt || userMsg?.content || ''}
                  conversationId={currentConversationId}
                  darkMode={darkMode}
                  onEnhancementSelected={handleEnhancementSelected}
                />
              );
            })()}
            <SendButton
              onClick={handleSend}
              disabled={!inputValue.trim()}
              isLoading={isLoading}
              darkMode={darkMode}
              label="Send"
              loadingText="Sending..."
            />
          </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <DebugTab
              conversationId={currentConversationId}
              darkMode={darkMode}
            />
          </div>
        )}
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

