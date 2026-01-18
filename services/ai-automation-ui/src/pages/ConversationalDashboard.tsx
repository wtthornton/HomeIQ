/**
 * Conversational Dashboard - Story AI1.23 Phase 5
 * 
 * Description-first UI for automation suggestions.
 * Users edit with natural language, approve to generate YAML.
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import { ConversationalSuggestionCard } from '../components/ConversationalSuggestionCard';
import api, { APIError } from '../services/api';
import { ProcessLoader } from '../components/ask-ai/ReverseEngineeringLoader';
import { LoadingSpinner } from '../components/LoadingSpinner';
import type { Suggestion } from '../types';

export const ConversationalDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  
  // Type safety: Use proper Suggestion type instead of any[]
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; retryable?: boolean } | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'refining' | 'yaml_generated' | 'deployed'>('draft');
  const [processingRedeploy, setProcessingRedeploy] = useState<number | null>(null);
  const [refreshAllowed, setRefreshAllowed] = useState(true);
  const [nextRefreshAt, setNextRefreshAt] = useState<string | null>(null);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false); // Loading state for refresh/analysis status
  const [analysisRun, setAnalysisRun] = useState<{
    status: string;
    started_at: string;
    finished_at?: string | null;
    duration_seconds?: number | null;
  } | null>(null);

  const loadSuggestions = async (retryAttempt = 0): Promise<void> => {
    const maxRetries = 3;
    const retryDelay = Math.min(1000 * Math.pow(2, retryAttempt), 5000); // Exponential backoff, max 5s
    
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Loading suggestions with device name mapping...');
      // Load all suggestions, filter on frontend
      const response = await api.getSuggestions();
      // Map API response to component format
      const suggestionsArray = response.data?.suggestions || [];
      console.log(`Loaded ${suggestionsArray.length} suggestions from API`);
      
      if (suggestionsArray.length > 0) {
        console.log('Raw API response (first suggestion):', suggestionsArray[0]);
      }
      
      const mappedSuggestions = suggestionsArray.map(suggestion => {
        // Extract device hash from title and replace with friendly name
        const deviceHashMatch = suggestion.title.match(/AI Suggested: ([a-f0-9]{32})/);
        let friendlyTitle = suggestion.title;
        const originalDescription = suggestion.description_only || suggestion.description || '';
        let friendlyDescription = originalDescription;
        
        if (deviceHashMatch) {
          const deviceHash = deviceHashMatch[1];
          console.log('Found device hash:', deviceHash);
          
          // Map known device hashes to friendly names
          const deviceNameMap: Record<string, string> = {
            '1ba44a8f25eab1397cb48dd7b743edcd': 'Sun',
            '71d5add6cf1f844d6f9bb34a3b58a09d': 'Living Room Light',
            'eca71f35d1ff44a1149dedc519f0d27a': 'Kitchen Light',
            '61234ae84aba13edf830eb7c5a7e3ae8': 'Bedroom Light',
            '603c07b7a7096b280ac6316c78dd1c1f': 'Office Light'
          };
          
          const friendlyName = deviceNameMap[deviceHash] || `Device ${deviceHash.substring(0, 8)}...`;
          console.log('Mapping device hash to friendly name:', deviceHash, '->', friendlyName);
          
          friendlyTitle = suggestion.title.replace(deviceHash, friendlyName);
          friendlyDescription = suggestion.description.replace(deviceHash, friendlyName);
          
          console.log('Updated title:', friendlyTitle);
          console.log('Updated description:', friendlyDescription);
        } else {
          console.log('No device hash match found in title:', suggestion.title);
        }
        
        const deviceCapabilities = suggestion.device_capabilities || {};
        const deviceInfoFromCapabilities = Array.isArray(deviceCapabilities?.devices)
          ? deviceCapabilities.devices
          : undefined;

        const mapped = {
          ...suggestion,
          title: friendlyTitle,
          description: friendlyDescription,
          description_only: friendlyDescription,
          status: suggestion.status || 'draft',
          refinement_count: suggestion.refinement_count ?? 0,
          conversation_history: Array.isArray(suggestion.conversation_history)
            ? suggestion.conversation_history
            : [],
          device_capabilities: deviceCapabilities,
          device_info: suggestion.device_info || deviceInfoFromCapabilities || [],
          ha_automation_id: suggestion.ha_automation_id || null,
          yaml_generated_at: suggestion.yaml_generated_at || null
        };
        console.log('Mapped suggestion:', mapped);
        return mapped;
      });
      console.log('All mapped suggestions:', mappedSuggestions);
      setSuggestions(mappedSuggestions);
      setRetryCount(0); // Reset retry count on success
    } catch (error: any) {
      console.error('Failed to load suggestions:', error);
      
      // Extract error details from API response
      const errorDetail = error?.response?.data?.detail;
      const errorCode = typeof errorDetail === 'object' ? errorDetail?.error_code : undefined;
      const errorMessage = typeof errorDetail === 'object' ? errorDetail?.message : (typeof errorDetail === 'string' ? errorDetail : error?.message || 'Failed to load suggestions');
      
      // Determine if error is retryable (5xx errors, network errors)
      const isRetryable = error?.status >= 500 || error?.status === 0 || !error?.status;
      
      // Auto-retry for retryable errors
      if (isRetryable && retryAttempt < maxRetries) {
        console.log(`Retrying in ${retryDelay}ms... (attempt ${retryAttempt + 1}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        return loadSuggestions(retryAttempt + 1);
      }
      
      // Set error state for UI display
      setError({
        message: errorMessage,
        code: errorCode,
        retryable: isRetryable && retryAttempt < maxRetries
      });
      setRetryCount(retryAttempt);
      
      // Show user-friendly error message
      const userMessage = errorCode === 'SUGGESTIONS_LIST_ERROR' 
        ? 'Unable to load suggestions. Please try again.'
        : errorMessage;
      toast.error(userMessage);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRetry = () => {
    setRetryCount(0);
    loadSuggestions(0);
  };

  const loadRefreshStatus = async () => {
    try {
      setStatusLoading(true);
      const status = await api.getRefreshStatus();
      setRefreshAllowed(status.allowed);
      setNextRefreshAt(status.next_allowed_at);
    } catch (error: any) {
      console.error('Failed to load refresh status', error);
      // Non-critical error, don't show toast but log it
      const errorDetail = error?.response?.data?.detail;
      if (typeof errorDetail === 'object' && errorDetail?.error_code === 'REFRESH_STATUS_ERROR') {
        console.warn('Refresh status unavailable, continuing without cooldown info');
      }
    } finally {
      setStatusLoading(false);
    }
  };

  const loadAnalysisStatus = async () => {
    try {
      setStatusLoading(true);
      const status = await api.getAnalysisStatus();
      setAnalysisRun(status.analysis_run ?? null);
    } catch (error: any) {
      console.error('Failed to load analysis status', error);
      // Non-critical error, don't show toast but log it
      const errorDetail = error?.response?.data?.detail;
      if (typeof errorDetail === 'object' && errorDetail?.error_code === 'ANALYSIS_STATUS_ERROR') {
        console.warn('Analysis status unavailable, continuing without run info');
      }
    } finally {
      setStatusLoading(false);
    }
  };

  const generateSampleSuggestion = async () => {
    try {
      setLoading(true);
      console.log('🔄 Generating sample suggestion...');
      
      const response = await api.generateSuggestion(
        undefined,  // No pattern_id for sample suggestions
        'time_of_day',
        'light.living_room',
        { hour: 18, confidence: 0.85, occurrences: 20 }
      );
      
      console.log('Generate response:', response);
      
      // Convert API response to suggestion format
      const suggestionId = response.suggestion_id;
      const idMatch = suggestionId.match(/-(\d+)$/);
      const id = idMatch ? parseInt(idMatch[1]) : Date.now();
      
      const suggestion: Suggestion = {
        id: id,
        title: `Automation: ${response.devices_involved?.[0]?.friendly_name || 'Living Room Light'}`,
        description: response.description || '',
        description_only: response.description || '',
        confidence: response.confidence || 0.85,
        status: (response.status || 'draft') as Suggestion['status'],
        created_at: response.created_at || new Date().toISOString(),
        conversation_history: [],
        refinement_count: 0,
        device_capabilities: {}
      };
      
      // Add to existing suggestions instead of replacing
      setSuggestions(prev => [...prev, suggestion]);
      
      // Switch to draft tab to show the new suggestion
      setSelectedStatus('draft');
      
      toast.success('✅ Generated sample suggestion!');
      
      // Reload suggestions to get fresh data from API
      await loadSuggestions();
    } catch (error: any) {
      console.error('Failed to generate suggestion:', error);
      const errorMessage = error?.message || error?.toString() || 'Unknown error';
      toast.error(`Failed to generate suggestion: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      await Promise.all([loadSuggestions(), loadRefreshStatus(), loadAnalysisStatus()]);
    };

    loadAll();

    const interval = setInterval(() => {
      loadSuggestions();
      loadRefreshStatus();
      loadAnalysisStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, [selectedStatus]);

  const handleRefreshClick = async () => {
    try {
      setRefreshLoading(true);
      const response = await api.refreshSuggestions();
      
      // Handle improved error response from API
      if (!response.success && response.error_code) {
        // Extract detailed error message
        let errorMessage = response.message || 'Failed to generate suggestions';
        
        // Provide specific guidance based on error code
        if (response.error_code === 'NO_SUGGESTIONS_GENERATED') {
          errorMessage = 'No suggestions generated. Possible reasons: No events available (need at least 100 events from Home Assistant), Data API not responding, or OpenAI API key not configured. Check service logs for details.';
        } else if (response.error_code === 'VALIDATION_ERROR') {
          errorMessage = `Configuration error: ${errorMessage}. Check service configuration and dependencies.`;
        } else if (response.error_code === 'GENERATION_ERROR') {
          errorMessage = `Generation error: ${errorMessage}. Check service logs for details.`;
        }
        
        toast.error(errorMessage);
        setError({
          message: errorMessage,
          code: response.error_code,
          retryable: response.error_code !== 'VALIDATION_ERROR'
        });
      } else if (response.success) {
        toast.success(response.message || `Successfully generated ${response.count || 0} suggestions`);
        // Reload suggestions to show new ones
        await loadSuggestions();
        await loadRefreshStatus();
      } else {
        // Fallback for unexpected response format
        toast.info(response.message || 'Refresh completed');
        await loadRefreshStatus();
      }
    } catch (error) {
      if (error instanceof APIError) {
        toast.error(error.message);
        setError({
          message: error.message,
          retryable: true
        });
      } else if (error instanceof Error) {
        toast.error(error.message);
        setError({
          message: error.message,
          retryable: true
        });
      } else {
        toast.error('Failed to generate suggestions. Check service health and logs.');
        setError({
          message: 'Failed to generate suggestions. Check service health and logs.',
          retryable: true
        });
      }
    } finally {
      setRefreshLoading(false);
    }
  };

  const handleRefine = async (id: number, userInput: string) => {
    try {
      const result = await api.refineSuggestion(id, userInput);
      
      // Update local state
      setSuggestions(prev =>
        prev.map(s =>
          s.id === id
            ? {
                ...s,
                description_only: result.updated_description,
                refinement_count: result.refinement_count,
                status: result.status as Suggestion['status'],
                conversation_history: [
                  ...(s.conversation_history || []),
                  {
                    timestamp: new Date().toISOString(),
                    user_input: userInput,
                    updated_description: result.updated_description,
                    changes: result.changes_detected,
                    validation: result.validation
                  }
                ]
              }
            : s
        )
      );

      // Show validation messages
      if (result.validation.ok) {
        if (result.changes_detected.length > 0) {
          toast.success(`✅ Updated: ${result.changes_detected.join(', ')}`);
        } else {
          toast.success('✅ Description updated');
        }
      } else if (result.validation.warnings.length > 0) {
        toast.error(`⚠️ ${result.validation.warnings[0]}`);
        if (result.validation.alternatives.length > 0) {
          toast(`💡 ${result.validation.alternatives[0]}`, { icon: '💡' });
        }
      }
    } catch (error) {
      console.error('Failed to refine:', error);
      throw error; // Re-throw so card can handle it
    }
  };

  const handleApprove = async (id: number) => {
    try {
      const result = await api.approveAndGenerateYAML(id);
      
      // Update local state
      setSuggestions(prev =>
        prev.map(s =>
          s.id === id
            ? {
                ...s,
                status: result.status as Suggestion['status'],
                automation_yaml: result.automation_yaml,
                yaml_generated_at: new Date().toISOString(),
                ha_automation_id: result.automation_id
              }
            : s
        )
      );

      // Show success with safety score
      toast.success(
        `✅ Automation created!\nSafety score: ${result.yaml_validation.safety_score}/100`,
        { duration: 5000 }
      );
    } catch (error) {
      console.error('Failed to approve:', error);
      throw error;
    }
  };

  const handleRedeploy = async (id: number) => {
    try {
      setProcessingRedeploy(id);
      toast.loading('🔄 Re-deploying with updated YAML and category...', { id: `redeploy-${id}` });
      
      const result = await api.redeploySuggestion(id);
      
      // Check if category changed
      const oldSuggestion = suggestions.find(s => s.id === id);
      const categoryChanged = result.category && oldSuggestion && result.category !== oldSuggestion.category;
      
      // Update local state
      setSuggestions(prev =>
        prev.map(s =>
          s.id === id
            ? {
                ...s,
                status: result.status as Suggestion['status'],
                automation_yaml: result.automation_yaml,
                category: (result.category || s.category) as Suggestion['category'],
                priority: (result.priority || s.priority) as Suggestion['priority'],
                yaml_generated_at: new Date().toISOString(),
                ha_automation_id: result.automation_id || s.ha_automation_id
              }
            : s
        )
      );

      // Build success message
      let successMsg = `✅ Re-deployed successfully!\nSafety score: ${result.yaml_validation.safety_score}/100`;
      if (categoryChanged) {
        successMsg += `\nCategory updated: ${oldSuggestion.category} → ${result.category}`;
      }

      toast.success(successMsg, { id: `redeploy-${id}`, duration: 6000 });
      
      // Reload suggestions to get fresh data
      await loadSuggestions();
    } catch (error: any) {
      console.error('Failed to re-deploy:', error);
      toast.error(
        `❌ Re-deploy failed: ${error?.message || 'Unknown error'}`,
        { id: `redeploy-${id}`, duration: 5000 }
      );
      throw error;
    } finally {
      setProcessingRedeploy(null);
    }
  };

  const handleReject = async (id: number) => {
    const reason = prompt('Why are you rejecting this? (optional)');
    try {
      await api.rejectSuggestion(id, reason || undefined);
      setSuggestions(prev => prev.filter(s => s.id !== id));
      toast.success('✅ Suggestion rejected');
    } catch (error) {
      toast.error('❌ Failed to reject suggestion');
    }
  };

  return (
    <>
      <ProcessLoader
        isVisible={!!processingRedeploy}
        processType="automation-creation"
      />
      <div className="space-y-6">
      {/* Header - Modern 2025 Design */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              💡 Automation Suggestions
            </h1>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Edit with natural language, approve to create
            </p>
          </div>
          <div className="flex flex-col sm:items-end gap-2">
            <div className="flex items-center gap-2">
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {suggestions.length} suggestions
              </span>
              <motion.button
                whileHover={refreshLoading || !refreshAllowed ? {} : { scale: 1.05 }}
                whileTap={refreshLoading || !refreshAllowed ? {} : { scale: 0.95 }}
                onClick={handleRefreshClick}
                disabled={refreshLoading || !refreshAllowed}
                className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-all flex items-center gap-2 ${
                  refreshLoading || !refreshAllowed
                    ? darkMode
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : darkMode
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
                }`}
              >
                {refreshLoading ? (
                  <>
                    <LoadingSpinner size="sm" variant="spinner" />
                    <span>Refreshing…</span>
                  </>
                ) : (
                  <>
                    <span>🔄</span>
                    <span>Refresh Suggestions</span>
                  </>
                )}
              </motion.button>
            </div>
            {statusLoading && (
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" variant="spinner" />
                <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Loading status...
                </span>
              </div>
            )}
            {!statusLoading && !refreshAllowed && nextRefreshAt && (
              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                Available after {new Date(nextRefreshAt).toLocaleString()}
              </span>
            )}
            {!statusLoading && analysisRun && (
              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                Last run {new Date(analysisRun.finished_at ?? analysisRun.started_at).toLocaleString()} ({analysisRun.status})
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Status Tabs - Modern 2025 Design */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['draft', 'refining', 'yaml_generated', 'deployed'] as const).map((status) => (
          <motion.button
            key={status}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelectedStatus(status)}
            className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-all whitespace-nowrap ${
              selectedStatus === status
                ? darkMode
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                : darkMode
                ? 'bg-gray-700/60 hover:bg-gray-600/60 text-gray-300 border border-gray-600/50'
                : 'bg-white/80 hover:bg-white text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
            }`}
          >
            {status === 'draft' && '📝 New'}
            {status === 'refining' && '✏️ Editing'}
            {status === 'yaml_generated' && '✅ Ready'}
            {status === 'deployed' && '🚀 Deployed'}
              <span className="ml-2 opacity-70">
              ({suggestions.filter(s => s.status === status).length})
            </span>
          </motion.button>
        ))}
      </div>

      {/* Info Banner - Glassmorphism */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-4 ${darkMode ? 'bg-blue-900/40 border-blue-700/50' : 'bg-blue-50/80 border-blue-200/50'} border backdrop-blur-sm shadow-lg`}
      >
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
            <strong>New!</strong> Edit suggestions with natural language. Say "Make it blue" or "Only on weekdays" 
            to customize automations without touching YAML code. We'll generate the code when you approve.
          </div>
        </div>
      </motion.div>

      {/* Error Display */}
      {error && !loading && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className={`rounded-lg p-6 border ${
            darkMode 
              ? 'bg-red-900/20 border-red-800 text-red-200' 
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h3 className={`font-semibold mb-1 ${darkMode ? 'text-red-200' : 'text-red-900'}`}>
                Failed to Load Suggestions
              </h3>
              <p className={`text-sm mb-4 ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                {error.message}
              </p>
              {error.retryable && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleRetry}
                  className={`px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                    darkMode
                      ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white shadow-lg shadow-red-500/30'
                      : 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg shadow-red-400/30'
                  }`}
                >
                  🔄 Retry {retryCount > 0 && `(Attempt ${retryCount + 1})`}
                </motion.button>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Suggestions List */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid gap-6"
          >
            <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <LoadingSpinner size="lg" variant="spinner" className="mb-4" />
              <p className="text-sm font-medium">Loading suggestions...</p>
            </div>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className={`h-80 rounded-lg animate-pulse ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-gray-200 border border-gray-300'}`}
              />
            ))}
          </motion.div>
        ) : error ? (
          // Show empty state when there's an error and no suggestions
          suggestions.length === 0 ? (
            <motion.div
              key="error-empty-state"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className={`text-center py-16 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
            >
              <div className="text-6xl mb-4">⚠️</div>
              <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Unable to Load Suggestions
              </h3>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} max-w-md mx-auto mb-6`}>
                {error.message || 'An error occurred while loading suggestions. Please check your connection and try again.'}
              </p>
              {error.retryable && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleRetry}
                  className={`px-4 py-2 text-sm rounded-xl font-medium transition-all ${
                    darkMode
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
                  }`}
                >
                  🔄 Retry Loading
                </motion.button>
              )}
            </motion.div>
          ) : null
        ) : (() => {
          // Filter suggestions by selected status
          const filteredSuggestions = suggestions.filter(suggestion => suggestion.status === selectedStatus);
          
          // Show empty state if no suggestions match the selected status
          if (filteredSuggestions.length === 0) {
            const totalSuggestions = suggestions.length;
            const hasOtherStatuses = totalSuggestions > 0;
            
            return (
              <motion.div
                key="empty-state"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`text-center py-16 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
              >
                <div className="text-6xl mb-4">🤖</div>
                <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {selectedStatus === 'draft' && totalSuggestions === 0
                    ? 'No draft suggestions'
                    : `No ${selectedStatus} suggestions`}
                </h3>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} max-w-md mx-auto mb-6`}>
                  {selectedStatus === 'draft' && totalSuggestions === 0 ? (
                    <>
                      {error ? (
                        <>
                          <span className="text-red-500 dark:text-red-400 font-medium">⚠️ {error.message}</span>
                          <br />
                          <span className="text-xs opacity-70 mt-2 block">
                            Suggestions require at least 100 events from Home Assistant. Check that websocket-ingestion is running and writing events to InfluxDB.
                          </span>
                        </>
                      ) : (
                        <>
                          Generate a sample suggestion to try the conversational automation flow.
                          <br />
                          <span className="text-xs opacity-70 mt-2 block">
                            AI will analyze your Home Assistant usage patterns and suggest automations in plain English.
                            <br />
                            <strong className="font-medium">Note:</strong> Requires at least 100 events from Home Assistant to generate suggestions.
                          </span>
                        </>
                      )}
                    </>
                  ) : hasOtherStatuses ? (
                    <>
                      You have {totalSuggestions} suggestion{totalSuggestions !== 1 ? 's' : ''} with other statuses.
                      <br />
                      <span className="text-xs opacity-70 mt-2 block">
                        Switch to another tab above to view them, or generate a new suggestion.
                      </span>
                    </>
                  ) : (
                    `No ${selectedStatus} suggestions found. Try generating a new suggestion or refreshing.`
                  )}
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
                  {selectedStatus === 'draft' && (
                    <motion.button
                      whileHover={loading ? {} : { scale: 1.05 }}
                      whileTap={loading ? {} : { scale: 0.95 }}
                      onClick={generateSampleSuggestion}
                      disabled={loading}
                      className={`px-4 py-2 text-sm rounded-xl font-medium transition-all flex items-center gap-2 ${
                        darkMode
                          ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30 disabled:bg-gray-700 disabled:text-gray-400 disabled:shadow-none'
                          : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30 disabled:bg-gray-300 disabled:text-gray-500 disabled:shadow-none'
                      }`}
                    >
                      {loading ? (
                        <>
                          <LoadingSpinner size="sm" variant="spinner" />
                          <span>Generating...</span>
                        </>
                      ) : (
                        <>
                          <span>🎯</span>
                          <span>Generate Sample Suggestion</span>
                        </>
                      )}
                    </motion.button>
                  )}
                  {hasOtherStatuses && (
                    <button
                      onClick={() => {
                        // Find first tab with suggestions
                        const statuses: Array<'draft' | 'refining' | 'yaml_generated' | 'deployed'> = ['draft', 'refining', 'yaml_generated', 'deployed'];
                        const firstWithSuggestions = statuses.find(s => 
                          suggestions.some(sugg => sugg.status === s)
                        );
                        if (firstWithSuggestions) {
                          setSelectedStatus(firstWithSuggestions);
                        }
                      }}
                      className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
                        darkMode
                          ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                          : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                      }`}
                    >
                      📋 View Other Suggestions
                    </button>
                  )}
                  {!hasOtherStatuses && (
                    <button
                      onClick={handleRefreshClick}
                      disabled={refreshLoading || !refreshAllowed}
                      className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors flex items-center gap-2 ${
                        refreshLoading || !refreshAllowed
                          ? darkMode
                            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                          : darkMode
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : 'bg-blue-500 hover:bg-blue-600 text-white'
                      }`}
                    >
                      {refreshLoading ? (
                        <>
                          <LoadingSpinner size="sm" variant="spinner" />
                          <span>Refreshing...</span>
                        </>
                      ) : (
                        <>
                          <span>🔄</span>
                          <span>Refresh Suggestions</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
                {selectedStatus === 'draft' && totalSuggestions === 0 && (
                  <div className={`mt-8 text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'} max-w-lg mx-auto`}>
                    <p className="mb-2">
                      <strong>💡 How it works:</strong> The AI analyzes your Home Assistant event history to detect patterns
                      and suggests automations that match your usage.
                    </p>
                    <p>
                      <strong>⚡ Quick start:</strong> Click "Generate Sample Suggestion" above to see how the conversational
                      editing flow works, or wait for automatic suggestions from your usage patterns.
                    </p>
                  </div>
                )}
              </motion.div>
            );
          }
          
          // Show filtered suggestions
          return (
            <motion.div 
              key="suggestions-list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid gap-6"
            >
              {filteredSuggestions.map((suggestion) => (
                <ConversationalSuggestionCard
                  key={suggestion.id}
                  suggestion={{
                    ...suggestion,
                    description_only: suggestion.description_only || suggestion.description || '',
                    category: suggestion.category || 'convenience',
                    status: suggestion.status as 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected' | 'pending' | 'approved',
                    refinement_count: suggestion.refinement_count || 0,
                    created_at: suggestion.created_at || new Date().toISOString(),
                    conversation_history: (suggestion.conversation_history || []).map(entry => ({
                      timestamp: entry.timestamp,
                      user_input: entry.user_input,
                      updated_description: entry.updated_description,
                      changes: entry.changes || [],
                      validation: entry.validation && typeof entry.validation === 'object' && 'ok' in entry.validation
                        ? { ok: (entry.validation as any).ok, error: (entry.validation as any).error }
                        : { ok: true }
                    })),
                    device_capabilities: suggestion.device_capabilities && typeof suggestion.device_capabilities === 'object' && 'entity_id' in suggestion.device_capabilities
                      ? suggestion.device_capabilities as any
                      : undefined
                  }}
                  onRefine={handleRefine}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onRedeploy={handleRedeploy}
                  darkMode={darkMode}
                />
              ))}
            </motion.div>
          );
        })()}
      </AnimatePresence>

      {/* Footer Info */}
      <div className={`rounded-lg p-6 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'} border`}>
        <div className={`text-sm space-y-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>
            <strong>💬 How it works:</strong> AI detects patterns in your Home Assistant usage and suggests automations in plain English.
          </p>
          <p>
            <strong>✏️ Natural editing:</strong> Click "Edit" and describe changes like "Make it blue" or "Only on weekdays". We'll handle the technical details.
          </p>
          <p>
            <strong>✅ Approve when ready:</strong> Once you're happy with the description, click "Approve & Create" to generate the automation code.
          </p>
          <p className="text-xs opacity-70">
            💰 Cost: ~$0.0004 per suggestion (~$0.12/month for 10 suggestions/day)
          </p>
        </div>
      </div>
      </div>
    </>
  );
};

