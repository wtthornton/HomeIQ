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
      className={`border overflow-hidden transition-all ${
        isSelected
          ? darkMode
            ? 'bg-blue-900 border-blue-500 ring-1 ring-blue-500'
            : 'bg-blue-50 border-blue-400 ring-1 ring-blue-400'
          : darkMode
          ? 'bg-gray-800 border-gray-700'
          : 'bg-white border-gray-200'
      }`}
    >
      {/* Header with Category Badge */}
      <div className={`p-6 ${darkMode ? 'bg-gray-750' : 'bg-gradient-to-r from-blue-50 to-purple-50'}`}>
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {suggestion.title}
            </h3>
            <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {suggestion.description}
            </p>
          </div>
          
          <div className="ml-4 flex flex-col gap-2 items-end">
            {suggestion.category && (
              <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getCategoryColor()}`}>
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
      <div className="p-6 space-y-4">
        {/* YAML Preview */}
        <div>
          <button
            onClick={() => setShowYaml(!showYaml)}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-all ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
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
              <pre className={`mt-2 p-4 rounded-lg text-xs overflow-x-auto overflow-y-auto max-h-96 font-mono ${
                darkMode ? 'bg-gray-900 text-green-400' : 'bg-gray-50 text-gray-800'
              } border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                {suggestion.automation_yaml}
              </pre>
            </motion.div>
          )}
        </div>

        {/* Enhanced Action Buttons */}
        {suggestion.status === 'pending' && onApprove && onReject && (
          <div className="flex gap-3">
            {/* Approve Button */}
            <button
              data-testid="approve-button"
              onClick={() => onApprove(suggestion.id)}
              className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium transition-colors flex items-center justify-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Approve</span>
            </button>

            {/* Edit Button (Optional) */}
            {onEdit && (
              <button
                data-testid="edit-button"
                onClick={() => onEdit(suggestion.id)}
                className={`px-3 py-2 text-sm font-medium transition-colors flex items-center justify-center gap-1 ${
                  darkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span>Edit</span>
              </button>
            )}

            {/* Reject Button */}
            <button
              data-testid="reject-button"
              onClick={() => onReject(suggestion.id)}
              className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors flex items-center justify-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Deploy to Home Assistant</span>
          </button>
        )}

        {/* Status Badge for deployed/rejected */}
        {(suggestion.status === 'deployed' || suggestion.status === 'rejected') && (
          <div className={`text-center py-3 rounded-lg font-semibold ${
            suggestion.status === 'deployed' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' :
            'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
          }`}>
            {suggestion.status === 'deployed' && '🚀 Deployed to Home Assistant'}
            {suggestion.status === 'rejected' && '❌ Rejected'}
          </div>
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

