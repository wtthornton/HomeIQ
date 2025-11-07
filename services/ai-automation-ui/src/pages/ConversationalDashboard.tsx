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

export const ConversationalDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'refining' | 'yaml_generated' | 'deployed'>('draft');
  const [processingRedeploy, setProcessingRedeploy] = useState<number | null>(null);
  const [refreshAllowed, setRefreshAllowed] = useState(true);
  const [nextRefreshAt, setNextRefreshAt] = useState<string | null>(null);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [analysisRun, setAnalysisRun] = useState<{ status: string; started_at: string; finished_at: string | null } | null>(null);

  const loadSuggestions = async () => {
    try {
      setLoading(true);
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
        let friendlyDescription = suggestion.description;
        
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
        
        const mapped = {
          ...suggestion,
          title: friendlyTitle,
          description: friendlyDescription,
          description_only: friendlyDescription, // Map description to description_only
          refinement_count: 0, // Default value
          conversation_history: [], // Default empty array
          device_capabilities: {} // Default empty object
        };
        console.log('Mapped suggestion:', mapped);
        return mapped;
      });
      console.log('All mapped suggestions:', mappedSuggestions);
      setSuggestions(mappedSuggestions);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      toast.error('Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  };

  const loadRefreshStatus = async () => {
    try {
      const status = await api.getRefreshStatus();
      setRefreshAllowed(status.allowed);
      setNextRefreshAt(status.next_allowed_at);
    } catch (error) {
      console.error('Failed to load refresh status', error);
    }
  };

  const loadAnalysisStatus = async () => {
    try {
      const status = await api.getAnalysisStatus();
      setAnalysisRun(status.analysis_run ?? null);
    } catch (error) {
      console.error('Failed to load analysis status', error);
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
      
      const suggestion = {
        id: id,
        suggestion_id: suggestionId,
        title: `Automation: ${response.devices_involved?.[0]?.friendly_name || 'Living Room Light'}`,
        description: response.description || '',
        description_only: response.description || '',
        trigger_summary: response.trigger_summary || '',
        action_summary: response.action_summary || '',
        devices_involved: response.devices_involved || [],
        confidence: response.confidence || 0.85,
        status: response.status || 'draft',
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
      toast.success(response.message || 'Manual refresh queued');
      await loadRefreshStatus();
    } catch (error) {
      if (error instanceof APIError) {
        toast.error(error.message);
      } else if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error('Failed to queue manual refresh');
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
                status: result.status,
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
                status: result.status,
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
                status: result.status,
                automation_yaml: result.automation_yaml,
                category: result.category || s.category,
                priority: result.priority || s.priority,
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
      {/* Header */}
      <div className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'} pb-4`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              💡 Automation Suggestions
            </h1>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Edit with natural language, approve to create
            </p>
          </div>
          <div className="flex flex-col sm:items-end gap-2">
            <div className="flex items-center gap-2">
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {suggestions.length} suggestions
              </span>
              <button
                onClick={handleRefreshClick}
                disabled={refreshLoading || !refreshAllowed}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1 ${
                  refreshLoading || !refreshAllowed
                    ? darkMode
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                {refreshLoading ? 'Refreshing…' : '🔄 Refresh Suggestions'}
              </button>
            </div>
            {!refreshAllowed && nextRefreshAt && (
              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                Available after {new Date(nextRefreshAt).toLocaleString()}
              </span>
            )}
            {analysisRun && (
              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                Last run {new Date(analysisRun.finished_at ?? analysisRun.started_at).toLocaleString()} ({analysisRun.status})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Status Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['draft', 'refining', 'yaml_generated', 'deployed'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setSelectedStatus(status)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              selectedStatus === status
                ? darkMode
                  ? 'bg-blue-600 text-white'
                  : 'bg-blue-500 text-white'
                : darkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status === 'draft' && '📝 New'}
            {status === 'refining' && '✏️ Editing'}
            {status === 'yaml_generated' && '✅ Ready'}
            {status === 'deployed' && '🚀 Deployed'}
            <span className="ml-2 opacity-70">
              ({suggestions.filter(s => s.status === status).length})
            </span>
          </button>
        ))}
      </div>

      {/* Info Banner */}
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-blue-900/30 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
            <strong>New!</strong> Edit suggestions with natural language. Say "Make it blue" or "Only on weekdays" 
            to customize automations without touching YAML code. We'll generate the code when you approve.
          </div>
        </div>
      </div>

      {/* Suggestions List */}
      <AnimatePresence mode="wait">
        {loading ? (
          <div className="grid gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className={`h-80 rounded-lg animate-pulse ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`}
              />
            ))}
          </div>
        ) : (() => {
          // Filter suggestions by selected status
          const filteredSuggestions = suggestions.filter(suggestion => suggestion.status === selectedStatus);
          
          // Show empty state if no suggestions match the selected status
          if (filteredSuggestions.length === 0) {
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
                  No {selectedStatus} suggestions
                </h3>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} max-w-md mx-auto mb-6`}>
                  {selectedStatus === 'draft'
                    ? 'Generate a sample suggestion to try the conversational automation flow'
                    : suggestions.length > 0
                    ? `You have ${suggestions.length} suggestion(s) with other statuses. Switch tabs to view them.`
                    : `No ${selectedStatus} suggestions found`}
                </p>
                {selectedStatus === 'draft' && (
                  <button
                    onClick={generateSampleSuggestion}
                    disabled={loading}
                    className={`px-4 py-2 text-xs rounded-lg font-medium transition-colors ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
                        : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300'
                    }`}
                  >
                    {loading ? 'Generating...' : '🎯 Generate Sample Suggestion'}
                  </button>
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
                  suggestion={suggestion}
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

