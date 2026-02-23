/**
 * AnalyticsErrorState Component
 * 
 * Error display for analytics panel with retry functionality
 */

import React from 'react';

interface AnalyticsErrorStateProps {
  message: string;
  onRetry: () => void;
  darkMode: boolean;
}

export const AnalyticsErrorState: React.FC<AnalyticsErrorStateProps> = ({
  message,
  onRetry,
  darkMode
}): JSX.Element => {
  return (
    <div className={`rounded-lg border p-8 text-center ${
      darkMode
        ? 'bg-red-900/20 border-red-500/50 text-red-300'
        : 'bg-red-50 border-red-200 text-red-700'
    }`}>
      <div className="text-4xl mb-4">❌</div>
      <h3 className="text-lg font-semibold mb-2">Failed to Load Analytics</h3>
      <p className="text-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
          darkMode
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-red-600 hover:bg-red-700 text-white'
        }`}
      >
        Retry
      </button>
    </div>
  );
};

