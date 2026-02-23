import React from 'react';

interface SkeletonCardProps {
  variant?: 'default' | 'metric' | 'service' | 'chart';
  className?: string;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ 
  variant = 'default',
  className = '' 
}) => {
  const baseClasses = 'bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse';
  
  if (variant === 'metric') {
    return (
      <div className={`${baseClasses} ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 shimmer"></div>
          <div className="h-6 w-6 bg-gray-200 dark:bg-gray-700 rounded shimmer"></div>
        </div>
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-2 shimmer"></div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-48 shimmer"></div>
      </div>
    );
  }
  
  if (variant === 'service') {
    return (
      <div className={`${baseClasses} ${className}`}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded-full shimmer"></div>
            <div>
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-2 shimmer"></div>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24 shimmer"></div>
            </div>
          </div>
          <div className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded-full shimmer"></div>
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full shimmer"></div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6 shimmer"></div>
        </div>
      </div>
    );
  }
  
  if (variant === 'chart') {
    return (
      <div className={`${baseClasses} ${className}`}>
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-4 shimmer"></div>
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded shimmer"></div>
      </div>
    );
  }
  
  // Default variant
  return (
    <div className={`${baseClasses} ${className}`}>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4 shimmer"></div>
      <div className="space-y-3">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded shimmer"></div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6 shimmer"></div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-4/6 shimmer"></div>
      </div>
    </div>
  );
};

