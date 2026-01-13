/**
 * Name Enhancement Skeleton Loader
 * 
 * Skeleton loader matching NameSuggestionCard layout for consistent loading states
 */

import React from 'react';
import { motion } from 'framer-motion';

interface NameEnhancementSkeletonProps {
  count?: number;
  darkMode?: boolean;
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

export const NameEnhancementSkeleton: React.FC<NameEnhancementSkeletonProps> = ({
  count = 3,
  darkMode = false
}) => {
  const baseClasses = `
    relative overflow-hidden rounded-xl mb-4 shadow-lg backdrop-blur-sm border
    ${darkMode
      ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20'
      : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
    }
    p-4
  `;

  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className={baseClasses}
        >
          {/* Shimmer effect */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={shimmerAnimation}
            style={{ width: '200%', height: '100%' }}
          />

          {/* Content skeleton */}
          <div className="relative">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex-1">
                <div className={`h-6 rounded w-64 mb-2 animate-pulse ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                <div className={`h-4 rounded w-48 animate-pulse ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`} />
              </div>
            </div>

            {/* Suggestions skeleton */}
            <div className="space-y-3">
              {[1, 2].map((suggestionIndex) => (
                <div
                  key={suggestionIndex}
                  className={`${darkMode ? 'bg-slate-800/60 border border-slate-700/50' : 'bg-white/80 border border-gray-200/50'} rounded-xl p-3`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`h-5 rounded w-32 animate-pulse ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                        <div className={`h-5 rounded-full w-24 animate-pulse ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                        <div className={`h-4 rounded w-16 animate-pulse ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`} />
                      </div>
                      <div className={`h-4 rounded w-full animate-pulse mt-1 ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`} />
                    </div>
                    <div className="flex gap-2 ml-4">
                      <div className={`h-8 rounded-xl w-20 animate-pulse ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                      <div className={`h-8 rounded-xl w-16 animate-pulse ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};
