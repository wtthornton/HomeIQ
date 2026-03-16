import React, { useState } from 'react';
import type { EntityRecord } from '../../hooks/useEntityAudit';
import { suggestAliases } from '../../hooks/useEntityAudit';

interface Props {
  entity: EntityRecord;
  darkMode: boolean;
  onSave: (aliases: string[]) => Promise<void>;
}

export const AliasEditor: React.FC<Props> = ({ entity, darkMode, onSave }) => {
  const [aliases, setAliases] = useState<string[]>(entity.aliases || []);
  const [newAlias, setNewAlias] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestions = suggestAliases({ ...entity, aliases });
  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const inputBg = darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300';

  const removeAlias = (alias: string) => {
    setAliases(prev => prev.filter(a => a !== alias));
  };

  const addAlias = (alias: string) => {
    const trimmed = alias.trim().toLowerCase();
    if (trimmed && !aliases.includes(trimmed)) {
      setAliases(prev => [...prev, trimmed]);
    }
  };

  const handleAddNew = () => {
    if (newAlias.trim()) {
      addAlias(newAlias);
      setNewAlias('');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(aliases);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = JSON.stringify(aliases.sort()) !== JSON.stringify((entity.aliases || []).sort());
  const fname = entity.friendly_name || entity.name || entity.entity_id;

  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <div className="text-xs font-medium mb-1 text-gray-400">
        Aliases for {fname}
      </div>

      {/* Current aliases */}
      <div className="flex flex-wrap gap-1 mb-3 min-h-[24px]">
        {aliases.length === 0 && (
          <span className="text-xs text-gray-500 italic">No aliases</span>
        )}
        {aliases.map(alias => (
          <span
            key={alias}
            className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded ${
              darkMode ? 'bg-purple-900/40 text-purple-300' : 'bg-purple-100 text-purple-800'
            }`}
          >
            {alias}
            <button onClick={() => removeAlias(alias)} className="hover:text-red-500">&times;</button>
          </span>
        ))}
      </div>

      {/* Add alias input */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={newAlias}
          onChange={(e) => setNewAlias(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddNew()}
          placeholder="Add alias..."
          className={`text-xs rounded border px-2 py-1 flex-1 ${inputBg}`}
        />
        <button
          onClick={handleAddNew}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + Add
        </button>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-medium mb-1 text-gray-400">Suggestions</div>
          <div className="flex flex-wrap gap-1">
            {suggestions.map(s => (
              <button
                key={s}
                onClick={() => addAlias(s)}
                className={`text-xs px-2 py-0.5 rounded border ${
                  darkMode ? 'border-purple-800 text-purple-400 hover:bg-purple-900/40' : 'border-purple-300 text-purple-700 hover:bg-purple-50'
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
          {saving ? 'Saving...' : 'Save Aliases'}
        </button>
      )}
    </div>
  );
};
