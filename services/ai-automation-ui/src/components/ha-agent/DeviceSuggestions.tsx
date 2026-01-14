/**
 * Device Suggestions Component
 * Phase 2: Device-Based Automation Suggestions Feature
 * 
 * Displays automation suggestions for a selected device
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { generateDeviceSuggestions, DeviceSuggestionsAPIError, type DeviceSuggestionsRequest } from '../../services/deviceSuggestionsApi';

/** Suggestion data structure matching backend API */
export interface DeviceSuggestion {
  suggestion_id: string;
  title: string;
  description: string;
  automation_preview: {
    trigger: string;
    action: string;
    yaml_preview?: string;
  };
  data_sources: {
    synergies?: string[];
    blueprints?: string[];
    sports?: boolean;
    weather?: boolean;
    device_capabilities?: boolean;
  };
  home_assistant_entities?: {
    trigger_entities?: string[];
    action_entities?: string[];
    condition_entities?: string[];
  };
  home_assistant_services?: {
    actions?: string[];
    validated?: boolean;
  };
  confidence_score: number;
  quality_score: number;
  enhanceable: boolean;
  home_assistant_compatible: boolean;
}

interface DeviceSuggestionsProps {
  /** Whether dark mode is enabled */
  darkMode: boolean;
  /** Selected device ID */
  deviceId: string | null;
  /** Callback when user clicks "Enhance" on a suggestion */
  onEnhanceSuggestion: (suggestion: DeviceSuggestion) => void;
  /** Callback when user clicks "Create" on a suggestion */
  onCreateSuggestion?: (suggestion: DeviceSuggestion) => void;
}

/**
 * Device Suggestions Component
 * 
 * Displays automation suggestions for a selected device.
 * Currently uses mock data - will be replaced with real API calls in Phase 2.
 */
export const DeviceSuggestions: React.FC<DeviceSuggestionsProps> = ({
  darkMode,
  deviceId,
  onEnhanceSuggestion,
  onCreateSuggestion,
}) => {
  const [suggestions, setSuggestions] = useState<DeviceSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Format score as percentage
  const formatScore = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };

  // Load suggestions when device is selected
  useEffect(() => {
    if (!deviceId) {
      setSuggestions([]);
      return;
    }

    const loadSuggestions = async () => {
      setIsLoading(true);
      try {
        const request: DeviceSuggestionsRequest = {
          device_id: deviceId,
          context: {
            include_synergies: true,
            include_blueprints: true,
            include_sports: true,
            include_weather: true,
          },
        };
        
        const response = await generateDeviceSuggestions(request);
        setSuggestions(response.suggestions);
      } catch (error) {
        console.error('Failed to load device suggestions:', error);
        if (error instanceof DeviceSuggestionsAPIError) {
          toast.error(`Failed to load suggestions: ${error.message}`);
        } else {
          toast.error('Failed to load suggestions');
        }
        // Fallback to empty suggestions on error
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadSuggestions();
  }, [deviceId]);

  if (!deviceId) {
    return null;
  }

  return (
    <div className={`p-4 border-b ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
      <div className="mb-4">
        <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Automation Suggestions
        </h3>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Based on your device capabilities and patterns
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className={`ml-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Generating suggestions...
          </span>
        </div>
      ) : suggestions.length === 0 ? (
        <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No suggestions available for this device
        </div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence>
            {suggestions.map((suggestion) => (
              <motion.div
                key={suggestion.suggestion_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`rounded-lg p-4 border ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 hover:border-gray-500'
                    : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                } transition-colors`}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className={`text-base font-semibold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {suggestion.title}
                    </h4>
                    <p className={`text-sm mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {suggestion.description}
                    </p>
                    
                    {/* Scores */}
                    <div className="flex items-center gap-4 text-sm">
                      <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                        Confidence: <span className={`font-semibold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                          {formatScore(suggestion.confidence_score)}
                        </span>
                      </span>
                      <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                        Quality: <span className={`font-semibold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                          {formatScore(suggestion.quality_score)}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Automation Preview */}
                <div className={`mb-3 p-3 rounded ${darkMode ? 'bg-gray-800' : 'bg-gray-100'}`}>
                  <div className="text-sm">
                    <div className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
                      <span className="font-medium">Trigger:</span> {suggestion.automation_preview.trigger}
                    </div>
                    <div className={`mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      <span className="font-medium">Action:</span> {suggestion.automation_preview.action}
                    </div>
                  </div>
                </div>

                {/* Data Source Indicators */}
                {Object.keys(suggestion.data_sources).length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {suggestion.data_sources.synergies && suggestion.data_sources.synergies.length > 0 && (
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-100 text-blue-700'
                        }`}
                        title="Based on device synergies"
                      >
                        🔗 Synergy
                      </span>
                    )}
                    {suggestion.data_sources.blueprints && suggestion.data_sources.blueprints.length > 0 && (
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-purple-500/20 text-purple-300' : 'bg-purple-100 text-purple-700'
                        }`}
                        title="Based on Home Assistant blueprint"
                      >
                        📋 Blueprint
                      </span>
                    )}
                    {suggestion.data_sources.sports && (
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-orange-500/20 text-orange-300' : 'bg-orange-100 text-orange-700'
                        }`}
                        title="Includes sports data"
                      >
                        ⚽ Sports
                      </span>
                    )}
                    {suggestion.data_sources.weather && (
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-cyan-500/20 text-cyan-300' : 'bg-cyan-100 text-cyan-700'
                        }`}
                        title="Includes weather data"
                      >
                        🌤️ Weather
                      </span>
                    )}
                    {suggestion.data_sources.device_capabilities && (
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-gray-500/20 text-gray-300' : 'bg-gray-200 text-gray-700'
                        }`}
                        title="Based on device capabilities"
                      >
                        🔧 Capabilities
                      </span>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => onEnhanceSuggestion(suggestion)}
                    className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      darkMode
                        ? 'bg-blue-600 text-white hover:bg-blue-500'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                    }`}
                  >
                    💬 Enhance
                  </button>
                  {onCreateSuggestion && (
                    <button
                      onClick={() => onCreateSuggestion(suggestion)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        darkMode
                          ? 'bg-gray-600 text-white hover:bg-gray-500'
                          : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                      }`}
                    >
                      ➕ Create
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};
