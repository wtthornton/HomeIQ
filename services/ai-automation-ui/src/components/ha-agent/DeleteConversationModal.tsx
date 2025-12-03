/**
 * Delete Conversation Confirmation Modal
 * Epic AI-20 Story AI20.8: Conversation Management UI
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DeleteConversationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  conversationTitle: string;
  darkMode: boolean;
}

export const DeleteConversationModal: React.FC<DeleteConversationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  conversationTitle,
  darkMode,
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
          className={`rounded-lg shadow-xl max-w-md w-full p-6 ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}
        >
          <div className="flex items-start gap-4 mb-6">
            <div className="text-4xl">🗑️</div>
            <div className="flex-1">
              <h2 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Delete Conversation?
              </h2>
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                Are you sure you want to delete "{conversationTitle}"? This action cannot be undone.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onConfirm}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-red-500 text-white hover:bg-red-600'
              }`}
            >
              Delete
            </button>
            <button
              onClick={onClose}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
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

