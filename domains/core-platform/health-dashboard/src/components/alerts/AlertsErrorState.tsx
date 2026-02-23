/**
 * AlertsErrorState Component
 * 
 * Error display for alerts panel with retry functionality
 */

import React from 'react';

interface AlertsErrorStateProps {
  message: string;
  onRetry: () => void;
  darkMode: boolean;
}

export const AlertsErrorState: React.FC<AlertsErrorStateProps> = ({
  message,
  onRetry,
  darkMode
}): JSX.Element => {
  return (
    <div className={`rounded-lg shadow-md p-6 ${
      darkMode ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border border-red-200'
    }`}>
      <div className="flex items-center gap-3">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <h3 className={`font-semibold ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
            Error Loading Alerts
          </h3>
          <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
            {message}
          </p>
        </div>
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
  );
};

