/**
 * Skeleton Stats Component
 * Loading skeleton for statistics sections
 */

import React from 'react';
import { motion } from 'framer-motion';

interface SkeletonStatsProps {
  statCount?: number;
  showCharts?: boolean;
  className?: string;
}

const shimmerAnimation = {
  x: ['-100%', '100%'],
  transition: {
    x: {
      repeat: Infinity,
      repeatType: 'loop' as const,
      duration: 1.5,
      ease: 'easeInOut',
    },
  },
};

export const SkeletonStats: React.FC<SkeletonStatsProps> = ({
  statCount = 4,
  showCharts = false,
  className = '',
}) => {
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: statCount }).map((_, index) => (
          <div
            key={index}
            className="relative overflow-hidden rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 p-4 shadow-sm"
          >
            {/* Shimmer effect */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              animate={shimmerAnimation}
              style={{ width: '200%', height: '100%' }}
            />
            
            <div className="relative space-y-2">
              <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-2/3 animate-pulse" />
              <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-1/2 animate-pulse" />
              <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-full animate-pulse" />
            </div>
          </div>
        ))}
      </div>

      {/* Charts skeleton */}
      {showCharts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2].map((index) => (
            <div
              key={index}
              className="relative overflow-hidden rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 p-6 shadow-sm"
            >
              {/* Shimmer effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                animate={shimmerAnimation}
                style={{ width: '200%', height: '100%' }}
              />
              
              <div className="relative space-y-4">
                <div className="h-5 bg-gray-300 dark:bg-gray-700 rounded w-1/3 animate-pulse" />
                <div className="h-48 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
                <div className="flex gap-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-16 animate-pulse" />
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-20 animate-pulse" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

