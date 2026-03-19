/**
 * HA Agent Chat Page
 * Epic AI-20 Story AI20.7: HA Agent Chat Page
 * 
 * Chat interface for interacting with the HA AI Agent
 */

import React, { useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import {
  sendChatMessage,
  getConversation,
  deleteConversation,
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
import { DevicePicker } from '../components/ha-agent/DevicePicker';
import { DeviceContextDisplay } from '../components/ha-agent/DeviceContextDisplay';
import { DeviceSuggestions, type DeviceSuggestion } from '../components/ha-agent/DeviceSuggestions';
import { startTracking, endTracking, createReport } from '../utils/performanceTracker';
import { parseProposal } from '../utils/proposalParser';
import { sanitizeMessageInput } from '../utils/inputSanitizer';
import { useChatState, deduplicateMessages, type ChatMessage } from '../hooks/useChatState';

export const HAAgentChat: React.FC = () => {
  const { darkMode } = useAppStore();
  const location = useLocation();
  const navigate = useNavigate();
  const {
    messages, setMessages,
    inputValue, setInputValue,
    isLoading, setIsLoading,
    currentConversationId, setCurrentConversationId,
    currentConversation, setCurrentConversation,
    isInitializing, setIsInitializing,
    blueprintContext, setBlueprintContext,
    sidebarOpen, setSidebarOpen,
    deleteModalOpen, setDeleteModalOpen,
    deleteTargetId, setDeleteTargetId,
    clearChatModalOpen, setClearChatModalOpen,
    automationPreviewOpen, setAutomationPreviewOpen,
    previewAutomationYaml, setPreviewAutomationYaml,
    previewAutomationAlias, setPreviewAutomationAlias,
    previewToolCall, setPreviewToolCall,
    originalPrompt, setOriginalPrompt,
    sidebarRefreshTrigger, setSidebarRefreshTrigger,
    activeTab, setActiveTab,
    selectedDeviceId, setSelectedDeviceId,
    devicePickerOpen, setDevicePickerOpen,
    messagesEndRef,
    inputRef,
  } = useChatState();

  // State persistence: Store originalPrompt in localStorage with conversation ID
  useEffect(() => {
    if (originalPrompt && currentConversationId) {
      try {
        localStorage.setItem(`originalPrompt:${currentConversationId}`, originalPrompt);
      } catch (error) {
        console.warn('[HAAgentChat] Failed to store originalPrompt in localStorage:', error);
      }
    }
  }, [originalPrompt, currentConversationId]);

  // Restore originalPrompt from localStorage on conversation load
  useEffect(() => {
    if (currentConversationId && !originalPrompt) {
      try {
        const stored = localStorage.getItem(`originalPrompt:${currentConversationId}`);
        if (stored) {
          setOriginalPrompt(stored);
        }
      } catch (error) {
        console.warn('[HAAgentChat] Failed to restore originalPrompt from localStorage:', error);
      }
    }
  }, [currentConversationId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
          // Map API tool_calls (snake_case) to component toolCalls (camelCase)
          toolCalls: msg.tool_calls || undefined,
        })) || [];
        
        // When loading a conversation, replace all messages (don't merge)
        // Deduplicate to prevent duplicates from API or previous state
        const deduplicated = deduplicateMessages(loadedMessages);
        setMessages(deduplicated);
        
        // Fix for EnhancementButton: Ensure originalPrompt is set after reload
        // Set originalPrompt from latest user message if not already set
        // This ensures EnhancementButton works after automation creation + reload
        if (!originalPrompt) {
          const latestUserMsg = deduplicated.slice().reverse().find(m => m.role === 'user');
          if (latestUserMsg) {
            setOriginalPrompt(latestUserMsg.content);
          } else {
            // Debug logging: Structured logging for diagnostics
            console.warn('[HAAgentChat] No user message found after reload:', {
              conversationId: currentConversationId,
              messageCount: deduplicated.length,
              messages: deduplicated.map(m => ({ role: m.role, id: m.message_id })),
            });
          }
        }
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

  // Check for blueprint context from navigation state
  useEffect(() => {
    const context = (location.state as any)?.blueprintContext;
    if (context) {
      setBlueprintContext(context);
      // Clear navigation state to prevent re-triggering on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate]);

  // Load conversation on mount or when conversation ID changes
  useEffect(() => {
    loadConversation();
  }, [currentConversationId]);

  // Fix for EnhancementButton: Set originalPrompt when automation is detected
  // This ensures originalPrompt is available even if user didn't preview automation first
  useEffect(() => {
    // Only set if not already set
    if (!originalPrompt && messages.length > 0) {
      // Check if any message contains automation (detectAutomation is defined in component scope)
      const hasAutomation = messages.some(m => {
        // Check tool calls for automation-related tools
        if (m.toolCalls) {
          return m.toolCalls.some(tc => 
            tc.name === 'preview_automation_from_prompt' || 
            tc.name === 'create_automation_from_prompt' ||
            tc.name === 'test_automation_yaml'
          );
        }
        // Check message content for YAML code blocks
        return /```yaml\n([\s\S]*?)```/.test(m.content);
      });
      
      if (hasAutomation) {
        const userMsg = messages.slice().reverse().find(m => m.role === 'user');
        if (userMsg) {
          setOriginalPrompt(userMsg.content);
        } else {
          // Debug logging: Structured logging for diagnostics
          console.warn('[HAAgentChat] Automation detected but no user message found:', {
            conversationId: currentConversationId,
            messageCount: messages.length,
            messages: messages.map(m => ({ role: m.role, id: m.message_id })),
          });
        }
      }
    }
  }, [messages, originalPrompt]);

  // Send initial message with blueprint context if present
  useEffect(() => {
    if (blueprintContext && !currentConversationId && !isLoading && !isInitializing) {
      const sendInitialBlueprintMessage = async () => {
        const hiddenContext = {
          blueprint_id: blueprintContext.blueprint_id,
          blueprint_yaml: blueprintContext.blueprint_yaml,
          blueprint_inputs: blueprintContext.blueprint_inputs,
          matched_devices: blueprintContext.matched_devices,
          constraint_mode: 'blueprint',
        };

        try {
          const response = await sendChatMessage({
            message: `I'd like to work with the "${blueprintContext.blueprint_name || 'Blueprint'}" blueprint.`,
            hidden_context: hiddenContext,
            title: `Blueprint: ${blueprintContext.blueprint_name || 'Blueprint'}`,
            source: 'blueprint',
          });
          
          setCurrentConversationId(response.conversation_id);
          toast.success('Blueprint context loaded');
        } catch (error) {
          console.error('Failed to send initial blueprint message:', error);
          toast.error('Failed to load blueprint context');
        }
      };
      
      sendInitialBlueprintMessage();
    }
  }, [blueprintContext, currentConversationId, isLoading, isInitializing]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    // SECURITY: Sanitize user input before processing
    const sanitizedInput = sanitizeMessageInput(inputValue, 10000);
    if (!sanitizedInput) {
      toast.error('Invalid input. Please check your message and try again.');
      return;
    }

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
      content: sanitizedInput,
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
                ? `Error: ${error.message}`
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
          ? error.message
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

  // Memoize latest user message to avoid repeated array operations
  const latestUserMessage = useMemo(() => {
    // Reverse iteration is more efficient than slice().reverse()
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return messages[i];
      }
    }
    return undefined;
  }, [messages]);

  // Memoization optimization: Reuse memoized latestUserMessage for EnhancementButton
  const userMsgForEnhance = useMemo(() => {
    if (originalPrompt) return null; // Don't calculate if already set
    return latestUserMessage;
  }, [originalPrompt, latestUserMessage]);

  const handlePreviewAutomation = (message: ChatMessage) => {
    const automation = detectAutomation(message);
    if (automation) {
      setPreviewAutomationYaml(automation.yaml);
      setPreviewAutomationAlias(automation.alias);
      setPreviewToolCall(automation.toolCall ?? undefined);
      setAutomationPreviewOpen(true);
      
      // Use memoized latest user message
      if (latestUserMessage) {
        setOriginalPrompt(latestUserMessage.content);
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
      // YAML enhancement: Apply YAML to preview and open the preview modal
      setPreviewAutomationYaml(enhancement.enhanced_yaml);
      if (enhancement.title) {
        setPreviewAutomationAlias(enhancement.title);
      }
      setAutomationPreviewOpen(true);
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
        {/* Device Picker */}
        <DevicePicker
          darkMode={darkMode}
          selectedDeviceId={selectedDeviceId}
          onSelectDevice={setSelectedDeviceId}
          isOpen={devicePickerOpen}
          onToggle={() => setDevicePickerOpen(!devicePickerOpen)}
        />
        
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
            {/* Device Picker Toggle Button */}
            <button
              onClick={() => setDevicePickerOpen(!devicePickerOpen)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedDeviceId
                  ? darkMode
                    ? 'bg-blue-600 text-white hover:bg-blue-500'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                  : darkMode
                  ? 'bg-gray-700 text-white hover:bg-gray-600'
                  : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
              }`}
              title={selectedDeviceId ? 'Change Device' : 'Select Device'}
            >
              {selectedDeviceId ? '🔌 Device Selected' : '🔌 Select Device'}
            </button>
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
              data-testid="new-chat"
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
            {/* Device Context Display */}
            <DeviceContextDisplay
              darkMode={darkMode}
              deviceId={selectedDeviceId}
              onClearSelection={() => setSelectedDeviceId(null)}
            />
            
            {/* Device Suggestions */}
            <DeviceSuggestions
              darkMode={darkMode}
              deviceId={selectedDeviceId}
              onEnhanceSuggestion={async (suggestion: DeviceSuggestion) => {
                try {
                  // Ensure we have a conversation
                  if (!currentConversationId) {
                    // Start new conversation
                    const response = await sendChatMessage({
                      message: `I'd like to enhance this automation suggestion: ${suggestion.title}`,
                      title: `Enhance: ${suggestion.title.substring(0, 50)}`,
                    });
                    setCurrentConversationId(response.conversation_id);
                    // Reload to get full conversation
                    await loadConversation();
                  }
                  
                  // Send enhancement request
                  const enhancementPrompt = `Enhance this automation suggestion:

Title: ${suggestion.title}
Description: ${suggestion.description}
Trigger: ${suggestion.automation_preview.trigger}
Action: ${suggestion.automation_preview.action}

Please provide an improved version with more details, better automation logic, and specific Home Assistant configuration.`;
                  
                  // Pre-populate input with enhancement prompt
                  setInputValue(enhancementPrompt);
                  
                  // Focus input so user can review/edit before sending
                  setTimeout(() => {
                    inputRef.current?.focus();
                    // Scroll input into view
                    inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                  }, 100);
                  
                  toast.success('Enhancement prompt ready - review and send to enhance', { 
                    icon: '✨',
                    duration: 3000,
                  });
                } catch (error) {
                  console.error('Failed to prepare enhancement:', error);
                  toast.error('Failed to prepare enhancement. Please try again.');
                }
              }}
            />
            
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
                <p className={`text-sm mb-4 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                  Start by typing below or try a suggested question.
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
                      data-testid={message.isLoading ? 'chat-loading' : 'chat-message'}
                      data-role={message.role}
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
                        <div className="flex items-center gap-2" data-testid="chat-loading-inner">
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
                                      automationYaml={previewAutomationYaml || detectAutomation(message)?.yaml}
                                      conversationId={currentConversationId}
                                      originalUserPrompt={latestUserMessage?.content}
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
                                    automationYaml={previewAutomationYaml || automation?.yaml}
                                    conversationId={currentConversationId}
                                    originalUserPrompt={latestUserMessage?.content}
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
              data-testid="message-input"
              ref={inputRef}
              value={inputValue}
              onChange={(e) => {
                // SECURITY: Basic input validation on change
                const value = e.target.value;
                if (value.length <= 10000) {
                  setInputValue(value);
                } else {
                  toast.error('Message is too long. Maximum 10,000 characters.');
                }
              }}
              onKeyDown={handleKeyPress}
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
                  originalPrompt={originalPrompt || userMsgForEnhance?.content || userMsg?.content || ''}
                  conversationId={currentConversationId}
                  darkMode={darkMode}
                  onEnhancementSelected={handleEnhancementSelected}
                />
              );
            })()}
            <SendButton
              data-testid="send-button"
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
          originalPrompt={originalPrompt}
        />
      )}
    </div>
  );
};

