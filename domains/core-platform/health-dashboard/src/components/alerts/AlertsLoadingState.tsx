/**
 * AlertsLoadingState Component
 * 
 * Loading skeleton for alerts panel
 */

import React from 'react';
import { SkeletonList } from '../skeletons';

interface AlertsLoadingStateProps {
  darkMode: boolean;
}

export const AlertsLoadingState: React.FC<AlertsLoadingStateProps> = ({ darkMode }): JSX.Element => {
  return (
    <div className="space-y-6">
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-4 shimmer"></div>
        <div className="flex gap-4 mb-6">
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32 shimmer"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32 shimmer"></div>
        </div>
      </div>
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <SkeletonList count={5} />
      </div>
    </div>
  );
};

