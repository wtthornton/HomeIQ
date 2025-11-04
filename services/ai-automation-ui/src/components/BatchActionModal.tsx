/**
 * Batch Action Confirmation Modal
 * Modal dialog for confirming batch operations with progress tracking
 * Updated with Modern & Manly Design System
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getModalOverlayStyles, getCardStyles, getButtonStyles } from '../utils/designSystem';
import { ProcessLoader } from './ask-ai/ReverseEngineeringLoader';

interface BatchActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'approve' | 'reject' | 'delete' | 'default';
  selectedCount: number;
  darkMode?: boolean;
}

export const BatchActionModal: React.FC<BatchActionModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  selectedCount,
  darkMode: _darkMode = false
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setIsProcessing(false);
      setProgress(0);
      setError(null);
    }
  }, [isOpen]);

  const handleConfirm = async () => {
    setIsProcessing(true);
    setError(null);
    setProgress(0);

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 100);

      await onConfirm();
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Wait a moment to show 100% before closing
      setTimeout(() => {
        onClose();
      }, 500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed');
      setProgress(0);
    } finally {
      setIsProcessing(false);
    }
  };

  const getVariantConfig = () => {
    switch (variant) {
      case 'approve':
        return {
          buttonVariant: 'primary' as const,
          icon: '✅',
          accentColor: '#10b981'
        };
      case 'reject':
      case 'delete':
        return {
          buttonVariant: 'danger' as const,
          icon: variant === 'delete' ? '🗑️' : '❌',
          accentColor: '#ef4444'
        };
      default:
        return {
          buttonVariant: 'primary' as const,
          icon: 'ℹ️',
          accentColor: '#3b82f6'
        };
    }
  };

  const config = getVariantConfig();

  if (!isOpen) return null;

  return (
    <>
      <ProcessLoader
        isVisible={isProcessing}
        processType="batch-action"
        progress={progress}
      />
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
              style={{ color: config.accentColor }}
            >
              {config.icon}
            </motion.div>
            <div className="flex-1">
              <h2 className="ds-title-card mb-2" style={{ color: '#ffffff' }}>
                {title.toUpperCase()}
              </h2>
              <p className="ds-text-body text-sm">
                {message}
              </p>
              <div className="ds-text-label mt-2" style={{ color: config.accentColor }}>
                {selectedCount} ITEM{selectedCount > 1 ? 'S' : ''} SELECTED
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {isProcessing && (
            <div className="mb-6">
              <div className="ds-progress-bar">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.3 }}
                  className="ds-progress-fill"
                />
              </div>
              <div className="ds-text-label mt-2 text-center">
                PROCESSING... {progress}%
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-lg"
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '2px solid rgba(239, 68, 68, 0.5)',
                color: '#fca5a5'
              }}
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">⚠️</span>
                <div>
                  <div className="ds-text-label font-semibold">ERROR</div>
                  <div className="ds-text-body text-sm">{error}</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isProcessing}
              style={getButtonStyles('secondary', { flex: 1 })}
              className="disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {cancelLabel.toUpperCase()}
            </button>
            <button
              onClick={handleConfirm}
              disabled={isProcessing}
              style={getButtonStyles(config.buttonVariant, { flex: 1 })}
              className="disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  PROCESSING...
                </span>
              ) : (
                confirmLabel.toUpperCase()
              )}
            </button>
          </div>

          {/* Keyboard Hint */}
          {!isProcessing && (
            <div className="ds-text-label mt-4 text-center">
              PRESS ESCAPE TO CANCEL, ENTER TO CONFIRM
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
    </>
  );
};
