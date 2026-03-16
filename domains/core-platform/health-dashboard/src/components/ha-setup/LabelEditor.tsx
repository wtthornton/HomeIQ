import React, { useState } from 'react';
import type { EntityRecord } from '../../hooks/useEntityAudit';
import { LABEL_TAXONOMY, suggestLabels } from '../../hooks/useEntityAudit';

interface Props {
  entity: EntityRecord;
  darkMode: boolean;
  onSave: (labels: string[]) => Promise<void>;
}

export const LabelEditor: React.FC<Props> = ({ entity, darkMode, onSave }) => {
  const [labels, setLabels] = useState<string[]>(entity.labels || []);
  const [customLabel, setCustomLabel] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestions = suggestLabels({ ...entity, labels });
  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const inputBg = darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300';

  const removeLabel = (label: string) => {
    setLabels(prev => prev.filter(l => l !== label));
  };

  const addLabel = (label: string) => {
    if (!labels.includes(label)) {
      setLabels(prev => [...prev, label]);
    }
  };

  const addCustomLabel = () => {
    const trimmed = customLabel.trim();
    if (!trimmed) return;
    if (!/^[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*$/.test(trimmed)) {
      setError('Label must match prefix:name format (lowercase, e.g. ai:automatable)');
      return;
    }
    setError(null);
    addLabel(trimmed);
    setCustomLabel('');
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(labels);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = JSON.stringify(labels.sort()) !== JSON.stringify((entity.labels || []).sort());

  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <div className="text-xs font-medium mb-2 text-gray-400">Current Labels</div>
      <div className="flex flex-wrap gap-1 mb-3 min-h-[24px]">
        {labels.length === 0 && (
          <span className="text-xs text-gray-500 italic">No labels</span>
        )}
        {labels.map(label => (
          <span
            key={label}
            className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded ${
              darkMode ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-100 text-blue-800'
            }`}
          >
            {label}
            <button onClick={() => removeLabel(label)} className="hover:text-red-500">&times;</button>
          </span>
        ))}
      </div>

      {/* Add from taxonomy */}
      <div className="mb-3">
        <select
          className={`text-xs rounded border px-2 py-1 ${inputBg}`}
          value=""
          onChange={(e) => { if (e.target.value) addLabel(e.target.value); }}
        >
          <option value="">Add from taxonomy...</option>
          {Object.entries(LABEL_TAXONOMY).map(([group, items]) => (
            <optgroup key={group} label={group}>
              {items.filter(l => !labels.includes(l)).map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* Custom label input */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={customLabel}
          onChange={(e) => setCustomLabel(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addCustomLabel()}
          placeholder="prefix:name"
          className={`text-xs rounded border px-2 py-1 flex-1 ${inputBg}`}
        />
        <button
          onClick={addCustomLabel}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + Custom
        </button>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-medium mb-1 text-gray-400">Suggested</div>
          <div className="flex flex-wrap gap-1">
            {suggestions.map(s => (
              <button
                key={s}
                onClick={() => addLabel(s)}
                className={`text-xs px-2 py-0.5 rounded border ${
                  darkMode ? 'border-green-800 text-green-400 hover:bg-green-900/40' : 'border-green-300 text-green-700 hover:bg-green-50'
                }`}
              >
                + {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <div className="text-xs text-red-500 mb-2">{error}</div>}

      {hasChanges && (
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-xs px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Labels'}
        </button>
      )}
    </div>
  );
};
