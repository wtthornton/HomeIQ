/**
 * Skeleton Card Component
 * Modern 2025 skeleton loader with shimmer effect for pattern/synergy cards
 */

import React from 'react';
import { motion } from 'framer-motion';

interface SkeletonCardProps {
  className?: string;
  variant?: 'pattern' | 'synergy' | 'default';
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

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ 
  className = '', 
  variant = 'default' 
}) => {
  const baseClasses = `
    relative overflow-hidden rounded-xl
    bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900
    border border-gray-200 dark:border-gray-700
    p-6 shadow-sm
    ${className}
  `;

  return (
    <div className={baseClasses}>
      {/* Shimmer effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
        animate={shimmerAnimation}
        style={{ width: '200%', height: '100%' }}
      />
      
      {/* Content skeleton */}
      <div className="relative space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <div className="h-5 bg-gray-300 dark:bg-gray-700 rounded w-3/4 animate-pulse" />
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2 animate-pulse" />
          </div>
          <div className="h-8 w-8 bg-gray-300 dark:bg-gray-700 rounded-full animate-pulse" />
        </div>

        {/* Body content - varies by variant */}
        {variant === 'pattern' && (
          <>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-full animate-pulse" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-5/6 animate-pulse" />
            </div>
            <div className="flex gap-2">
              <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded-full w-20 animate-pulse" />
              <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded-full w-24 animate-pulse" />
            </div>
            <div className="flex items-center justify-between pt-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-32 animate-pulse" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-24 animate-pulse" />
            </div>
          </>
        )}

        {variant === 'synergy' && (
          <>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-full animate-pulse" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-4/5 animate-pulse" />
            </div>
            <div className="flex items-center gap-4">
              <div className="h-10 bg-gray-300 dark:bg-gray-700 rounded-lg w-20 animate-pulse" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-8 animate-pulse" />
              <div className="h-10 bg-gray-300 dark:bg-gray-700 rounded-lg w-20 animate-pulse" />
            </div>
            <div className="flex gap-2 pt-2">
              <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-32 animate-pulse" />
              <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-28 animate-pulse" />
            </div>
          </>
        )}

        {variant === 'default' && (
          <>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-full animate-pulse" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-5/6 animate-pulse" />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

/**
 * Skeleton Card Grid - Multiple skeleton cards
 */
interface SkeletonCardGridProps {
  count?: number;
  variant?: 'pattern' | 'synergy' | 'default';
  className?: string;
}

export const SkeletonCardGrid: React.FC<SkeletonCardGridProps> = ({
  count = 6,
  variant = 'default',
  className = '',
}) => {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 ${className}`}>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonCard key={index} variant={variant} />
      ))}
    </div>
  );
};

