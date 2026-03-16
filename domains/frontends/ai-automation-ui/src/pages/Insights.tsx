/**
 * Insights Page (FR-2.3)
 * Merges: Patterns + Synergies
 */

import React, { lazy, Suspense, useState } from 'react';
const LazyPatterns = lazy(() => import('./Patterns').then(m => ({ default: m.Patterns })));
const LazySynergies = lazy(() => import('./Synergies').then(m => ({ default: m.Synergies })));

type InsightView = 'patterns' | 'connections' | 'rooms';

export const Insights: React.FC = () => {
  const [activeView, setActiveView] = useState<InsightView>('patterns');

  const views: { id: InsightView; label: string }[] = [
    { id: 'patterns', label: 'Usage Patterns' },
    { id: 'connections', label: 'Device Connections' },
    { id: 'rooms', label: 'Room View' },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          Insights
        </h1>
        <p className="text-sm mt-1 text-[var(--text-tertiary)]">
          ML-detected patterns and cross-device opportunities
        </p>
      </div>

      {/* Sub-tab strip */}
      <div className="flex gap-1 mb-6 border-b border-[var(--card-border)] pb-2" role="tablist" aria-label="Insight views">
        {views.map((v) => (
          <button
            key={v.id}
            role="tab"
            aria-selected={activeView === v.id}
            aria-controls={`insight-tabpanel-${v.id}`}
            id={`insight-tab-${v.id}`}
            onClick={() => setActiveView(v.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
              activeView === v.id
                ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)]'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)]'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div role="tabpanel" id={`insight-tabpanel-${activeView}`} aria-labelledby={`insight-tab-${activeView}`}>
        <Suspense fallback={<div className="animate-pulse h-64 rounded bg-[var(--bg-tertiary)]" />}>
          {activeView === 'patterns' && <LazyPatterns />}
          {(activeView === 'connections' || activeView === 'rooms') && <LazySynergies />}
        </Suspense>
      </div>
    </div>
  );
};
