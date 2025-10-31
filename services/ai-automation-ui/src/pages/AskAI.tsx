/**
 * Ask AI Page - Natural Language Query Interface
 * 
 * Chat-based interface for asking questions about Home Assistant devices
 * and receiving automation suggestions. Optimized for full screen utilization.
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import { ConversationalSuggestionCard } from '../components/ConversationalSuggestionCard';
import { ContextIndicator } from '../components/ask-ai/ContextIndicator';
import api from '../services/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  suggestions?: any[];
  entities?: any[];
  confidence?: number;
  followUpPrompts?: string[];
}

interface AskAIQuery {
  query_id: string;
  original_query: string;
  parsed_intent: string;
  extracted_entities: any[];
  suggestions: any[];
  confidence: number;
  processing_time_ms: number;
  created_at: string;
}

interface ConversationContext {
  mentioned_devices: string[];
  mentioned_intents: string[];
  active_suggestions: string[];
  last_query: string;
  last_entities: any[];
}

const exampleQueries = [
  "Turn on the living room lights when I get home",
  "Flash the office lights when VGK scores",
  "Alert me when the garage door is left open",
  "Turn off all lights when I leave the house",
  "Dim the bedroom lights at sunset",
  "Turn on the coffee maker at 7 AM on weekdays"
];

export const AskAI: React.FC = () => {
  const { darkMode } = useAppStore();
  
  // Welcome message constant
  const welcomeMessage: ChatMessage = {
    id: 'welcome',
    type: 'ai',
    content: "Hi! I'm your Home Assistant AI assistant. I can help you create automations by understanding your natural language requests. Here are some examples:",
    timestamp: new Date(),
    suggestions: []
  };
  
  // Load conversation from localStorage or start fresh
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem('ask-ai-conversation');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Restore Date objects from ISO strings
        return parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
      } catch (e) {
        console.error('Failed to parse saved conversation:', e);
        return [welcomeMessage];
      }
    }
    return [welcomeMessage];
  });
  
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [processingActions, setProcessingActions] = useState<Set<string>>(new Set());
  
  // Conversation context tracking
  const [conversationContext, setConversationContext] = useState<ConversationContext>({
    mentioned_devices: [],
    mentioned_intents: [],
    active_suggestions: [],
    last_query: '',
    last_entities: []
  });
  
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Save conversation to localStorage whenever messages change
  useEffect(() => {
    try {
      localStorage.setItem('ask-ai-conversation', JSON.stringify(messages));
    } catch (e) {
      console.error('Failed to save conversation to localStorage:', e);
    }
  }, [messages]);
  
  // Update context from message
  const updateContextFromMessage = (message: ChatMessage) => {
    if (message.entities && message.entities.length > 0) {
      const devices = message.entities
        .map(e => e.name || e.entity_id || '')
        .filter(Boolean) as string[];
      
      setConversationContext(prev => ({
        ...prev,
        mentioned_devices: [...new Set([...prev.mentioned_devices, ...devices])], // Deduplicate
        last_query: message.content,
        last_entities: message.entities || []
      }));
    }
    
    if (message.suggestions && message.suggestions.length > 0) {
      const suggestionIds = message.suggestions.map(s => s.suggestion_id || '');
      setConversationContext(prev => ({
        ...prev,
        active_suggestions: [...new Set([...prev.active_suggestions, ...suggestionIds])] // Deduplicate
      }));
    }
  };
  
  // Generate follow-up prompts based on query and suggestions
  const generateFollowUpPrompts = (query: string, suggestions: any[]): string[] => {
    const prompts: string[] = [];
    const queryLower = query.toLowerCase();
    
    // Flash-specific prompts
    if (queryLower.includes('flash')) {
      prompts.push('Make it flash 5 times instead');
      prompts.push('Use different colors for the flash');
    }
    
    // Light-specific prompts
    if (queryLower.includes('light')) {
      prompts.push(`Set brightness to 50%`);
      prompts.push('Only after sunset');
      if (!queryLower.includes('flash')) {
        prompts.push('Make it flash instead');
      }
    }
    
    // Time-specific prompts
    if (queryLower.includes('when') || queryLower.includes('at ')) {
      prompts.push('Change the time schedule');
      prompts.push('Add more conditions');
    }
    
    // General refinement prompts
    if (suggestions.length > 0) {
      prompts.push('Show me more automation ideas');
      prompts.push('What else can I automate?');
    }
    
    // Return up to 4 prompts, removing duplicates
    return [...new Set(prompts)].slice(0, 4);
  };

  const handleSendMessage = async () => {
    const inputValue = inputRef.current?.value.trim();
    if (!inputValue || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      // Pass context and conversation history to API
      const response = await api.askAIQuery(inputValue, {
        conversation_context: conversationContext,
        conversation_history: messages
          .filter(msg => msg.type !== 'ai' || msg.id !== 'welcome')
          .map(msg => ({
            role: msg.type,
            content: msg.content,
            timestamp: msg.timestamp.toISOString()
          }))
      });
      
      // Simulate typing delay for better UX
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Generate follow-up prompts
      const followUpPrompts = generateFollowUpPrompts(
        inputValue,
        response.suggestions
      );
      
      const aiMessage: ChatMessage = {
        id: response.query_id,
        type: 'ai',
        content: generateAIResponse(response),
        timestamp: new Date(),
        suggestions: response.suggestions,
        entities: response.extracted_entities,
        confidence: response.confidence,
        followUpPrompts: followUpPrompts
      };

      setMessages(prev => [...prev, aiMessage]);
      
      // Update context with the AI response
      updateContextFromMessage(aiMessage);
      
      if (response.suggestions.length === 0) {
        toast.error('No suggestions found. Try rephrasing your question.');
      } else {
        toast.success(`Found ${response.suggestions.length} automation suggestion${response.suggestions.length > 1 ? 's' : ''}`);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to process your request. Please try again.');
      
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'ai',
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const generateAIResponse = (query: AskAIQuery): string => {
    const { suggestions, extracted_entities, confidence } = query;

    let response = `I found ${suggestions.length} automation suggestion${suggestions.length > 1 ? 's' : ''} for your request.`;

    if (extracted_entities.length > 0) {
      const entityNames = extracted_entities.map(e => e.name || e.entity_id || 'unknown').join(', ');
      response += ` I detected these devices: ${entityNames}.`;
    }

    if (confidence < 0.7) {
      response += ` Note: I'm ${Math.round(confidence * 100)}% confident in these suggestions. You may want to refine them.`;
    }

    return response;
  };

  const handleSuggestionAction = async (suggestionId: string, action: 'refine' | 'approve' | 'reject' | 'test', refinement?: string) => {
    const actionKey = `${suggestionId}-${action}`;
    
    try {
      setProcessingActions(prev => new Set(prev).add(actionKey));
      
      if (action === 'test') {
        const messageWithQuery = messages.find(msg => 
          msg.suggestions?.some(s => s.suggestion_id === suggestionId)
        );
        const queryId = messageWithQuery?.id || 'unknown';
        
        // Show loading toast
        const loadingToast = toast.loading('⏳ Creating and running test automation...');
        
        try {
          const response = await api.testAskAISuggestion(queryId, suggestionId);
          toast.dismiss(loadingToast);
          
          // Log the quality report to console
          if (response.quality_report) {
            console.log('🔍 Quality Report:', JSON.stringify(response.quality_report, null, 2));
          }
          
          if (!response.valid) {
            toast.error(`❌ Validation failed: ${response.validation_details?.error || 'Unknown error'}`, {
              duration: 6000
            });
          } else if (response.executed) {
            toast.success(
              `✅ Test automation executed! Check your devices.\n\nAutomation ID: ${response.automation_id}`,
              { duration: 8000 }
            );
            
            // Show additional info
            if (response.validation_details?.warnings?.length > 0) {
              response.validation_details.warnings.forEach((warning: string) => {
                toast(warning, { icon: '⚠️', duration: 5000 });
              });
            }
            
            // Show cleanup info
            toast(
              `💡 The test automation "${response.automation_id}" is now disabled. You can delete it from HA or approve this suggestion.`,
              { icon: 'ℹ️', duration: 6000 }
            );
          } else {
            toast.error(
              `⚠️ Test automation created but execution failed. Check HA logs.\n\nAutomation ID: ${response.automation_id}`,
              { duration: 8000 }
            );
          }
        } catch (error) {
          toast.dismiss(loadingToast);
          throw error;
        }
      } else if (action === 'refine' && refinement) {
        // TODO: Implement refinement API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        toast.success('Refinement submitted');
      } else if (action === 'approve') {
        const messageWithQuery = messages.find(msg => 
          msg.suggestions?.some(s => s.suggestion_id === suggestionId)
        );
        const queryId = messageWithQuery?.id || 'unknown';
        
        await api.approveAskAISuggestion(queryId, suggestionId);
        toast.success('✅ Automation approved and YAML generated!');
        
        setMessages(prev => prev.map(msg => ({
          ...msg,
          suggestions: msg.suggestions?.filter(s => s.suggestion_id !== suggestionId) || []
        })));
      } else if (action === 'reject') {
        await new Promise(resolve => setTimeout(resolve, 500));
        toast.success('Suggestion rejected');
        
        setMessages(prev => prev.map(msg => ({
          ...msg,
          suggestions: msg.suggestions?.filter(s => s.suggestion_id !== suggestionId) || []
        })));
      }
    } catch (error) {
      console.error('Suggestion action failed:', error);
      toast.error(`Failed to ${action} suggestion`);
    } finally {
      setProcessingActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(actionKey);
        return newSet;
      });
    }
  };

  const clearChat = () => {
    localStorage.removeItem('ask-ai-conversation');
    setMessages([welcomeMessage]);
    setConversationContext({
      mentioned_devices: [],
      mentioned_intents: [],
      active_suggestions: [],
      last_query: '',
      last_entities: []
    });
    toast.success('Chat cleared');
  };

  const handleExampleClick = (example: string) => {
    setInputValue(example);
    inputRef.current?.focus();
  };
  
  const exportConversation = () => {
    try {
      const conversationData = {
        messages: messages,
        context: conversationContext,
        exportedAt: new Date().toISOString(),
        version: '1.0'
      };
      
      const dataStr = JSON.stringify(conversationData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `ask-ai-conversation-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.success('Conversation exported successfully');
    } catch (error) {
      console.error('Failed to export conversation:', error);
      toast.error('Failed to export conversation');
    }
  };
  
  const importConversation = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const data = JSON.parse(content);
        
        // Validate structure
        if (!data.messages || !Array.isArray(data.messages)) {
          throw new Error('Invalid conversation format');
        }
        
        // Restore Date objects
        const restoredMessages = data.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        
        setMessages(restoredMessages);
        
        // Restore context if available
        if (data.context) {
          setConversationContext(data.context);
        }
        
        // Save to localStorage
        localStorage.setItem('ask-ai-conversation', JSON.stringify(restoredMessages));
        
        toast.success('Conversation imported successfully');
      } catch (error) {
        console.error('Failed to import conversation:', error);
        toast.error('Failed to import conversation - invalid file format');
      }
    };
    
    reader.readAsText(file);
    // Reset input so same file can be selected again
    event.target.value = '';
  };

  return (
    <div className={`flex transition-colors ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`} style={{ 
      height: 'calc(100vh - 80px)',
      position: 'fixed',
      top: '80px',
      left: '0',
      right: '0',
      bottom: '0'
    }}>
      {/* Sidebar with Examples */}
      <motion.div
        initial={false}
        animate={{ width: sidebarOpen ? '320px' : '0px' }}
        className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-r overflow-hidden`}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Quick Examples
            </h3>
            <button
              onClick={() => setSidebarOpen(false)}
              className={`p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="space-y-2">
            {exampleQueries.map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleClick(example)}
                className={`w-full text-left p-3 rounded-lg text-sm transition-colors ${
                  darkMode 
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' 
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Main Chat Area - Full Height Container */}
      <div className="flex-1 flex flex-col h-full">
        {/* Ultra-Compact Header - Full width */}
        <div className={`flex items-center justify-between px-6 py-2 border-b flex-shrink-0 ${
          darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
        }`}>
          <div className="flex items-center space-x-3">
            <h1 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Ask AI
            </h1>
            <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Home Assistant Automation Assistant
            </span>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className={`p-1.5 rounded transition-colors ${
                darkMode 
                  ? 'hover:bg-gray-700 text-gray-300' 
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Toggle Examples"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={exportConversation}
              className={`p-1.5 rounded transition-colors ${
                darkMode 
                  ? 'hover:bg-gray-700 text-gray-300' 
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Export Conversation"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <label
              className={`p-1.5 rounded cursor-pointer transition-colors ${
                darkMode 
                  ? 'hover:bg-gray-700 text-gray-300' 
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Import Conversation"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <input
                type="file"
                accept=".json"
                onChange={importConversation}
                className="hidden"
              />
            </label>
            <button
              onClick={clearChat}
              className={`px-2 py-1 rounded text-xs transition-colors ${
                darkMode 
                  ? 'border-gray-600 text-gray-300 hover:bg-gray-700' 
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              } border`}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Messages Area - Full width and optimized for space */}
        <div 
          className={`flex-1 overflow-y-auto px-6 py-3 ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}
        >
          <div className="w-full space-y-3">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`w-full ${
                    message.type === 'user' 
                      ? 'bg-blue-500 text-white max-w-2xl ml-auto' 
                      : darkMode 
                        ? 'bg-gray-800 text-gray-100 max-w-5xl' 
                        : 'bg-white text-gray-900 max-w-5xl'
                  } rounded-lg p-3 shadow-sm`}>
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    
                    {/* Show suggestions if available */}
                    {message.suggestions && message.suggestions.length > 0 && (
                      <div className="mt-4 space-y-3">
                        {message.suggestions.map((suggestion, idx) => {
                          const isProcessing = processingActions.has(`${suggestion.suggestion_id}-approve`) || 
                                             processingActions.has(`${suggestion.suggestion_id}-reject`) ||
                                             processingActions.has(`${suggestion.suggestion_id}-refine`);
                          
                          return (
                            <div key={idx} className="border-t border-gray-400 pt-3">
                              <ConversationalSuggestionCard
                                suggestion={{
                                  id: idx + 1,
                                  description_only: suggestion.description,
                                  title: `${suggestion.trigger_summary} → ${suggestion.action_summary}`,
                                  category: 'automation',
                                  confidence: suggestion.confidence,
                                  status: suggestion.status as 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected',
                                  refinement_count: 0,
                                  conversation_history: [],
                                  automation_yaml: null,
                                  created_at: suggestion.created_at
                                }}
                                onRefine={async (_id: number, refinement: string) => handleSuggestionAction(suggestion.suggestion_id, 'refine', refinement)}
                                onApprove={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'approve')}
                                onReject={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'reject')}
                                onTest={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'test')}
                                darkMode={darkMode}
                                disabled={isProcessing}
                              />
                            </div>
                          );
                        })}
                      </div>
                    )}
                    
                    {/* Show follow-up prompts if available */}
                    {message.followUpPrompts && message.followUpPrompts.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-400">
                        <p className={`text-xs mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          💡 Try asking:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {message.followUpPrompts.map((prompt, idx) => (
                            <button
                              key={idx}
                              onClick={() => {
                                setInputValue(prompt);
                                inputRef.current?.focus();
                              }}
                              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                                darkMode
                                  ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                              }`}
                            >
                              {prompt}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className={`text-xs mt-2 opacity-60 ${
                      message.type === 'user' ? 'text-blue-100' : ''
                    }`}>
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing indicator */}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className={`px-4 py-3 rounded-lg max-w-5xl ${
                  darkMode ? 'bg-gray-800' : 'bg-white'
                }`}>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Context Indicator - Shows active conversation context */}
        <ContextIndicator context={conversationContext} darkMode={darkMode} />

        {/* Input Area - Full width and compact at bottom */}
        <div className={`border-t px-6 py-2 flex-shrink-0 ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
          <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="flex space-x-3 max-w-6xl mx-auto">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask me about your devices or automations..."
              disabled={isLoading}
              className={`flex-1 px-3 py-2 rounded-lg border transition-colors text-sm ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:border-blue-500'
                  : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500 focus:border-blue-500'
              } focus:outline-none focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50`}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className={`px-4 py-2 rounded-lg font-medium transition-colors text-sm ${
                isLoading || !inputValue.trim()
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};