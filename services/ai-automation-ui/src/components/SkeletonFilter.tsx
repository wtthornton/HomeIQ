/**
 * Skeleton Filter Component
 * Loading skeleton for filter/search sections
 */

import React from 'react';
import { motion } from 'framer-motion';

interface SkeletonFilterProps {
  showSearch?: boolean;
  pillCount?: number;
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

export const SkeletonFilter: React.FC<SkeletonFilterProps> = ({
  showSearch = true,
  pillCount = 5,
  className = '',
}) => {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search bar skeleton */}
      {showSearch && (
        <div className="relative overflow-hidden rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700">
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={shimmerAnimation}
            style={{ width: '200%', height: '100%' }}
          />
          <div className="relative h-12 flex items-center px-4">
            <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-full animate-pulse" />
          </div>
        </div>
      )}

      {/* Filter pills skeleton */}
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: pillCount }).map((_, index) => (
          <div
            key={index}
            className="relative overflow-hidden rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 px-4 py-2"
          >
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              animate={shimmerAnimation}
              style={{ width: '200%', height: '100%' }}
            />
            <div className="relative h-5 w-16 bg-gray-300 dark:bg-gray-700 rounded-full animate-pulse" />
          </div>
        ))}
      </div>

      {/* Sort/View controls skeleton */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-24 animate-pulse" />
          <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-32 animate-pulse" />
        </div>
        <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-20 animate-pulse" />
      </div>
    </div>
  );
};

