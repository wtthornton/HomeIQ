/**
 * Synergies Tab - Displays synergy opportunities and blueprint recommendations
 * 
 * Phase 2: Blueprint-First Architecture
 * 
 * This tab provides:
 * - Detected synergy opportunities from device patterns
 * - Blueprint recommendations based on device inventory
 * - One-click blueprint deployment
 * - Fit score visualization
 */

import React, { useState, useEffect, useCallback } from 'react';
import type { TabProps } from './types';

// Blueprint Opportunity types
interface BlueprintOpportunity {
  blueprint_id: string;
  name: string;
  description: string;
  fit_score: number;
  match_details: MatchDetails;
  auto_fill_suggestions: Record<string, AutoFillSuggestion>;
  missing_requirements: string[];
  community_rating: number;
  stars: number;
  author: string;
  source_url: string;
}

interface MatchDetails {
  matched_domains: string[];
  matched_device_classes: string[];
  total_required: number;
  total_matched: number;
}

interface AutoFillSuggestion {
  input_name: string;
  suggested_entity: string;
  confidence: number;
  alternatives: string[];
}

// Synergy types
interface Synergy {
  id: number;
  synergy_id: string;
  synergy_type: string;
  devices: string[];
  metadata: Record<string, any>;
  impact_score: number;
  confidence: number;
  complexity: string;
  area: string | null;
  explanation?: string;
}

// API configuration
const API_BASE_URL = import.meta.env.VITE_AI_PATTERN_SERVICE_URL || 'http://localhost:8020';

