/**
 * Conversational Dashboard - Story AI1.23 Phase 5
 * 
 * Description-first UI for automation suggestions.
 * Users edit with natural language, approve to generate YAML.
 */

import React, { useState } from 'react';
// React Query handles data fetching, caching, and polling (see useSuggestions hook)
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store';
import { ConversationalSuggestionCard } from '../components/ConversationalSuggestionCard';
import api from '../services/api';
import { ProcessLoader } from '../components/ask-ai/ReverseEngineeringLoader';
import { LoadingSpinner } from '../components/LoadingSpinner';
import type { Suggestion } from '../types';
import { useSuggestions, useRefreshStatus, useAnalysisStatus } from '../hooks/useSuggestions';

export const ConversationalDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  const queryClient = useQueryClient();

  // React Query: suggestions, refresh status, analysis status
  const {
    data: suggestions = [],
    isLoading: loading,
    error: suggestionsError,
    refetch: refetchSuggestions,
  } = useSuggestions();
  const {
    data: refreshStatusData,
    isLoading: refreshStatusLoading,
  } = useRefreshStatus();
  const {
    data: analysisRun,
    isLoading: analysisStatusLoading,
  } = useAnalysisStatus();

  const refreshAllowed = refreshStatusData?.allowed ?? true;
  const nextRefreshAt = refreshStatusData?.nextAllowedAt ?? null;
  const statusLoading = refreshStatusLoading || analysisStatusLoading;

  // Local UI state (not fetched from API)
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'refining' | 'yaml_generated' | 'deployed'>('draft');
  const [processingRedeploy, setProcessingRedeploy] = useState<number | null>(null);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [refreshError, setRefreshError] = useState<{ message: string; code?: string; retryable?: boolean } | null>(null);

  // Derived error state: React Query fetch errors + refresh-specific errors
  const error = refreshError ?? (suggestionsError ? {
    message: (suggestionsError as Error).message || 'Failed to load suggestions',
    retryable: true,
  } : null);

  // React Query handles initial fetch, retries, and polling (refetchInterval: 30s)
  const handleRetry = () => {
    refetchSuggestions();
  };

  const generateSampleSuggestion = async () => {
    try {
      const response = await api.generateSuggestion(
        undefined,
        'time_of_day',
        'light.living_room',
        { hour: 18, confidence: 0.85, occurrences: 20 }
      );

      void response; // API call triggers server-side creation
      setSelectedStatus('draft');
      toast.success('Generated sample suggestion!');
      refetchSuggestions();
    } catch (error: any) {
      console.error('Failed to generate suggestion:', error);
      const errorMessage = error?.message || error?.toString() || 'Unknown error';
      toast.error(`Failed to generate suggestion: ${errorMessage}`);
    }
  };

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
        setRefreshError({
          message: errorMessage,
          code: response.error_code,
          retryable: response.error_code !== 'VALIDATION_ERROR'
        });
      } else if (response.success) {
        toast.success(response.message || `Successfully generated ${response.count || 0} suggestions`);
        refetchSuggestions();
        queryClient.invalidateQueries({ queryKey: ['refreshStatus'] });
      } else {
        toast(response.message || 'Refresh completed');
        queryClient.invalidateQueries({ queryKey: ['refreshStatus'] });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate suggestions. Check service health and logs.';
      toast.error(msg);
    } finally {
      setRefreshLoading(false);
    }
  };

  const handleRefine = async (id: number, userInput: string) => {
    try {
      const result = await api.refineSuggestion(id, userInput);
      
      // Update local state
      queryClient.setQueryData<Suggestion[]>(['suggestions'], (prev = []) =>
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
      queryClient.setQueryData<Suggestion[]>(['suggestions'], (prev = []) =>
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
      queryClient.setQueryData<Suggestion[]>(['suggestions'], (prev = []) =>
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

      // Build success message (Story 7: include deploy feedback when present)
      let successMsg = `✅ Re-deployed successfully!\nSafety score: ${result.yaml_validation?.safety_score ?? '—'}/100`;
      if (categoryChanged) {
        successMsg += `\nCategory updated: ${oldSuggestion.category} → ${result.category}`;
      }
      const deployData = result.data ?? result;
      if (deployData?.state) {
        successMsg += `\nStatus: ${deployData.state}`;
      }
      if (deployData?.last_triggered) {
        successMsg += `\nLast triggered: ${deployData.last_triggered}`;
      }
      if (deployData?.verification_warning) {
        successMsg += `\n⚠️ ${deployData.verification_warning}`;
      }

      toast.success(successMsg, { id: `redeploy-${id}`, duration: 6000 });
      
      // Reload suggestions to get fresh data
      refetchSuggestions();
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
      queryClient.setQueryData<Suggestion[]>(['suggestions'], (prev = []) => prev.filter(s => s.id !== id));
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
        className={`p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-teal-900/30 to-cyan-900/30 border border-teal-700/50' : 'bg-gradient-to-br from-teal-50 to-cyan-50 border border-teal-200'} shadow-lg`}
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
                    ? 'bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white shadow-lg shadow-teal-500/30'
                    : 'bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 text-white shadow-lg shadow-teal-400/30'
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
      <div className="flex gap-2 overflow-x-auto pb-2" role="tablist" aria-label="Suggestion status filters">
        {(['draft', 'refining', 'yaml_generated', 'deployed'] as const).map((status) => (
          <motion.button
            key={status}
            role="tab"
            aria-selected={selectedStatus === status}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelectedStatus(status)}
            className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-all whitespace-nowrap ${
              selectedStatus === status
                ? darkMode
                  ? 'bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-lg shadow-teal-500/30'
                  : 'bg-gradient-to-r from-teal-500 to-cyan-500 text-white shadow-lg shadow-teal-400/30'
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
            <span className="text-2xl">{error.code === 'AUTH_ERROR' ? '🔒' : '⚠️'}</span>
            <div className="flex-1">
              <h3 className={`font-semibold mb-1 ${darkMode ? 'text-red-200' : 'text-red-900'}`}>
                {error.code === 'AUTH_ERROR' ? 'Authentication Error' : 'Failed to Load Suggestions'}
              </h3>
              <p className={`text-sm mb-2 ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                {error.message}
              </p>
              {error.code === 'AUTH_ERROR' && (
                <p className={`text-xs mb-4 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
                  Verify your VITE_API_KEY environment variable is set correctly and the backend accepts it.
                </p>
              )}
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
                  Retry
                </motion.button>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Suggestions List */}
      <div role="tabpanel" aria-label={`${selectedStatus} suggestions`}>
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
                      ? 'bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white shadow-lg shadow-teal-500/30'
                      : 'bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 text-white shadow-lg shadow-teal-400/30'
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
                      No suggestions yet &mdash; we'll suggest automations based on your data.
                      <br />
                      <span className="text-xs opacity-70 mt-2 block">
                        AI analyzes your Home Assistant event history to detect patterns
                        and suggest automations that match your usage.
                        <br />
                        <strong className="font-medium">Note:</strong> Requires at least 100 events from Home Assistant. You can also generate a sample to try the flow.
                      </span>
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
                          ? 'bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white shadow-lg shadow-teal-500/30 disabled:bg-gray-700 disabled:text-gray-400 disabled:shadow-none'
                          : 'bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 text-white shadow-lg shadow-teal-400/30 disabled:bg-gray-300 disabled:text-gray-500 disabled:shadow-none'
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
      </div>

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

