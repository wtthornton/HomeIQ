/**
 * LoadingSkeleton Component
 *
 * Displayed as a Suspense fallback while lazy-loaded tab chunks are loading.
 * Uses the teal accent color and matches the dashboard card layout.
 */

import React from 'react';

export const LoadingSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse">
    {/* Header skeleton */}
    <div className="rounded-lg bg-card border border-border p-6">
      <div className="h-6 w-48 rounded bg-muted mb-3" />
      <div className="h-4 w-72 rounded bg-muted" />
    </div>

    {/* Cards grid skeleton */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-lg bg-card border border-border p-4">
          <div className="h-3 w-20 rounded bg-muted mb-3" />
          <div className="h-8 w-24 rounded bg-muted mb-2" />
          <div className="h-3 w-16 rounded bg-muted" />
        </div>
      ))}
    </div>

    {/* Content skeleton */}
    <div className="rounded-lg bg-card border border-border p-6">
      <div className="h-5 w-36 rounded bg-muted mb-4" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-4 rounded bg-muted" style={{ width: `${85 - i * 10}%` }} />
        ))}
      </div>
    </div>
  </div>
);
