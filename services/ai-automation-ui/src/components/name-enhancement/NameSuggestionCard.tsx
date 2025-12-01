/**
 * Name Suggestion Card Component
 * 
 * Displays name suggestions for devices with accept/reject actions.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

interface NameSuggestion {
  name: string;
  confidence: number;
  source: string;
  reasoning: string | null;
}

interface NameSuggestionCardProps {
  deviceId: string;
  currentName: string;
  suggestions: NameSuggestion[];
  onAccept: (deviceId: string, suggestedName: string) => Promise<void>;
  onReject: (deviceId: string, suggestedName: string) => Promise<void>;
  darkMode?: boolean;
}

export const NameSuggestionCard: React.FC<NameSuggestionCardProps> = ({
  deviceId,
  currentName,
  suggestions,
  onAccept,
  onReject,
  darkMode = false
}) => {
  const [processing, setProcessing] = useState<string | null>(null);

  const handleAccept = async (suggestedName: string) => {
    setProcessing(suggestedName);
    try {
      await onAccept(deviceId, suggestedName);
      toast.success(`Device name updated to "${suggestedName}"`);
    } catch (error) {
      toast.error(`Failed to accept name: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (suggestedName: string) => {
    setProcessing(suggestedName);
    try {
      await onReject(deviceId, suggestedName);
      toast.success('Suggestion rejected');
    } catch (error) {
      toast.error(`Failed to reject suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setProcessing(null);
    }
  };

  if (suggestions.length === 0) {
    return null;
  }

  const textColor = darkMode ? 'text-gray-100' : 'text-gray-900';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`${borderColor} border rounded-xl p-4 mb-4 shadow-lg backdrop-blur-sm ${
        darkMode
          ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20'
          : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className={`${textColor} font-semibold text-lg`}>Name Enhancement Available</h3>
          <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'} text-sm mt-1`}>
            Current: <span className="font-mono">{currentName}</span>
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {suggestions.map((suggestion, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`${darkMode ? 'bg-slate-800/60 backdrop-blur-sm border border-slate-700/50' : 'bg-white/80 backdrop-blur-sm border border-gray-200/50'} rounded-xl p-3`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`${textColor} font-semibold text-base`}>
                    {suggestion.name}
                  </span>
                  <span className={`${darkMode ? 'bg-blue-600' : 'bg-blue-100'} ${darkMode ? 'text-white' : 'text-blue-800'} text-xs px-2 py-1 rounded`}>
                    {Math.round(suggestion.confidence * 100)}% confidence
                  </span>
                  <span className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} text-xs`}>
                    ({suggestion.source})
                  </span>
                </div>
                {suggestion.reasoning && (
                  <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} text-sm mt-1`}>
                    {suggestion.reasoning}
                  </p>
                )}
              </div>
              <div className="flex gap-2 ml-4">
                <button
                  onClick={() => handleAccept(suggestion.name)}
                  disabled={processing === suggestion.name}
                  className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                    processing === suggestion.name
                      ? 'bg-gray-400 cursor-not-allowed'
                      : darkMode
                      ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg shadow-green-500/30'
                      : 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white shadow-lg shadow-green-400/30'
                  }`}
                >
                  {processing === suggestion.name ? 'Accepting...' : 'Accept'}
                </button>
                <button
                  onClick={() => handleReject(suggestion.name)}
                  disabled={processing === suggestion.name}
                  className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                    processing === suggestion.name
                      ? 'bg-gray-400 cursor-not-allowed'
                      : darkMode
                      ? 'bg-slate-800/60 hover:bg-slate-700/60 text-white border border-slate-700/50'
                      : 'bg-white/80 hover:bg-white text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
                  }`}
                >
                  Reject
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

