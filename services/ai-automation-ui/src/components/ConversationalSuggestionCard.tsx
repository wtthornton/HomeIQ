/**
 * Conversational Suggestion Card - Story AI1.23 Phase 5
 * 
 * Description-first UI with natural language editing.
 * No YAML shown until after approval!
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { getButtonStyles } from '../utils/designSystem';

interface DeviceInfo {
  friendly_name: string;
  entity_id: string;
  domain?: string;
}

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
  device_info?: DeviceInfo[]; // List of devices involved in the suggestion
  automation_yaml?: string | null;
  created_at: string;
}

interface Props {
  suggestion: ConversationalSuggestion;
  onRefine: (id: number, userInput: string) => Promise<void>;
  onApprove: (id: number) => Promise<void>;
  onReject: (id: number) => Promise<void>;
  onTest?: (id: number) => Promise<void>;
  onRedeploy?: (id: number) => Promise<void>;
  darkMode?: boolean;
  disabled?: boolean;
  tested?: boolean;
}

export const ConversationalSuggestionCard: React.FC<Props> = ({
  suggestion,
  onRefine,
  onApprove,
  onReject,
  onTest,
  onRedeploy,
  darkMode = false,
  disabled = false,
  tested = false
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

  const handleTest = async () => {
    if (!onTest) return;
    
    try {
      await onTest(suggestion.id);
      toast.success('✅ Automation validated successfully!');
    } catch (error) {
      toast.error('❌ Validation failed');
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
      className="rounded-lg border overflow-hidden shadow-lg"
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
        border: '1px solid rgba(51, 65, 85, 0.5)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(59, 130, 246, 0.2)'
      }}
    >
      {/* Header */}
      <div className="p-4" style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(51, 65, 85, 0.6) 100%)',
        borderBottom: '1px solid rgba(51, 65, 85, 0.5)'
      }}>
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <motion.span
                animate={{ rotate: [0, -10, 10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                className="text-lg"
              >
                💡
              </motion.span>
              <h3 className="ds-title-card" style={{ color: '#ffffff', fontSize: '0.95rem' }}>
                {suggestion.title.toUpperCase()}
              </h3>
            </div>
            
            {/* Status Badge */}
            <div className="flex gap-1.5 items-center flex-wrap">
              {suggestion.category && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor()}`}>
                  {getCategoryIcon()} {suggestion.category}
                </span>
              )}
              
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
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
              
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
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
        <div className="ds-text-body text-sm leading-relaxed p-3 rounded-lg border mt-2" style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          color: '#cbd5e1'
        }}>
          {suggestion.description_only || 'No description available'}
        </div>
        
        {/* Device Information Buttons */}
        {suggestion.device_info && suggestion.device_info.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 items-center">
            <span className="text-xs opacity-70" style={{ color: '#94a3b8' }}>
              Devices:
            </span>
            {suggestion.device_info.map((device, idx) => {
              // Generate Home Assistant entity URL
              // Default to localhost if env var not set, or use environment variable
              const haBaseUrl = import.meta.env.VITE_HA_URL || 'http://192.168.1.86:8123';
              const haUrl = `${haBaseUrl}/config/entities/${encodeURIComponent(device.entity_id)}`;
              
              return (
                <a
                  key={idx}
                  href={haUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs px-2 py-0.5 rounded-md font-medium transition-all hover:scale-105"
                  style={{
                    background: 'rgba(59, 130, 246, 0.2)',
                    border: '1px solid rgba(59, 130, 246, 0.4)',
                    color: '#93c5fd',
                    textDecoration: 'none'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)';
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.6)';
                    e.currentTarget.style.color = '#bfdbfe';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)';
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.4)';
                    e.currentTarget.style.color = '#93c5fd';
                  }}
                  title={`View ${device.friendly_name} details (${device.entity_id})`}
                >
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {device.friendly_name}
                  </span>
                </a>
              );
            })}
          </div>
        )}
        
        {suggestion.conversation_history && suggestion.conversation_history.length > 0 && (
          <div className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
            Based on {suggestion.conversation_history.length} edit{suggestion.conversation_history.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Device Capabilities (Expandable) */}
        {suggestion.device_capabilities && suggestion.device_capabilities.friendly_capabilities && suggestion.device_capabilities.friendly_capabilities.length > 0 && (
          <div>
            <button
              onClick={() => setShowCapabilities(!showCapabilities)}
              className="w-full text-left px-3 py-1.5 rounded-lg font-medium transition-all text-sm"
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
                  className="mt-2 p-4 rounded-lg border"
                  style={{
                    background: 'rgba(30, 58, 138, 0.2)',
                    borderColor: 'rgba(59, 130, 246, 0.3)'
                  }}
                >
                  <ul className="space-y-2 text-sm">
                    {suggestion.device_capabilities.friendly_capabilities.map((cap, idx) => (
                      <li key={idx} className="flex items-start gap-2" style={{ color: '#93c5fd' }}>
                        <span style={{ color: '#60a5fa' }}>•</span>
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs italic" style={{ color: '#bfdbfe' }}>
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
              className="w-full text-left px-3 py-1.5 rounded-lg font-medium transition-all text-sm"
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
                  className="w-full p-3 rounded-lg border-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  style={{
                    background: 'rgba(30, 41, 59, 0.6)',
                    borderColor: 'rgba(51, 65, 85, 0.5)',
                    color: '#ffffff'
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                    e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-1.5">
                  <button
                    onClick={handleRefine}
                    disabled={isRefining || !editInput.trim()}
                    style={getButtonStyles(isRefining || !editInput.trim() ? 'secondary' : 'primary', { flex: 1 })}
                    className={isRefining || !editInput.trim() ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {isRefining ? (
                      <>
                        <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>UPDATING...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>UPDATE DESCRIPTION</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    style={getButtonStyles('secondary')}
                  >
                    CANCEL
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-1.5 flex-wrap items-center">
                {/* Test Button */}
                {onTest && (
                  <button
                    onClick={handleTest}
                    disabled={disabled || tested}
                    style={getButtonStyles(disabled || tested ? 'secondary' : 'primary', {
                      background: disabled || tested ? undefined : 'linear-gradient(to right, #f59e0b, #d97706)',
                      boxShadow: disabled || tested ? undefined : '0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                    })}
                    className={disabled || tested ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {tested ? (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>TESTED</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>TEST</span>
                      </>
                    )}
                  </button>
                )}

                {/* Approve Button */}
                <button
                  onClick={handleApprove}
                  disabled={disabled}
                  style={getButtonStyles(disabled ? 'secondary' : 'primary', {
                    flex: 1,
                    minWidth: '120px',
                    maxWidth: '200px',
                    background: disabled ? undefined : 'linear-gradient(to right, #10b981, #059669)',
                    boxShadow: disabled ? undefined : '0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                  })}
                  className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  {disabled ? (
                    <>
                      <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>PROCESSING...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>APPROVE & CREATE</span>
                    </>
                  )}
                </button>

                {/* Edit Button */}
                <button
                  onClick={() => setIsEditing(true)}
                  disabled={disabled}
                  style={getButtonStyles(disabled ? 'secondary' : 'primary')}
                  className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>EDIT</span>
                </button>

                {/* Reject Button */}
                <button
                  onClick={() => onReject(suggestion.id)}
                  disabled={disabled}
                  style={getButtonStyles('secondary')}
                  className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span>NOT INTERESTED</span>
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
              className="w-full text-left px-3 py-1.5 rounded-lg font-medium transition-all text-sm"
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
                  <pre className="mt-2 p-4 rounded-lg text-xs overflow-x-auto overflow-y-auto max-h-96 font-mono border" style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    borderColor: 'rgba(51, 65, 85, 0.5)',
                    color: '#10b981'
                  }}>
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
            className="w-full px-3 py-0.5 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-medium rounded-lg transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-1.5 text-xs"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Deploy to Home Assistant</span>
          </button>
        )}

        {/* Re-deploy Button (for deployed suggestions) */}
        {suggestion.status === 'deployed' && onRedeploy && (
          <button
            onClick={() => onRedeploy(suggestion.id)}
            disabled={disabled}
            className={`w-full px-3 py-0.5 font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-md text-xs ${
              disabled
                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-lg'
            }`}
          >
            {disabled ? (
              <>
                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Re-deploying...</span>
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>RE-DEPLOY WITH UPDATED YAML</span>
              </>
            )}
          </button>
        )}

        {/* Metadata Footer */}
        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} pt-2 mt-2 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between">
            <span>Created: {new Date(suggestion.created_at).toLocaleString()}</span>
            <span>ID: #{suggestion.id}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

