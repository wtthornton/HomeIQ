/**
 * AlertStats Component
 * 
 * Display alert statistics summary
 */

import React from 'react';

interface AlertStatsProps {
  criticalCount: number;
  warningCount: number;
  errorCount: number;
  totalCount: number;
  darkMode: boolean;
}

export const AlertStats: React.FC<AlertStatsProps> = ({
  criticalCount,
  warningCount,
  errorCount,
  totalCount,
  darkMode
}): JSX.Element => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {/* Total */}
      <div className={`rounded-lg shadow-md p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Total Alerts</p>
        <p className={`text-2xl font-bold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {totalCount}
        </p>
      </div>
      
      {/* Critical */}
      <div className={`rounded-lg shadow-md p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Critical</p>
        <p className={`text-2xl font-bold mt-1 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
          {criticalCount}
        </p>
      </div>
      
      {/* Warning */}
      <div className={`rounded-lg shadow-md p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Warning</p>
        <p className={`text-2xl font-bold mt-1 ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
          {warningCount}
        </p>
      </div>
      
      {/* Error */}
      <div className={`rounded-lg shadow-md p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Error</p>
        <p className={`text-2xl font-bold mt-1 ${darkMode ? 'text-red-300' : 'text-red-500'}`}>
          {errorCount}
        </p>
      </div>
    </div>
  );
};

