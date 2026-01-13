/**
 * Preference Settings Component
 * 
 * UI component for managing suggestion preferences:
 * - max_suggestions (slider 5-50)
 * - creativity_level (dropdown)
 * - blueprint_preference (dropdown)
 * 
 * Epic AI-6 Story AI6.12: Frontend Preference Settings UI
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { getPreferences, updatePreferences, defaultPreferences, type Preferences, type PreferenceUpdateRequest } from '../api/preferences';

interface PreferenceSettingsProps {
  darkMode: boolean;
  userId?: string;
}

export const PreferenceSettings: React.FC<PreferenceSettingsProps> = ({ darkMode, userId = 'default' }) => {
  const queryClient = useQueryClient();
  
  const [localPreferences, setLocalPreferences] = useState<Preferences>(defaultPreferences);

  const {
    data: preferences,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['preferences', userId],
    queryFn: () => getPreferences(userId),
    staleTime: 60 * 1000,
    retry: (failureCount, error) => {
      // Don't retry on 404 errors (handled gracefully by getPreferences)
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      return failureCount < 1;
    },
    // Use default preferences as initial data and fallback
    initialData: defaultPreferences,
    placeholderData: defaultPreferences,
    // Don't treat 404 as an error since we handle it gracefully
    retryOnMount: false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (preferences) {
      setLocalPreferences(preferences);
    }
  }, [preferences]);

  const mutation = useMutation({
    mutationFn: (updates: PreferenceUpdateRequest) => updatePreferences(updates, userId),
    onMutate: async (updates) => {
      await queryClient.cancelQueries({ queryKey: ['preferences', userId] });
      const previous = queryClient.getQueryData<Preferences>(['preferences', userId]);
      
      const optimistic: Preferences = {
        ...localPreferences,
        ...updates,
      };
      
      queryClient.setQueryData(['preferences', userId], optimistic);
      setLocalPreferences(optimistic);
      
      return { previous };
    },
    onError: (err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['preferences', userId], context.previous);
        setLocalPreferences(context.previous);
      }
      toast.error('❌ Failed to save preferences');
      console.error('Preference save error:', err);
    },
    onSuccess: (savedPreferences) => {
      queryClient.setQueryData(['preferences', userId], savedPreferences);
      setLocalPreferences(savedPreferences);
      toast.success('✅ Preferences saved successfully!');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['preferences', userId] });
    },
  });

  const handleMaxSuggestionsChange = (value: number) => {
    const updates: PreferenceUpdateRequest = { max_suggestions: value };
    mutation.mutate(updates);
  };

  const handleCreativityLevelChange = (value: 'conservative' | 'balanced' | 'creative') => {
    const updates: PreferenceUpdateRequest = { creativity_level: value };
    mutation.mutate(updates);
  };

  const handleBlueprintPreferenceChange = (value: 'low' | 'medium' | 'high') => {
    const updates: PreferenceUpdateRequest = { blueprint_preference: value };
    mutation.mutate(updates);
  };

  // Only show error if we don't have data (actual failure, not 404 handled gracefully)
  const hasActualError = isError && !preferences;

  if (isLoading && !preferences) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
      >
        <p className={darkMode ? 'text-gray-300' : 'text-gray-700'}>Loading preferences...</p>
      </motion.div>
    );
  }

  if (hasActualError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-6 border ${darkMode ? 'bg-red-900/30 border-red-700 text-red-300' : 'bg-red-50 border-red-200 text-red-700'} shadow-lg`}
      >
        <p>⚠️ Failed to load preferences: {error instanceof Error ? error.message : 'Unknown error'}</p>
        <p className={`text-sm mt-2 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
          Using default preferences. Changes will be saved when you update them.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className={`rounded-xl p-6 shadow-lg ${
        darkMode 
          ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
          : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
      }`}
      data-testid="preference-settings-section"
    >
      <h2 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        🎯 Suggestion Preferences
      </h2>
      
      <div className="space-y-6">
        {/* Max Suggestions Slider */}
        <div>
          <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Maximum Suggestions: {localPreferences.max_suggestions}
          </label>
          <input
            type="range"
            min="5"
            max="50"
            step="1"
            value={localPreferences.max_suggestions}
            onChange={(e) => handleMaxSuggestionsChange(parseInt(e.target.value, 10))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            data-testid="max-suggestions-slider"
          />
          <div className="flex justify-between text-sm text-gray-500 mt-1">
            <span>5</span>
            <span>50</span>
          </div>
          <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Maximum number of suggestions to show in results
          </p>
        </div>

        {/* Creativity Level Dropdown */}
        <div>
          <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Creativity Level
          </label>
          <select
            value={localPreferences.creativity_level}
            onChange={(e) => handleCreativityLevelChange(e.target.value as 'conservative' | 'balanced' | 'creative')}
            className={`px-4 py-2 rounded-lg border w-full ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            data-testid="creativity-level-dropdown"
          >
            <option value="conservative">Conservative - High confidence only (≥85%)</option>
            <option value="balanced">Balanced - Moderate confidence (≥70%)</option>
            <option value="creative">Creative - Lower confidence allowed (≥55%)</option>
          </select>
          <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Controls how experimental or creative suggestions can be
          </p>
        </div>

        {/* Blueprint Preference Dropdown */}
        <div>
          <label className={`block font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Blueprint Preference
          </label>
          <select
            value={localPreferences.blueprint_preference}
            onChange={(e) => handleBlueprintPreferenceChange(e.target.value as 'low' | 'medium' | 'high')}
            className={`px-4 py-2 rounded-lg border w-full ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            data-testid="blueprint-preference-dropdown"
          >
            <option value="low">Low - Blueprints ranked lower (0.5x weight)</option>
            <option value="medium">Medium - Normal blueprint ranking (1.0x weight)</option>
            <option value="high">High - Blueprints ranked higher (1.5x weight)</option>
          </select>
          <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Controls how much blueprint-based suggestions are prioritized in ranking
          </p>
        </div>

        {mutation.isPending && (
          <div className={`text-sm ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}>
            💾 Saving preferences...
          </div>
        )}
      </div>
    </motion.div>
  );
};
