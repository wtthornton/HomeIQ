/**
 * Beautiful Suggestion Card Component
 * Displays AI-generated automation suggestions with swipe-to-approve
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import type { Suggestion } from '../types';
import { ConfidenceMeter } from './ConfidenceMeter';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
  onEdit?: (id: number) => void;
  onDeploy?: (id: number) => void;
  darkMode?: boolean;
  isSelected?: boolean;
}

export const SuggestionCard: React.FC<SuggestionCardProps> = ({
  suggestion,
  onApprove,
  onReject,
  onEdit,
  onDeploy,
  darkMode = false,
  isSelected = false
}) => {
  const [showYaml, setShowYaml] = useState(false);
  const createdAtLabel = suggestion.created_at
    ? new Date(suggestion.created_at).toLocaleString()
    : 'Unknown';

  const getCategoryColor = () => {
    const colors = {
      energy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-300 dark:border-green-700',
      comfort: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border-blue-300 dark:border-blue-700',
      security: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 border-red-300 dark:border-red-700',
      convenience: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 border-purple-300 dark:border-purple-700',
    };
    return colors[suggestion.category || 'convenience'];
  };

  const getCategoryIcon = () => {
    const icons = {
      energy: '🌱',
      comfort: '💙',
      security: '🔐',
      convenience: '✨',
    };
    return icons[suggestion.category || 'convenience'];
  };


  return (
    <motion.div
      data-testid="suggestion-card"
      data-id={suggestion.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`border overflow-hidden transition-all rounded-xl ${
        isSelected
          ? darkMode
            ? 'bg-gradient-to-br from-blue-900/60 to-purple-900/60 border-blue-500/50 ring-1 ring-blue-500/50 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
            : 'bg-gradient-to-br from-blue-50 to-purple-50 border-blue-400/50 ring-1 ring-blue-400/50 shadow-xl shadow-blue-100/50'
          : darkMode
          ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
          : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
      }`}
    >
      {/* Header with Category Badge - Glassmorphism */}
      <div className={`p-4 ${darkMode ? 'bg-slate-800/60 backdrop-blur-sm' : 'bg-gradient-to-r from-blue-50/80 to-purple-50/80 backdrop-blur-sm'}`}>
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1">
            <h3 className={`text-lg font-bold mb-1.5 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {suggestion.title}
            </h3>
            <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {suggestion.description}
            </p>
          </div>
          
          <div className="ml-3 flex flex-col gap-1.5 items-end">
            {suggestion.category && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getCategoryColor()}`}>
                {getCategoryIcon()} {suggestion.category}
              </span>
            )}
          </div>
        </div>

        {/* Enhanced Confidence Meter - Integrated display */}
        <ConfidenceMeter 
          confidence={suggestion.confidence} 
          darkMode={darkMode}
          variant="standard"
          accessibility={true}
        />
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* YAML Preview */}
        <div>
          <button
            onClick={() => setShowYaml(!showYaml)}
            className={`w-full text-left px-3 py-1.5 rounded-xl font-medium transition-all text-xs ${
              darkMode
                ? 'bg-slate-800/60 hover:bg-slate-700/60 text-white border border-slate-700/50'
                : 'bg-white/80 hover:bg-white text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
            }`}
          >
            <span className="flex items-center justify-between">
              <span>
                {showYaml ? '▼' : '▶'} Home Assistant Automation
              </span>
              <span className="text-xs opacity-70">
                {showYaml ? 'Hide' : 'Show'} YAML
              </span>
            </span>
          </button>

          {showYaml && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <pre className={`mt-2 p-4 rounded-xl text-xs overflow-x-auto overflow-y-auto max-h-96 font-mono ${
                darkMode ? 'bg-slate-900/60 text-green-400 backdrop-blur-sm border border-slate-700/50' : 'bg-white/80 text-gray-800 backdrop-blur-sm border border-gray-200/50'
              }`}>
                {suggestion.automation_yaml}
              </pre>
            </motion.div>
          )}
        </div>

        {/* Enhanced Action Buttons */}
        {suggestion.status === 'pending' && onApprove && onReject && (
          <div className="flex gap-1.5 flex-wrap">
            {/* Approve Button */}
            <button
              data-testid="approve-button"
              onClick={() => onApprove(suggestion.id)}
              className="flex-1 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium transition-colors flex items-center justify-center gap-1.5 min-w-[100px]"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Approve</span>
            </button>

            {/* Edit Button (Optional) */}
            {onEdit && (
              <button
                data-testid="edit-button"
                onClick={() => onEdit(suggestion.id)}
                className={`px-3 py-1 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                  darkMode
                    ? 'bg-slate-800/60 hover:bg-slate-700/60 text-white border border-slate-700/50'
                    : 'bg-white/80 hover:bg-white text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span>Edit</span>
              </button>
            )}

            {/* Reject Button */}
            <button
              data-testid="reject-button"
              onClick={() => onReject(suggestion.id)}
              className="flex-1 px-3 py-1 rounded-xl text-white text-xs font-medium transition-all flex items-center justify-center gap-1.5 min-w-[100px] bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 shadow-lg shadow-red-500/30"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>Reject</span>
            </button>
          </div>
        )}

        {/* Deploy Button */}
        {suggestion.status === 'approved' && onDeploy && (
          <button
            data-testid={`deploy-${suggestion.id}`}
            onClick={() => onDeploy(suggestion.id)}
            className="w-full px-3 py-1.5 rounded-xl text-white text-xs font-medium transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg shadow-blue-500/30"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Deploy to Home Assistant</span>
          </button>
        )}

        {/* Status Badge for deployed/rejected */}
        {(suggestion.status === 'deployed' || suggestion.status === 'rejected') && (
          <div className={`text-center py-2 rounded-xl font-medium text-sm ${
            suggestion.status === 'deployed' 
              ? darkMode
                ? 'bg-gradient-to-r from-blue-600/30 to-purple-600/30 text-blue-200 border border-blue-500/50 backdrop-blur-sm'
                : 'bg-gradient-to-r from-blue-50 to-purple-50 text-blue-800 border border-blue-200/50'
              : darkMode
              ? 'bg-slate-800/60 text-gray-200 border border-slate-700/50 backdrop-blur-sm'
              : 'bg-white/80 text-gray-800 border border-gray-200/50'
          }`}>
            {suggestion.status === 'deployed' && '🚀 Deployed to Home Assistant'}
            {suggestion.status === 'rejected' && '❌ Rejected'}
          </div>
        )}

        {/* Metadata Footer */}
        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} pt-2 mt-2 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between">
            <span>Created: {createdAtLabel}</span>
            <span>ID: #{suggestion.id}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

