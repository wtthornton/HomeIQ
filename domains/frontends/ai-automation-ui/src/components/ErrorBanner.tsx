/**
 * Error Banner Component
 * Modern 2025 error display with retry functionality
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

interface ErrorBannerProps {
  error: string | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  variant?: 'banner' | 'inline' | 'toast';
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onRetry,
  onDismiss,
  className = '',
  variant = 'banner',
}) => {
  // Determine error type (before early returns to avoid hook issues)
  const isNetworkError = error ? (error.toLowerCase().includes('network') || 
                         error.toLowerCase().includes('fetch') ||
                         error.toLowerCase().includes('connection')) : false;
  const isApiError = error ? (error.toLowerCase().includes('api') ||
                     error.toLowerCase().includes('404') ||
                     error.toLowerCase().includes('500')) : false;
  const isTimeoutError = error ? error.toLowerCase().includes('timeout') : false;

  const errorIcon = isNetworkError ? '🌐' : isApiError ? '⚠️' : isTimeoutError ? '⏱️' : '❌';

  // Handle toast variant with useEffect (must be called unconditionally)
  React.useEffect(() => {
    if (variant === 'toast' && error) {
      toast.error(error, {
        duration: 5000,
        icon: errorIcon,
      });
    }
  }, [error, errorIcon, variant]);

  if (!error) return null;

  if (variant === 'toast') {
    return null;
  }

  if (variant === 'inline') {
    return (
      <div className={`p-4 rounded-lg border-l-4 ${
        isNetworkError 
          ? 'bg-red-50 dark:bg-red-900/20 border-red-500'
          : isApiError
          ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500'
          : 'bg-red-50 dark:bg-red-900/20 border-red-500'
      } ${className}`}>
        <div className="flex items-start gap-3">
          <span className="text-xl">{errorIcon}</span>
          <div className="flex-1">
            <p className={`text-sm font-medium ${
              isNetworkError 
                ? 'text-red-800 dark:text-red-200'
                : isApiError
                ? 'text-yellow-800 dark:text-yellow-200'
                : 'text-red-800 dark:text-red-200'
            }`}>
              {error}
            </p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-2 text-xs underline hover:no-underline"
              >
                Retry
              </button>
            )}
          </div>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    );
  }

  // Banner variant (default)
  return (
    <AnimatePresence>
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className={`mb-6 p-4 rounded-xl border-l-4 shadow-lg ${
            isNetworkError 
              ? 'bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30 border-red-500'
              : isApiError
              ? 'bg-gradient-to-r from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30 border-yellow-500'
              : 'bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30 border-red-500'
          } ${className}`}
        >
          <div className="flex items-start gap-4">
            <div className="text-2xl flex-shrink-0">{errorIcon}</div>
            <div className="flex-1 min-w-0">
              <h3 className={`font-semibold mb-1 ${
                isNetworkError 
                  ? 'text-red-900 dark:text-red-200'
                  : isApiError
                  ? 'text-yellow-900 dark:text-yellow-200'
                  : 'text-red-900 dark:text-red-200'
              }`}>
                {isNetworkError ? 'Connection Error' : isApiError ? 'API Error' : 'Error'}
              </h3>
              <p className={`text-sm ${
                isNetworkError 
                  ? 'text-red-800 dark:text-red-300'
                  : isApiError
                  ? 'text-yellow-800 dark:text-yellow-300'
                  : 'text-red-800 dark:text-red-300'
              }`}>
                {error}
              </p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className={`mt-3 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    isNetworkError
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : isApiError
                      ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  }`}
                >
                  🔄 Retry
                </button>
              )}
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className={`flex-shrink-0 p-1 rounded hover:bg-opacity-20 ${
                  isNetworkError 
                    ? 'text-red-600 dark:text-red-400 hover:bg-red-600'
                    : isApiError
                    ? 'text-yellow-600 dark:text-yellow-400 hover:bg-yellow-600'
                    : 'text-red-600 dark:text-red-400 hover:bg-red-600'
                }`}
                aria-label="Dismiss error"
              >
                ✕
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

