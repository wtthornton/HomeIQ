/**
 * AnalyticsLoadingState Component
 * 
 * Loading skeleton for analytics panel
 */

import React from 'react';
import { SkeletonCard } from '../skeletons';

export const AnalyticsLoadingState: React.FC = (): JSX.Element => {
  return (
    <div className="space-y-6">
      {/* Header Skeleton */}
      <div className="flex justify-between items-center">
        <SkeletonCard className="h-8 w-48" />
        <SkeletonCard className="h-10 w-64" />
      </div>

      {/* Summary Cards Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} className="h-32" />
        ))}
      </div>

      {/* Metrics Cards Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} className="h-64" />
        ))}
      </div>
    </div>
  );
};

