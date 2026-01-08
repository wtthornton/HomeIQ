/**
 * ThresholdConfig Component
 * 
 * Configure custom metric thresholds and alert preferences
 * Epic 15.4: Custom Thresholds & Personalization
 */

import React, { useState, useEffect } from 'react';

interface Threshold {
  metric: string;
  warning: number;
  critical: number;
  enabled: boolean;
}

interface UserPreferences {
  thresholds: Threshold[];
  notifications: {
    browser: boolean;
    sound: boolean;
    email: boolean;
  };
  refreshInterval: number;
  timezone: string;
}

interface ThresholdConfigProps {
  darkMode: boolean;
  onSave: (preferences: UserPreferences) => void;
}

const DEFAULT_THRESHOLDS: Threshold[] = [
  { metric: 'events_per_minute', warning: 100, critical: 200, enabled: true },
  { metric: 'error_rate', warning: 5, critical: 10, enabled: true },
  { metric: 'response_time', warning: 500, critical: 1000, enabled: true },
  { metric: 'api_usage', warning: 80, critical: 95, enabled: true }
];

const DEFAULT_PREFERENCES: UserPreferences = {
  thresholds: DEFAULT_THRESHOLDS,
  notifications: {
    browser: true,
    sound: false,
    email: false
  },
  refreshInterval: 30,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
};

export const ThresholdConfig: React.FC<ThresholdConfigProps> = ({ darkMode, onSave }) => {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [hasChanges, setHasChanges] = useState(false);

  // Load saved preferences with full error handling
  useEffect(() => {
    try {
      if (typeof window === 'undefined') return;
      
      const saved = localStorage.getItem('user-preferences');
      if (saved) {
        const parsed = JSON.parse(saved);
        setPreferences(parsed);
      }
    } catch (e) {
      console.error('Failed to load preferences from localStorage:', e);
      // Continue with default preferences
    }
  }, []);

  // Update threshold
  const updateThreshold = (index: number, field: keyof Threshold, value: any) => {
    setPreferences(prev => ({
      ...prev,
      thresholds: prev.thresholds.map((t, i) => 
        i === index ? { ...t, [field]: value } : t
      )
    }));
    setHasChanges(true);
  };

  // Update notification preference
  const updateNotification = (type: keyof UserPreferences['notifications'], value: boolean) => {
    setPreferences(prev => ({
      ...prev,
      notifications: { ...prev.notifications, [type]: value }
    }));
    setHasChanges(true);
  };

  // Save preferences with error handling
  const handleSave = () => {
    try {
      localStorage.setItem('user-preferences', JSON.stringify(preferences));
    } catch (error) {
      console.error('Failed to save preferences to localStorage:', error);
      // Still notify parent even if localStorage fails
    }
    onSave(preferences);
    setHasChanges(false);
  };

  // Reset to defaults
  const handleReset = () => {
    setPreferences(DEFAULT_PREFERENCES);
    setHasChanges(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={'card-base p-6'}>
        <h2 className={`text-h2 ${darkMode ? 'text-white' : 'text-gray-900'} mb-2`}>
          ⚙️ Preferences & Thresholds
        </h2>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Customize alert thresholds and dashboard preferences
        </p>
      </div>

      {/* Metric Thresholds */}
      <div className={'card-base p-6'}>
        <h3 className={`text-h3 ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          📊 Metric Thresholds
        </h3>
        
        <div className="space-y-4">
          {preferences.thresholds.map((threshold, index) => (
            <div key={threshold.metric} className={`p-4 rounded-lg border ${
              darkMode ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-gray-50'
            }`}>
              <div className="flex items-center justify-between mb-3">
                <label className={`font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {threshold.metric.replace(/_/g, ' ').toUpperCase()}
                </label>
                <input
                  type="checkbox"
                  checked={threshold.enabled}
                  onChange={(e) => updateThreshold(index, 'enabled', e.target.checked)}
                  className="w-5 h-5"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-1 block`}>
                    Warning Threshold
                  </label>
                  <input
                    type="number"
                    value={threshold.warning}
                    onChange={(e) => updateThreshold(index, 'warning', Number(e.target.value))}
                    disabled={!threshold.enabled}
                    className="input-base"
                  />
                </div>
                <div>
                  <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-1 block`}>
                    Critical Threshold
                  </label>
                  <input
                    type="number"
                    value={threshold.critical}
                    onChange={(e) => updateThreshold(index, 'critical', Number(e.target.value))}
                    disabled={!threshold.enabled}
                    className="input-base"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Notification Preferences */}
      <div className={'card-base p-6'}>
        <h3 className={`text-h3 ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          🔔 Notification Preferences
        </h3>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className={`${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Browser Notifications
            </label>
            <input
              type="checkbox"
              checked={preferences.notifications.browser}
              onChange={(e) => updateNotification('browser', e.target.checked)}
              className="w-5 h-5"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <label className={`${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Sound Alerts
            </label>
            <input
              type="checkbox"
              checked={preferences.notifications.sound}
              onChange={(e) => updateNotification('sound', e.target.checked)}
              className="w-5 h-5"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <label className={`${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Email Notifications
            </label>
            <input
              type="checkbox"
              checked={preferences.notifications.email}
              onChange={(e) => updateNotification('email', e.target.checked)}
              className="w-5 h-5"
            />
          </div>
        </div>
      </div>

      {/* General Preferences */}
      <div className={'card-base p-6'}>
        <h3 className={`text-h3 ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          🎨 General Preferences
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-1 block`}>
              Refresh Interval (seconds)
            </label>
            <select
              value={preferences.refreshInterval}
              onChange={(e) => {
                setPreferences(prev => ({ ...prev, refreshInterval: Number(e.target.value) }));
                setHasChanges(true);
              }}
              className="input-base w-full"
            >
              <option value={5}>5 seconds</option>
              <option value={15}>15 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>1 minute</option>
              <option value={300}>5 minutes</option>
            </select>
          </div>
          
          <div>
            <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-1 block`}>
              Timezone
            </label>
            <input
              type="text"
              value={preferences.timezone}
              onChange={(e) => {
                setPreferences(prev => ({ ...prev, timezone: e.target.value }));
                setHasChanges(true);
              }}
              className="input-base w-full"
              placeholder="America/New_York"
            />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3">
        <button
          onClick={handleReset}
          className="btn-secondary"
          disabled={!hasChanges}
        >
          🔄 Reset to Defaults
        </button>
        <button
          onClick={handleSave}
          className="btn-primary"
          disabled={!hasChanges}
        >
          💾 Save Preferences
        </button>
      </div>
    </div>
  );
};

