/**
 * Ideas Page (FR-2.2)
 * Merges: ConversationalDashboard + ProactiveSuggestions + BlueprintSuggestions
 */

import React, { useState } from 'react';
import { useAppStore } from '../store';
import { ConversationalDashboard } from './ConversationalDashboard';
import { ProactiveSuggestions } from './ProactiveSuggestions';
import { BlueprintSuggestions } from './BlueprintSuggestions';

type IdeasSource = 'data' | 'context' | 'blueprints';

export const Ideas: React.FC = () => {
  const { darkMode } = useAppStore();
  const [activeSource, setActiveSource] = useState<IdeasSource>(() => {
    const params = new URLSearchParams(window.location.search);
    const source = params.get('source');
    if (source === 'context' || source === 'blueprints') return source;
    return 'data';
  });

  const sources: { id: IdeasSource; label: string }[] = [
    { id: 'data', label: 'From Your Data' },
    { id: 'context', label: 'From Context' },
    { id: 'blueprints', label: 'From Blueprints' },
  ];

  const handleSourceChange = (source: IdeasSource) => {
    setActiveSource(source);
    const url = new URL(window.location.href);
    url.searchParams.set('source', source);
    window.history.replaceState(null, '', url.toString());
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Ideas
        </h1>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          AI-generated automation ideas from multiple sources
        </p>
      </div>

      {/* Sub-tab strip */}
      <div className="flex gap-1 mb-6 border-b border-[var(--card-border)] pb-2" role="tablist" aria-label="Idea sources">
        {sources.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={activeSource === s.id}
            aria-controls={`tabpanel-${s.id}`}
            id={`tab-${s.id}`}
            onClick={() => handleSourceChange(s.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
              activeSource === s.id
                ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)]'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)]'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div role="tabpanel" id={`tabpanel-${activeSource}`} aria-labelledby={`tab-${activeSource}`}>
        {activeSource === 'data' && <ConversationalDashboard />}
        {activeSource === 'context' && <ProactiveSuggestions />}
        {activeSource === 'blueprints' && <BlueprintSuggestions />}
      </div>
    </div>
  );
};
