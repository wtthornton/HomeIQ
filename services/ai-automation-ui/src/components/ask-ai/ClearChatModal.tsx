/**
 * Clear Chat Confirmation Modal
 * 
 * Confirmation dialog for clearing the conversation history
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ClearChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onExportAndClear?: () => void;
  messageCount: number;
  darkMode: boolean;
}

export const ClearChatModal: React.FC<ClearChatModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onExportAndClear,
  messageCount,
  darkMode
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={`relative max-w-md w-full rounded-2xl shadow-2xl p-6 ${
            darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start gap-4 mb-6">
            <div className="text-4xl">🗑️</div>
            <div className="flex-1">
              <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Clear Conversation?
              </h2>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                This will clear all {messageCount} message{messageCount !== 1 ? 's' : ''} from this conversation.
                {onExportAndClear && ' You can export the conversation before clearing if you want to save it.'}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2">
            {onExportAndClear && (
              <button
                onClick={onExportAndClear}
                className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                📥 Export & Clear
              </button>
            )}
            <button
              onClick={onConfirm}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              Clear Conversation
            </button>
            <button
              onClick={onClose}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-colors border ${
                darkMode
                  ? 'border-gray-600 hover:bg-gray-700 text-gray-300'
                  : 'border-gray-300 hover:bg-gray-50 text-gray-700'
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

