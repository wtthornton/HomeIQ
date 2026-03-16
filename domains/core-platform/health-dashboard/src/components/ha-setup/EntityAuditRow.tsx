import React, { useState } from 'react';
import type { EntityRecord, AuditScore } from '../../hooks/useEntityAudit';
import { LabelEditor } from './LabelEditor';
import { AliasEditor } from './AliasEditor';
import { NameEditor } from './NameEditor';

interface Props {
  entity: EntityRecord;
  score: AuditScore;
  areaNames: string[];
  darkMode: boolean;
  selected: boolean;
  onToggleSelect: (entityId: string) => void;
  onUpdateLabels: (entityId: string, labels: string[]) => Promise<void>;
  onUpdateAliases: (entityId: string, aliases: string[]) => Promise<void>;
  onUpdateName: (entityId: string, name: string) => Promise<void>;
}

export const EntityAuditRow: React.FC<Props> = ({
  entity, score, areaNames, darkMode, selected,
  onToggleSelect, onUpdateLabels, onUpdateAliases, onUpdateName,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [editPanel, setEditPanel] = useState<'labels' | 'aliases' | 'name' | null>(null);

  const bg = darkMode ? 'hover:bg-gray-750' : 'hover:bg-gray-50';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';
  const border = darkMode ? 'border-gray-700' : 'border-gray-200';
  const fname = entity.friendly_name || entity.name || entity.original_name || entity.entity_id;

  const scoreColor = score.total >= 70 ? 'text-green-500' : score.total >= 40 ? 'text-yellow-500' : 'text-red-500';
  const scoreBg = score.total >= 70
    ? (darkMode ? 'bg-green-900/30' : 'bg-green-50')
    : score.total >= 40
      ? (darkMode ? 'bg-yellow-900/30' : 'bg-yellow-50')
      : (darkMode ? 'bg-red-900/30' : 'bg-red-50');

  return (
    <div className={`border-b ${border}`}>
      <div
        className={`flex items-center gap-3 px-4 py-2 cursor-pointer ${bg}`}
        onClick={() => setExpanded(!expanded)}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => { e.stopPropagation(); onToggleSelect(entity.entity_id); }}
          className="h-4 w-4 rounded"
          onClick={(e) => e.stopPropagation()}
        />
        <div className="flex-1 min-w-0">
          <div className={`text-sm font-medium truncate ${text}`}>{fname}</div>
          <div className={`text-xs truncate ${muted}`}>{entity.entity_id}</div>
        </div>
        <div className={`text-xs w-20 text-center ${muted}`}>
          {entity.area_id ? entity.area_id.replace(/_/g, ' ') : '—'}
        </div>
        <div className={`text-xs w-14 text-center ${muted}`}>
          {(entity.labels || []).length}
        </div>
        <div className={`text-xs w-14 text-center ${muted}`}>
          {(entity.aliases || []).length}
        </div>
        <div className={`text-xs w-14 text-center font-bold px-2 py-0.5 rounded ${scoreColor} ${scoreBg}`}>
          {score.total}
        </div>
        <div className="w-6 text-center">
          {score.issues.length > 0 ? (
            <span className="text-yellow-500" title={score.issues.join(', ')}>
              {'!'.repeat(Math.min(score.issues.length, 3))}
            </span>
          ) : (
            <span className="text-green-500">OK</span>
          )}
        </div>
      </div>

      {expanded && (
        <div className={`px-4 py-3 ${darkMode ? 'bg-gray-800/50' : 'bg-gray-50'}`}>
          {/* Issues */}
          {score.issues.length > 0 && (
            <div className="mb-3">
              <span className={`text-xs font-medium ${muted}`}>Issues:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {score.issues.map((issue, i) => (
                  <span
                    key={i}
                    className={`text-xs px-2 py-0.5 rounded ${darkMode ? 'bg-yellow-900/40 text-yellow-300' : 'bg-yellow-100 text-yellow-800'}`}
                  >
                    {issue}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quick action buttons */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setEditPanel(editPanel === 'labels' ? null : 'labels')}
              className={`text-xs px-3 py-1 rounded ${editPanel === 'labels'
                ? 'bg-blue-600 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
              }`}
            >
              Edit Labels
            </button>
            <button
              onClick={() => setEditPanel(editPanel === 'aliases' ? null : 'aliases')}
              className={`text-xs px-3 py-1 rounded ${editPanel === 'aliases'
                ? 'bg-blue-600 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
              }`}
            >
              Edit Aliases
            </button>
            <button
              onClick={() => setEditPanel(editPanel === 'name' ? null : 'name')}
              className={`text-xs px-3 py-1 rounded ${editPanel === 'name'
                ? 'bg-blue-600 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
              }`}
            >
              Edit Name
            </button>
          </div>

          {/* Inline editors */}
          {editPanel === 'labels' && (
            <LabelEditor
              entity={entity}
              darkMode={darkMode}
              onSave={(labels) => onUpdateLabels(entity.entity_id, labels)}
            />
          )}
          {editPanel === 'aliases' && (
            <AliasEditor
              entity={entity}
              darkMode={darkMode}
              onSave={(aliases) => onUpdateAliases(entity.entity_id, aliases)}
            />
          )}
          {editPanel === 'name' && (
            <NameEditor
              entity={entity}
              areaNames={areaNames}
              darkMode={darkMode}
              onSave={(name) => onUpdateName(entity.entity_id, name)}
            />
          )}
        </div>
      )}
    </div>
  );
};
