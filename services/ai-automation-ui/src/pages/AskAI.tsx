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
import { ClearChatModal } from '../components/ask-ai/ClearChatModal';
import { ReverseEngineeringLoader } from '../components/ask-ai/ReverseEngineeringLoader';
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
  const [reverseEngineeringStatus, setReverseEngineeringStatus] = useState<{
    visible: boolean;
    iteration?: number;
    similarity?: number;
    action?: 'test' | 'approve';
  }>({ visible: false });
  const [testedSuggestions, setTestedSuggestions] = useState<Set<string>>(new Set());
  const [showClearModal, setShowClearModal] = useState(false);
  
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

  // Keyboard shortcut for clearing chat (Ctrl+K / Cmd+K)
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Only open modal if there are messages to clear (excluding welcome message)
        if (messages.length > 1) {
          setShowClearModal(true);
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [messages.length]);
  
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
        
        // Mark as tested immediately (prevent double-click)
        setTestedSuggestions(prev => new Set(prev).add(suggestionId));
        
        // Show engaging reverse engineering loader IMMEDIATELY
        setReverseEngineeringStatus({ visible: true, action: 'test' });
        console.log('🎨 Loader set to visible for test action');
        
        // Minimum display time to ensure user sees it (2 seconds)
        const loaderStartTime = Date.now();
        const minDisplayTime = 2000;
        
        // Show loading toast as backup
        const loadingToast = toast.loading('⏳ Creating automation (will be disabled)...');
        
        try {
          // Call approve endpoint (same as Approve & Create - no simplification)
          const response = await api.approveAskAISuggestion(queryId, suggestionId);
          console.log('✅ API response received', { 
            hasReverseEng: !!response.reverse_engineering,
            enabled: response.reverse_engineering?.enabled 
          });
          
          // Update loader with progress if available
          if (response.reverse_engineering?.enabled && response.reverse_engineering?.iteration_history) {
            const lastIteration = response.reverse_engineering.iteration_history[
              response.reverse_engineering.iteration_history.length - 1
            ];
            if (lastIteration) {
              setReverseEngineeringStatus({
                visible: true,
                iteration: response.reverse_engineering.iterations_completed,
                similarity: response.reverse_engineering.final_similarity,
                action: 'test'
              });
              console.log('📊 Updated loader with progress', {
                iteration: response.reverse_engineering.iterations_completed,
                similarity: response.reverse_engineering.final_similarity
              });
            }
          }
          
          // Ensure minimum display time
          const elapsed = Date.now() - loaderStartTime;
          const remainingTime = Math.max(0, minDisplayTime - elapsed);
          await new Promise(resolve => setTimeout(resolve, remainingTime));
          
          // Hide loader after minimum display time
          setReverseEngineeringStatus({ visible: false });
          console.log('👋 Loader hidden');
          
          // Check if automation creation was blocked by safety validation
          if (response.status === 'blocked' || response.safe === false) {
            toast.dismiss(loadingToast);
            const warnings = response.warnings || [];
            const errorMessage = response.message || 'Test automation creation blocked due to safety concerns';
            
            toast.error(`❌ ${errorMessage}`);
            
            // Show individual warnings
            warnings.forEach((warning: string) => {
              toast(warning, { icon: '⚠️', duration: 6000 });
            });
            
            // Re-enable button so user can try again after fixing the issue
            setTestedSuggestions(prev => {
              const newSet = new Set(prev);
              newSet.delete(suggestionId);
              return newSet;
            });
            return;
          }
          
          if (response.automation_id && response.status === 'approved') {
            // Immediately disable the automation
            try {
              await api.disableAutomation(response.automation_id);
              toast.dismiss(loadingToast);
              
              // Show success with reverse engineering stats if available
              if (response.reverse_engineering?.enabled) {
                const simPercent = Math.round(response.reverse_engineering.final_similarity * 100);
                toast.success(
                  `✅ Test automation created and disabled!\n\nAutomation ID: ${response.automation_id}\n✨ Quality match: ${simPercent}%`,
                  { duration: 8000 }
                );
              } else {
                toast.success(
                  `✅ Test automation created and disabled!\n\nAutomation ID: ${response.automation_id}`,
                  { duration: 8000 }
                );
              }
              
              toast(
                `💡 The automation "${response.automation_id}" is disabled. You can enable it manually or approve this suggestion.`,
                { icon: 'ℹ️', duration: 6000 }
              );
              
              // Show warnings if any (non-critical)
              if (response.warnings && response.warnings.length > 0) {
                response.warnings.forEach((warning: string) => {
                  toast(warning, { icon: '⚠️', duration: 5000 });
                });
              }
            } catch (disableError: any) {
              toast.dismiss(loadingToast);
              const errorMessage = disableError?.message || disableError?.toString() || 'Unknown error';
              toast.error(
                `⚠️ Automation created but failed to disable: ${response.automation_id}\n\n${errorMessage}`,
                { duration: 8000 }
              );
              // Re-enable button on disable failure
              setTestedSuggestions(prev => {
                const newSet = new Set(prev);
                newSet.delete(suggestionId);
                return newSet;
              });
            }
          } else {
            toast.dismiss(loadingToast);
            toast.error(`❌ Failed to create test automation: ${response.message || 'Unknown error'}`);
            // Re-enable button on error
            setTestedSuggestions(prev => {
              const newSet = new Set(prev);
              newSet.delete(suggestionId);
              return newSet;
            });
          }
        } catch (error: any) {
          console.error('❌ Test action failed:', error);
          setReverseEngineeringStatus({ visible: false });
          toast.dismiss(loadingToast);
          const errorMessage = error?.message || error?.toString() || 'Unknown error';
          toast.error(`❌ Failed to create test automation: ${errorMessage}`);
          // Re-enable button on error
          setTestedSuggestions(prev => {
            const newSet = new Set(prev);
            newSet.delete(suggestionId);
            return newSet;
          });
          throw error;
        }
      } else if (action === 'refine' && refinement) {
        const messageWithQuery = messages.find(msg => 
          msg.suggestions?.some(s => s.suggestion_id === suggestionId)
        );
        const queryId = messageWithQuery?.id || 'unknown';
        
        if (!refinement.trim()) {
          toast.error('Please enter your refinement');
          return;
        }
        
        try {
          const response = await api.refineAskAIQuery(queryId, refinement);
          
          // Update the specific suggestion in the message
          setMessages(prev => prev.map(msg => {
            if (msg.id === queryId && msg.suggestions) {
              return {
                ...msg,
                suggestions: msg.suggestions.map(s => {
                  if (s.suggestion_id === suggestionId) {
                    // Update the suggestion with refined data
                    const refinedSuggestion = response.refined_suggestions?.find(
                      (rs: any) => rs.suggestion_id === suggestionId || 
                      (msg.suggestions && response.refined_suggestions?.indexOf(rs) === msg.suggestions.indexOf(s))
                    );
                    
                    if (refinedSuggestion) {
                      // Add to conversation history
                      const newHistoryEntry = {
                        timestamp: new Date().toISOString(),
                        user_input: refinement,
                        updated_description: refinedSuggestion.description || s.description,
                        changes: response.changes_made || [`Applied: ${refinement}`],
                        validation: { ok: true }
                      };
                      
                      return {
                        ...s,
                        description: refinedSuggestion.description || s.description,
                        trigger_summary: refinedSuggestion.trigger_summary || s.trigger_summary,
                        action_summary: refinedSuggestion.action_summary || s.action_summary,
                        confidence: refinedSuggestion.confidence || s.confidence,
                        status: 'refining' as const,
                        refinement_count: (s.refinement_count || 0) + 1,
                        conversation_history: [...(s.conversation_history || []), newHistoryEntry]
                      };
                    }
                    
                    // If no specific refined suggestion found, update description with refinement context
                    const newHistoryEntry = {
                      timestamp: new Date().toISOString(),
                      user_input: refinement,
                      updated_description: s.description,
                      changes: [`Applied: ${refinement}`],
                      validation: { ok: true }
                    };
                    
                    return {
                      ...s,
                      description: s.description,
                      status: 'refining' as const,
                      refinement_count: (s.refinement_count || 0) + 1,
                      conversation_history: [...(s.conversation_history || []), newHistoryEntry]
                    };
                  }
                  return s;
                })
              };
            }
            return msg;
          }));
          
          toast.success('✅ Suggestion refined successfully!');
        } catch (error: any) {
          console.error('Refinement failed:', error);
          const errorMessage = error?.message || error?.toString() || 'Unknown error';
          toast.error(`Failed to refine suggestion: ${errorMessage}`);
          throw error;
        }
      } else if (action === 'approve') {
        const messageWithQuery = messages.find(msg => 
          msg.suggestions?.some(s => s.suggestion_id === suggestionId)
        );
        const queryId = messageWithQuery?.id || 'unknown';
        
        // Show engaging reverse engineering loader IMMEDIATELY
        setReverseEngineeringStatus({ visible: true, action: 'approve' });
        console.log('🎨 Loader set to visible for approve action');
        
        // Minimum display time to ensure user sees it (2 seconds)
        const loaderStartTime = Date.now();
        const minDisplayTime = 2000;
        
        try {
          const response = await api.approveAskAISuggestion(queryId, suggestionId);
          
          // Debug logging to understand response structure
          console.log('🔍 APPROVE RESPONSE:', {
            status: response?.status,
            safe: response?.safe,
            automation_id: response?.automation_id,
            has_warnings: !!response?.warnings,
            message: response?.message,
            hasReverseEng: !!response.reverse_engineering,
            enabled: response.reverse_engineering?.enabled
          });
          
          // Update loader with progress if available
          if (response.reverse_engineering?.enabled && response.reverse_engineering?.iteration_history) {
            const lastIteration = response.reverse_engineering.iteration_history[
              response.reverse_engineering.iteration_history.length - 1
            ];
            if (lastIteration) {
              setReverseEngineeringStatus({
                visible: true,
                iteration: response.reverse_engineering.iterations_completed,
                similarity: response.reverse_engineering.final_similarity,
                action: 'approve'
              });
              console.log('📊 Updated loader with progress', {
                iteration: response.reverse_engineering.iterations_completed,
                similarity: response.reverse_engineering.final_similarity
              });
            }
          }
          
          // Ensure minimum display time
          const elapsed = Date.now() - loaderStartTime;
          const remainingTime = Math.max(0, minDisplayTime - elapsed);
          await new Promise(resolve => setTimeout(resolve, remainingTime));
          
          // Hide loader after minimum display time
          setReverseEngineeringStatus({ visible: false });
          console.log('👋 Loader hidden');
          
          // PRIORITY 1: Check if automation creation failed (error, blocked, or unsafe)
          // This MUST be checked FIRST and return early to prevent success toast
          if (response && (
            response.status === 'error' || 
            response.status === 'blocked' || 
            response.safe === false ||
            (response.error_details && response.error_details.type)
          )) {
            console.log('🔍 Response indicates FAILURE - showing error only', {
              status: response.status,
              safe: response.safe,
              error_details: response.error_details
            });
            
            const warnings = Array.isArray(response.warnings) ? response.warnings : [];
            let errorMessage = response.message || 'Failed to create automation';
            
            // Enhance error message with details if available
            if (response.error_details) {
              if (response.error_details.message) {
                errorMessage = response.error_details.message;
              }
              if (response.error_details.suggestion) {
                errorMessage += `\n\n💡 ${response.error_details.suggestion}`;
              }
            }
            
            toast.error(`❌ ${errorMessage}`, { duration: 10000 });
            
            // Show individual warnings (filter out null/undefined values)
            warnings.filter((w: any) => w != null).forEach((warning: string) => {
              toast(typeof warning === 'string' ? warning : String(warning), { icon: '⚠️', duration: 6000 });
            });
            
            // CRITICAL: Return early to prevent any success path execution
            setReverseEngineeringStatus({ visible: false });
            return;
          }
          
          // PRIORITY 2: Success - automation was created
          // Must check BOTH status === 'approved' AND automation_id exists
          if (response && response.status === 'approved' && response.automation_id) {
            console.log('🔍 Response is APPROVED - showing success');
            
            // Show success with reverse engineering stats if available
            if (response.reverse_engineering?.enabled) {
              const simPercent = Math.round(response.reverse_engineering.final_similarity * 100);
              toast.success(
                `✅ Automation created successfully!\n\nAutomation ID: ${response.automation_id}\n✨ Quality match: ${simPercent}%`,
                { duration: 8000 }
              );
            } else {
              toast.success(`✅ Automation created successfully!\n\nAutomation ID: ${response.automation_id}`);
            }
            
            // Show warnings if any (non-critical)
            if (Array.isArray(response.warnings) && response.warnings.length > 0) {
              response.warnings.filter((w: any) => w != null).forEach((warning: string) => {
                toast(typeof warning === 'string' ? warning : String(warning), { icon: '⚠️', duration: 5000 });
              });
            }
            
            // Remove the suggestion from the UI
            setMessages(prev => prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.filter(s => s.suggestion_id !== suggestionId) || []
            })));
          } else {
            // PRIORITY 3: Unexpected response - show error with details
            console.error('🔍 Unexpected approve response:', response);
            const errorMsg = response?.message || 'Unexpected response from server';
            toast.error(`❌ Failed to create automation: ${errorMsg}`);
            
            // Show warnings if any
            if (response && Array.isArray(response.warnings) && response.warnings.length > 0) {
              response.warnings.filter((w: any) => w != null).forEach((warning: string) => {
                toast(typeof warning === 'string' ? warning : String(warning), { icon: '⚠️', duration: 6000 });
              });
            }
          }
        } catch (error: any) {
          console.error('❌ Approve action failed:', error);
          setReverseEngineeringStatus({ visible: false });
          const errorMessage = error?.message || error?.toString() || 'Unknown error occurred';
          toast.error(`❌ Failed to approve automation: ${errorMessage}`);
          
          // Re-throw to be caught by outer try-catch
          throw error;
        }
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
    // Store message count for toast
    const messageCount = messages.length - 1; // Exclude welcome message
    
    // Clear localStorage
    localStorage.removeItem('ask-ai-conversation');
    
    // Reset all state
    setMessages([welcomeMessage]);
    setInputValue('');
    setIsLoading(false);
    setIsTyping(false);
    setProcessingActions(new Set());
    setTestedSuggestions(new Set());
    setConversationContext({
      mentioned_devices: [],
      mentioned_intents: [],
      active_suggestions: [],
      last_query: '',
      last_entities: []
    });
    
    // Clear input field
    if (inputRef.current) {
      inputRef.current.value = '';
      // Focus input after a brief delay to ensure state updates
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
    
    // Scroll to top smoothly
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Close modal and show toast
    setShowClearModal(false);
    toast.success(
      messageCount > 0 
        ? `Chat cleared! (${messageCount} message${messageCount !== 1 ? 's' : ''} removed)`
        : 'Chat cleared - ready for a new conversation'
    );
  };

  const handleExampleClick = (example: string) => {
    setInputValue(example);
    inputRef.current?.focus();
  };

  const handleExportAndClear = () => {
    exportConversation();
    // Small delay to ensure export completes before clearing
    setTimeout(() => {
      clearChat();
    }, 500);
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
              onClick={() => {
                // Only show modal if there are messages to clear (excluding welcome message)
                if (messages.length > 1) {
                  setShowClearModal(true);
                }
              }}
              disabled={messages.length <= 1}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                messages.length <= 1
                  ? darkMode
                    ? 'border-gray-700 text-gray-500 cursor-not-allowed border opacity-50'
                    : 'border-gray-200 text-gray-400 cursor-not-allowed border opacity-50'
                  : darkMode
                    ? 'border-gray-600 text-gray-300 hover:bg-gray-700 border'
                    : 'border-gray-300 text-gray-600 hover:bg-gray-50 border'
              }`}
              title="Clear conversation and start new (Ctrl+K / Cmd+K)"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Chat
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
                          
                          // Find if this suggestion has been refined (has a status of 'refining')
                          const suggestionStatus = suggestion.status || 'draft';
                          const refinementCount = suggestion.refinement_count || 0;
                          const conversationHistory = suggestion.conversation_history || [];
                          
                          return (
                            <div key={idx} className="border-t border-gray-400 pt-3">
                              <ConversationalSuggestionCard
                                suggestion={{
                                  id: parseInt(suggestion.suggestion_id.replace(/\D/g, '')) || idx + 1, // Extract numeric part or use index
                                  description_only: suggestion.description,
                                  title: `${suggestion.trigger_summary} → ${suggestion.action_summary}`,
                                  category: suggestion.category || 'automation',
                                  confidence: suggestion.confidence,
                                  status: suggestionStatus as 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected',
                                  refinement_count: refinementCount,
                                  conversation_history: conversationHistory,
                                  device_capabilities: suggestion.device_capabilities || {},
                                  automation_yaml: suggestion.automation_yaml || null,
                                  created_at: suggestion.created_at
                                }}
                                onRefine={async (_id: number, refinement: string) => {
                                  try {
                                    await handleSuggestionAction(suggestion.suggestion_id, 'refine', refinement);
                                  } catch (error) {
                                    // Error is already handled in handleSuggestionAction
                                    throw error;
                                  }
                                }}
                                onApprove={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'approve')}
                                onReject={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'reject')}
                                onTest={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'test')}
                                darkMode={darkMode}
                                disabled={isProcessing}
                                tested={testedSuggestions.has(suggestion.suggestion_id)}
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

      {/* Clear Chat Modal */}
      <ClearChatModal
        isOpen={showClearModal}
        onClose={() => setShowClearModal(false)}
        onConfirm={clearChat}
        onExportAndClear={handleExportAndClear}
        messageCount={messages.length - 1} // Exclude welcome message
        darkMode={darkMode}
      />

      {/* Reverse Engineering Loader */}
      <ReverseEngineeringLoader
        isVisible={reverseEngineeringStatus.visible}
        iteration={reverseEngineeringStatus.iteration}
        similarity={reverseEngineeringStatus.similarity}
      />
    </div>
  );
};