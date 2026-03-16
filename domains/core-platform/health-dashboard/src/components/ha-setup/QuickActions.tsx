import React, { useState } from 'react';
import type { EntityRecord } from '../../hooks/useEntityAudit';

interface Props {
  entities: EntityRecord[];
  darkMode: boolean;
  onBulkLabel: (entityIds: string[], addLabels: string[], removeLabels?: string[]) => Promise<void>;
}

interface QuickActionDef {
  label: string;
  description: string;
  getEntityIds: (entities: EntityRecord[]) => string[];
  addLabels: string[];
}

const QUICK_ACTIONS: QuickActionDef[] = [
  {
    label: 'Label all lights as ai:automatable',
    description: 'All light.* entities',
    getEntityIds: (entities) => entities.filter(e => e.domain === 'light' && !(e.labels || []).includes('ai:automatable')).map(e => e.entity_id),
    addLabels: ['ai:automatable'],
  },
  {
    label: 'Label all switches as ai:automatable',
    description: 'All switch.* entities',
    getEntityIds: (entities) => entities.filter(e => e.domain === 'switch' && !(e.labels || []).includes('ai:automatable')).map(e => e.entity_id),
    addLabels: ['ai:automatable'],
  },
  {
    label: 'Label battery sensors as ai:ignore',
    description: 'Sensors with device_class=battery',
    getEntityIds: (entities) => entities.filter(e => e.device_class === 'battery' && !(e.labels || []).includes('ai:ignore')).map(e => e.entity_id),
    addLabels: ['ai:ignore'],
  },
  {
    label: 'Label motion sensors as sensor:trigger',
    description: 'binary_sensor with device_class=motion',
    getEntityIds: (entities) => entities.filter(e => e.device_class === 'motion' && !(e.labels || []).includes('sensor:trigger')).map(e => e.entity_id),
    addLabels: ['sensor:trigger'],
  },
  {
    label: 'Label temperature sensors as sensor:primary',
    description: 'Sensors with device_class=temperature',
    getEntityIds: (entities) => entities.filter(e => e.device_class === 'temperature' && !(e.labels || []).includes('sensor:primary')).map(e => e.entity_id),
    addLabels: ['sensor:primary'],
  },
  {
    label: 'Label climate entities as group:climate',
    description: 'All climate.* entities',
    getEntityIds: (entities) => entities.filter(e => e.domain === 'climate' && !(e.labels || []).includes('group:climate')).map(e => e.entity_id),
    addLabels: ['group:climate'],
  },
];

export const QuickActions: React.FC<Props> = ({ entities, darkMode, onBulkLabel }) => {
  const [running, setRunning] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';

  const handleAction = async (action: QuickActionDef) => {
    const ids = action.getEntityIds(entities);
    if (ids.length === 0) {
      setLastResult(`No entities need "${action.addLabels.join(', ')}"`);
      return;
    }
    setRunning(action.label);
    try {
      await onBulkLabel(ids, action.addLabels);
      setLastResult(`Applied ${action.addLabels.join(', ')} to ${ids.length} entities`);
    } catch {
      setLastResult('Failed to apply labels');
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className={`rounded-lg border p-4 ${bg}`}>
      <h3 className={`text-sm font-medium mb-3 ${text}`}>Domain Quick Actions</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {QUICK_ACTIONS.map(action => {
          const count = action.getEntityIds(entities).length;
          return (
            <button
              key={action.label}
              onClick={() => handleAction(action)}
              disabled={running !== null || count === 0}
              className={`text-left p-2 rounded border text-xs ${
                count > 0
                  ? darkMode ? 'border-gray-600 hover:bg-gray-700' : 'border-gray-200 hover:bg-gray-50'
                  : 'opacity-50 cursor-not-allowed border-gray-600'
              }`}
            >
              <div className={`font-medium ${text}`}>
                {running === action.label ? 'Applying...' : action.label}
              </div>
              <div className={muted}>
                {action.description} — {count} eligible
              </div>
            </button>
          );
        })}
      </div>
      {lastResult && (
        <div className={`text-xs mt-2 ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
          {lastResult}
        </div>
      )}
    </div>
  );
};
