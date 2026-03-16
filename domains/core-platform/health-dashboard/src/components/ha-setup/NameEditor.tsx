import React, { useState, useMemo } from 'react';
import type { EntityRecord } from '../../hooks/useEntityAudit';

interface Props {
  entity: EntityRecord;
  areaNames: string[];
  darkMode: boolean;
  onSave: (name: string) => Promise<void>;
}

const BRAND_PATTERNS = [
  /philips/i, /hue/i, /aqara/i, /ikea/i, /tradfri/i, /sonoff/i,
  /shelly/i, /zigbee/i, /z-wave/i, /tuya/i, /xiaomi/i,
];

interface ConventionCheck {
  label: string;
  pass: boolean;
  hint?: string;
}

export const NameEditor: React.FC<Props> = ({ entity, areaNames, darkMode, onSave }) => {
  const currentName = entity.friendly_name || entity.name || entity.original_name || '';
  const [name, setName] = useState(currentName);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const inputBg = darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300';

  // Generate a suggested name
  const suggestion = useMemo(() => {
    const area = entity.area_id?.replace(/_/g, ' ') || '';
    const deviceClass = entity.device_class || '';
    const domain = entity.domain || '';

    // Build a reasonable suggestion
    const areaTitle = area.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    let typeWord = '';
    if (deviceClass) {
      typeWord = deviceClass.charAt(0).toUpperCase() + deviceClass.slice(1);
    } else if (domain === 'light') {
      typeWord = 'Light';
    } else if (domain === 'switch') {
      typeWord = 'Switch';
    } else if (domain === 'sensor') {
      typeWord = 'Sensor';
    } else if (domain === 'binary_sensor') {
      typeWord = 'Sensor';
    } else if (domain === 'climate') {
      typeWord = 'Thermostat';
    } else if (domain === 'cover') {
      typeWord = 'Cover';
    } else if (domain === 'fan') {
      typeWord = 'Fan';
    } else if (domain === 'media_player') {
      typeWord = 'Media';
    } else {
      typeWord = domain.charAt(0).toUpperCase() + domain.slice(1);
    }

    return areaTitle ? `${areaTitle} ${typeWord}` : typeWord;
  }, [entity.area_id, entity.device_class, entity.domain]);

  // Convention checks
  const checks = useMemo((): ConventionCheck[] => {
    if (!name) return [];
    const result: ConventionCheck[] = [];

    // Starts with area name
    const areaId = entity.area_id || '';
    const areaDisplay = areaId.replace(/_/g, ' ');
    const startsWithArea = areaNames.some(a =>
      name.toLowerCase().startsWith(a.toLowerCase())
    ) || (areaDisplay && name.toLowerCase().startsWith(areaDisplay.toLowerCase()));
    result.push({
      label: `Starts with area name${areaDisplay ? ` (${areaDisplay})` : ''}`,
      pass: startsWithArea || !areaId,
      hint: areaId ? `Start with "${areaDisplay.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}"` : undefined,
    });

    // Title Case
    const isTitleCase = name.split(/\s+/).every(w => w.length === 0 || w[0] === w[0].toUpperCase());
    result.push({ label: 'Title Case', pass: isTitleCase });

    // No manufacturer name
    const hasBrand = BRAND_PATTERNS.some(p => p.test(name));
    result.push({ label: 'No manufacturer name', pass: !hasBrand });

    // No model number
    const hasModel = /\b[A-Z]{2,}\d{2,}|#\d+|\b\d{4,}\b/.test(name);
    result.push({ label: 'No model number', pass: !hasModel });

    // Appropriate length
    result.push({
      label: 'Reasonable length',
      pass: name.length >= 3 && name.length <= 50,
      hint: name.length < 3 ? 'Too short' : name.length > 50 ? 'Too long' : undefined,
    });

    return result;
  }, [name, entity.area_id, areaNames]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(name.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = name !== currentName;

  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <div className="text-xs font-medium mb-2 text-gray-400">
        Friendly Name for {entity.entity_id}
      </div>

      <div className="mb-2">
        <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Current: {currentName || '(none)'}
        </span>
      </div>

      {suggestion && suggestion !== currentName && (
        <div className="mb-2">
          <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Suggested:{' '}
          </span>
          <button
            onClick={() => setName(suggestion)}
            className={`text-xs underline ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}
          >
            {suggestion}
          </button>
        </div>
      )}

      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className={`text-sm rounded border px-2 py-1 w-full mb-3 ${inputBg}`}
      />

      {/* Convention checks */}
      <div className="space-y-1 mb-3">
        {checks.map(c => (
          <div key={c.label} className="flex items-center gap-2 text-xs">
            <span className={c.pass ? 'text-green-500' : 'text-yellow-500'}>
              {c.pass ? '\u2713' : '\u26A0'}
            </span>
            <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
              {c.label}
            </span>
            {c.hint && !c.pass && (
              <span className="text-gray-500">({c.hint})</span>
            )}
          </div>
        ))}
      </div>

      {error && <div className="text-xs text-red-500 mb-2">{error}</div>}

      <div className="flex gap-2">
        {hasChanges && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        )}
        {suggestion && suggestion !== name && (
          <button
            onClick={() => setName(suggestion)}
            className={`text-xs px-3 py-1 rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'}`}
          >
            Use Suggestion
          </button>
        )}
      </div>
    </div>
  );
};
