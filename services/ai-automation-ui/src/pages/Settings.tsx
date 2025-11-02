/**
 * Settings Page
 * Configure AI automation preferences
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';

interface Settings {
  scheduleEnabled: boolean;
  scheduleTime: string;
  minConfidence: number;
  maxSuggestions: number;
  enabledCategories: {
    energy: boolean;
    comfort: boolean;
    security: boolean;
    convenience: boolean;
  };
  budgetLimit: number;
  notificationsEnabled: boolean;
  notificationEmail: string;
}

export const Settings: React.FC = () => {
  const { darkMode } = useAppStore();
  const [settings, setSettings] = useState<Settings>({
    scheduleEnabled: true,
    scheduleTime: '03:00',
    minConfidence: 70,
    maxSuggestions: 10,
    enabledCategories: {
      energy: true,
      comfort: true,
      security: true,
      convenience: true,
    },
    budgetLimit: 10,
    notificationsEnabled: false,
    notificationEmail: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const saved = localStorage.getItem('ai-automation-settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    }
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      // Save to localStorage
      localStorage.setItem('ai-automation-settings', JSON.stringify(settings));
      
      // In a real implementation, you'd also send to the backend API
      // await api.updateSettings(settings);
      
      toast.success('✅ Settings saved successfully!');
    } catch (error) {
      toast.error('❌ Failed to save settings');
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm('Reset all settings to defaults?')) {
      setSettings({
        scheduleEnabled: true,
        scheduleTime: '03:00',
        minConfidence: 70,
        maxSuggestions: 10,
        enabledCategories: {
          energy: true,
          comfort: true,
          security: true,
          convenience: true,
        },
        budgetLimit: 10,
        notificationsEnabled: false,
        notificationEmail: '',
      });
      toast.success('✅ Settings reset to defaults');
    }
  };

  const estimatedCost = () => {
    const costPerRun = 0.0025;
    const runsPerMonth = settings.scheduleEnabled ? 30 : 0;
    return (costPerRun * runsPerMonth).toFixed(3);
  };

  return (
    <div className="space-y-6" data-testid="settings-container">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className={`text-3xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          ⚙️ Settings
        </h1>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
          Configure your AI automation preferences
        </p>
      </motion.div>

      {/* Settings Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSave(); }} className="space-y-6" data-testid="settings-form">
        {/* Analysis Schedule Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📅 Analysis Schedule
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Enable Daily Analysis
              </label>
              <input
                type="checkbox"
                checked={settings.scheduleEnabled}
                onChange={(e) => setSettings({ ...settings, scheduleEnabled: e.target.checked })}
                className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </div>

            {settings.scheduleEnabled && (
              <div>
                <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Run Time (24-hour format)
                </label>
                <input
                  type="time"
                  value={settings.scheduleTime}
                  onChange={(e) => setSettings({ ...settings, scheduleTime: e.target.value })}
                  className={`px-4 py-2 rounded-lg border ${
                    darkMode
                      ? 'bg-gray-700 border-gray-600 text-white'
                      : 'bg-white border-gray-300 text-gray-900'
                  } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                />
              </div>
            )}
          </div>
        </div>

        {/* Confidence & Quality Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🎯 Confidence & Quality
          </h2>
          
          <div className="space-y-6">
            <div>
              <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Minimum Confidence Threshold: {settings.minConfidence}%
              </label>
              <input
                type="range"
                min="50"
                max="95"
                step="5"
                value={settings.minConfidence}
                onChange={(e) => setSettings({ ...settings, minConfidence: parseInt(e.target.value) })}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
              />
              <div className="flex justify-between text-sm text-gray-500 mt-1">
                <span>50%</span>
                <span>95%</span>
              </div>
            </div>

            <div>
              <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Maximum Suggestions Per Run
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={settings.maxSuggestions}
                onChange={(e) => setSettings({ ...settings, maxSuggestions: parseInt(e.target.value) })}
                className={`px-4 py-2 rounded-lg border w-full ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-gray-900'
                } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              />
            </div>
          </div>
        </div>

        {/* Category Preferences Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🏷️ Category Preferences
          </h2>
          
          <div className="space-y-3">
            {Object.entries(settings.enabledCategories).map(([category, enabled]) => (
              <div key={category} className="flex items-center justify-between">
                <label className={`font-medium capitalize ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {category}
                </label>
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    enabledCategories: {
                      ...settings.enabledCategories,
                      [category]: e.target.checked
                    }
                  })}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Budget Management Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            💰 Budget Management
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Monthly Budget Limit ($)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                value={settings.budgetLimit}
                onChange={(e) => setSettings({ ...settings, budgetLimit: parseFloat(e.target.value) })}
                className={`px-4 py-2 rounded-lg border w-full ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-gray-900'
                } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              />
            </div>

            <div className={`p-4 rounded-lg ${darkMode ? 'bg-blue-900/30 border-blue-700' : 'bg-blue-50 border-blue-200'} border`}>
              <div className="flex items-center justify-between">
                <span className={`font-medium ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
                  Estimated Monthly Cost:
                </span>
                <span className={`text-xl font-bold ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}>
                  ${estimatedCost()}
                </span>
              </div>
              <div className={`text-sm mt-2 ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
                Based on current settings ({settings.scheduleEnabled ? '30 runs/month' : '0 runs/month'})
              </div>
            </div>
          </div>
        </div>

        {/* Notification Preferences Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🔔 Notification Preferences
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Enable Notifications
              </label>
              <input
                type="checkbox"
                checked={settings.notificationsEnabled}
                onChange={(e) => setSettings({ ...settings, notificationsEnabled: e.target.checked })}
                className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </div>

            {settings.notificationsEnabled && (
              <div>
                <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Email Address
                </label>
                <input
                  type="email"
                  value={settings.notificationEmail}
                  onChange={(e) => setSettings({ ...settings, notificationEmail: e.target.value })}
                  placeholder="your.email@example.com"
                  className={`px-4 py-2 rounded-lg border w-full ${
                    darkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                  } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                />
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <motion.button
            type="submit"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            disabled={saving}
            className={`flex-1 px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-500 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {saving ? '💾 Saving...' : '💾 Save Settings'}
          </motion.button>

          <motion.button
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleReset}
            className={`px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
            }`}
          >
            🔄 Reset to Defaults
          </motion.button>
        </div>
      </form>
    </div>
  );
};

