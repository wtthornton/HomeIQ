/**
 * Insights Page (FR-2.3)
 * Merges: Patterns + Synergies
 */

import React, { useState } from 'react';
import { useAppStore } from '../store';
import { Patterns } from './Patterns';
import { Synergies } from './Synergies';

type InsightView = 'patterns' | 'connections' | 'rooms';

export const Insights: React.FC = () => {
  const { darkMode } = useAppStore();
  const [activeView, setActiveView] = useState<InsightView>('patterns');

  const views: { id: InsightView; label: string }[] = [
    { id: 'patterns', label: 'Usage Patterns' },
    { id: 'connections', label: 'Device Connections' },
    { id: 'rooms', label: 'Room View' },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Insights
        </h1>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          ML-detected patterns and cross-device opportunities
        </p>
      </div>

      {/* Sub-tab strip */}
      <div className="flex gap-1 mb-6 border-b border-[var(--card-border)] pb-2">
        {views.map((v) => (
          <button
            key={v.id}
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
      {activeView === 'patterns' && <Patterns />}
      {(activeView === 'connections' || activeView === 'rooms') && <Synergies />}
    </div>
  );
};
