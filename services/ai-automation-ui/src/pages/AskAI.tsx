/**
 * Ask AI Page - Natural Language Query Interface
 * 
 * Chat-based interface for asking questions about Home Assistant devices
 * and receiving automation suggestions. Optimized for full screen utilization.
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import confetti from 'canvas-confetti';
import { useAppStore } from '../store';
import { ConversationalSuggestionCard } from '../components/ConversationalSuggestionCard';
import { ContextIndicator } from '../components/ask-ai/ContextIndicator';
import { ClearChatModal } from '../components/ask-ai/ClearChatModal';
import { ProcessLoader } from '../components/ask-ai/ReverseEngineeringLoader';
import { DebugPanel } from '../components/ask-ai/DebugPanel';
import { ClarificationDialog } from '../components/ask-ai/ClarificationDialog';
import { ContextTimeline } from '../components/ask-ai/ContextTimeline';
import api from '../services/api';
import { useConversationV2 } from '../hooks/useConversationV2';
import { ResponseType } from '../services/api-v2';

// Feature flag: Enable v2 API (set via environment variable or localStorage)
const USE_V2_API = import.meta.env.VITE_USE_V2_API === 'true' || 
                   localStorage.getItem('use-v2-api') === 'true';

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
  previousConfidence?: number;
  confidenceDelta?: number;
  confidenceSummary?: string;
  enrichedPrompt?: string;
  questionsAndAnswers?: Array<{
    question: string;
    answer: string;
    selected_entities?: string[];
  }>;
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
  
  // v2 API hook (only used when USE_V2_API is true)
  const v2Conversation = useConversationV2({
    userId: 'anonymous',
    enableStreaming: true,
  });
  
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
    previousConfidence?: number;
    confidenceDelta?: number;
    confidenceSummary?: string;
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
  
  // v2 API message handler
  const handleSendMessageV2 = async (inputValue: string, _userMessage: ChatMessage) => {
    try {
      // Start conversation if not already started
      if (!v2Conversation.conversationId) {
        await v2Conversation.startConversation(inputValue);
      } else {
        // Send message in existing conversation
        const turnResponse = await v2Conversation.sendMessage(inputValue, true); // Use streaming
        
        if (turnResponse) {
          // Convert v2 response to ChatMessage format
          const aiMessage: ChatMessage = {
            id: `turn-${turnResponse.turn_number}`,
            type: 'ai',
            content: turnResponse.content,
            timestamp: new Date(turnResponse.created_at),
            suggestions: turnResponse.suggestions?.map(s => ({
              suggestion_id: s.suggestion_id,
              description: s.description,
              title: s.title,
              confidence: s.confidence,
              status: s.status,
              automation_yaml: s.automation_yaml,
              validated_entities: s.validated_entities,
            })),
            confidence: turnResponse.confidence?.overall,
            clarificationNeeded: turnResponse.response_type === ResponseType.CLARIFICATION_NEEDED,
            questions: turnResponse.clarification_questions?.map(q => ({
              id: q.id,
              category: q.category || 'unknown',
              question_text: q.question_text,
              question_type: q.question_type,
              options: q.options || [],
              priority: q.priority ?? 2,
              related_entities: q.related_entities || [],
            })),
          };

          setMessages(prev => [...prev, aiMessage]);
          updateContextFromMessage(aiMessage);

          // Handle clarification dialog
          if (turnResponse.response_type === ResponseType.CLARIFICATION_NEEDED && 
              turnResponse.clarification_questions && 
              turnResponse.clarification_questions.length > 0) {
            setClarificationDialog({
              questions: turnResponse.clarification_questions.map(q => ({
                id: q.id,
                category: q.category || 'unknown',
                question_text: q.question_text,
                question_type: q.question_type,
                options: q.options || [],
                priority: q.priority ?? 2,
                related_entities: q.related_entities || [],
              })),
              sessionId: turnResponse.conversation_id,
              confidence: turnResponse.confidence?.overall || 0.5,
              threshold: 0.7,
            });
          }

          // Show success message
          if (turnResponse.suggestions && turnResponse.suggestions.length > 0) {
            toast.success(`Found ${turnResponse.suggestions.length} automation suggestion${turnResponse.suggestions.length > 1 ? 's' : ''}`);
          }
        }
      }
    } catch (error: any) {
      console.error('v2 API error:', error);
      toast.error(`Failed to send message: ${error.message}`);
      throw error;
    } finally {
      setIsLoading(false);
      setIsTyping(false);
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
      // Use v2 API if enabled
      if (USE_V2_API) {
        return await handleSendMessageV2(inputValue, userMessage);
      }

      // v1 API (legacy)
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
      
      // Debug logging
      console.log('🔍 Clarification check:', {
        clarification_needed: response.clarification_needed,
        questions_count: response.questions?.length || 0,
        questions: response.questions,
        session_id: response.clarification_session_id
      });
      
      // Show clarification dialog if needed
      // Check both clarification_needed flag AND presence of questions
      const hasQuestions = response.questions && Array.isArray(response.questions) && response.questions.length > 0;
      const needsClarification = response.clarification_needed === true || response.clarification_needed === 'true';
      
      console.log('🔍 Clarification dialog check:', {
        clarification_needed: response.clarification_needed,
        needsClarification,
        hasQuestions,
        questions_count: response.questions?.length || 0,
        questions: response.questions,
        session_id: response.clarification_session_id
      });
      
      if (needsClarification && hasQuestions) {
        console.log('✅ Showing clarification dialog with questions:', response.questions);
        setClarificationDialog({
          questions: response.questions,
          sessionId: response.clarification_session_id || '',
          confidence: response.confidence || 0.5,
          threshold: 0.85,  // Default threshold
          previousConfidence: undefined,  // No previous confidence on first display
          confidenceDelta: undefined,
          confidenceSummary: undefined
        });
      } else {
        console.log('❌ NOT showing clarification dialog:', {
          needsClarification,
          hasQuestions,
          clarification_needed: response.clarification_needed,
          has_questions: !!response.questions,
          questions_type: typeof response.questions,
          questions_length: response.questions?.length || 0,
          questions: response.questions
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
        console.log('🚀 [APPROVE] Approve action started', { suggestionId, action });
        
        const messageWithQuery = messages.find(msg => 
          msg.suggestions?.some(s => s.suggestion_id === suggestionId)
        );
        const queryId = messageWithQuery?.id || 'unknown';
        
        console.log('🔍 [APPROVE] Found message with query', { 
          queryId, 
          hasMessage: !!messageWithQuery,
          messageId: messageWithQuery?.id,
          suggestionsCount: messageWithQuery?.suggestions?.length 
        });
        
        if (!messageWithQuery || queryId === 'unknown') {
          console.error('❌ [APPROVE] Cannot find query ID for suggestion', { suggestionId, messages });
          toast.error('❌ Cannot find query for this suggestion. Please try refreshing the page.');
          return;
        }
        
        // Show engaging reverse engineering loader IMMEDIATELY
        setReverseEngineeringStatus({ visible: true, action: 'approve' });
        console.log('🎨 [APPROVE] Loader set to visible for approve action');
        
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
          
          console.log('📡 [APPROVE] Calling API', { 
            queryId, 
            suggestionId, 
            selectedEntityIdsCount: selectedEntityIds.length,
            hasCustomMappings: !!(customMappings && Object.keys(customMappings).length > 0)
          });
          
          const response = await api.approveAskAISuggestion(
            queryId, 
            suggestionId, 
            selectedEntityIds.length > 0 ? selectedEntityIds : undefined,
            customMappings && Object.keys(customMappings).length > 0 ? customMappings : undefined
          );
          
          console.log('✅ [APPROVE] API call completed successfully');
          
          // Debug logging to understand response structure
          console.log('🔍 [APPROVE] API Response:', {
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
            
            // Store approve response for DebugPanel even on error
            setMessages(prev => prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.map(s => 
                s.suggestion_id === suggestionId 
                  ? { ...s, automation_yaml: response.automation_yaml || s.automation_yaml, approve_response: response }
                  : s
              ) || []
            })));
            
            // CRITICAL: Return early to prevent any success path execution
            setReverseEngineeringStatus({ visible: false });
            return;
          }
          
          // PRIORITY 2: Check for yaml_generated but deployment failed
          if (response && response.status === 'yaml_generated' && !response.automation_id) {
            console.warn('⚠️ [APPROVE] YAML generated but deployment failed', {
              status: response.status,
              automation_id: response.automation_id,
              error_details: response.error_details,
              message: response.message
            });
            
            const errorMsg = response.message || response.error_details?.message || 'YAML was generated but deployment to Home Assistant failed';
            toast.error(`❌ ${errorMsg}`, { duration: 10000 });
            
            // Show warnings if any
            if (response.warnings && Array.isArray(response.warnings) && response.warnings.length > 0) {
              response.warnings.forEach((warning: string) => {
                toast(warning, { icon: '⚠️', duration: 6000 });
              });
            }
            
            // Store response for DebugPanel
            setMessages(prev => prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.map(s => 
                s.suggestion_id === suggestionId 
                  ? { ...s, automation_yaml: response.automation_yaml || s.automation_yaml, approve_response: response }
                  : s
              ) || []
            })));
            
            setReverseEngineeringStatus({ visible: false });
            return;
          }
          
          // PRIORITY 3: Success - automation was created
          // Must check BOTH status === 'approved' AND automation_id exists
          console.log('🔍 [APPROVE] Checking response status', {
            hasResponse: !!response,
            status: response?.status,
            automation_id: response?.automation_id,
            ready_to_deploy: response?.ready_to_deploy,
            message: response?.message
          });
          
          if (response && response.status === 'approved' && response.automation_id) {
            console.log('✅ [APPROVE] Response is APPROVED - showing success');
            
            // Trigger particle celebration
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (!prefersReducedMotion) {
              // Find the approve button by looking for buttons with "APPROVE & CREATE" text
              // Use a small delay to ensure DOM is updated
              setTimeout(() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const approveButton = buttons.find(btn => 
                  btn.textContent?.includes('APPROVE & CREATE') || 
                  btn.textContent?.includes('PROCESSING')
                );
                
                let x = 0.5; // Default to center
                let y = 0.5;
                
                if (approveButton) {
                  const rect = approveButton.getBoundingClientRect();
                  x = (rect.left + rect.width / 2) / window.innerWidth;
                  y = (rect.top + rect.height / 2) / window.innerHeight;
                }
                
                // Fire confetti from button position (or center if not found)
                confetti({
                  particleCount: 100,
                  spread: 70,
                  origin: { x, y },
                  colors: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b'],
                  gravity: 0.8,
                  ticks: 200,
                  decay: 0.94
                });
                
                // Additional burst after short delay
                setTimeout(() => {
                  confetti({
                    particleCount: 50,
                    angle: 60,
                    spread: 55,
                    origin: { x, y },
                    colors: ['#10b981', '#3b82f6'],
                    gravity: 0.8,
                    ticks: 150
                  });
                  confetti({
                    particleCount: 50,
                    angle: 120,
                    spread: 55,
                    origin: { x, y },
                    colors: ['#10b981', '#3b82f6'],
                    gravity: 0.8,
                    ticks: 150
                  });
                }, 300);
              }, 100);
            }
            
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
            
            // Update suggestion with approve response, YAML, and deployed status
            // Mark as deployed and keep it visible (don't remove)
            setMessages(prev => prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.map(s => 
                s.suggestion_id === suggestionId 
                  ? { 
                      ...s, 
                      automation_yaml: response.automation_yaml || s.automation_yaml, 
                      approve_response: {
                        ...response,
                        deployed_at: new Date().toISOString()
                      },
                      status: 'deployed' as const
                    }
                  : s
              ) || []
            })));
            
            // Don't remove the suggestion - keep it visible with deployed state
            // The card will now show the deployed badge and green border
          } else {
            // PRIORITY 3: Unexpected response - show error with details
            console.error('❌ [APPROVE] Unexpected approve response:', response);
            console.error('❌ [APPROVE] Response details:', {
              status: response?.status,
              automation_id: response?.automation_id,
              ready_to_deploy: response?.ready_to_deploy,
              message: response?.message,
              error_details: response?.error_details,
              warnings: response?.warnings
            });
            
            const errorMsg = response?.message || response?.error_details?.message || 'Unexpected response from server';
            const errorType = response?.error_details?.type || 'unknown';
            
            // Show detailed error message
            if (errorType === 'deployment_error') {
              toast.error(`❌ Failed to deploy automation to Home Assistant: ${errorMsg}`, { duration: 10000 });
            } else if (errorType === 'connection_error') {
              toast.error(`❌ Cannot connect to Home Assistant: ${errorMsg}`, { duration: 10000 });
            } else {
              toast.error(`❌ Failed to create automation: ${errorMsg}`, { duration: 8000 });
            }
            
            // Show warnings if any
            if (response && Array.isArray(response.warnings) && response.warnings.length > 0) {
              response.warnings.forEach((warning: string) => {
                toast(warning, { icon: '⚠️', duration: 6000 });
              });
            }
            
            // Show warnings if any
            if (response && Array.isArray(response.warnings) && response.warnings.length > 0) {
              response.warnings.filter((w: any) => w != null).forEach((warning: string) => {
                toast(typeof warning === 'string' ? warning : String(warning), { icon: '⚠️', duration: 6000 });
              });
            }
          }
        } catch (error: any) {
          console.error('❌ [APPROVE] Approve action failed:', error);
          console.error('❌ [APPROVE] Error details:', {
            message: error?.message,
            response: error?.response?.data,
            status: error?.response?.status,
            queryId,
            suggestionId
          });
          
          setReverseEngineeringStatus({ visible: false });
          
          // Parse error details for user-friendly message
          const errorDetail = error?.response?.data?.detail;
          let errorMessage = 'Unknown error occurred';
          
          if (typeof errorDetail === 'string') {
            errorMessage = errorDetail;
          } else if (errorDetail?.message) {
            errorMessage = errorDetail.message;
          } else if (error?.message) {
            errorMessage = error.message;
          } else if (error?.toString()) {
            errorMessage = error.toString();
          }
          
          // Show detailed error to user
          toast.error(`❌ Failed to create automation: ${errorMessage}`, { duration: 8000 });
          
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
                    
                    {/* Show suggestions with context timeline if available */}
                    {message.suggestions && message.suggestions.length > 0 && (() => {
                      // Find the original user request (look backwards through messages for the first user message)
                      const messageIndex = messages.findIndex(m => m.id === message.id);
                      let originalRequest = '';
                      // Look backwards to find the original user message (skip over any intermediate AI messages)
                      for (let i = messageIndex - 1; i >= 0; i--) {
                        if (messages[i]?.type === 'user') {
                          originalRequest = messages[i].content;
                          break;
                        }
                      }
                      
                      // Extract clarifications from questionsAndAnswers (answers are the clarifications)
                      const clarifications = message.questionsAndAnswers?.map(qa => qa?.answer || '').filter(a => a) || [];
                      
                      // Only show timeline if we have original request or clarifications
                      const hasContext = originalRequest || clarifications.length > 0;
                      
                      // Debug logging
                      console.log('🔍 [SUGGESTIONS RENDER]', {
                        hasSuggestions: !!(message.suggestions && message.suggestions.length > 0),
                        suggestionsCount: message.suggestions?.length || 0,
                        hasContext,
                        originalRequest: !!originalRequest,
                        clarificationsCount: clarifications.length,
                        questionsAndAnswers: message.questionsAndAnswers?.length || 0
                      });
                      
                      return hasContext ? (
                        <div className="mt-4">
                          <ContextTimeline
                            originalRequest={originalRequest}
                            clarifications={clarifications}
                            questionsAndAnswers={message.questionsAndAnswers}
                            darkMode={darkMode}
                          >
                            <div className="space-y-3">
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
                            
                            // Helper to check if a string is an entity ID format
                            const isEntityId = (str: string): boolean => {
                              if (!str || typeof str !== 'string') return false;
                              // Entity IDs follow pattern: domain.entity_name
                              // Must contain a dot and have at least domain and entity parts
                              const parts = str.split('.');
                              return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
                            };
                            
                            // Helper to add device safely
                              const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
                                // Skip if friendlyName equals entityId (prevents entity IDs from appearing as friendly names)
                                if (friendlyName === entityId) {
                                  return; // Skip duplicate - entity ID used as friendly name
                                }
                                
                                // Skip if friendlyName is an entity ID format (defensive check)
                                if (isEntityId(friendlyName)) {
                                  return; // Skip - entity ID format should not be used as friendly name
                                }
                                
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
                            
                            // 1. Try entity_id_annotations FIRST (has actual friendly names from HA Entity Registry)
                            // This is the preferred source as it includes the actual friendly_name from Home Assistant
                            if (suggestion.entity_id_annotations && typeof suggestion.entity_id_annotations === 'object') {
                              Object.entries(suggestion.entity_id_annotations).forEach(([queryTerm, annotation]: [string, any]) => {
                                // Skip if queryTerm is an entity ID (defensive check)
                                if (annotation?.entity_id && !isEntityId(queryTerm)) {
                                  // Use actual friendly_name from HA entity registry if available, otherwise use query term
                                  const actualFriendlyName = annotation.friendly_name || queryTerm;
                                  // Only use if it's not an entity ID format
                                  if (!isEntityId(actualFriendlyName)) {
                                    addDevice(actualFriendlyName, annotation.entity_id, annotation.domain);
                                  }
                                }
                              });
                            }
                            
                            // 2. Fallback to validated_entities (user query terms mapped to entity IDs)
                            // Only use if entity_id_annotations didn't provide devices
                            // Note: validated_entities keys are user query terms, not necessarily actual friendly names
                            if (devices.length === 0 && suggestion.validated_entities && typeof suggestion.validated_entities === 'object') {
                              Object.entries(suggestion.validated_entities).forEach(([queryTerm, entityId]: [string, any]) => {
                                // Skip if queryTerm is an entity ID (defensive check - backend should filter but handle if not)
                                if (entityId && typeof entityId === 'string' && !isEntityId(queryTerm)) {
                                  addDevice(queryTerm, entityId);
                                }
                              });
                            }
                            
                            // 3. Try device_mentions
                            if (suggestion.device_mentions && typeof suggestion.device_mentions === 'object') {
                              Object.entries(suggestion.device_mentions).forEach(([mention, entityId]: [string, any]) => {
                                // Skip if mention is an entity ID (defensive check - backend should filter but handle if not)
                                if (entityId && typeof entityId === 'string' && !isEntityId(mention)) {
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
                                    // Skip if deviceName is an entity ID (defensive check)
                                    if (isEntityId(deviceName)) {
                                      return; // Skip - entity ID should not be used as device name
                                    }
                                    
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
                                  created_at: suggestion.created_at,
                                  approve_response: suggestion.approve_response,
                                  ha_automation_id: suggestion.ha_automation_id
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
                                previousConfidence={message.previousConfidence}
                                confidenceDelta={message.confidenceDelta}
                                confidenceSummary={message.confidenceSummary}
                              />
                              {/* Debug Panel */}
                              <DebugPanel
                                debug={suggestion.debug}
                                technicalPrompt={suggestion.technical_prompt}
                                deviceInfo={deviceInfo.length > 0 ? deviceInfo : undefined}
                                automation_yaml={suggestion.automation_yaml || null}
                                originalQuery={(() => {
                                  // Find the user message that precedes this AI message
                                  const messageIndex = messages.findIndex(m => m.id === message.id);
                                  if (messageIndex > 0) {
                                    const prevMessage = messages[messageIndex - 1];
                                    if (prevMessage.type === 'user') {
                                      return prevMessage.content;
                                    }
                                  }
                                  return undefined;
                                })()}
                                extractedEntities={message.entities}
                                approveResponse={suggestion.approve_response}
                                darkMode={darkMode}
                              />
                            </div>
                          );
                        })}
                            </div>
                          </ContextTimeline>
                        </div>
                      ) : (
                        <div className="mt-4 space-y-3">
                          {message.suggestions.map((suggestion, idx) => {
                            const isProcessing = processingActions.has(`${suggestion.suggestion_id}-approve`) || 
                                               processingActions.has(`${suggestion.suggestion_id}-reject`) ||
                                               processingActions.has(`${suggestion.suggestion_id}-refine`);
                            
                            const suggestionStatus = suggestion.status || 'draft';
                            const refinementCount = suggestion.refinement_count || 0;
                            const conversationHistory = suggestion.conversation_history || [];
                            
                            const extractDeviceInfo = (suggestion: any, extractedEntities?: any[], suggestionId?: string): Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> => {
                              const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
                              const seenEntityIds = new Set<string>();
                              
                              const isEntityId = (str: string): boolean => {
                                if (!str || typeof str !== 'string') return false;
                                const parts = str.split('.');
                                return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
                              };
                              
                              const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
                                if (friendlyName === entityId) return;
                                if (isEntityId(friendlyName)) return;
                                
                                const friendlyNameLower = friendlyName.toLowerCase().trim();
                                const genericTerms = ['light', 'lights', 'device', 'devices', 'sensor', 'sensors', 'switch', 'switches'];
                                if (genericTerms.includes(friendlyNameLower)) return;
                                
                                if (entityId && entityId.split('.').length === 2 && 
                                    entityId.split('.')[1].toLowerCase() === entityId.split('.')[0].toLowerCase()) {
                                  return;
                                }
                                
                                if (entityId && !seenEntityIds.has(entityId)) {
                                  let isSelected = true;
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
                              
                              if (suggestion.entity_id_annotations && typeof suggestion.entity_id_annotations === 'object') {
                                Object.entries(suggestion.entity_id_annotations).forEach(([queryTerm, annotation]: [string, any]) => {
                                  if (annotation?.entity_id && !isEntityId(queryTerm)) {
                                    const actualFriendlyName = annotation.friendly_name || queryTerm;
                                    if (!isEntityId(actualFriendlyName)) {
                                      addDevice(actualFriendlyName, annotation.entity_id, annotation.domain);
                                    }
                                  }
                                });
                              }
                              
                              if (devices.length === 0 && suggestion.validated_entities && typeof suggestion.validated_entities === 'object') {
                                Object.entries(suggestion.validated_entities).forEach(([queryTerm, entityId]: [string, any]) => {
                                  if (entityId && typeof entityId === 'string' && !isEntityId(queryTerm)) {
                                    addDevice(queryTerm, entityId);
                                  }
                                });
                              }
                              
                              if (suggestion.device_mentions && typeof suggestion.device_mentions === 'object') {
                                Object.entries(suggestion.device_mentions).forEach(([mention, entityId]: [string, any]) => {
                                  if (entityId && typeof entityId === 'string' && !isEntityId(mention)) {
                                    addDevice(mention, entityId);
                                  }
                                });
                              }
                              
                              if (suggestion.entity_ids_used && Array.isArray(suggestion.entity_ids_used)) {
                                suggestion.entity_ids_used.forEach((entityId: string) => {
                                  if (entityId && typeof entityId === 'string') {
                                    const parts = entityId.split('.');
                                    const friendlyName = parts.length > 1 
                                      ? parts[1].split('_').map((word: string) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                                      : entityId;
                                    addDevice(friendlyName, entityId);
                                  }
                                });
                              }
                              
                              if (suggestion.devices_involved && Array.isArray(suggestion.devices_involved)) {
                                const seenFriendlyNames = new Set(devices.map(d => d.friendly_name.toLowerCase()));
                                
                                suggestion.devices_involved.forEach((deviceName: string) => {
                                  if (typeof deviceName === 'string' && deviceName.trim()) {
                                    if (isEntityId(deviceName)) return;
                                    
                                    const deviceNameLower = deviceName.toLowerCase().trim();
                                    if (seenFriendlyNames.has(deviceNameLower)) return;
                                    
                                    if (suggestion.validated_entities && 
                                        typeof suggestion.validated_entities === 'object' &&
                                        suggestion.validated_entities[deviceName]) {
                                      const actualEntityId = suggestion.validated_entities[deviceName];
                                      if (actualEntityId && typeof actualEntityId === 'string') {
                                        addDevice(deviceName, actualEntityId);
                                        seenFriendlyNames.add(deviceNameLower);
                                        return;
                                      }
                                    }
                                    
                                    const normalizedName = deviceName.toLowerCase().replace(/\s+/g, '_');
                                    const inferredEntityId = `light.${normalizedName}`;
                                    addDevice(deviceName, inferredEntityId, 'light');
                                    seenFriendlyNames.add(deviceNameLower);
                                  }
                                });
                              }
                              
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
                            
                            return (
                              <div key={idx}>
                                <ConversationalSuggestionCard
                                  key={suggestion.suggestion_id}
                                  suggestion={{
                                    id: parseInt(suggestion.suggestion_id.replace(/\D/g, '')) || idx + 1,
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
                                    created_at: suggestion.created_at,
                                    approve_response: suggestion.approve_response,
                                    ha_automation_id: suggestion.ha_automation_id
                                  }}
                                  onRefine={async (_id: number, refinement: string) => {
                                    try {
                                      await handleSuggestionAction(suggestion.suggestion_id, 'refine', refinement);
                                    } catch (error) {
                                      throw error;
                                    }
                                  }}
                                  onApprove={async (_id: number, customMappings?: Record<string, string>) => handleSuggestionAction(suggestion.suggestion_id, 'approve', undefined, customMappings)}
                                  onReject={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'reject')}
                                  onTest={async (_id: number) => handleSuggestionAction(suggestion.suggestion_id, 'test')}
                                  onDeviceToggle={(id: number, entityId: string, selected: boolean) => {
                                    handleDeviceToggle(id, entityId, selected);
                                    setMessages(prev => [...prev]);
                                  }}
                                  darkMode={darkMode}
                                  disabled={isProcessing}
                                  tested={testedSuggestions.has(suggestion.suggestion_id)}
                                  previousConfidence={message.previousConfidence}
                                  confidenceDelta={message.confidenceDelta}
                                  confidenceSummary={message.confidenceSummary}
                                />
                                <DebugPanel
                                  debug={suggestion.debug}
                                  technicalPrompt={suggestion.technical_prompt}
                                  deviceInfo={deviceInfo.length > 0 ? deviceInfo : undefined}
                                  automation_yaml={suggestion.automation_yaml || null}
                                  originalQuery={(() => {
                                    const messageIndex = messages.findIndex(m => m.id === message.id);
                                    if (messageIndex > 0) {
                                      const prevMessage = messages[messageIndex - 1];
                                      if (prevMessage.type === 'user') {
                                        return prevMessage.content;
                                      }
                                    }
                                    return undefined;
                                  })()}
                                  extractedEntities={message.entities}
                                  approveResponse={suggestion.approve_response}
                                  darkMode={darkMode}
                                />
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                    
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
          previousConfidence={clarificationDialog.previousConfidence}
          confidenceDelta={clarificationDialog.confidenceDelta}
          confidenceSummary={clarificationDialog.confidenceSummary}
          onAnswer={async (answers) => {
            try {
              const response = await api.clarifyAnswers(clarificationDialog.sessionId, answers);
              
              console.log('🔍 Clarification response:', {
                clarification_complete: response.clarification_complete,
                has_suggestions: !!response.suggestions,
                suggestions_count: response.suggestions?.length || 0,
                has_questions: !!response.questions,
                questions_count: response.questions?.length || 0,
                confidence: response.confidence,
                previous_confidence: response.previous_confidence,
                confidence_delta: response.confidence_delta,
                confidence_summary: response.confidence_summary,
                message: response.message,
                has_previous_confidence: response.previous_confidence !== undefined,
                has_confidence_delta: response.confidence_delta !== undefined,
                will_show_improvement: response.previous_confidence !== undefined && 
                                      response.previous_confidence > 0 && 
                                      response.confidence_delta !== undefined && 
                                      response.confidence_delta > 0,
                has_questions_and_answers: !!response.questions_and_answers,
                questions_and_answers_count: response.questions_and_answers?.length || 0,
                questions_and_answers: response.questions_and_answers
              });
              
              if (response.clarification_complete && response.suggestions) {
                console.log('✅ [CLARIFICATION] Clarification complete, suggestions received', {
                  session_id: response.session_id,
                  suggestions_count: response.suggestions?.length,
                  suggestions: response.suggestions?.map((s: any) => ({
                    suggestion_id: s.suggestion_id,
                    title: s.title || `${s.trigger_summary} → ${s.action_summary}`,
                    has_validated_entities: !!s.validated_entities,
                    has_description: !!s.description,
                    has_trigger_summary: !!s.trigger_summary,
                    has_action_summary: !!s.action_summary,
                    has_debug: !!s.debug
                  }))
                });
                
                // Validate suggestions array is not empty
                if (!response.suggestions || response.suggestions.length === 0) {
                  console.error('❌ [CLARIFICATION] Suggestions array is empty after clarification completion');
                  toast.error('⚠️ No suggestions were generated. Please try rephrasing your request or try again.');
                  setClarificationDialog(null);
                  return; // Don't add message with empty suggestions
                }
                
                // Verify suggestions have required fields for approval
                const invalidSuggestions = response.suggestions?.filter((s: any) => !s.suggestion_id);
                if (invalidSuggestions && invalidSuggestions.length > 0) {
                  console.error('❌ [CLARIFICATION] Some suggestions are missing suggestion_id', invalidSuggestions);
                  toast.error('⚠️ Some suggestions are missing required fields. Please try again.');
                }
                
                // Log each suggestion's structure for debugging
                response.suggestions?.forEach((s: any, idx: number) => {
                  console.log(`📋 [SUGGESTION ${idx + 1}]`, {
                    suggestion_id: s.suggestion_id,
                    has_description: !!s.description,
                    has_trigger_summary: !!s.trigger_summary,
                    has_action_summary: !!s.action_summary,
                    has_validated_entities: !!s.validated_entities,
                    validated_entities_count: s.validated_entities ? Object.keys(s.validated_entities).length : 0,
                    has_debug: !!s.debug,
                    has_devices_involved: !!s.devices_involved,
                    devices_involved_count: s.devices_involved ? s.devices_involved.length : 0
                  });
                });
                
                // Add enriched prompt message if available
                if (response.enriched_prompt) {
                  const enrichedPromptMessage: ChatMessage = {
                    id: `enriched-prompt-${response.session_id}`,
                    type: 'ai',
                    content: response.enriched_prompt,
                    timestamp: new Date(),
                    enrichedPrompt: response.enriched_prompt,
                    questionsAndAnswers: response.questions_and_answers
                  };
                  setMessages(prev => [...prev, enrichedPromptMessage]);
                }
                
                // Add suggestions to conversation
                // Use session_id as the message id so approval can find the query record
                // Build enhanced message content with confidence improvement info
                let messageContent = response.message || 'Based on your answers, here are the automation suggestions:';
                
                // Add confidence improvement information if available
                console.log('🔍 Checking confidence improvement display:', {
                  previous_confidence: response.previous_confidence,
                  confidence_delta: response.confidence_delta,
                  confidence_summary: response.confidence_summary,
                  will_display: response.previous_confidence !== undefined && 
                               response.previous_confidence > 0 && 
                               response.confidence_delta !== undefined && 
                               response.confidence_delta > 0
                });
                
                if (response.previous_confidence !== undefined && 
                    response.previous_confidence > 0 && 
                    response.confidence_delta !== undefined && 
                    response.confidence_delta > 0) {
                  const prevPercent = Math.round(response.previous_confidence * 100);
                  const currPercent = Math.round(response.confidence * 100);
                  const deltaPercent = Math.round(response.confidence_delta * 100);
                  messageContent += `\n\n✨ Confidence improved from ${prevPercent}% to ${currPercent}% (+${deltaPercent}%)`;
                  if (response.confidence_summary) {
                    messageContent += `\n${response.confidence_summary}`;
                  }
                  console.log('✅ Added confidence improvement to message:', messageContent);
                } else {
                  console.log('⚠️ Confidence improvement NOT added - missing data:', {
                    has_previous: response.previous_confidence !== undefined,
                    previous_value: response.previous_confidence,
                    has_delta: response.confidence_delta !== undefined,
                    delta_value: response.confidence_delta
                  });
                }
                
                const suggestionMessage: ChatMessage = {
                  id: response.session_id,  // Use session_id as id so it matches the query_id in database
                  type: 'ai',
                  content: messageContent,
                  timestamp: new Date(),
                  suggestions: response.suggestions,
                  confidence: response.confidence,
                  clarificationSessionId: response.session_id,  // Also store for reference
                  previousConfidence: response.previous_confidence,
                  confidenceDelta: response.confidence_delta,
                  confidenceSummary: response.confidence_summary,
                  enrichedPrompt: response.enriched_prompt,
                  questionsAndAnswers: response.questions_and_answers
                };
                
                // Log the message structure before adding it
                console.log('📝 [CLARIFICATION] Adding suggestion message to conversation:', {
                  message_id: suggestionMessage.id,
                  has_suggestions: !!(suggestionMessage.suggestions && suggestionMessage.suggestions.length > 0),
                  suggestions_count: suggestionMessage.suggestions?.length || 0,
                  has_questionsAndAnswers: !!suggestionMessage.questionsAndAnswers,
                  questionsAndAnswers_count: suggestionMessage.questionsAndAnswers?.length || 0,
                  message_content: suggestionMessage.content.substring(0, 100)
                });
                
                setMessages(prev => {
                  const updated = [...prev, suggestionMessage];
                  console.log('✅ [CLARIFICATION] Messages updated, total messages:', updated.length);
                  // Log the last message to verify it was added correctly
                  const lastMessage = updated[updated.length - 1];
                  console.log('📋 [CLARIFICATION] Last message in array:', {
                    id: lastMessage.id,
                    type: lastMessage.type,
                    has_suggestions: !!(lastMessage.suggestions && lastMessage.suggestions.length > 0),
                    suggestions_count: lastMessage.suggestions?.length || 0
                  });
                  return updated;
                });
                setClarificationDialog(null);
                toast.success(`Clarification complete! ${response.suggestions?.length || 0} suggestion(s) generated.`);
              } else if (response.questions && response.questions.length > 0) {
                // More questions needed
                setClarificationDialog({
                  questions: response.questions,
                  sessionId: response.session_id,
                  confidence: response.confidence,
                  threshold: response.confidence_threshold,
                  previousConfidence: response.previous_confidence,
                  confidenceDelta: response.confidence_delta,
                  confidenceSummary: response.confidence_summary
                });
                toast(response.message || 'Please answer the additional questions.', { icon: 'ℹ️' });
              } else {
                // No more questions but clarification not complete - this shouldn't happen
                // but we'll handle it gracefully by closing the dialog and showing a message
                console.warn('⚠️ Clarification incomplete but no questions returned:', response);
                setClarificationDialog(null);
                toast.error(response.message || 'Clarification incomplete. Please try rephrasing your request.');
              }
            } catch (error: any) {
              console.error('❌ Clarification error:', error);
              
              // Check for network timeout (504) or abort error
              const isTimeout = error.response?.status === 504 || 
                               error.name === 'AbortError' ||
                               error.message?.includes('timeout') ||
                               error.message?.includes('timed out');
              
              // Parse error details from API response
              const errorDetail = error.response?.data?.detail;
              let errorMessage: string;
              let errorType: string;
              let retryAfter: number | undefined;
              
              if (errorDetail) {
                // Handle both string and object error details
                if (typeof errorDetail === 'string') {
                  errorMessage = errorDetail;
                  errorType = isTimeout ? 'timeout' : 'unknown';
                } else {
                  errorMessage = errorDetail.message || 'Failed to submit clarification';
                  errorType = errorDetail.error || (isTimeout ? 'timeout' : 'unknown');
                  retryAfter = errorDetail.retry_after;
                }
              } else {
                // Fallback to error message
                errorMessage = error.message || 'Failed to submit clarification';
                errorType = isTimeout ? 'timeout' : 'unknown';
              }
              
              // Show appropriate error message based on error type
              if (errorType === 'timeout' || isTimeout) {
                toast.error(
                  `⏱️ ${errorMessage}\n\nThe request is taking longer than expected. This may be due to a complex query or high system load. Please try again with a simpler request or wait a moment.`,
                  { duration: 10000 }
                );
                // Keep dialog open for retry on timeout
              } else if (errorType === 'api_error') {
                toast.error(
                  `🔌 ${errorMessage}${retryAfter ? `\n\nPlease wait ${retryAfter} seconds before retrying.` : ''}`,
                  { duration: 8000 }
                );
                // Keep dialog open for retry on API errors
              } else {
                // For other errors, show message and close dialog
                toast.error(`❌ ${errorMessage}`, { duration: 6000 });
                // Close dialog on non-retryable errors to prevent resubmission
                setClarificationDialog(null);
              }
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