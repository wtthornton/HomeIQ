/**
 * Settings Page
 * Configure AI automation preferences
 */

import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store';
import {
  defaultSettings,
  getSettings,
  updateSettings,
  type SettingsPayload,
} from '../api/settings';
import { TeamTrackerSettings } from '../components/TeamTrackerSettings';
import { ModelComparisonMetricsComponent } from '../components/ModelComparisonMetrics';
import { PreferenceSettings } from '../components/PreferenceSettings';

export const Settings: React.FC = () => {
  const { darkMode } = useAppStore();
  const queryClient = useQueryClient();

  const [settings, setSettings] = useState<SettingsPayload>(() => ({
    ...defaultSettings,
    enabledCategories: { ...defaultSettings.enabledCategories },
  }));
  const [hasLoaded, setHasLoaded] = useState(false);

  const {
    data: remoteSettings,
    isLoading,
    isFetching,
    isError,
    error,
  } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (remoteSettings) {
      setSettings({
        ...remoteSettings,
        enabledCategories: { ...remoteSettings.enabledCategories },
      });
      setHasLoaded(true);
    }
  }, [remoteSettings]);

  useEffect(() => {
    if (isError && !hasLoaded) {
      toast.error('⚠️ Unable to load settings from server. Using local defaults.');
      setSettings({
        ...defaultSettings,
        enabledCategories: { ...defaultSettings.enabledCategories },
      });
      setHasLoaded(true);
      console.error('Settings load error:', error);
    }
  }, [isError, hasLoaded, error]);

  const mutation = useMutation({
    mutationFn: updateSettings,
    onMutate: async (newSettings) => {
      await queryClient.cancelQueries({ queryKey: ['settings'] });
      const previous = queryClient.getQueryData<SettingsPayload>(['settings']);
      const optimistic = {
        ...newSettings,
        enabledCategories: { ...newSettings.enabledCategories },
      };
      queryClient.setQueryData(['settings'], optimistic);
      setSettings(optimistic);
      return { previous };
    },
    onError: (err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['settings'], context.previous);
        setSettings(context.previous);
      }
      toast.error('❌ Failed to save settings');
      console.error('Settings save error:', err);
    },
    onSuccess: (savedSettings) => {
      const normalized = {
        ...savedSettings,
        enabledCategories: { ...savedSettings.enabledCategories },
      };
      queryClient.setQueryData(['settings'], normalized);
      setSettings(normalized);
      toast.success('✅ Settings saved successfully!');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleSave = () => {
    const payload: SettingsPayload = {
      ...settings,
      enabledCategories: { ...settings.enabledCategories },
    };
    mutation.mutate(payload);
  };

  const handleReset = () => {
    if (confirm('Reset all settings to defaults?')) {
      const resetPayload: SettingsPayload = {
        ...defaultSettings,
        enabledCategories: { ...defaultSettings.enabledCategories },
      };
      setSettings(resetPayload);
      mutation.mutate(resetPayload);
    }
  };

  const estimatedCost = useMemo(() => {
    const costPerRun = 0.0025;
    const runsPerMonth = settings.scheduleEnabled ? 30 : 0;
    return (costPerRun * runsPerMonth).toFixed(3);
  }, [settings.scheduleEnabled]);

  const isSaving = mutation.isPending;
  const showLoadingState = isLoading && !hasLoaded;

  return (
    <div className="space-y-6" data-testid="settings-container">
      {/* Header - Modern 2025 Design */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex items-center gap-3 mb-1">
          <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            ⚙️ Settings
          </h1>
        </div>
        <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Configure your AI automation preferences
        </p>
      </motion.div>

      {showLoadingState && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-xl p-6 border text-sm ${darkMode ? 'bg-slate-900/60 border-gray-700/50 text-gray-200 backdrop-blur-sm' : 'bg-white/80 border-gray-200/50 text-gray-600 backdrop-blur-sm'}`}
        >
          Loading latest settings from server...
        </motion.div>
      )}

      {/* Settings Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSave(); }} className="space-y-6" data-testid="settings-form">
        {/* Analysis Schedule Section - Glassmorphism */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={`rounded-xl p-6 shadow-lg ${
            darkMode 
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
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
        </motion.div>

        {/* Confidence & Quality Section - Glassmorphism */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`rounded-xl p-6 shadow-lg ${
            darkMode 
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
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
                onChange={(e) => setSettings({ ...settings, minConfidence: parseInt(e.target.value, 10) })}
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
                onChange={(e) => setSettings({ ...settings, maxSuggestions: parseInt(e.target.value, 10) || 1 })}
                className={`px-4 py-2 rounded-lg border w-full ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-gray-900'
                } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              />
            </div>
          </div>
        </motion.div>

        {/* Category Preferences Section - Glassmorphism */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`rounded-xl p-6 shadow-lg ${
            darkMode 
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          }`}
        >
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
        </motion.div>

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
                onChange={(e) => setSettings({ ...settings, budgetLimit: parseFloat(e.target.value) || 0 })}
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
                  ${estimatedCost}
                </span>
              </div>
              <div className={`text-sm mt-2 ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
                Based on current settings ({settings.scheduleEnabled ? '30 runs/month' : '0 runs/month'})
              </div>
            </div>
          </div>
        </div>

        {/* Parallel Model Testing Section */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🤖 Parallel Model Testing
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Enable Parallel Testing
                </label>
                <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Run multiple models in parallel to compare quality and cost
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enableParallelModelTesting || false}
                onChange={(e) => setSettings({ ...settings, enableParallelModelTesting: e.target.checked })}
                className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </div>
            
            {settings.enableParallelModelTesting && (
              <div className="mt-4 space-y-3 pl-4 border-l-2 border-blue-500">
                <div>
                  <label className={`text-sm font-medium block mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Suggestion Models
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={settings.parallelTestingModels?.suggestion?.[0] || 'gpt-4o'}
                      onChange={(e) => {
                        const model1 = e.target.value;
                        const model2 = settings.parallelTestingModels?.suggestion?.[1] || 'gpt-4o-mini';
                        setSettings({
                          ...settings,
                          parallelTestingModels: {
                            suggestion: [model1, model2],
                            yaml: settings.parallelTestingModels?.yaml || ["gpt-4o", "gpt-4o-mini"]
                          }
                        });
                      }}
                      className={`px-4 py-2 rounded-lg border ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    >
                      <optgroup label="Latest Models (2025)">
                        <option value="gpt-5.1">GPT-5.1 (Latest)</option>
                        <option value="gpt-5">GPT-5</option>
                        <option value="gpt-4.1">GPT-4.1</option>
                      </optgroup>
                      <optgroup label="GPT-4o Series">
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o-mini</option>
                      </optgroup>
                      <optgroup label="GPT-4 Series">
                        <option value="gpt-4-turbo">GPT-4 Turbo</option>
                        <option value="gpt-4">GPT-4</option>
                      </optgroup>
                      <optgroup label="Reasoning Models (o-series)">
                        <option value="o1">o1</option>
                        <option value="o1-mini">o1-mini</option>
                        <option value="o1-preview">o1-preview</option>
                        <option value="o3">o3</option>
                        <option value="o3-mini">o3-mini</option>
                        <option value="o4-mini">o4-mini</option>
                      </optgroup>
                      <optgroup label="Legacy Models">
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </optgroup>
                    </select>
                    <select
                      value={settings.parallelTestingModels?.suggestion?.[1] || 'gpt-4o-mini'}
                      onChange={(e) => {
                        const model1 = settings.parallelTestingModels?.suggestion?.[0] || 'gpt-4o';
                        const model2 = e.target.value;
                        setSettings({
                          ...settings,
                          parallelTestingModels: {
                            suggestion: [model1, model2],
                            yaml: settings.parallelTestingModels?.yaml || ["gpt-4o", "gpt-4o-mini"]
                          }
                        });
                      }}
                      className={`px-4 py-2 rounded-lg border ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    >
                      <optgroup label="Latest Models (2025)">
                        <option value="gpt-5.1">GPT-5.1 (Latest)</option>
                        <option value="gpt-5">GPT-5</option>
                        <option value="gpt-4.1">GPT-4.1</option>
                      </optgroup>
                      <optgroup label="GPT-4o Series">
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o-mini</option>
                      </optgroup>
                      <optgroup label="GPT-4 Series">
                        <option value="gpt-4-turbo">GPT-4 Turbo</option>
                        <option value="gpt-4">GPT-4</option>
                      </optgroup>
                      <optgroup label="Reasoning Models (o-series)">
                        <option value="o1">o1</option>
                        <option value="o1-mini">o1-mini</option>
                        <option value="o1-preview">o1-preview</option>
                        <option value="o3">o3</option>
                        <option value="o3-mini">o3-mini</option>
                        <option value="o4-mini">o4-mini</option>
                      </optgroup>
                      <optgroup label="Legacy Models">
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </optgroup>
                    </select>
                  </div>
                  <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Compare Model 1 vs Model 2 for suggestion generation
                  </p>
                </div>
                <div>
                  <label className={`text-sm font-medium block mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    YAML Generation Models
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={settings.parallelTestingModels?.yaml?.[0] || 'gpt-4o'}
                      onChange={(e) => {
                        const model1 = e.target.value;
                        const model2 = settings.parallelTestingModels?.yaml?.[1] || 'gpt-4o-mini';
                        setSettings({
                          ...settings,
                          parallelTestingModels: {
                            suggestion: settings.parallelTestingModels?.suggestion || ["gpt-4o", "gpt-4o-mini"],
                            yaml: [model1, model2]
                          }
                        });
                      }}
                      className={`px-4 py-2 rounded-lg border ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    >
                      <optgroup label="Latest Models (2025)">
                        <option value="gpt-5.1">GPT-5.1 (Latest)</option>
                        <option value="gpt-5">GPT-5</option>
                        <option value="gpt-4.1">GPT-4.1</option>
                      </optgroup>
                      <optgroup label="GPT-4o Series">
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o-mini</option>
                      </optgroup>
                      <optgroup label="GPT-4 Series">
                        <option value="gpt-4-turbo">GPT-4 Turbo</option>
                        <option value="gpt-4">GPT-4</option>
                      </optgroup>
                      <optgroup label="Reasoning Models (o-series)">
                        <option value="o1">o1</option>
                        <option value="o1-mini">o1-mini</option>
                        <option value="o1-preview">o1-preview</option>
                        <option value="o3">o3</option>
                        <option value="o3-mini">o3-mini</option>
                        <option value="o4-mini">o4-mini</option>
                      </optgroup>
                      <optgroup label="Legacy Models">
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </optgroup>
                    </select>
                    <select
                      value={settings.parallelTestingModels?.yaml?.[1] || 'gpt-4o-mini'}
                      onChange={(e) => {
                        const model1 = settings.parallelTestingModels?.yaml?.[0] || 'gpt-4o';
                        const model2 = e.target.value;
                        setSettings({
                          ...settings,
                          parallelTestingModels: {
                            suggestion: settings.parallelTestingModels?.suggestion || ["gpt-4o", "gpt-4o-mini"],
                            yaml: [model1, model2]
                          }
                        });
                      }}
                      className={`px-4 py-2 rounded-lg border ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    >
                      <optgroup label="Latest Models (2025)">
                        <option value="gpt-5.1">GPT-5.1 (Latest)</option>
                        <option value="gpt-5">GPT-5</option>
                        <option value="gpt-4.1">GPT-4.1</option>
                      </optgroup>
                      <optgroup label="GPT-4o Series">
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o-mini</option>
                      </optgroup>
                      <optgroup label="GPT-4 Series">
                        <option value="gpt-4-turbo">GPT-4 Turbo</option>
                        <option value="gpt-4">GPT-4</option>
                      </optgroup>
                      <optgroup label="Reasoning Models (o-series)">
                        <option value="o1">o1</option>
                        <option value="o1-mini">o1-mini</option>
                        <option value="o1-preview">o1-preview</option>
                        <option value="o3">o3</option>
                        <option value="o3-mini">o3-mini</option>
                        <option value="o4-mini">o4-mini</option>
                      </optgroup>
                      <optgroup label="Legacy Models">
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </optgroup>
                    </select>
                  </div>
                  <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Compare Model 1 vs Model 2 for YAML generation
                  </p>
                </div>
                <div className={`text-xs p-3 rounded-lg ${darkMode ? 'bg-yellow-900/30 border-yellow-700 text-yellow-300' : 'bg-yellow-50 border-yellow-200 text-yellow-700'} border`}>
                  ⚠️ Parallel testing doubles API costs during testing period
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Model Comparison Metrics Section */}
        {settings.enableParallelModelTesting && (
          <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <ModelComparisonMetricsComponent darkMode={darkMode} />
          </div>
        )}

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

        {/* AI Model Configuration */}
        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🤖 AI Model Configuration
          </h2>

          <div className="space-y-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Enable Soft Prompt Fallback
                </label>
                <input
                  type="checkbox"
                  checked={settings.softPromptEnabled}
                  onChange={(e) => setSettings({ ...settings, softPromptEnabled: e.target.checked })}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>

              {settings.softPromptEnabled && (
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <label className={`block font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Model Directory
                    </label>
                    <input
                      type="text"
                      value={settings.softPromptModelDir}
                      onChange={(e) => setSettings({ ...settings, softPromptModelDir: e.target.value })}
                      placeholder="data/ask_ai_soft_prompt"
                      className={`px-4 py-2 rounded-lg border w-full ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className={`block font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Confidence Threshold
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={settings.softPromptConfidenceThreshold}
                      onChange={(e) => setSettings({
                        ...settings,
                        softPromptConfidenceThreshold: Number.isFinite(Number(e.target.value))
                          ? parseFloat(e.target.value)
                          : settings.softPromptConfidenceThreshold,
                      })}
                      className={`px-4 py-2 rounded-lg border w-full ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-dashed border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center justify-between">
                <label className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Enable Guardrail Checks
                </label>
                <input
                  type="checkbox"
                  checked={settings.guardrailEnabled}
                  onChange={(e) => setSettings({ ...settings, guardrailEnabled: e.target.checked })}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>

              {settings.guardrailEnabled && (
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <label className={`block font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Model Name
                    </label>
                    <input
                      type="text"
                      value={settings.guardrailModelName}
                      onChange={(e) => setSettings({ ...settings, guardrailModelName: e.target.value })}
                      placeholder="unitary/toxic-bert"
                      className={`px-4 py-2 rounded-lg border w-full ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className={`block font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Risk Threshold
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={settings.guardrailThreshold}
                      onChange={(e) => setSettings({
                        ...settings,
                        guardrailThreshold: Number.isFinite(Number(e.target.value))
                          ? parseFloat(e.target.value)
                          : settings.guardrailThreshold,
                      })}
                      className={`px-4 py-2 rounded-lg border w-full ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-white'
                          : 'bg-white border-gray-300 text-gray-900'
                      } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {isFetching && !mutation.isPending && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`rounded-xl p-4 text-sm border ${darkMode ? 'bg-slate-900/60 border-gray-700/50 text-gray-300 backdrop-blur-sm' : 'bg-white/80 border-gray-200/50 text-gray-600 backdrop-blur-sm'}`}
          >
            Refreshing settings…
          </motion.div>
        )}

        {/* Suggestion Preferences Section - Epic AI-6 Story AI6.12 */}
        <PreferenceSettings darkMode={darkMode} userId="default" />

        {/* Team Tracker Integration */}
        <TeamTrackerSettings />

        {/* Action Buttons */}
        <div className="flex gap-4">
          <motion.button
            type="submit"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            disabled={isSaving}
            className={`flex-1 px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
              darkMode
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
            } disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none`}
          >
            {isSaving ? '💾 Saving...' : '💾 Save Settings'}
          </motion.button>

          <motion.button
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleReset}
            className={`px-4 py-2 text-xs rounded-xl font-bold shadow-lg transition-all ${
              darkMode
                ? 'bg-slate-800/60 hover:bg-slate-700/60 text-white border border-slate-700/50'
                : 'bg-white/80 hover:bg-white text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
            }`}
          >
            🔄 Reset to Defaults
          </motion.button>
        </div>
      </form>
    </div>
  );
};

