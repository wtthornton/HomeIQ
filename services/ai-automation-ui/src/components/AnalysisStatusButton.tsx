/**
 * Enhanced Analysis Status Button Component
 * Provides immediate feedback for analysis operations with loading states and progress indicators
 */

import React from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { ProcessLoader } from './ask-ai/ReverseEngineeringLoader';

interface AnalysisStatusProps {
  status: 'ready' | 'running' | 'success' | 'error';
  progress?: number;
  estimatedTime?: number;
  onRunAnalysis: () => void;
  darkMode?: boolean;
  disabled?: boolean;
}

export const AnalysisStatusButton: React.FC<AnalysisStatusProps> = ({
  status,
  progress = 0,
  estimatedTime,
  onRunAnalysis,
  darkMode = false,
  disabled = false
}) => {
  const handleClick = async () => {
    if (status === 'running' || disabled) return;
    
    // Show immediate toast feedback
    toast.loading('Starting analysis...', {
      id: 'analysis-start',
      duration: 2000
    });
    
    try {
      await onRunAnalysis();
      
      // Update toast to success
      toast.success('Analysis started successfully! Check back in 1-2 minutes for new suggestions.', {
        id: 'analysis-start',
        duration: 5000
      });
    } catch (error) {
      // Update toast to error
      toast.error(`Failed to start analysis: ${error instanceof Error ? error.message : 'Unknown error'}`, {
        id: 'analysis-start',
        duration: 5000
      });
    }
  };

  const getButtonContent = () => {
    switch (status) {
      case 'running':
        return (
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Analyzing...</span>
            {progress > 0 && (
              <span className="text-sm opacity-75">({progress}%)</span>
            )}
          </div>
        );
      case 'success':
        return (
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span>Analysis Complete</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2">
            <span>❌</span>
            <span>Analysis Failed</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2">
            <span>▶️</span>
            <span>Run Analysis</span>
          </div>
        );
    }
  };

  const getButtonStyles = () => {
    const baseStyles = "px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded-md";
    
    switch (status) {
      case 'running':
        return `${baseStyles} bg-blue-600 text-white cursor-not-allowed`;
      case 'success':
        return `${baseStyles} bg-green-600 text-white`;
      case 'error':
        return `${baseStyles} bg-red-600 text-white`;
      default:
        return `${baseStyles} bg-white text-blue-600 hover:bg-blue-50 border border-blue-600`;
    }
  };

  return (
    <>
      <ProcessLoader
        isVisible={status === 'running'}
        processType="analysis"
        progress={progress}
      />
      <div className="flex flex-col items-end gap-2">
      {/* Progress Bar for Running State */}
      {status === 'running' && progress > 0 && (
        <div className="w-full max-w-xs">
          <div className={`w-full h-2 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
              className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
            />
          </div>
          {estimatedTime && (
            <div className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Estimated time remaining: {estimatedTime}s
            </div>
          )}
        </div>
      )}

      {/* Main Button */}
      <motion.button
        whileHover={{ scale: status === 'ready' ? 1.05 : 1 }}
        whileTap={{ scale: status === 'ready' ? 0.95 : 1 }}
        onClick={handleClick}
        disabled={status === 'running' || disabled}
        className={getButtonStyles()}
        aria-label={
          status === 'running' 
            ? `Analysis in progress (${progress}% complete)`
            : status === 'success'
            ? 'Analysis completed successfully'
            : status === 'error'
            ? 'Analysis failed - click to retry'
            : 'Start new analysis'
        }
      >
        {getButtonContent()}
      </motion.button>

      {/* Status Indicator */}
      {status !== 'ready' && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`text-xs px-2 py-1 rounded-full ${
            status === 'running' 
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
              : status === 'success'
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
          }`}
        >
          {status === 'running' && '🔄 In Progress'}
          {status === 'success' && '✅ Completed'}
          {status === 'error' && '❌ Failed'}
        </motion.div>
      )}
      </div>
    </>
  );
};
