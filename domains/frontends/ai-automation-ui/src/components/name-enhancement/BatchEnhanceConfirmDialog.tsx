/**
 * Batch Enhance Confirmation Dialog
 * 
 * Confirmation dialog before starting batch enhancement operations
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface BatchEnhanceConfirmDialogProps {
  isOpen: boolean;
  useAI: boolean;
  deviceCount?: number;
  onConfirm: () => void;
  onCancel: () => void;
  darkMode?: boolean;
}

export const BatchEnhanceConfirmDialog: React.FC<BatchEnhanceConfirmDialogProps> = ({
  isOpen,
  useAI,
  deviceCount,
  onConfirm,
  onCancel,
  darkMode = false
}) => {
  if (!isOpen) return null;

  const methodName = useAI ? 'AI' : 'Pattern';
  const methodDescription = useAI 
    ? 'AI-powered analysis for more sophisticated name suggestions'
    : 'Pattern-based matching for faster, rule-based suggestions';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onCancel}
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
          className={`rounded-xl shadow-xl max-w-md w-full p-6 ${
            darkMode 
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
          <div className="flex items-start gap-4 mb-6">
            <div className="text-4xl">{useAI ? '🤖' : '🔍'}</div>
            <div className="flex-1">
              <h2 className={`text-xl font-bold mb-2 ${darkMode ? 'text-gray-100' : 'text-gray-900'}`}>
                Start Batch Enhancement?
              </h2>
              <p className={`text-sm mb-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                This will generate name suggestions for your devices using the <strong>{methodName}</strong> method.
              </p>
              <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                {methodDescription}
              </p>
              {deviceCount !== undefined && (
                <div className={`mt-3 p-2 rounded-lg ${darkMode ? 'bg-slate-800/60' : 'bg-blue-50'}`}>
                  <p className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Estimated devices: {deviceCount}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onConfirm}
              className={`flex-1 px-4 py-2 rounded-xl font-medium transition-all ${
                useAI
                  ? darkMode
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg shadow-purple-500/30'
                    : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg shadow-purple-400/30'
                  : darkMode
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
              }`}
            >
              Start Enhancement
            </button>
            <button
              onClick={onCancel}
              className={`flex-1 px-4 py-2 rounded-xl font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700 text-white hover:bg-gray-600'
                  : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
              }`}
            >
              Cancel
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
