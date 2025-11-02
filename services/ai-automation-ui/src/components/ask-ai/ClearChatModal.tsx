/**
 * Clear Chat Confirmation Modal
 * 
 * Confirmation dialog for clearing the conversation history
 * Updated with Modern & Manly Design System
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getModalOverlayStyles, getCardStyles, getButtonStyles } from '../../utils/designSystem';

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
  darkMode: _darkMode
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={getModalOverlayStyles()}
        className="p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          style={getCardStyles({ maxWidth: '28rem', width: '100%' })}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Corner accents */}
          <div style={{ position: 'absolute', top: 0, left: 0, width: '5rem', height: '5rem', borderTop: '2px solid rgba(59, 130, 246, 0.5)', borderLeft: '2px solid rgba(59, 130, 246, 0.5)' }} />
          <div style={{ position: 'absolute', top: 0, right: 0, width: '5rem', height: '5rem', borderTop: '2px solid rgba(59, 130, 246, 0.5)', borderRight: '2px solid rgba(59, 130, 246, 0.5)' }} />
          <div style={{ position: 'absolute', bottom: 0, left: 0, width: '5rem', height: '5rem', borderBottom: '2px solid rgba(59, 130, 246, 0.5)', borderLeft: '2px solid rgba(59, 130, 246, 0.5)' }} />
          <div style={{ position: 'absolute', bottom: 0, right: 0, width: '5rem', height: '5rem', borderBottom: '2px solid rgba(59, 130, 246, 0.5)', borderRight: '2px solid rgba(59, 130, 246, 0.5)' }} />
          {/* Header */}
          <div className="flex items-start gap-4 mb-6">
            <motion.div
              animate={{ rotate: [0, -10, 10, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
              className="text-4xl"
            >
              🗑️
            </motion.div>
            <div className="flex-1">
              <h2 className="ds-title-card mb-2" style={{ color: '#ffffff' }}>
                CLEAR CONVERSATION?
              </h2>
              <p className="ds-text-body text-sm">
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
                style={getButtonStyles('primary', { width: '100%' })}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                📥 EXPORT & CLEAR
              </button>
            )}
            <button
              onClick={onConfirm}
              style={getButtonStyles('danger', { width: '100%' })}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              CLEAR CONVERSATION
            </button>
            <button
              onClick={onClose}
              style={getButtonStyles('secondary', { width: '100%' })}
            >
              CANCEL
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

