import React from 'react';

interface SkeletonGraphProps {
  variant?: 'dependency' | 'chart';
  className?: string;
}

export const SkeletonGraph: React.FC<SkeletonGraphProps> = ({
  variant = 'chart',
  className = ''
}) => {
  if (variant === 'dependency') {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}>
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-6 animate-pulse shimmer"></div>
        
        {/* Graph skeleton with nodes */}
        <div className="relative h-[500px] bg-gray-50 dark:bg-gray-900 rounded-lg p-8">
          {/* Simulated nodes */}
          <div className="absolute top-8 left-1/2 transform -translate-x-1/2">
            <div className="h-16 w-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse shimmer"></div>
          </div>
          <div className="absolute top-32 left-1/4">
            <div className="h-16 w-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse shimmer"></div>
          </div>
          <div className="absolute top-32 right-1/4">
            <div className="h-16 w-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse shimmer"></div>
          </div>
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
            <div className="h-16 w-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse shimmer"></div>
          </div>
        </div>
      </div>
    );
  }
  
  // Chart variant
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}>
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-4 animate-pulse shimmer"></div>
      <div className="h-64 bg-gray-100 dark:bg-gray-900 rounded p-4">
        {/* Simulated chart bars */}
        <div className="flex items-end justify-around h-full space-x-2">
          {[60, 80, 50, 90, 70, 85, 65].map((height, index) => (
            <div
              key={index}
              className="bg-gray-200 dark:bg-gray-700 rounded-t animate-pulse shimmer"
              style={{ width: '12%', height: `${height}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

