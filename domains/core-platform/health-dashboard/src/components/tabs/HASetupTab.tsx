import React from 'react';
import type { TabProps } from './types';
import { useEntityAudit } from '../../hooks/useEntityAudit';
import type { SubView } from '../../hooks/useEntityAudit';
import { EntityAuditView } from '../ha-setup/EntityAuditView';
import { ExclusionManager } from '../ha-setup/ExclusionManager';

const SUB_VIEWS: { id: SubView; label: string }[] = [
  { id: 'audit', label: 'Audit' },
  { id: 'labels', label: 'Labels' },
  { id: 'aliases', label: 'Aliases' },
  { id: 'exclusions', label: 'Exclusions' },
];

export const HASetupTab: React.FC<TabProps> = ({ darkMode }) => {
  const {
    entities, areas, labelsList, loading, error, scores,
    subView, setSubView, refresh,
    updateEntityLabels, updateEntityAliases, updateEntityName, bulkAddLabels,
  } = useEntityAudit();

  const bg = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';

  if (loading) {
    return (
      <div className={`p-6 ${bg}`}>
        <div className="animate-pulse space-y-4">
          <div className={`h-8 w-48 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} />
          <div className={`h-24 rounded ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`} />
          <div className={`h-64 rounded ${darkMode ? 'bg-gray-800' : 'bg-gray-200'}`} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-6 ${bg}`}>
        <div className="text-red-500 mb-4">Failed to load entity data: {error}</div>
        <button onClick={refresh} className="text-sm px-3 py-1 bg-blue-600 text-white rounded">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`p-6 ${bg} min-h-full`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className={`text-lg font-semibold ${text}`}>HA Setup</h2>
        <button
          onClick={refresh}
          className={`text-xs px-3 py-1 rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'} hover:opacity-80`}
        >
          Refresh
        </button>
      </div>

      {/* Sub-navigation */}
      <div className="flex gap-1 mb-4">
        {SUB_VIEWS.map(sv => (
          <button
            key={sv.id}
            onClick={() => setSubView(sv.id)}
            className={`text-sm px-4 py-1.5 rounded-t ${
              subView === sv.id
                ? 'bg-blue-600 text-white'
                : darkMode ? 'bg-gray-800 text-gray-400 hover:text-gray-200' : 'bg-gray-200 text-gray-600 hover:text-gray-900'
            }`}
          >
            {sv.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {(subView === 'audit' || subView === 'labels' || subView === 'aliases') && (
        <EntityAuditView
          entities={entities}
          scores={scores}
          areas={areas}
          darkMode={darkMode}
          onUpdateLabels={updateEntityLabels}
          onUpdateAliases={updateEntityAliases}
          onUpdateName={updateEntityName}
          onBulkLabel={bulkAddLabels}
        />
      )}

      {subView === 'exclusions' && (
        <ExclusionManager entities={entities} darkMode={darkMode} />
      )}

      {/* Stats footer */}
      <div className={`mt-4 text-xs ${muted}`}>
        {entities.length} entities | {areas.length} areas | {labelsList.length} distinct labels
      </div>
    </div>
  );
};
