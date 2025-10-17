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
import api from '../services/api';

export const ConversationalDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'refining' | 'yaml_generated' | 'deployed'>('draft');

  const loadSuggestions = async () => {
    try {
      setLoading(true);
      // For now, return empty list since we don't have the list endpoint yet
      // TODO: Implement GET /api/v1/suggestions endpoint
      setSuggestions([]);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      toast.error('Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  };

  const generateSampleSuggestion = async () => {
    try {
      setLoading(true);
      const response = await api.generateSuggestion(
        1,
        'time_of_day',
        'light.living_room',
        { hour: 18, confidence: 0.85 }
      );
      
      // Convert API response to suggestion format
      const suggestion = {
        id: parseInt(response.suggestion_id.split('-')[1]),
        suggestion_id: response.suggestion_id,
        description_only: response.description,
        trigger_summary: response.trigger_summary,
        action_summary: response.action_summary,
        devices_involved: response.devices_involved,
        confidence: response.confidence,
        status: response.status,
        created_at: response.created_at,
        conversation_history: [],
        refinement_count: 0,
        device_capabilities: {}
      };
      
      setSuggestions([suggestion]);
      toast.success('✅ Generated sample suggestion!');
    } catch (error) {
      console.error('Failed to generate suggestion:', error);
      toast.error('Failed to generate suggestion');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuggestions();
    const interval = setInterval(loadSuggestions, 30000);
    return () => clearInterval(interval);
  }, [selectedStatus]);

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
                yaml_generated_at: new Date().toISOString()
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
    <div className="space-y-6">
      {/* Header */}
      <div className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'} pb-4`}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              💡 Automation Suggestions
            </h1>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Edit with natural language, approve to create
            </p>
          </div>
          <div className="text-sm text-gray-500">
            {suggestions.length} suggestions
          </div>
        </div>
      </div>

      {/* Status Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['draft', 'refining', 'yaml_generated', 'deployed'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setSelectedStatus(status)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
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
        ) : suggestions.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`text-center py-16 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            <div className="text-6xl mb-4">🤖</div>
            <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              No {selectedStatus} suggestions
            </h3>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} max-w-md mx-auto mb-6`}>
              {selectedStatus === 'draft'
                ? 'Generate a sample suggestion to try the conversational automation flow'
                : `No ${selectedStatus} suggestions found`}
            </p>
            {selectedStatus === 'draft' && (
              <button
                onClick={generateSampleSuggestion}
                disabled={loading}
                className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
                    : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300'
                }`}
              >
                {loading ? 'Generating...' : '🎯 Generate Sample Suggestion'}
              </button>
            )}
          </motion.div>
        ) : (
          <div className="grid gap-6">
            {suggestions.map((suggestion) => (
              <ConversationalSuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onRefine={handleRefine}
                onApprove={handleApprove}
                onReject={handleReject}
                darkMode={darkMode}
              />
            ))}
          </div>
        )}
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
  );
};

