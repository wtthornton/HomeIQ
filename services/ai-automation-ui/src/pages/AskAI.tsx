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
import { ProcessLoader } from '../components/ask-ai/ReverseEngineeringLoader';
import { DebugPanel } from '../components/ask-ai/DebugPanel';
import { ClarificationDialog } from '../components/ask-ai/ClarificationDialog';
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
  clarificationNeeded?: boolean;
  clarificationSessionId?: string;
  questions?: any[];
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
  clarification_needed?: boolean;
  clarification_session_id?: string;
  questions?: any[];
  message?: string;
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
  const [clarificationDialog, setClarificationDialog] = useState<{
    questions: any[];
    sessionId: string;
    confidence: number;
    threshold: number;
  } | null>(null);
  
  // Device selection state: Map of suggestionId -> Map of entityId -> selected boolean
  const [deviceSelections, setDeviceSelections] = useState<Map<string, Map<string, boolean>>>(new Map());
  
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
        followUpPrompts: followUpPrompts,
        clarificationNeeded: response.clarification_needed,
        clarificationSessionId: response.clarification_session_id,
        questions: response.questions
      };

      setMessages(prev => [...prev, aiMessage]);
      
      // Show clarification dialog if needed
      if (response.clarification_needed && response.questions && response.questions.length > 0) {
        setClarificationDialog({
          questions: response.questions,
          sessionId: response.clarification_session_id || '',
          confidence: response.confidence,
          threshold: 0.85  // Default threshold
        });
      }
      
      // Update context with the AI response
      updateContextFromMessage(aiMessage);
      
      if (response.suggestions.length === 0) {
        toast.error('No suggestions found. Try rephrasing your question.');
      } else {
        toast.success(`Found ${response.suggestions.length} automation suggestion${response.suggestions.length > 1 ? 's' : ''}`);
      }
    } catch (error: any) {
      console.error('Failed to send message:', error);
      console.error('Error details:', {
        message: error?.message,
        status: error?.status,
        stack: error?.stack,
        response: error?.response
      });
      
      // Show more detailed error message to user
      let errorMessageText = "Sorry, I encountered an error processing your request. Please try again.";
      if (error?.message) {
        errorMessageText += ` (Error: ${error.message})`;
      } else if (error?.status) {
        errorMessageText += ` (Status: ${error.status})`;
      }
      
      toast.error(errorMessageText);
      
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'ai',
        content: errorMessageText,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const generateAIResponse = (query: AskAIQuery): string => {
    const { suggestions, extracted_entities, confidence, message } = query;

    // Use message from API if provided (for clarification cases)
    if (message) {
      return message;
    }

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

  // Handle device selection toggle
  const handleDeviceToggle = (suggestionId: number, entityId: string, selected: boolean) => {
    setDeviceSelections(prev => {
      const newSelections = new Map(prev);
      const suggestionIdStr = suggestionId.toString();
      
      if (!newSelections.has(suggestionIdStr)) {
        newSelections.set(suggestionIdStr, new Map());
      }
      
      const selectionMap = newSelections.get(suggestionIdStr)!;
      selectionMap.set(entityId, selected);
      newSelections.set(suggestionIdStr, selectionMap);
      
      return newSelections;
    });
  };

  // Get selected entity IDs for a suggestion
  const getSelectedEntityIds = (suggestionId: string, deviceInfo?: Array<{ entity_id: string; selected?: boolean }>): string[] => {
    const suggestionIdStr = suggestionId;
    
    // If deviceInfo is provided, use it to filter selected devices
    if (deviceInfo) {
      return deviceInfo
        .filter(device => device.selected !== false) // Default to true if not specified
        .map(device => device.entity_id);
    }
    
    // Otherwise, check deviceSelections state
    if (deviceSelections.has(suggestionIdStr)) {
      const selectionMap = deviceSelections.get(suggestionIdStr)!;
      const selected: string[] = [];
      selectionMap.forEach((isSelected, entityId) => {
        if (isSelected) {
          selected.push(entityId);
        }
      });
      return selected;
    }
    
    return []; // Return empty array if no selections made
  };

  const handleSuggestionAction = async (suggestionId: string, action: 'refine' | 'approve' | 'reject' | 'test', refinement?: string, customMappings?: Record<string, string>) => {
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
          // Get selected entity IDs for this suggestion
          const messageWithSuggestion = messages.find(msg => 
            msg.suggestions?.some(s => s.suggestion_id === suggestionId)
          );
          const suggestion = messageWithSuggestion?.suggestions?.find(s => s.suggestion_id === suggestionId);
          // Extract device info inline (helper function defined below in render)
          const deviceInfo = suggestion ? (() => {
            const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
            const seenEntityIds = new Set<string>();
            const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
              if (entityId && !seenEntityIds.has(entityId)) {
                let isSelected = true;
                if (deviceSelections.has(suggestionId)) {
                  const selectionMap = deviceSelections.get(suggestionId)!;
                  if (selectionMap.has(entityId)) {
                    isSelected = selectionMap.get(entityId)!;
                  }
                }
                devices.push({ friendly_name: friendlyName, entity_id: entityId, domain: domain || entityId.split('.')[0], selected: isSelected });
                seenEntityIds.add(entityId);
              }
            };
            if (suggestion.validated_entities) {
              Object.entries(suggestion.validated_entities).forEach(([fn, eid]: [string, any]) => {
                if (eid && typeof eid === 'string') addDevice(fn, eid);
              });
            }
            return devices;
          })() : undefined;
          const selectedEntityIds = getSelectedEntityIds(suggestionId, deviceInfo);
          
          // Call approve endpoint (same as Approve & Create - no simplification)
          const response = await api.approveAskAISuggestion(queryId, suggestionId, selectedEntityIds.length > 0 ? selectedEntityIds : undefined);
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
          // Get selected entity IDs for this suggestion
          const messageWithSuggestion = messages.find(msg => 
            msg.suggestions?.some(s => s.suggestion_id === suggestionId)
          );
          const suggestion = messageWithSuggestion?.suggestions?.find(s => s.suggestion_id === suggestionId);
          // Extract device info inline (since it's used in render too)
          const deviceInfo = suggestion ? (() => {
            const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
            const seenEntityIds = new Set<string>();
            const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
              if (entityId && !seenEntityIds.has(entityId)) {
                let isSelected = true;
                if (deviceSelections.has(suggestionId)) {
                  const selectionMap = deviceSelections.get(suggestionId)!;
                  if (selectionMap.has(entityId)) {
                    isSelected = selectionMap.get(entityId)!;
                  }
                }
                devices.push({ friendly_name: friendlyName, entity_id: entityId, domain: domain || entityId.split('.')[0], selected: isSelected });
                seenEntityIds.add(entityId);
              }
            };
            if (suggestion.validated_entities) {
              Object.entries(suggestion.validated_entities).forEach(([fn, eid]: [string, any]) => {
                if (eid && typeof eid === 'string') addDevice(fn, eid);
              });
            }
            return devices;
          })() : undefined;
          const selectedEntityIds = getSelectedEntityIds(suggestionId, deviceInfo);
          
          const response = await api.approveAskAISuggestion(
            queryId, 
            suggestionId, 
            selectedEntityIds.length > 0 ? selectedEntityIds : undefined,
            customMappings && Object.keys(customMappings).length > 0 ? customMappings : undefined
          );
          
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
    <div className="flex transition-colors ds-bg-gradient-primary" style={{ 
      height: 'calc(100vh - 40px)',
      position: 'fixed',
      top: '40px',
      left: '0',
      right: '0',
      bottom: '0',
      background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)'
    }}>
      {/* Sidebar with Examples */}
      <motion.div
        initial={false}
        animate={{ width: sidebarOpen ? '320px' : '0px' }}
        className="border-r overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
          borderColor: 'rgba(51, 65, 85, 0.5)',
          backdropFilter: 'blur(12px)'
        }}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="ds-title-card" style={{ fontSize: '1rem', color: '#ffffff' }}>
              QUICK EXAMPLES
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
                className="w-full text-left p-3 rounded-lg text-sm transition-colors"
                style={{
                  background: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  color: '#cbd5e1'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                  e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                  e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                }}
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
        <div className="flex items-center justify-between px-6 py-1 border-b flex-shrink-0" style={{
          borderColor: 'rgba(51, 65, 85, 0.5)',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
          backdropFilter: 'blur(12px)'
        }}>
          <div className="flex items-center space-x-3">
            <h1 className="ds-title-section" style={{ fontSize: '1.125rem', color: '#ffffff' }}>
              ASK AI
            </h1>
            <span className="ds-text-label" style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              Home Assistant Automation Assistant
            </span>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded transition-colors"
              style={{ color: '#cbd5e1' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
              title="Toggle Examples"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={exportConversation}
              className="p-1.5 rounded transition-colors"
              style={{ color: '#cbd5e1' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
              title="Export Conversation"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <label
              className="p-1.5 rounded cursor-pointer transition-colors"
              style={{ color: '#cbd5e1' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
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
              className="px-2.5 py-0.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 border uppercase"
              style={messages.length <= 1 ? {
                borderColor: 'rgba(51, 65, 85, 0.3)',
                color: '#64748b',
                opacity: 0.5,
                cursor: 'not-allowed'
              } : {
                borderColor: 'rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1',
                background: 'rgba(30, 41, 59, 0.6)'
              }}
              onMouseEnter={(e) => {
                if (messages.length > 1) {
                  e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                  e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                }
              }}
              onMouseLeave={(e) => {
                if (messages.length > 1) {
                  e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                  e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                }
              }}
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
          className="flex-1 overflow-y-auto px-6 py-3"
          style={{
            background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)'
          }}
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
                  <div className={`w-full rounded-lg p-3 shadow-sm ${
                    message.type === 'user' 
                      ? 'max-w-2xl ml-auto' 
                      : 'ds-card max-w-5xl'
                  }`} style={message.type === 'user' ? {
                    background: 'linear-gradient(to right, #3b82f6, #2563eb)',
                    color: '#ffffff',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 0 20px rgba(59, 130, 246, 0.2)'
                  } : {
                    background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    color: '#cbd5e1',
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(59, 130, 246, 0.2)'
                  }}>
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
                          
                          // Extract device information from suggestion
                          const extractDeviceInfo = (suggestion: any, extractedEntities?: any[], suggestionId?: string): Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> => {
                            const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
                            const seenEntityIds = new Set<string>();
                            
                                                          // Helper to add device safely
                              const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
                                // Filter out generic/redundant device names (same as backend)
                                const friendlyNameLower = friendlyName.toLowerCase().trim();
                                const genericTerms = ['light', 'lights', 'device', 'devices', 'sensor', 'sensors', 'switch', 'switches'];
                                if (genericTerms.includes(friendlyNameLower)) {
                                  return; // Skip generic terms
                                }
                                
                                // Skip if entity ID is just a domain (e.g., "light.light")
                                if (entityId && entityId.split('.').length === 2 && 
                                    entityId.split('.')[1].toLowerCase() === entityId.split('.')[0].toLowerCase()) {
                                  return; // Skip generic entity IDs like "light.light"
                                }
                                
                                if (entityId && !seenEntityIds.has(entityId)) {
                                  // Check if device selection exists for this suggestion
                                  let isSelected = true; // Default to selected
                                  if (suggestionId && deviceSelections.has(suggestionId)) {
                                    const selectionMap = deviceSelections.get(suggestionId)!;
                                    if (selectionMap.has(entityId)) {
                                      isSelected = selectionMap.get(entityId)!;
                                    }
                                  }
                                  
                                  devices.push({
                                    friendly_name: friendlyName,
                                    entity_id: entityId,
                                    domain: domain || entityId.split('.')[0],
                                    selected: isSelected
                                  });
                                  seenEntityIds.add(entityId);
                                }
                              };
                            
                            // 1. Try validated_entities (most reliable - direct mapping from API)
                            if (suggestion.validated_entities && typeof suggestion.validated_entities === 'object') {
                              Object.entries(suggestion.validated_entities).forEach(([friendlyName, entityId]: [string, any]) => {
                                if (entityId && typeof entityId === 'string') {
                                  addDevice(friendlyName, entityId);
                                }
                              });
                            }
                            
                            // 2. Try entity_id_annotations (enhanced suggestion format)
                            if (suggestion.entity_id_annotations && typeof suggestion.entity_id_annotations === 'object') {
                              Object.entries(suggestion.entity_id_annotations).forEach(([friendlyName, annotation]: [string, any]) => {
                                if (annotation?.entity_id) {
                                  addDevice(friendlyName, annotation.entity_id, annotation.domain);
                                }
                              });
                            }
                            
                            // 3. Try device_mentions
                            if (suggestion.device_mentions && typeof suggestion.device_mentions === 'object') {
                              Object.entries(suggestion.device_mentions).forEach(([mention, entityId]: [string, any]) => {
                                if (entityId && typeof entityId === 'string') {
                                  addDevice(mention, entityId);
                                }
                              });
                            }
                            
                            // 4. Try entity_ids_used array
                            if (suggestion.entity_ids_used && Array.isArray(suggestion.entity_ids_used)) {
                              suggestion.entity_ids_used.forEach((entityId: string) => {
                                if (entityId && typeof entityId === 'string') {
                                  // Extract friendly name from entity_id
                                  const parts = entityId.split('.');
                                  const friendlyName = parts.length > 1 
                                    ? parts[1].split('_').map((word: string) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                                    : entityId;
                                  addDevice(friendlyName, entityId);
                                }
                              });
                            }
                            
                                                          // 5. Try devices_involved array (may have device names without entity IDs)
                              // ONLY if not already processed via validated_entities (prevent duplicates)
                              if (suggestion.devices_involved && Array.isArray(suggestion.devices_involved)) {
                                // Track friendly names already processed to avoid duplicates
                                const seenFriendlyNames = new Set(
                                  devices.map(d => d.friendly_name.toLowerCase())
                                );
                                
                                suggestion.devices_involved.forEach((deviceName: string) => {
                                  if (typeof deviceName === 'string' && deviceName.trim()) {
                                    // Skip if this friendly name was already added from validated_entities
                                    const deviceNameLower = deviceName.toLowerCase().trim();
                                    if (seenFriendlyNames.has(deviceNameLower)) {
                                      return; // Skip - already added from validated_entities
                                    }
                                    
                                    // Check if this device name exists in validated_entities
                                    if (suggestion.validated_entities && 
                                        typeof suggestion.validated_entities === 'object' &&
                                        suggestion.validated_entities[deviceName]) {
                                      // Use the actual entity ID from validated_entities
                                      const actualEntityId = suggestion.validated_entities[deviceName];
                                      if (actualEntityId && typeof actualEntityId === 'string') {
                                        addDevice(deviceName, actualEntityId);
                                        seenFriendlyNames.add(deviceNameLower);
                                        return;
                                      }
                                    }
                                    
                                    // Only infer if not in validated_entities (fallback)
                                    const normalizedName = deviceName.toLowerCase().replace(/\s+/g, '_');
                                    const inferredEntityId = `light.${normalizedName}`; // Default to light domain
                                    addDevice(deviceName, inferredEntityId, 'light');
                                    seenFriendlyNames.add(deviceNameLower);
                                  }
                                });
                              }
                            
                            // 6. Try extracted_entities from message
                            if (extractedEntities && Array.isArray(extractedEntities)) {
                              extractedEntities.forEach((entity: any) => {
                                const entityId = entity.entity_id || entity.id;
                                if (entityId) {
                                  const friendlyName = entity.name || entity.friendly_name || 
                                    (entityId.includes('.') ? entityId.split('.')[1]?.split('_').map((word: string) => 
                                      word.charAt(0).toUpperCase() + word.slice(1)).join(' ') : entityId);
                                  addDevice(friendlyName, entityId, entity.domain);
                                }
                              });
                            }
                            
                            // 7. Last resort: parse device names from description/action text
                            if (devices.length === 0) {
                              const text = `${suggestion.description || ''} ${suggestion.action_summary || ''} ${suggestion.trigger_summary || ''}`.toLowerCase();
                              
                              const devicePatterns = [
                                { pattern: /\bwled\b.*?\bled\b.*?\bstrip\b/gi, defaultName: 'WLED LED Strip', defaultDomain: 'light' },
                                { pattern: /\bceiling\b.*?\blights?\b/gi, defaultName: 'Ceiling Lights', defaultDomain: 'light' },
                                { pattern: /\boffice\b.*?\blights?\b/gi, defaultName: 'Office Lights', defaultDomain: 'light' },
                                { pattern: /\bliving\b.*?\broom\b.*?\blights?\b/gi, defaultName: 'Living Room Lights', defaultDomain: 'light' },
                                { pattern: /\bbedroom\b.*?\blights?\b/gi, defaultName: 'Bedroom Lights', defaultDomain: 'light' },
                                { pattern: /\bkitchen\b.*?\blights?\b/gi, defaultName: 'Kitchen Lights', defaultDomain: 'light' },
                              ];
                              
                              devicePatterns.forEach(({ pattern, defaultName, defaultDomain }) => {
                                if (pattern.test(text)) {
                                  const deviceId = `${defaultDomain}.${defaultName.toLowerCase().replace(/\s+/g, '_').replace(/s$/, '')}`;
                                  addDevice(defaultName, deviceId, defaultDomain);
                                }
                              });
                            }
                            
                            return devices;
                          };
                          
                          const deviceInfo = extractDeviceInfo(suggestion, message.entities, suggestion.suggestion_id);
                          
                          // Debug logging
                          if (deviceInfo.length > 0) {
                            console.log('✅ Extracted device info:', deviceInfo);
                          } else {
                            console.log('⚠️ No devices extracted from suggestion:', {
                              hasEntityAnnotations: !!suggestion.entity_id_annotations,
                              hasDeviceMentions: !!suggestion.device_mentions,
                              hasEntityIdsUsed: !!suggestion.entity_ids_used,
                              hasMessageEntities: !!message.entities,
                              description: suggestion.description?.substring(0, 100),
                              actionSummary: suggestion.action_summary?.substring(0, 100)
                            });
                          }
                          
                          return (
                            <div key={idx} className="pt-3" style={{ borderTop: '1px solid rgba(51, 65, 85, 0.5)' }}>
                              <ConversationalSuggestionCard
                                key={suggestion.suggestion_id}
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
                                  device_info: deviceInfo.length > 0 ? deviceInfo : undefined,
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
                                onApprove={async (_id: number, customMappings?: Record<string, string>) => handleSuggestionAction(suggestion.suggestion_id, 'approve', undefined, customMappings)}
                                onReject={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'reject')}
                                onTest={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'test')}
                                onDeviceToggle={(id: number, entityId: string, selected: boolean) => {
                                  handleDeviceToggle(id, entityId, selected);
                                  // Force re-render to update device button states
                                  setMessages(prev => [...prev]);
                                }}
                                darkMode={darkMode}
                                disabled={isProcessing}
                                tested={testedSuggestions.has(suggestion.suggestion_id)}
                              />
                              {/* Debug Panel */}
                              <DebugPanel
                                debug={suggestion.debug}
                                technicalPrompt={suggestion.technical_prompt}
                                darkMode={darkMode}
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
                              className="text-xs px-3 py-1.5 rounded-lg transition-colors"
                              style={{
                                background: 'rgba(30, 41, 59, 0.6)',
                                border: '1px solid rgba(51, 65, 85, 0.5)',
                                color: '#cbd5e1'
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                                e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                              }}
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
                <div className="px-4 py-3 rounded-lg max-w-5xl" style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(59, 130, 246, 0.2)'
                }}>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#3b82f6' }}></div>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#3b82f6', animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#3b82f6', animationDelay: '0.2s' }}></div>
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
        <div className="border-t px-6 py-2 flex-shrink-0" style={{
          borderColor: 'rgba(51, 65, 85, 0.5)',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
          backdropFilter: 'blur(12px)'
        }}>
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
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors text-xs ${
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

      {/* Reverse engineering loader */}
      <ProcessLoader
        isVisible={reverseEngineeringStatus.visible}
        processType="reverse-engineering"
        iteration={reverseEngineeringStatus.iteration}
        similarity={reverseEngineeringStatus.similarity}
      />
      
      {/* Query processing loader */}
      <ProcessLoader
        isVisible={isLoading}
        processType="query-processing"
      />
      
      {/* Clarification Dialog */}
      {clarificationDialog && (
        <ClarificationDialog
          questions={clarificationDialog.questions}
          sessionId={clarificationDialog.sessionId}
          currentConfidence={clarificationDialog.confidence}
          confidenceThreshold={clarificationDialog.threshold}
          onAnswer={async (answers) => {
            try {
              const response = await api.clarifyAnswers(clarificationDialog.sessionId, answers);
              
              if (response.clarification_complete && response.suggestions) {
                // Add suggestions to conversation
                const suggestionMessage: ChatMessage = {
                  id: `clarify-${Date.now()}`,
                  type: 'ai',
                  content: response.message || 'Based on your answers, here are the automation suggestions:',
                  timestamp: new Date(),
                  suggestions: response.suggestions,
                  confidence: response.confidence
                };
                
                setMessages(prev => [...prev, suggestionMessage]);
                setClarificationDialog(null);
                toast.success('Clarification complete! Suggestions generated.');
              } else if (response.questions && response.questions.length > 0) {
                // More questions needed
                setClarificationDialog({
                  questions: response.questions,
                  sessionId: response.session_id,
                  confidence: response.confidence,
                  threshold: response.confidence_threshold
                });
                toast(response.message || 'Please answer the additional questions.', { icon: 'ℹ️' });
              }
            } catch (error: any) {
              toast.error(`Failed to submit clarification: ${error.message || 'Unknown error'}`);
            }
          }}
          onCancel={() => {
            setClarificationDialog(null);
            toast('Clarification cancelled', { icon: 'ℹ️' });
          }}
        />
      )}
    </div>
  );
};