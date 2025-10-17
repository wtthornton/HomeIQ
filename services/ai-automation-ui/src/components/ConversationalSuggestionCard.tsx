/**
 * Conversational Suggestion Card - Story AI1.23 Phase 5
 * 
 * Description-first UI with natural language editing.
 * No YAML shown until after approval!
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

interface ConversationalSuggestion {
  id: number;
  description_only: string;
  title: string;
  category: string;
  confidence: number;
  status: 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected';
  refinement_count: number;
  conversation_history: Array<{
    timestamp: string;
    user_input: string;
    updated_description: string;
    changes: string[];
    validation: { ok: boolean; error?: string };
  }>;
  device_capabilities?: {
    entity_id: string;
    friendly_name: string;
    domain: string;
    supported_features?: Record<string, boolean>;
    friendly_capabilities?: string[];
  };
  automation_yaml?: string | null;
  created_at: string;
}

interface Props {
  suggestion: ConversationalSuggestion;
  onRefine: (id: number, userInput: string) => Promise<void>;
  onApprove: (id: number) => Promise<void>;
  onReject: (id: number) => Promise<void>;
  darkMode?: boolean;
}

export const ConversationalSuggestionCard: React.FC<Props> = ({
  suggestion,
  onRefine,
  onApprove,
  onReject,
  darkMode = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editInput, setEditInput] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showCapabilities, setShowCapabilities] = useState(false);
  const [showYaml, setShowYaml] = useState(false);

  const getCategoryColor = () => {
    const colors = {
      energy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      comfort: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      security: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      convenience: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    };
    return colors[suggestion.category as keyof typeof colors] || colors.convenience;
  };

  const getCategoryIcon = () => {
    const icons = {
      energy: '🌱',
      comfort: '💙',
      security: '🔐',
      convenience: '✨',
    };
    return icons[suggestion.category as keyof typeof icons] || '✨';
  };

  const handleRefine = async () => {
    if (!editInput.trim()) {
      toast.error('Please enter your changes');
      return;
    }

    setIsRefining(true);
    try {
      await onRefine(suggestion.id, editInput);
      setEditInput('');
      toast.success('✅ Description updated!');
    } catch (error) {
      toast.error('❌ Failed to refine suggestion');
    } finally {
      setIsRefining(false);
    }
  };

  const handleApprove = async () => {
    try {
      await onApprove(suggestion.id);
      toast.success('✅ Automation created successfully!');
    } catch (error) {
      toast.error('❌ Failed to create automation');
    }
  };

  const isApproved = suggestion.status === 'yaml_generated' || suggestion.status === 'deployed';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border overflow-hidden ${
        darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
    >
      {/* Header */}
      <div className={`p-6 ${darkMode ? 'bg-gray-750' : 'bg-gradient-to-r from-blue-50 to-purple-50'}`}>
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">💡</span>
              <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {suggestion.title}
              </h3>
            </div>
            
            {/* Status Badge */}
            <div className="flex gap-2 items-center">
              {suggestion.category && (
                <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getCategoryColor()}`}>
                  {getCategoryIcon()} {suggestion.category}
                </span>
              )}
              
              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                suggestion.status === 'draft' ? 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300' :
                suggestion.status === 'refining' ? 'bg-yellow-200 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                suggestion.status === 'yaml_generated' ? 'bg-green-200 text-green-800 dark:bg-green-900 dark:text-green-200' :
                'bg-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
              }`}>
                {suggestion.status === 'draft' && '📝 New'}
                {suggestion.status === 'refining' && `✏️ ${suggestion.refinement_count} edit${suggestion.refinement_count > 1 ? 's' : ''}`}
                {suggestion.status === 'yaml_generated' && '✅ Ready'}
                {suggestion.status === 'deployed' && '🚀 Deployed'}
              </span>
              
              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                suggestion.confidence >= 0.9 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                suggestion.confidence >= 0.7 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
              }`}>
                {Math.round(suggestion.confidence * 100)}% confident
              </span>
            </div>
          </div>
        </div>

        {/* Main Description (NO YAML!) */}
        <div className={`text-base leading-relaxed ${darkMode ? 'text-gray-200' : 'text-gray-800'} bg-white/50 dark:bg-gray-900/50 p-4 rounded-lg border ${darkMode ? 'border-gray-600' : 'border-gray-300'}`}>
          {suggestion.description_only}
        </div>
        
        {suggestion.conversation_history && suggestion.conversation_history.length > 0 && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Based on {suggestion.conversation_history.length} edit{suggestion.conversation_history.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-6 space-y-4">
        {/* Device Capabilities (Expandable) */}
        {suggestion.device_capabilities && suggestion.device_capabilities.friendly_capabilities && suggestion.device_capabilities.friendly_capabilities.length > 0 && (
          <div>
            <button
              onClick={() => setShowCapabilities(!showCapabilities)}
              className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-all ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-blue-50 hover:bg-blue-100 text-blue-900'
              }`}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showCapabilities ? '▼' : '▶'}</span>
                  <span>💡 This device can also...</span>
                </span>
                <span className="text-xs opacity-70">
                  {suggestion.device_capabilities.friendly_capabilities.length} features
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showCapabilities && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`mt-2 p-4 rounded-lg ${darkMode ? 'bg-blue-900/30' : 'bg-blue-50'} border ${darkMode ? 'border-blue-800' : 'border-blue-200'}`}
                >
                  <ul className="space-y-2 text-sm">
                    {suggestion.device_capabilities.friendly_capabilities.map((cap, idx) => (
                      <li key={idx} className={`flex items-start gap-2 ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
                        <span className="text-blue-500">•</span>
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                  <p className={`mt-3 text-xs italic ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
                    Try saying: "Make it blue" or "Set to 75% brightness" or "Only on weekdays"
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Conversation History (Expandable) */}
        {suggestion.conversation_history && suggestion.conversation_history.length > 0 && (
          <div>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-all ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
              }`}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showHistory ? '▼' : '▶'}</span>
                  <span>📝 Edit History</span>
                </span>
                <span className="text-xs opacity-70">
                  {suggestion.conversation_history.length} edit{suggestion.conversation_history.length > 1 ? 's' : ''}
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showHistory && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-2 space-y-2"
                >
                  {suggestion.conversation_history.map((entry, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'} border ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}
                    >
                      <div className="flex items-start gap-2 mb-1">
                        <span className="text-sm font-medium text-blue-500">You said:</span>
                        <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          "{entry.user_input}"
                        </span>
                      </div>
                      {entry.changes && entry.changes.length > 0 && (
                        <div className="mt-2 text-xs space-y-1">
                          {entry.changes.map((change, changeIdx) => (
                            <div key={changeIdx} className={`flex items-start gap-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              <span className="text-green-500">✓</span>
                              <span>{change}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {entry.validation && !entry.validation.ok && entry.validation.error && (
                        <div className="mt-2 text-xs text-yellow-600 dark:text-yellow-400">
                          ⚠️ {entry.validation.error}
                        </div>
                      )}
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Natural Language Edit Mode */}
        {!isApproved && (
          <div>
            {isEditing ? (
              <div className="space-y-3">
                <textarea
                  value={editInput}
                  onChange={(e) => setEditInput(e.target.value)}
                  placeholder="Describe your changes... (e.g., 'Make it blue and only on weekdays')"
                  className={`w-full p-4 rounded-lg border-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    darkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                  }`}
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleRefine}
                    disabled={isRefining || !editInput.trim()}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {isRefining ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>Updating...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>Update Description</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className={`px-4 py-2 font-medium rounded-lg transition-colors ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-white'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                    }`}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                {/* Approve Button */}
                <button
                  onClick={handleApprove}
                  className="flex-1 px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Approve & Create</span>
                </button>

                {/* Edit Button */}
                <button
                  onClick={() => setIsEditing(true)}
                  className={`px-4 py-3 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-md hover:shadow-lg ${
                    darkMode
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-blue-500 hover:bg-blue-600 text-white'
                  }`}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>Edit</span>
                </button>

                {/* Reject Button */}
                <button
                  onClick={() => onReject(suggestion.id)}
                  className="px-4 py-3 bg-gray-300 hover:bg-gray-400 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span>Not Interested</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* YAML Preview (Only shown after approval) */}
        {isApproved && suggestion.automation_yaml && (
          <div>
            <button
              onClick={() => setShowYaml(!showYaml)}
              className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-all ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
              }`}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showYaml ? '▼' : '▶'}</span>
                  <span>🔧 Home Assistant YAML</span>
                </span>
                <span className="text-xs opacity-70">
                  {showYaml ? 'Hide' : 'Show'} code
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showYaml && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <pre className={`mt-2 p-4 rounded-lg text-xs overflow-x-auto font-mono ${
                    darkMode ? 'bg-gray-900 text-green-400' : 'bg-gray-50 text-gray-800'
                  } border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                    {suggestion.automation_yaml}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Deploy Button (after YAML generated) */}
        {suggestion.status === 'yaml_generated' && (
          <button
            className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-bold rounded-lg transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Deploy to Home Assistant</span>
          </button>
        )}

        {/* Metadata Footer */}
        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} pt-3 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between">
            <span>Created: {new Date(suggestion.created_at).toLocaleString()}</span>
            <span>ID: #{suggestion.id}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

