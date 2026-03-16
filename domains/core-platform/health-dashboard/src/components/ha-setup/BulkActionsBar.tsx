import React, { useState } from 'react';
import { LABEL_TAXONOMY } from '../../hooks/useEntityAudit';

interface Props {
  selectedCount: number;
  selectedIds: string[];
  darkMode: boolean;
  onBulkLabel: (entityIds: string[], addLabels: string[], removeLabels?: string[]) => Promise<void>;
  onClearSelection: () => void;
}

export const BulkActionsBar: React.FC<Props> = ({
  selectedCount, selectedIds, darkMode, onBulkLabel, onClearSelection,
}) => {
  const [action, setAction] = useState<string>('');
  const [label, setLabel] = useState<string>('');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (selectedCount === 0) return null;

  const bg = darkMode ? 'bg-blue-900/50 border-blue-700' : 'bg-blue-50 border-blue-200';
  const text = darkMode ? 'text-blue-200' : 'text-blue-900';

  const handleApply = async () => {
    if (!action || !label) return;
    setRunning(true);
    setError(null);
    try {
      if (action === 'add') {
        await onBulkLabel(selectedIds, [label]);
      } else if (action === 'remove') {
        await onBulkLabel(selectedIds, [], [label]);
      }
      setAction('');
      setLabel('');
      onClearSelection();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk operation failed');
    } finally {
      setRunning(false);
    }
  };

  const allLabels = Object.values(LABEL_TAXONOMY).flat();

  return (
    <div className={`rounded-lg border p-3 flex items-center gap-3 flex-wrap ${bg}`}>
      <span className={`text-sm font-medium ${text}`}>
        {selectedCount} selected
      </span>

      <select
        value={action}
        onChange={(e) => setAction(e.target.value)}
        className={`text-xs rounded border px-2 py-1 ${darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300'}`}
      >
        <option value="">Action...</option>
        <option value="add">Add Label</option>
        <option value="remove">Remove Label</option>
      </select>

      {action && (
        <select
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className={`text-xs rounded border px-2 py-1 ${darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300'}`}
        >
          <option value="">Select label...</option>
          {allLabels.map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      )}

      {action && label && (
        <button
          onClick={handleApply}
          disabled={running}
          className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {running ? 'Applying...' : 'Apply'}
        </button>
      )}

      {/* Quick actions */}
      <div className="flex gap-1 ml-auto">
        <button
          onClick={async () => {
            setRunning(true);
            try {
              await onBulkLabel(selectedIds, ['ai:automatable']);
              onClearSelection();
            } finally { setRunning(false); }
          }}
          disabled={running}
          className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-green-900/50 text-green-300' : 'bg-green-100 text-green-800'} hover:opacity-80`}
        >
          Mark Automatable
        </button>
        <button
          onClick={async () => {
            setRunning(true);
            try {
              await onBulkLabel(selectedIds, ['ai:ignore']);
              onClearSelection();
            } finally { setRunning(false); }
          }}
          disabled={running}
          className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'} hover:opacity-80`}
        >
          Mark Ignore
        </button>
        <button
          onClick={onClearSelection}
          className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'} hover:opacity-80`}
        >
          Clear
        </button>
      </div>

      {error && <div className="w-full text-xs text-red-500">{error}</div>}
    </div>
  );
};