export const SynergiesTab: React.FC<TabProps> = ({ darkMode }) => {
  // State for active sub-tab
  const [activeSubTab, setActiveSubTab] = useState<'synergies' | 'blueprints'>('synergies');
  
  // Synergies state
  const [synergies, setSynergies] = useState<Synergy[]>([]);
  const [synergiesLoading, setSynergiesLoading] = useState(true);
  const [synergiesError, setSynergiesError] = useState<string | null>(null);
  
  // Blueprint opportunities state
  const [blueprints, setBlueprints] = useState<BlueprintOpportunity[]>([]);
  const [blueprintsLoading, setBlueprintsLoading] = useState(false);
  const [blueprintsError, setBlueprintsError] = useState<string | null>(null);
  
  // Filters
  const [minFitScore, setMinFitScore] = useState(0.5);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [minConfidence, setMinConfidence] = useState(0.5);
  
  // Preview modal state
  const [previewBlueprint, setPreviewBlueprint] = useState<BlueprintOpportunity | null>(null);
  const [previewYaml, setPreviewYaml] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState(false);

  // Fetch synergies
  const fetchSynergies = useCallback(async () => {
    setSynergiesLoading(true);
    setSynergiesError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/synergies/list?min_confidence=${minConfidence}&limit=50`
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setSynergies(data.data?.synergies || []);
    } catch (err) {
      setSynergiesError(err instanceof Error ? err.message : 'Failed to load synergies');
    } finally {
      setSynergiesLoading(false);
    }
  }, [minConfidence]);

  // Fetch blueprint opportunities
  const fetchBlueprints = useCallback(async () => {
    setBlueprintsLoading(true);
    setBlueprintsError(null);
    try {
      const params = new URLSearchParams({
        min_fit_score: minFitScore.toString(),
        limit: '20',
      });
      if (selectedDomain) params.append('domain', selectedDomain);
      
      const response = await fetch(
        `${API_BASE_URL}/api/v1/blueprint-opportunities?${params}`
      );
      if (!response.ok) {
        if (response.status === 503) {
          throw new Error('Blueprint service not available');
        }
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setBlueprints(data.data?.opportunities || []);
    } catch (err) {
      setBlueprintsError(err instanceof Error ? err.message : 'Failed to load blueprints');
    } finally {
      setBlueprintsLoading(false);
    }
  }, [minFitScore, selectedDomain]);

  // Load data on mount and when filters change
  useEffect(() => {
    if (activeSubTab === 'synergies') {
      fetchSynergies();
    } else {
      fetchBlueprints();
    }
  }, [activeSubTab, fetchSynergies, fetchBlueprints]);

  // Preview blueprint deployment
  const handlePreview = async (blueprint: BlueprintOpportunity) => {
    setPreviewBlueprint(blueprint);
    setPreviewLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/blueprint-opportunities/${blueprint.blueprint_id}/preview`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            blueprint_id: blueprint.blueprint_id,
            input_values: blueprint.auto_fill_suggestions,
          }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setPreviewYaml(data.data?.automation_yaml || '# Preview not available');
    } catch (err) {
      setPreviewYaml(`# Error: ${err instanceof Error ? err.message : 'Preview failed'}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Fit score color
  const getFitScoreColor = (score: number): string => {
    if (score >= 0.9) return 'text-green-500';
    if (score >= 0.7) return 'text-blue-500';
    if (score >= 0.5) return 'text-yellow-500';
    return 'text-red-500';
  };

  // Confidence badge color
  const getConfidenceBadge = (confidence: number): { bg: string; text: string } => {
    if (confidence >= 0.8) return { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-800 dark:text-green-200' };
    if (confidence >= 0.6) return { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-800 dark:text-blue-200' };
    if (confidence >= 0.4) return { bg: 'bg-yellow-100 dark:bg-yellow-900', text: 'text-yellow-800 dark:text-yellow-200' };
    return { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-800 dark:text-red-200' };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🔗 Synergies & Blueprints
            </h2>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Discover automation opportunities based on your device patterns
            </p>
          </div>
          
          {/* Sub-tab Toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
            <button
              onClick={() => setActiveSubTab('synergies')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeSubTab === 'synergies'
                  ? 'bg-blue-600 text-white'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🔗 Synergies
            </button>
            <button
              onClick={() => setActiveSubTab('blueprints')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeSubTab === 'blueprints'
                  ? 'bg-blue-600 text-white'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              📋 Blueprint Opportunities
            </button>
          </div>
        </div>
      </div>

      {/* Synergies Tab Content */}
      {activeSubTab === 'synergies' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className={`rounded-lg p-4 ${
            darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
          }`}>
            <div className="flex flex-wrap gap-4 items-center">
              <div>
                <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Min Confidence
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                  className="block w-32"
                />
                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  {(minConfidence * 100).toFixed(0)}%
                </span>
              </div>
              <button
                onClick={fetchSynergies}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Synergies List */}
          {synergiesLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : synergiesError ? (
            <div className={`rounded-lg p-6 text-center ${
              darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'
            }`}>
              <p className="text-red-500">❌ {synergiesError}</p>
              <button
                onClick={fetchSynergies}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          ) : synergies.length === 0 ? (
            <div className={`rounded-lg p-6 text-center ${
              darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-gray-50 border border-gray-200'
            }`}>
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                No synergies detected yet. Keep using your devices to discover patterns!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {synergies.map((synergy) => {
                const confidenceBadge = getConfidenceBadge(synergy.confidence);
                return (
                  <div
                    key={synergy.synergy_id}
                    className={`rounded-lg p-4 ${
                      darkMode ? 'bg-gray-800 border border-gray-700 hover:border-blue-600' : 'bg-white border border-gray-200 hover:border-blue-400'
                    } transition-colors cursor-pointer`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                          {synergy.synergy_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </h3>
                        {synergy.area && (
                          <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                            📍 {synergy.area}
                          </span>
                        )}
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${confidenceBadge.bg} ${confidenceBadge.text}`}>
                        {(synergy.confidence * 100).toFixed(0)}% confident
                      </span>
                    </div>
                    
                    {synergy.explanation && (
                      <p className={`text-sm mb-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {synergy.explanation}
                      </p>
                    )}
                    
                    <div className="flex flex-wrap gap-2 mb-3">
                      {synergy.devices.slice(0, 3).map((device, idx) => (
                        <span
                          key={idx}
                          className={`px-2 py-1 rounded text-xs ${
                            darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {device}
                        </span>
                      ))}
                      {synergy.devices.length > 3 && (
                        <span className={`px-2 py-1 rounded text-xs ${
                          darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-500'
                        }`}>
                          +{synergy.devices.length - 3} more
                        </span>
                      )}
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <div className="flex gap-3 text-sm">
                        <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                          Impact: <span className="font-medium">{(synergy.impact_score * 100).toFixed(0)}%</span>
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          synergy.complexity === 'low' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                          synergy.complexity === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        }`}>
                          {synergy.complexity}
                        </span>
                      </div>
                      <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                        Create Automation →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Blueprint Opportunities Tab Content */}
      {activeSubTab === 'blueprints' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className={`rounded-lg p-4 ${
            darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
          }`}>
            <div className="flex flex-wrap gap-4 items-center">
              <div>
                <label className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Min Fit Score
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={minFitScore}
                  onChange={(e) => setMinFitScore(parseFloat(e.target.value))}
                  className="block w-32"
                />
                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  {(minFitScore * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <label className={`text-sm block ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Domain
                </label>
                <select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  className={`px-3 py-1.5 rounded-lg border text-sm ${
                    darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
                  }`}
                >
                  <option value="">All Domains</option>
                  <option value="light">Light</option>
                  <option value="switch">Switch</option>
                  <option value="climate">Climate</option>
                  <option value="binary_sensor">Binary Sensor</option>
                  <option value="sensor">Sensor</option>
                  <option value="cover">Cover</option>
                  <option value="lock">Lock</option>
                </select>
              </div>
              <button
                onClick={fetchBlueprints}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Blueprints List */}
          {blueprintsLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : blueprintsError ? (
            <div className={`rounded-lg p-6 text-center ${
              darkMode ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'
            }`}>
              <p className="text-yellow-600 mb-2">⚠️ {blueprintsError}</p>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                The Blueprint Index service may not be running. Start it with:
                <code className="block mt-2 px-3 py-2 bg-gray-800 text-green-400 rounded">
                  docker-compose up blueprint-index
                </code>
              </p>
            </div>
          ) : blueprints.length === 0 ? (
            <div className={`rounded-lg p-6 text-center ${
              darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-gray-50 border border-gray-200'
            }`}>
              <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                No matching blueprints found. Try adjusting your filters or adding more devices.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {blueprints.map((blueprint) => (
                <div
                  key={blueprint.blueprint_id}
                  className={`rounded-lg p-4 ${
                    darkMode ? 'bg-gray-800 border border-gray-700 hover:border-blue-600' : 'bg-white border border-gray-200 hover:border-blue-400'
                  } transition-colors`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {blueprint.name}
                      </h3>
                      <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {blueprint.description}
                      </p>
                    </div>
                    <div className="text-right ml-4">
                      <div className={`text-2xl font-bold ${getFitScoreColor(blueprint.fit_score)}`}>
                        {(blueprint.fit_score * 100).toFixed(0)}%
                      </div>
                      <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                        fit score
                      </div>
                    </div>
                  </div>
                  
                  {/* Match Details */}
                  <div className={`rounded-lg p-3 mb-3 ${
                    darkMode ? 'bg-gray-700/50' : 'bg-gray-50'
                  }`}>
                    <div className="flex justify-between text-sm mb-2">
                      <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Device Match</span>
                      <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
                        {blueprint.match_details.total_matched} / {blueprint.match_details.total_required}
                      </span>
                    </div>
                    <div className="w-full bg-gray-300 dark:bg-gray-600 rounded-full h-2">
                      <div
                        className="bg-blue-600 rounded-full h-2 transition-all"
                        style={{
                          width: `${(blueprint.match_details.total_matched / blueprint.match_details.total_required) * 100}%`
                        }}
                      />
                    </div>
                    {blueprint.match_details.matched_domains.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {blueprint.match_details.matched_domains.map((domain, idx) => (
                          <span
                            key={idx}
                            className={`px-2 py-0.5 rounded text-xs ${
                              darkMode ? 'bg-green-900/50 text-green-300' : 'bg-green-100 text-green-700'
                            }`}
                          >
                            ✓ {domain}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* Missing Requirements */}
                  {blueprint.missing_requirements.length > 0 && (
                    <div className="mb-3">
                      <p className={`text-xs ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
                        Missing: {blueprint.missing_requirements.join(', ')}
                      </p>
                    </div>
                  )}
                  
                  {/* Community Stats */}
                  <div className="flex items-center gap-4 text-sm mb-3">
                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                      ⭐ {blueprint.stars}
                    </span>
                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                      📊 {(blueprint.community_rating * 5).toFixed(1)}/5
                    </span>
                    <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>
                      by {blueprint.author}
                    </span>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handlePreview(blueprint)}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        darkMode
                          ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      👁️ Preview
                    </button>
                    <button
                      disabled={blueprint.fit_score < 0.5}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        blueprint.fit_score >= 0.5
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                      }`}
                    >
                      🚀 Deploy
                    </button>
                    <a
                      href={blueprint.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        darkMode
                          ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      🔗
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Preview Modal */}
      {previewBlueprint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className={`w-full max-w-3xl max-h-[90vh] overflow-auto rounded-xl shadow-2xl ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}>
            <div className={`sticky top-0 flex justify-between items-center p-4 border-b ${
              darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}>
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                📋 Blueprint Preview: {previewBlueprint.name}
              </h3>
              <button
                onClick={() => setPreviewBlueprint(null)}
                className={`p-2 rounded-lg ${
                  darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
                }`}
              >
                ✕
              </button>
            </div>
            
            <div className="p-4">
              {previewLoading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <>
                  <h4 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Generated Automation YAML
                  </h4>
                  <pre className={`p-4 rounded-lg overflow-x-auto text-sm ${
                    darkMode ? 'bg-gray-900 text-green-400' : 'bg-gray-50 text-gray-800'
                  }`}>
                    {previewYaml}
                  </pre>
                  
                  {Object.keys(previewBlueprint.auto_fill_suggestions).length > 0 && (
                    <>
                      <h4 className={`text-sm font-medium mt-4 mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Auto-filled Inputs
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {Object.entries(previewBlueprint.auto_fill_suggestions).map(([key, value]) => (
                          <div
                            key={key}
                            className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}
                          >
                            <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              {value.input_name}
                            </span>
                            <div className={`font-mono text-sm ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                              {value.suggested_entity}
                            </div>
                            <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                              {(value.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
            
            <div className={`sticky bottom-0 flex justify-end gap-2 p-4 border-t ${
              darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}>
              <button
                onClick={() => setPreviewBlueprint(null)}
                className={`px-4 py-2 rounded-lg ${
                  darkMode ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Close
              </button>
              <button
                className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                onClick={() => {
                  // TODO: Implement deployment
                  alert('Blueprint deployment coming in Phase 3!');
                }}
              >
                🚀 Deploy Blueprint
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
