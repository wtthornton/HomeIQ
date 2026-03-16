import React, { useState, useMemo } from 'react';
import type { EntityRecord } from '../../hooks/useEntityAudit';
import { matchesGlobPattern, getDefaultExclusionPatterns } from '../../hooks/useEntityAudit';

interface Props {
  entities: EntityRecord[];
  darkMode: boolean;
}

const SUGGESTED_PATTERNS = [
  { pattern: 'sensor.*_linkquality', reason: 'Zigbee diagnostic' },
  { pattern: 'number.*_calibration_*', reason: 'Device config' },
  { pattern: 'binary_sensor.*_tamper', reason: 'Tamper sensors' },
  { pattern: 'sensor.*_uptime', reason: 'Device uptime' },
  { pattern: 'switch.*_child_lock', reason: 'Child lock switches' },
];

export const ExclusionManager: React.FC<Props> = ({ entities, darkMode }) => {
  const [patterns, setPatterns] = useState<string[]>(getDefaultExclusionPatterns());
  const [newPattern, setNewPattern] = useState('');
  const [showExcluded, setShowExcluded] = useState(false);

  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const inputBg = darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';

  // Entities with ai:ignore label
  const aiIgnoredEntities = useMemo(() =>
    entities.filter(e => (e.labels || []).includes('ai:ignore')),
    [entities]
  );

  // Pattern match counts
  const patternMatches = useMemo(() => {
    return patterns.map(pattern => ({
      pattern,
      count: entities.filter(e => matchesGlobPattern(e.entity_id, pattern)).length,
    }));
  }, [patterns, entities]);

  // All excluded entity IDs (patterns + ai:ignore)
  const excludedEntities = useMemo(() => {
    const excluded = new Set<string>();
    entities.forEach(e => {
      if ((e.labels || []).includes('ai:ignore')) excluded.add(e.entity_id);
      if (patterns.some(p => matchesGlobPattern(e.entity_id, p))) excluded.add(e.entity_id);
    });
    return excluded;
  }, [entities, patterns]);

  // Suggestions not already in patterns
  const availableSuggestions = useMemo(() =>
    SUGGESTED_PATTERNS.filter(s => !patterns.includes(s.pattern)),
    [patterns]
  );

  const addPattern = (pattern: string) => {
    const trimmed = pattern.trim();
    if (trimmed && !patterns.includes(trimmed)) {
      setPatterns(prev => [...prev, trimmed]);
    }
  };

  const removePattern = (pattern: string) => {
    setPatterns(prev => prev.filter(p => p !== pattern));
  };

  const handleAddNew = () => {
    if (newPattern.trim()) {
      addPattern(newPattern);
      setNewPattern('');
    }
  };

  return (
    <div className="space-y-4">
      {/* Glob Patterns */}
      <div className={`rounded-lg border p-4 ${bg}`}>
        <h3 className={`text-sm font-medium mb-3 ${text}`}>Exclusion Patterns</h3>
        <div className="space-y-2 mb-3">
          {patternMatches.map(({ pattern, count }) => (
            <div key={pattern} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <code className={`text-xs px-2 py-0.5 rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-800'}`}>
                  {pattern}
                </code>
                <span className={`text-xs ${muted}`}>({count} matched)</span>
              </div>
              <button
                onClick={() => removePattern(pattern)}
                className="text-xs text-red-500 hover:text-red-700"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={newPattern}
            onChange={(e) => setNewPattern(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddNew()}
            placeholder="e.g. sensor.*_battery"
            className={`text-xs rounded border px-2 py-1 flex-1 ${inputBg}`}
          />
          <button
            onClick={handleAddNew}
            className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + Add Pattern
          </button>
        </div>
      </div>

      {/* ai:ignore labeled */}
      <div className={`rounded-lg border p-4 ${bg}`}>
        <h3 className={`text-sm font-medium mb-2 ${text}`}>
          Labeled ai:ignore (auto-excluded)
        </h3>
        {aiIgnoredEntities.length === 0 ? (
          <p className={`text-xs ${muted}`}>No entities labeled ai:ignore</p>
        ) : (
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {aiIgnoredEntities.slice(0, 20).map(e => (
              <div key={e.entity_id} className={`text-xs ${muted}`}>
                {e.entity_id} ({e.friendly_name || e.name || ''})
              </div>
            ))}
            {aiIgnoredEntities.length > 20 && (
              <div className={`text-xs ${muted}`}>... {aiIgnoredEntities.length - 20} more</div>
            )}
          </div>
        )}
      </div>

      {/* Suggested patterns */}
      {availableSuggestions.length > 0 && (
        <div className={`rounded-lg border p-4 ${bg}`}>
          <h3 className={`text-sm font-medium mb-2 ${text}`}>Suggested Exclusions</h3>
          <div className="space-y-2">
            {availableSuggestions.map(s => {
              const count = entities.filter(e => matchesGlobPattern(e.entity_id, s.pattern)).length;
              return (
                <div key={s.pattern} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => addPattern(s.pattern)}
                      className={`text-xs px-2 py-0.5 rounded border ${
                        darkMode ? 'border-green-800 text-green-400 hover:bg-green-900/40' : 'border-green-300 text-green-700 hover:bg-green-50'
                      }`}
                    >
                      + {s.pattern}
                    </button>
                    <span className={`text-xs ${muted}`}>({count} entities — {s.reason})</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className={`rounded-lg border p-4 ${bg}`}>
        <div className="flex items-center justify-between">
          <div>
            <span className={`text-sm font-medium ${text}`}>
              {excludedEntities.size} excluded
            </span>
            <span className={`text-xs ml-1 ${muted}`}>/ {entities.length} total ({
              entities.length > 0 ? Math.round((excludedEntities.size / entities.length) * 100) : 0
            }%)</span>
          </div>
          <button
            onClick={() => setShowExcluded(!showExcluded)}
            className={`text-xs underline ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}
          >
            {showExcluded ? 'Hide' : 'Show'} excluded entities
          </button>
        </div>
        {showExcluded && (
          <div className="mt-2 max-h-60 overflow-y-auto">
            {Array.from(excludedEntities).sort().map(id => (
              <div key={id} className={`text-xs py-0.5 ${muted}`}>{id}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
