/**
 * Synergies Page
 * Display detected cross-device automation opportunities
 * 
 * Epic AI-3: Cross-Device Synergy & Contextual Opportunities
 * Story AI3.8: Frontend Synergy Tab
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import api from '../services/api';
import type { SynergyOpportunity } from '../types';

export const Synergies: React.FC = () => {
  const { darkMode } = useAppStore();
  const [synergies, setSynergies] = useState<SynergyOpportunity[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string | null>(null);

  useEffect(() => {
    const loadSynergies = async () => {
      try {
        const [synergiesRes, statsRes] = await Promise.all([
          api.getSynergies(filterType, 0.7),
          api.getSynergyStats()
        ]);
        setSynergies(synergiesRes.data.synergies || []);
        setStats(statsRes.data || statsRes);
      } catch (err) {
        console.error('Failed to load synergies:', err);
      } finally {
        setLoading(false);
      }
    };

    loadSynergies();
  }, [filterType]);

  const getSynergyIcon = (type: string) => {
    const icons = {
      device_pair: '🔗',
      weather_context: '🌤️',
      energy_context: '⚡',
      event_context: '📅',
    };
    return icons[type as keyof typeof icons] || '🔮';
  };

  const getSynergyTypeLabel = (type: string) => {
    const labels = {
      device_pair: 'Device Synergy',
      weather_context: 'Weather-Aware',
      energy_context: 'Energy Optimization',
      event_context: 'Event-Based',
    };
    return labels[type as keyof typeof labels] || type;
  };

  const getComplexityColor = (complexity: string) => {
    const colors = {
      low: darkMode ? 'text-green-400' : 'text-green-600',
      medium: darkMode ? 'text-yellow-400' : 'text-yellow-600',
      high: darkMode ? 'text-red-400' : 'text-red-600',
    };
    return colors[complexity as keyof typeof colors] || 'text-gray-500';
  };

  return (
    <div className="space-y-6" data-testid="synergies-container">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className={`text-3xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🔮 Automation Opportunities
        </h1>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
          Discover what your smart home devices could do together
        </p>
      </motion.div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {stats.total_synergies || 0}
            </div>
            <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Total Opportunities
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            <div className="text-3xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              {Object.keys(stats.by_type || {}).length}
            </div>
            <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Synergy Types
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            <div className="text-3xl font-bold bg-gradient-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
              {Math.round((stats.avg_impact_score || 0) * 100)}%
            </div>
            <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Avg Impact
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
          >
            <div className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              {(stats.by_complexity?.low || 0) + (stats.by_complexity?.medium || 0)}
            </div>
            <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Easy to Implement
            </div>
          </motion.div>
        </div>
      )}

      {/* Filter Pills */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilterType(null)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            filterType === null
              ? 'bg-blue-600 text-white'
              : darkMode
              ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          All ({stats?.total_synergies || 0})
        </button>
        {Object.entries(stats?.by_type || {}).map(([type, count]) => (
          <button
            key={type}
            onClick={() => setFilterType(type)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              filterType === type
                ? 'bg-blue-600 text-white'
                : darkMode
                ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {getSynergyIcon(type)} {getSynergyTypeLabel(type)} ({count as number})
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Empty State */}
      {!loading && synergies.length === 0 && (
        <div className={`text-center py-20 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-xl font-semibold mb-2">No Opportunities Found</h3>
          <p>Run the daily analysis to discover automation opportunities</p>
        </div>
      )}

      {/* Synergy Grid */}
      <AnimatePresence mode="popLayout">
        {!loading && synergies.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {synergies.map((synergy, index) => (
              <motion.div
                key={synergy.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.05 }}
                className={`p-6 rounded-xl ${
                  darkMode ? 'bg-gray-800' : 'bg-white'
                } shadow-lg hover:shadow-xl transition-shadow cursor-pointer`}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="text-3xl">{getSynergyIcon(synergy.synergy_type)}</div>
                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getComplexityColor(synergy.complexity)}`}>
                      {synergy.complexity}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-600 text-white">
                      {Math.round(synergy.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {/* Type */}
                <div className={`text-xs font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {getSynergyTypeLabel(synergy.synergy_type)}
                </div>

                {/* Area */}
                {synergy.area && (
                  <div className={`text-sm mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    📍 {synergy.area}
                  </div>
                )}

                {/* Metadata */}
                {synergy.opportunity_metadata && (
                  <div className="space-y-2">
                    {synergy.opportunity_metadata.trigger_name && synergy.opportunity_metadata.action_name && (
                      <div className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        <span className="font-medium">{synergy.opportunity_metadata.trigger_name}</span>
                        <span className="mx-2">→</span>
                        <span className="font-medium">{synergy.opportunity_metadata.action_name}</span>
                      </div>
                    )}
                    
                    {synergy.opportunity_metadata.relationship && (
                      <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {synergy.opportunity_metadata.relationship.replace(/_/g, ' ')}
                      </div>
                    )}

                    {synergy.opportunity_metadata.rationale && (
                      <div className={`text-sm mt-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {synergy.opportunity_metadata.rationale}
                      </div>
                    )}
                  </div>
                )}

                {/* Impact Score */}
                <div className="mt-4 pt-4 border-t border-gray-700">
                  <div className="flex justify-between items-center text-sm">
                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                      Impact Score
                    </span>
                    <span className="font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                      {Math.round(synergy.impact_score * 100)}%
                    </span>
                  </div>
                </div>

                {/* Created Date */}
                <div className={`text-xs mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  Detected {new Date(synergy.created_at).toLocaleDateString()}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

