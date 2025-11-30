/**
 * Synergies Page
 * Display detected cross-device automation opportunities
 * 
 * Epic AI-3: Cross-Device Synergy & Contextual Opportunities
 * Story AI3.8: Frontend Synergy Tab
 */

import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import api from '../services/api';
import type { SynergyOpportunity } from '../types';
import { ImpactScoreGauge, ScoreBreakdownChart } from '../components/SynergyChart';
import { RoomMapView } from '../components/synergies/RoomMapView';
import { NetworkGraphView } from '../components/synergies/NetworkGraphView';

export const Synergies: React.FC = () => {
  const { darkMode } = useAppStore();
  const [synergies, setSynergies] = useState<SynergyOpportunity[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterValidated, setFilterValidated] = useState<boolean | null>(null);
  const [minConfidence, setMinConfidence] = useState<number>(0.0); // Changed from 0.7 to 0.0 to show all by default
  const [expandedSynergies, setExpandedSynergies] = useState<Set<number>>(new Set());
  const [showSynergyGuide, setShowSynergyGuide] = useState(false);
  const [showHelpInfo, setShowHelpInfo] = useState(false); // Collapsed by default
  const [showStatsAndFilters, setShowStatsAndFilters] = useState(true); // Collapsible stats/filters
  const [showBreakdown, setShowBreakdown] = useState<Set<number>>(new Set());
  const [sortBy, setSortBy] = useState<string>('recommended');
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<Set<number>>(new Set());
  const [viewMode, setViewMode] = useState<'grid' | 'map' | 'graph'>('grid');
  
  // Load dismissed/saved synergies from localStorage
  const [dismissedSynergies, setDismissedSynergies] = useState<Set<number>>(() => {
    try {
      const stored = localStorage.getItem('dismissedSynergies');
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });
  
  const [savedSynergies, setSavedSynergies] = useState<Set<number>>(() => {
    try {
      const stored = localStorage.getItem('savedSynergies');
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  useEffect(() => {
    const loadSynergies = async () => {
      try {
        const [synergiesRes, statsRes] = await Promise.all([
          api.getSynergies(filterType, minConfidence, filterValidated),
          api.getSynergyStats()
        ]);
        // Filter out dismissed synergies
        const allSynergies = (synergiesRes.data.synergies || []).filter(
          s => !dismissedSynergies.has(s.id)
        );
        setSynergies(allSynergies);
        setStats(statsRes.data || statsRes);
      } catch (err: any) {
        console.error('Failed to load synergies:', err);
        // Log detailed error information
        if (err.status) {
          console.error(`API Error ${err.status}: ${err.message}`);
        }
        // Set empty stats on error so UI doesn't show undefined
        setStats({
          total_synergies: 0,
          by_type: {},
          by_complexity: {},
          avg_impact_score: 0
        });
      } finally {
        setLoading(false);
      }
    };

    loadSynergies();
  }, [filterType, filterValidated, minConfidence, dismissedSynergies]);
  
  // Save dismissed synergies to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('dismissedSynergies', JSON.stringify(Array.from(dismissedSynergies)));
    } catch (err) {
      console.error('Failed to save dismissed synergies:', err);
    }
  }, [dismissedSynergies]);
  
  // Save saved synergies to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('savedSynergies', JSON.stringify(Array.from(savedSynergies)));
    } catch (err) {
      console.error('Failed to save saved synergies:', err);
    }
  }, [savedSynergies]);

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

  const getSynergyTypeInfo = (type: string) => {
    const info: Record<string, { name: string; description: string; importance: string; example: string }> = {
      device_pair: {
        name: 'Device Pair Synergies',
        description: 'Identifies opportunities where two or more devices in the same room or area could work together to create intelligent automations.',
        importance: 'Discovers relationships between devices that are physically close to each other (same area/room) but aren\'t currently automated. These synergies enable coordinated actions between nearby devices that make your home more responsive and convenient.',
        example: 'Bedroom motion sensor → Bedroom light (same room), or Hallway door sensor → Hallway light (same area).'
      },
      weather_context: {
        name: 'Weather-Aware Synergies',
        description: 'Detects automation opportunities where devices in the same area respond to weather conditions like temperature, humidity, or precipitation.',
        importance: 'Makes your home adapt to weather automatically. Saves energy by adjusting HVAC in specific rooms based on conditions, and enhances comfort by responding to weather changes for nearby devices.',
        example: 'When temperature drops below 65°F → Living room thermostat adjusts, or When it\'s cloudy → Bedroom lights turn on earlier (weather affects room-specific devices).'
      },
      energy_context: {
        name: 'Energy Optimization Synergies',
        description: 'Identifies opportunities where devices in the same area can optimize energy usage based on pricing, carbon intensity, or peak demand periods.',
        importance: 'Reduces energy costs and environmental impact. Automatically shifts device usage in specific rooms to cheaper times or coordinates nearby devices to reduce consumption during peak periods.',
        example: 'Kitchen devices coordinate to delay dishwasher start until off-peak hours, or Living room devices turn off non-essentials during high carbon intensity periods.'
      },
      event_context: {
        name: 'Event-Based Synergies',
        description: 'Detects automation opportunities where devices in the same entertainment area are triggered by calendar events, sports games, or scheduled activities.',
        importance: 'Enhances your entertainment and lifestyle experiences. Automatically coordinates nearby devices (in the same room/area) to prepare your home for events, games, or scheduled activities.',
        example: 'When favorite team plays → Living room lights dim and TV activates (same entertainment area), or Before calendar event → Bedroom thermostat and lighting adjust together (same room).'
      }
    };
    return info[type] || {
      name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      description: 'Synergy opportunity detected in your smart home.',
      importance: 'Helps create intelligent automations based on device relationships and context.',
      example: 'Device synergy opportunity detected.'
    };
  };

  const getComplexityColor = (complexity: string) => {
    const colors = {
      low: darkMode ? 'text-green-400' : 'text-green-600',
      medium: darkMode ? 'text-yellow-400' : 'text-yellow-600',
      high: darkMode ? 'text-red-400' : 'text-red-600',
    };
    return colors[complexity as keyof typeof colors] || 'text-gray-500';
  };

  const parseDeviceIds = (deviceIds: string): string[] => {
    try {
      if (typeof deviceIds === 'string') {
        const parsed = JSON.parse(deviceIds);
        return Array.isArray(parsed) ? parsed : [deviceIds];
      }
      return Array.isArray(deviceIds) ? deviceIds : [];
    } catch {
      // If not JSON, treat as comma-separated or single value
      if (typeof deviceIds === 'string' && deviceIds.includes(',')) {
        return deviceIds.split(',').map(id => id.trim());
      }
      return deviceIds ? [deviceIds] : [];
    }
  };

  const toggleExpanded = (synergyId: number) => {
    setExpandedSynergies(prev => {
      const next = new Set(prev);
      if (next.has(synergyId)) {
        next.delete(synergyId);
      } else {
        next.add(synergyId);
      }
      return next;
    });
  };
  
  const toggleBreakdown = (synergyId: number) => {
    setShowBreakdown(prev => {
      const next = new Set(prev);
      if (next.has(synergyId)) {
        next.delete(synergyId);
      } else {
        next.add(synergyId);
      }
      return next;
    });
  };
  
  const handleDismiss = (synergyId: number) => {
    setDismissedSynergies(prev => new Set(prev).add(synergyId));
    setExpandedSynergies(prev => {
      const next = new Set(prev);
      next.delete(synergyId);
      return next;
    });
  };
  
  const handleSave = (synergyId: number) => {
    setSavedSynergies(prev => {
      const next = new Set(prev);
      if (next.has(synergyId)) {
        next.delete(synergyId);
      } else {
        next.add(synergyId);
      }
      return next;
    });
  };
  
  const handleCompareToggle = (synergyId: number) => {
    if (!compareMode) return;
    setSelectedForCompare(prev => {
      const next = new Set(prev);
      if (next.has(synergyId)) {
        next.delete(synergyId);
      } else if (next.size < 3) {
        next.add(synergyId);
      }
      return next;
    });
  };
  
  // Sort synergies based on sortBy
  const sortedSynergies = useMemo(() => {
    const sorted = [...synergies];
    switch (sortBy) {
      case 'recommended':
        // High impact + low complexity
        return sorted.sort((a, b) => {
          const scoreA = a.impact_score * (a.complexity === 'low' ? 1.5 : a.complexity === 'medium' ? 1.2 : 1);
          const scoreB = b.impact_score * (b.complexity === 'low' ? 1.5 : b.complexity === 'medium' ? 1.2 : 1);
          return scoreB - scoreA;
        });
      case 'quick-wins':
        // Low complexity, high impact
        return sorted.sort((a, b) => {
          if (a.complexity !== b.complexity) {
            const complexityOrder = { low: 0, medium: 1, high: 2 };
            return complexityOrder[a.complexity] - complexityOrder[b.complexity];
          }
          return b.impact_score - a.impact_score;
        });
      case 'highest-impact':
        return sorted.sort((a, b) => b.impact_score - a.impact_score);
      case 'most-confident':
        return sorted.sort((a, b) => b.confidence - a.confidence);
      case 'by-area':
        return sorted.sort((a, b) => {
          const areaA = a.area || 'zzz';
          const areaB = b.area || 'zzz';
          return areaA.localeCompare(areaB);
        });
      default:
        return sorted;
    }
  }, [synergies, sortBy]);

  return (
    <div className="space-y-6" data-testid="synergies-container">
      {/* Modern 2025 Hero Section - Collapsible by Default */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-2xl overflow-hidden transition-all duration-300 ${
          darkMode 
            ? 'bg-gradient-to-br from-slate-900/95 via-purple-900/20 to-pink-900/20 border border-purple-500/20 shadow-2xl shadow-purple-900/20' 
            : 'bg-gradient-to-br from-white via-purple-50/50 to-pink-50/50 border border-purple-200/50 shadow-xl shadow-purple-100/50'
        } backdrop-blur-sm`}
      >
        {/* Header - Always Visible */}
        <motion.div
          className={`p-5 ${showHelpInfo ? 'border-b' : ''} ${
            darkMode ? 'border-purple-500/20' : 'border-purple-200/50'
          }`}
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              {/* Icon with glow effect */}
              <motion.div
                animate={{ 
                  scale: [1, 1.05, 1],
                  opacity: [0.8, 1, 0.8]
                }}
                transition={{ 
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className={`text-3xl ${darkMode ? 'drop-shadow-[0_0_8px_rgba(168,85,247,0.6)]' : 'drop-shadow-[0_0_6px_rgba(168,85,247,0.4)]'}`}
              >
                🔮
              </motion.div>
              <div className="flex-1 min-w-0">
                <h1 className={`text-2xl font-bold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Device Synergies
                </h1>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Discover automation opportunities between nearby devices
                </p>
              </div>
            </div>
            
            {/* Modern Toggle Button - 2025 Design */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowHelpInfo(!showHelpInfo)}
              className={`group relative flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all duration-300 ${
                showHelpInfo
                  ? darkMode
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                  : darkMode
                  ? 'bg-slate-800/60 hover:bg-slate-700/60 text-gray-300 hover:text-white border border-slate-700/50'
                  : 'bg-white/80 hover:bg-white text-gray-700 hover:text-gray-900 border border-gray-200 shadow-sm hover:shadow-md'
              }`}
              aria-label={showHelpInfo ? 'Hide information' : 'Show information'}
            >
              <motion.span
                animate={{ rotate: showHelpInfo ? 180 : 0 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="text-lg"
              >
                {showHelpInfo ? '▲' : '▼'}
              </motion.span>
              <span className="hidden sm:inline">
                {showHelpInfo ? 'Less Info' : 'Learn More'}
              </span>
            </motion.button>
          </div>
        </motion.div>

        {/* Collapsible Help Information - Modern 2025 Accordion */}
        <AnimatePresence>
          {showHelpInfo && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
              className="overflow-hidden"
            >
              <div className={`p-6 space-y-6 ${darkMode ? 'bg-slate-900/40' : 'bg-white/60'} backdrop-blur-sm`}>
                {/* What Are Synergies - Modern Card */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  className={`p-5 rounded-xl ${
                    darkMode 
                      ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/20 border border-purple-500/30' 
                      : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200/50'
                  } shadow-lg`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`text-2xl ${darkMode ? 'opacity-90' : 'opacity-80'}`}>💡</div>
                    <div className="flex-1">
                      <h3 className={`text-base font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        What Are Synergies?
                      </h3>
                      <p className={`text-sm leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Automation opportunities where devices <strong className={darkMode ? 'text-purple-300' : 'text-purple-700'}>in the same room or area</strong> could work together intelligently but currently don't. Our AI analyzes devices that are <strong className={darkMode ? 'text-purple-300' : 'text-purple-700'}>physically close to each other</strong> (same area/room) and identifies compatible relationships that would create useful automations.
                      </p>
                    </div>
                  </div>
                </motion.div>

                {/* Why Synergies Matter - Modern Grid Cards */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className={`p-5 rounded-xl ${
                    darkMode 
                      ? 'bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30' 
                      : 'bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200/50'
                  } shadow-lg`}
                >
                  <h3 className={`text-base font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Why Synergies Matter
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {[
                      { icon: '🔍', title: 'Hidden Connections', desc: 'Find relationships between nearby devices you might not have noticed' },
                      { icon: '⚡', title: 'Energy Savings', desc: 'Optimize device usage to reduce costs and environmental impact' },
                      { icon: '✨', title: 'Enhanced Convenience', desc: 'Automate coordinated actions that make daily life easier' },
                      { icon: '🧠', title: 'Context-Aware Intelligence', desc: 'Respond to weather, events, and energy conditions automatically' },
                      { icon: '✅', title: 'Pattern Validated', desc: 'Many synergies are backed by detected usage patterns for high confidence' }
                    ].map((item, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 + idx * 0.05 }}
                        whileHover={{ scale: 1.02, y: -2 }}
                        className={`p-3 rounded-lg ${
                          darkMode 
                            ? 'bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50' 
                            : 'bg-white/80 hover:bg-white border border-gray-200/50'
                        } transition-all duration-200 shadow-sm hover:shadow-md`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-lg flex-shrink-0">{item.icon}</span>
                          <div>
                            <div className={`text-sm font-semibold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                              {item.title}
                            </div>
                            <div className={`text-xs leading-relaxed ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              {item.desc}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>

                {/* Synergy Type Guide Toggle - Modern 2025 Design */}
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => setShowSynergyGuide(!showSynergyGuide)}
                  className={`w-full p-4 rounded-xl font-medium text-sm transition-all duration-200 ${
                    darkMode 
                      ? 'bg-slate-800/60 hover:bg-slate-700/60 text-gray-200 hover:text-white border border-slate-700/50 hover:border-purple-500/50' 
                      : 'bg-white/80 hover:bg-white text-gray-700 hover:text-gray-900 border border-gray-200 hover:border-purple-300 shadow-sm hover:shadow-md'
                  }`}
                >
                  <span className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <motion.span
                        animate={{ rotate: showSynergyGuide ? 90 : 0 }}
                        transition={{ duration: 0.2 }}
                        className="text-lg"
                      >
                        ▶
                      </motion.span>
                      <span className="font-semibold">Synergy Type Guide</span>
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      darkMode 
                        ? 'bg-purple-900/40 text-purple-300' 
                        : 'bg-purple-100 text-purple-700'
                    }`}>
                      {showSynergyGuide ? 'Hide Details' : 'Show All Types'}
                    </span>
                  </span>
                </motion.button>

                {/* Synergy Type Guide - Modern Collapsible */}
                <AnimatePresence>
                  {showSynergyGuide && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                      className="overflow-hidden"
                    >
                      <div className={`mt-4 p-5 rounded-xl ${
                        darkMode 
                          ? 'bg-slate-800/40 border border-slate-700/50' 
                          : 'bg-white/60 border border-gray-200/50'
                      } max-h-96 overflow-y-auto custom-scrollbar`}>
                        <h4 className={`text-base font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                          Synergy Types Explained
                        </h4>
                        <div className="grid grid-cols-1 gap-4">
                          {['device_pair', 'weather_context', 'energy_context', 'event_context'].map((type, idx) => {
                            const info = getSynergyTypeInfo(type);
                            const colorClasses = [
                              { 
                                bg: darkMode ? 'bg-gradient-to-br from-purple-600/20 to-pink-600/10' : 'bg-gradient-to-br from-purple-600/10 to-pink-600/5',
                                border: darkMode ? 'border-purple-500/30 hover:border-purple-500/50' : 'border-purple-200/50 hover:border-purple-300/70',
                                highlight: darkMode ? 'bg-gradient-to-r from-purple-600/30 to-pink-600/20 border-purple-500/20' : 'bg-gradient-to-r from-purple-600/10 to-pink-600/5 border-purple-200/30',
                                text: darkMode ? 'text-purple-300' : 'text-purple-700'
                              },
                              { 
                                bg: darkMode ? 'bg-gradient-to-br from-blue-600/20 to-cyan-600/10' : 'bg-gradient-to-br from-blue-600/10 to-cyan-600/5',
                                border: darkMode ? 'border-blue-500/30 hover:border-blue-500/50' : 'border-blue-200/50 hover:border-blue-300/70',
                                highlight: darkMode ? 'bg-gradient-to-r from-blue-600/30 to-cyan-600/20 border-blue-500/20' : 'bg-gradient-to-r from-blue-600/10 to-cyan-600/5 border-blue-200/30',
                                text: darkMode ? 'text-blue-300' : 'text-blue-700'
                              },
                              { 
                                bg: darkMode ? 'bg-gradient-to-br from-green-600/20 to-emerald-600/10' : 'bg-gradient-to-br from-green-600/10 to-emerald-600/5',
                                border: darkMode ? 'border-green-500/30 hover:border-green-500/50' : 'border-green-200/50 hover:border-green-300/70',
                                highlight: darkMode ? 'bg-gradient-to-r from-green-600/30 to-emerald-600/20 border-green-500/20' : 'bg-gradient-to-r from-green-600/10 to-emerald-600/5 border-green-200/30',
                                text: darkMode ? 'text-green-300' : 'text-green-700'
                              },
                              { 
                                bg: darkMode ? 'bg-gradient-to-br from-orange-600/20 to-red-600/10' : 'bg-gradient-to-br from-orange-600/10 to-red-600/5',
                                border: darkMode ? 'border-orange-500/30 hover:border-orange-500/50' : 'border-orange-200/50 hover:border-orange-300/70',
                                highlight: darkMode ? 'bg-gradient-to-r from-orange-600/30 to-red-600/20 border-orange-500/20' : 'bg-gradient-to-r from-orange-600/10 to-red-600/5 border-orange-200/30',
                                text: darkMode ? 'text-orange-300' : 'text-orange-700'
                              }
                            ];
                            const colors = colorClasses[idx % colorClasses.length];
                            return (
                              <motion.div
                                key={type}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                whileHover={{ scale: 1.02, y: -2 }}
                                className={`p-5 rounded-xl border transition-all duration-200 ${colors.bg} ${colors.border} shadow-lg hover:shadow-xl`}
                              >
                                <div className="flex items-start gap-4 mb-3">
                                  <div className={`text-3xl ${darkMode ? 'opacity-90' : 'opacity-80'}`}>
                                    {getSynergyIcon(type)}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <h5 className={`text-base font-bold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                      {info.name}
                                    </h5>
                                    <p className={`text-sm leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                      {info.description}
                                    </p>
                                  </div>
                                </div>
                                <div className={`mt-3 p-4 rounded-lg border ${colors.highlight}`}>
                                  <p className={`text-sm font-semibold mb-2 ${colors.text}`}>
                                    Why it matters:
                                  </p>
                                  <p className={`text-sm leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                    {info.importance}
                                  </p>
                                </div>
                                <div className={`mt-3 p-3 rounded-lg ${
                                  darkMode ? 'bg-slate-800/40 border border-slate-700/50' : 'bg-gray-50 border border-gray-200/50'
                                }`}>
                                  <p className={`text-xs font-semibold mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                    Example:
                                  </p>
                                  <p className={`text-sm italic leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                    {info.example}
                                  </p>
                                </div>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Stats Cards - Collapsible */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-2xl overflow-hidden transition-all duration-300 ${
            darkMode 
              ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20' 
              : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          } backdrop-blur-sm`}
        >
          {/* Stats Header - Collapsible */}
          <motion.div
            className={`p-4 ${showStatsAndFilters ? 'border-b' : ''} ${
              darkMode ? 'border-blue-500/20' : 'border-blue-200/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl">📊</span>
                <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Statistics & Filters
                </h2>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowStatsAndFilters(!showStatsAndFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all duration-300 ${
                  showStatsAndFilters
                    ? darkMode
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                    : darkMode
                    ? 'bg-slate-800/60 hover:bg-slate-700/60 text-gray-300 hover:text-white border border-slate-700/50'
                    : 'bg-white/80 hover:bg-white text-gray-700 hover:text-gray-900 border border-gray-200 shadow-sm hover:shadow-md'
                }`}
              >
                <motion.span
                  animate={{ rotate: showStatsAndFilters ? 180 : 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                  className="text-lg"
                >
                  {showStatsAndFilters ? '▲' : '▼'}
                </motion.span>
                <span className="hidden sm:inline">
                  {showStatsAndFilters ? 'Hide' : 'Show'}
                </span>
              </motion.button>
            </div>
          </motion.div>

          {/* Collapsible Stats Content */}
          <AnimatePresence>
            {showStatsAndFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                className="overflow-hidden"
              >
                <div className={`p-6 ${darkMode ? 'bg-slate-900/40' : 'bg-white/60'} backdrop-blur-sm`}>
                  <div className={`grid grid-cols-2 ${stats.validated_by_patterns !== undefined ? 'md:grid-cols-5' : 'md:grid-cols-4'} gap-4 mb-6`}>
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                    >
                      <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        {(filterType !== null || filterValidated !== null || minConfidence > 0)
                          ? synergies.length
                          : (stats?.total_synergies || 0)}
                      </div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {(filterType !== null || filterValidated !== null || minConfidence > 0)
                          ? 'Filtered Opportunities' 
                          : 'Total Opportunities'}
                        {(filterType !== null || filterValidated !== null || minConfidence > 0) && (
                          <span className="block text-xs mt-1 opacity-75">
                            of {stats?.total_synergies || 0} total
                          </span>
                        )}
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
                    {/* Phase 2: Pattern Validation Stats */}
                    {stats.validated_by_patterns !== undefined && (
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                      >
                        <div className="text-3xl font-bold bg-gradient-to-r from-green-500 to-emerald-600 bg-clip-text text-transparent">
                          {stats.validated_by_patterns || 0}
                        </div>
                        <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Pattern Validated
                        </div>
                        {stats.avg_pattern_support_score !== undefined && (
                          <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                            Avg support: {Math.round((stats.avg_pattern_support_score || 0) * 100)}%
                          </div>
                        )}
                      </motion.div>
                    )}
                  </div>

                  {/* View Toggle and Filters */}
                  <div className="space-y-4">
                    {/* View Toggle */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setViewMode('grid')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          viewMode === 'grid'
                            ? darkMode
                              ? 'bg-blue-600 text-white'
                              : 'bg-blue-500 text-white'
                            : darkMode
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        📋 Grid View
                      </button>
                      <button
                        onClick={() => setViewMode('map')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          viewMode === 'map'
                            ? darkMode
                              ? 'bg-blue-600 text-white'
                              : 'bg-blue-500 text-white'
                            : darkMode
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        🗺️ Room Map View
                      </button>
                      <button
                        onClick={() => setViewMode('graph')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          viewMode === 'graph'
                            ? darkMode
                              ? 'bg-blue-600 text-white'
                              : 'bg-blue-500 text-white'
                            : darkMode
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        🕸️ Network Graph
                      </button>
                    </div>
                    
                    {/* Sorting and Comparison Controls */}
                    <div className="flex gap-4 flex-wrap items-center justify-between">
                      <div className="flex gap-2 flex-wrap items-center">
                        <label className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          Sort by:
                        </label>
                        <select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value)}
                          className={`px-3 py-2 rounded-lg text-sm border ${
                            darkMode
                              ? 'bg-gray-800 border-gray-700 text-gray-300'
                              : 'bg-white border-gray-300 text-gray-900'
                          } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        >
                          <option value="recommended">Recommended for You</option>
                          <option value="quick-wins">Quick Wins</option>
                          <option value="highest-impact">Highest Impact</option>
                          <option value="most-confident">Most Confident</option>
                          <option value="by-area">By Area</option>
                        </select>
                      </div>
                      
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={compareMode}
                          onChange={(e) => {
                            setCompareMode(e.target.checked);
                            if (!e.target.checked) {
                              setSelectedForCompare(new Set());
                            }
                          }}
                          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          Compare Synergies
                        </span>
                      </label>
                    </div>
                    
                    {/* Comparison View */}
                    {compareMode && selectedForCompare.size > 0 && (
                      <div className={`p-4 rounded-lg border-2 ${
                        darkMode ? 'bg-gray-800 border-blue-500' : 'bg-blue-50 border-blue-400'
                      }`}>
                        <div className="flex items-center justify-between mb-3">
                          <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            Comparing {selectedForCompare.size} Synerg{selectedForCompare.size === 1 ? 'y' : 'ies'}
                          </h3>
                          <button
                            onClick={() => setSelectedForCompare(new Set())}
                            className={`text-xs px-2 py-1 rounded ${
                              darkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                            }`}
                          >
                            Clear Selection
                          </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {Array.from(selectedForCompare).map(id => {
                            const synergy = synergies.find(s => s.id === id);
                            if (!synergy) return null;
                            return (
                              <div
                                key={id}
                                className={`p-3 rounded-lg border ${
                                  darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-300'
                                }`}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <span className={`text-sm font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                    {getSynergyTypeLabel(synergy.synergy_type)}
                                  </span>
                                  <button
                                    onClick={() => handleCompareToggle(id)}
                                    className="text-xs text-red-500 hover:text-red-600"
                                  >
                                    ✕
                                  </button>
                                </div>
                                <div className="space-y-1 text-xs">
                                  <div className="flex justify-between">
                                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Impact:</span>
                                    <span className="font-semibold">{Math.round(synergy.impact_score * 100)}%</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Confidence:</span>
                                    <span className="font-semibold">{Math.round(synergy.confidence * 100)}%</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Complexity:</span>
                                    <span className={`font-semibold ${getComplexityColor(synergy.complexity)}`}>
                                      {synergy.complexity}
                                    </span>
                                  </div>
                                  {synergy.area && (
                                    <div className="flex justify-between">
                                      <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Area:</span>
                                      <span className="font-semibold">{synergy.area}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Filter Pills */}
                    <div className="flex gap-2 flex-wrap items-center">
                      <button
                        onClick={() => {
                          setFilterType(null);
                          setFilterValidated(null);
                          setMinConfidence(0.0);
                        }}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                          filterType === null && filterValidated === null && minConfidence === 0.0
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
                      {/* Phase 2: Pattern Validation Filter */}
                      <button
                        onClick={() => setFilterValidated(filterValidated === true ? null : true)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                          filterValidated === true
                            ? 'bg-green-600 text-white'
                            : darkMode
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                        title="Filter synergies validated by patterns"
                      >
                        ✓ Validated
                      </button>
                      <button
                        onClick={() => setFilterValidated(filterValidated === false ? null : false)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                          filterValidated === false
                            ? 'bg-yellow-600 text-white'
                            : darkMode
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                        title="Filter unvalidated synergies"
                      >
                        ⚠ Unvalidated
                      </button>
                      
                      {/* Confidence Filter */}
                      <div className={`px-4 py-2 rounded-full text-sm font-medium ${darkMode ? 'bg-gray-800' : 'bg-gray-200'} flex items-center gap-2 ${minConfidence > 0 ? (darkMode ? 'ring-2 ring-blue-500' : 'ring-2 ring-blue-400') : ''}`}>
                        <label className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Min Confidence:
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={minConfidence * 100}
                          onChange={(e) => setMinConfidence(parseFloat(e.target.value) / 100)}
                          className={`w-24 h-2 rounded-lg appearance-none cursor-pointer ${
                            darkMode 
                              ? 'bg-gray-600 accent-blue-500' 
                              : 'bg-gray-300 accent-blue-600'
                          }`}
                          style={{
                            background: darkMode
                              ? `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${minConfidence * 100}%, #4b5563 ${minConfidence * 100}%, #4b5563 100%)`
                              : `linear-gradient(to right, #2563eb 0%, #2563eb ${minConfidence * 100}%, #d1d5db ${minConfidence * 100}%, #d1d5db 100%)`
                          }}
                          title={`Minimum confidence: ${Math.round(minConfidence * 100)}%`}
                        />
                        <span className={`text-xs font-semibold min-w-[3rem] ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          {Math.round(minConfidence * 100)}%
                        </span>
                        {minConfidence > 0 && (
                          <button
                            onClick={() => setMinConfidence(0.0)}
                            className={`ml-1 text-xs hover:underline ${darkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-600 hover:text-gray-800'}`}
                            title="Reset confidence filter"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
      
      {/* Filter Feedback */}
      {(filterType !== null || filterValidated !== null || minConfidence > 0) && synergies.length === 0 && stats && stats.total_synergies > 0 && (
        <div className={`p-4 rounded-lg ${darkMode ? 'bg-yellow-900/30 border border-yellow-700' : 'bg-yellow-50 border border-yellow-200'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm font-medium ${darkMode ? 'text-yellow-300' : 'text-yellow-800'}`}>
                {stats.total_synergies} opportunities found, but none match your current filters.
              </p>
              <p className={`text-xs mt-1 ${darkMode ? 'text-yellow-400' : 'text-yellow-700'}`}>
                Try adjusting your filters or click "All" to see all opportunities.
              </p>
            </div>
            <button
              onClick={() => {
                setFilterType(null);
                setFilterValidated(null);
                setMinConfidence(0.0);
              }}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                darkMode
                  ? 'bg-yellow-700 hover:bg-yellow-600 text-white'
                  : 'bg-yellow-200 hover:bg-yellow-300 text-yellow-800'
              }`}
            >
              Clear Filters
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Empty State */}
      {!loading && synergies.length === 0 && (!stats || stats.total_synergies === 0) && (
        <div className={`text-center py-12 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
          <div className="text-6xl mb-4">🔍</div>
          <div className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            No Synergies Detected Yet
          </div>
          <p className={`mt-2 mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Run the daily analysis to discover automation opportunities between your devices
          </p>
          <div className={`mt-6 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <p className="font-semibold mb-2">Analysis will detect synergies including:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-left max-w-2xl mx-auto">
              <div className="flex items-start gap-2">
                <span>🔗</span>
                <span><strong>Device Pairs:</strong> Devices that could work together</span>
              </div>
              <div className="flex items-start gap-2">
                <span>🌤️</span>
                <span><strong>Weather-Aware:</strong> Weather-responsive automations</span>
              </div>
              <div className="flex items-start gap-2">
                <span>⚡</span>
                <span><strong>Energy Optimization:</strong> Cost-saving opportunities</span>
              </div>
              <div className="flex items-start gap-2">
                <span>📅</span>
                <span><strong>Event-Based:</strong> Calendar and event triggers</span>
              </div>
            </div>
            <p className="mt-4 text-xs italic">
              Click "Synergy Type Guide" above to learn more about each synergy type and why they matter for automation.
            </p>
          </div>
        </div>
      )}

      {/* Conditional Rendering: Grid, Map, or Graph View */}
      {viewMode === 'map' ? (
        <RoomMapView synergies={sortedSynergies} darkMode={darkMode} />
      ) : viewMode === 'graph' ? (
        <NetworkGraphView 
          synergies={sortedSynergies} 
          darkMode={darkMode}
        />
      ) : (
        /* Synergy Grid */
        <AnimatePresence mode="popLayout">
          {!loading && sortedSynergies.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {sortedSynergies.map((synergy, index) => (
              <motion.div
                key={synergy.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.05 }}
                className={`p-6 rounded-xl ${
                  darkMode ? 'bg-gray-800' : 'bg-white'
                } shadow-lg hover:shadow-xl transition-shadow ${
                  compareMode && selectedForCompare.has(synergy.id)
                    ? 'ring-2 ring-blue-500'
                    : ''
                }`}
                onClick={() => {
                  if (compareMode) {
                    handleCompareToggle(synergy.id);
                  } else {
                    toggleExpanded(synergy.id);
                  }
                }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="text-3xl">{getSynergyIcon(synergy.synergy_type)}</div>
                  <div className="flex gap-2 flex-wrap">
                    {/* Phase 2: Pattern Validation Badge */}
                    {synergy.validated_by_patterns && (
                      <span 
                        className="px-2 py-1 rounded-full text-xs font-medium bg-green-600 text-white"
                        title={`Validated by patterns (${Math.round((synergy.pattern_support_score || 0) * 100)}% support)`}
                      >
                        ✓ Validated
                      </span>
                    )}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getComplexityColor(synergy.complexity)}`}>
                      {synergy.complexity}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-600 text-white">
                      {Math.round(synergy.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {/* Type with Enhanced Info */}
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {getSynergyTypeLabel(synergy.synergy_type)}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      darkMode 
                        ? 'bg-purple-900/30 text-purple-300 border border-purple-700/50' 
                        : 'bg-purple-100 text-purple-800 border border-purple-200'
                    }`}>
                      {getSynergyTypeInfo(synergy.synergy_type).name}
                    </span>
                  </div>
                  <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {getSynergyTypeInfo(synergy.synergy_type).description}
                  </p>
                </div>

                {/* Area - Emphasize Spatial Proximity */}
                {synergy.area && (
                  <div className={`p-2 rounded-lg mb-3 ${darkMode ? 'bg-blue-900/20 border border-blue-700/50' : 'bg-blue-50 border border-blue-200'}`}>
                    <div className={`text-xs font-semibold mb-1 ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
                      📍 Same Room/Area
                    </div>
                    <div className={`text-sm font-medium ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
                      {synergy.area}
                    </div>
                    <div className={`text-xs mt-1 ${darkMode ? 'text-blue-300/80' : 'text-blue-700/80'}`}>
                      These devices are physically close to each other in the same space
                    </div>
                  </div>
                )}

                {/* Devices & Trigger/Action */}
                <div className="space-y-3 mb-4">
                  {/* Event-Based Synergies (different display) */}
                  {synergy.synergy_type === 'event_context' ? (
                    <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                      <div className={`text-xs font-semibold mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Event-Triggered Automation
                      </div>
                      <div className={`text-sm ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-blue-400">Event:</span>
                          <span className="font-medium">
                            {synergy.opportunity_metadata?.event_context || 'Sports/Calendar Event'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-green-400">Action:</span>
                          <span className="font-medium">
                            {synergy.opportunity_metadata?.action_name || synergy.opportunity_metadata?.action_entity || 'Activate scene'}
                          </span>
                        </div>
                        {synergy.opportunity_metadata?.suggested_action && (
                          <div className={`text-xs mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            💡 {synergy.opportunity_metadata.suggested_action}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    /* Device Pair Synergies */
                    synergy.opportunity_metadata?.trigger_name && synergy.opportunity_metadata?.action_name && (
                      <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                        <div className={`text-xs font-semibold mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Automation Flow
                        </div>
                        <div className={`text-sm ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-blue-400">Trigger:</span>
                            <span className="font-medium">{synergy.opportunity_metadata.trigger_name}</span>
                            {synergy.opportunity_metadata.trigger_entity && (
                              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                                ({synergy.opportunity_metadata.trigger_entity})
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-green-400">Action:</span>
                            <span className="font-medium">{synergy.opportunity_metadata.action_name}</span>
                            {synergy.opportunity_metadata.action_entity && (
                              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                                ({synergy.opportunity_metadata.action_entity})
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  )}

                  {/* Device IDs List */}
                  {(() => {
                    const deviceIds = parseDeviceIds(synergy.device_ids);
                    const chainDevices = (synergy as any).chain_devices || [];
                    const allDevices = chainDevices.length > 0 ? chainDevices : deviceIds;
                    
                    if (allDevices.length > 0) {
                      return (
                        <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                          <div className={`text-xs font-semibold mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            Devices Involved ({allDevices.length})
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {allDevices.map((deviceId: string, idx: number) => (
                              <span
                                key={idx}
                                className={`px-2 py-1 rounded text-xs font-mono ${
                                  darkMode 
                                    ? 'bg-gray-600 text-gray-300' 
                                    : 'bg-gray-200 text-gray-700'
                                }`}
                              >
                                {deviceId}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>

                {/* Rationale/Explanation - Prominently Displayed */}
                {(() => {
                  // Prefer rationale from opportunity_metadata, then from root, then generate from explanation
                  const rationale = synergy.opportunity_metadata?.rationale || 
                                   (synergy as any).rationale || 
                                   (synergy as any).explanation?.summary;
                  
                  // For event_context, show better explanation
                  if (synergy.synergy_type === 'event_context' && !rationale) {
                    const eventContext = synergy.opportunity_metadata?.event_context || 'sports/calendar event';
                    const actionName = synergy.opportunity_metadata?.action_name || 'device';
                    const suggestedAction = synergy.opportunity_metadata?.suggested_action || 'Activate scene';
                    return (
                      <div className={`p-4 rounded-lg mb-4 border-l-4 ${
                        darkMode 
                          ? 'bg-purple-900/20 border-purple-500' 
                          : 'bg-purple-50 border-purple-400'
                      }`}>
                        <div className={`text-xs font-semibold mb-2 ${
                          darkMode ? 'text-purple-300' : 'text-purple-700'
                        }`}>
                          💡 Why This Synergy Was Detected
                        </div>
                        <div className={`text-sm leading-relaxed mb-2 ${
                          darkMode ? 'text-gray-200' : 'text-gray-800'
                        }`}>
                          {suggestedAction} for {actionName} when {eventContext} occurs. This automation would enhance your entertainment experience during scheduled events.
                        </div>
                        <div className={`p-2 rounded text-xs ${darkMode ? 'bg-purple-900/30 text-purple-200' : 'bg-purple-100 text-purple-800'}`}>
                          <p className="font-semibold mb-0.5">💡 Why this matters:</p>
                          <p>{getSynergyTypeInfo(synergy.synergy_type).importance}</p>
                        </div>
                      </div>
                    );
                  }
                  
                  if (rationale && rationale !== 'None' && !rationale.includes('None → None')) {
                    return (
                      <div className={`p-4 rounded-lg mb-4 border-l-4 ${
                        darkMode 
                          ? 'bg-purple-900/20 border-purple-500' 
                          : 'bg-purple-50 border-purple-400'
                      }`}>
                        <div className={`text-xs font-semibold mb-2 ${
                          darkMode ? 'text-purple-300' : 'text-purple-700'
                        }`}>
                          💡 Why This Synergy Was Detected
                        </div>
                        <div className={`text-sm leading-relaxed mb-2 ${
                          darkMode ? 'text-gray-200' : 'text-gray-800'
                        }`}>
                          {rationale}
                        </div>
                        <div className={`p-2 rounded text-xs ${darkMode ? 'bg-purple-900/30 text-purple-200' : 'bg-purple-100 text-purple-800'}`}>
                          <p className="font-semibold mb-0.5">💡 Why this matters:</p>
                          <p>{getSynergyTypeInfo(synergy.synergy_type).importance}</p>
                        </div>
                      </div>
                    );
                  }
                  
                  // Fallback: Show synergy type importance even without rationale
                  return (
                    <div className={`p-4 rounded-lg mb-4 border-l-4 ${
                      darkMode 
                        ? 'bg-purple-900/20 border-purple-500' 
                        : 'bg-purple-50 border-purple-400'
                    }`}>
                      <div className={`text-xs font-semibold mb-2 ${
                        darkMode ? 'text-purple-300' : 'text-purple-700'
                      }`}>
                        💡 Why This Synergy Matters
                      </div>
                      <div className={`text-sm leading-relaxed ${
                        darkMode ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        {getSynergyTypeInfo(synergy.synergy_type).importance}
                      </div>
                    </div>
                  );
                })()}

                {/* Additional Metadata */}
                {synergy.opportunity_metadata && (
                  <div className="space-y-2 mb-4">
                    {synergy.opportunity_metadata.relationship && (
                      <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        <span className="font-semibold">Relationship:</span>{' '}
                        {synergy.opportunity_metadata.relationship.replace(/_/g, ' ')}
                      </div>
                    )}
                    {synergy.opportunity_metadata.weather_condition && (
                      <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        <span className="font-semibold">Weather Condition:</span>{' '}
                        {synergy.opportunity_metadata.weather_condition}
                      </div>
                    )}
                    {synergy.opportunity_metadata.suggested_action && (
                      <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        <span className="font-semibold">Suggested Action:</span>{' '}
                        {synergy.opportunity_metadata.suggested_action}
                      </div>
                    )}
                    {synergy.opportunity_metadata.estimated_savings && (
                      <div className={`text-xs font-semibold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                        💰 Estimated Savings: {synergy.opportunity_metadata.estimated_savings}
                      </div>
                    )}
                  </div>
                )}

                {/* Impact Score Visualization - Show in expanded view */}
                {expandedSynergies.has(synergy.id) && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <div className="mb-4">
                      <ImpactScoreGauge synergy={synergy} darkMode={darkMode} />
                    </div>
                  </div>
                )}
                
                {/* Impact Score & Pattern Support */}
                <div className="mt-4 pt-4 border-t border-gray-700 space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                      Impact Score
                    </span>
                    <span className="font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                      {Math.round(synergy.impact_score * 100)}%
                    </span>
                  </div>
                  {/* Phase 2: Pattern Support Score */}
                  {synergy.pattern_support_score !== undefined && synergy.pattern_support_score > 0 && (
                    <div className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-500'}>
                          Pattern Support
                        </span>
                        <span className={`font-medium ${
                          synergy.pattern_support_score >= 0.7 
                            ? 'text-green-500' 
                            : synergy.pattern_support_score >= 0.5
                            ? 'text-yellow-500'
                            : 'text-gray-500'
                        }`}>
                          {Math.round(synergy.pattern_support_score * 100)}%
                        </span>
                      </div>
                      <div className={`h-1.5 rounded-full overflow-hidden ${
                        darkMode ? 'bg-gray-700' : 'bg-gray-200'
                      }`}>
                        <div 
                          className={`h-full ${
                            synergy.pattern_support_score >= 0.7
                              ? 'bg-green-500'
                              : synergy.pattern_support_score >= 0.5
                              ? 'bg-yellow-500'
                              : 'bg-gray-400'
                          }`}
                          style={{ width: `${synergy.pattern_support_score * 100}%` }}
                        />
                      </div>
                      {synergy.supporting_pattern_ids && synergy.supporting_pattern_ids.length > 0 && (
                        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                          Supported by {synergy.supporting_pattern_ids.length} pattern{synergy.supporting_pattern_ids.length !== 1 ? 's' : ''}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Quick Actions */}
                <div className="mt-4 pt-4 border-t border-gray-700 flex gap-2 flex-wrap">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSave(synergy.id);
                    }}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      savedSynergies.has(synergy.id)
                        ? darkMode
                          ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                          : 'bg-yellow-500 hover:bg-yellow-600 text-white'
                        : darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                    title={savedSynergies.has(synergy.id) ? 'Remove from saved' : 'Save for later'}
                  >
                    {savedSynergies.has(synergy.id) ? '✓ Saved' : '💾 Save'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDismiss(synergy.id);
                    }}
                    className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                    title="Dismiss this synergy"
                  >
                    ✕ Dismiss
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Implement automation creation
                      alert('Automation creation coming soon!');
                    }}
                    className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    }`}
                    title="Create automation from this synergy"
                  >
                    🚀 Create
                  </button>
                </div>
                
                {/* Expandable Details Section */}
                <div className="mt-4 pt-4 border-t border-gray-700">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpanded(synergy.id);
                    }}
                    className={`w-full text-left text-xs font-medium transition-colors ${
                      darkMode 
                        ? 'text-gray-400 hover:text-gray-300' 
                        : 'text-gray-600 hover:text-gray-800'
                    }`}
                  >
                    {expandedSynergies.has(synergy.id) ? '▼ Hide Details' : '▶ Show More Details'}
                  </button>
                  
                  {expandedSynergies.has(synergy.id) && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-3 space-y-2"
                    >
                      {/* Synergy ID */}
                      <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                        <span className="font-semibold">Synergy ID:</span>{' '}
                        <span className="font-mono">{synergy.synergy_id}</span>
                      </div>

                      {/* Pattern Support Details */}
                      {synergy.supporting_pattern_ids && synergy.supporting_pattern_ids.length > 0 && (
                        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                          <span className="font-semibold">Supporting Patterns:</span>{' '}
                          {synergy.supporting_pattern_ids.join(', ')}
                        </div>
                      )}

                      {/* Chain Path (for multi-device chains) */}
                      {(synergy as any).chain_path && (
                        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          <span className="font-semibold">Chain Path:</span>{' '}
                          {(synergy as any).chain_path}
                        </div>
                      )}

                      {/* Synergy Depth */}
                      {(synergy as any).synergy_depth && (synergy as any).synergy_depth > 2 && (
                        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          <span className="font-semibold">Chain Depth:</span>{' '}
                          {(synergy as any).synergy_depth} devices
                        </div>
                      )}

                      {/* Score Breakdown Chart */}
                      {((synergy as any).explanation_breakdown || synergy.explanation?.score_breakdown) && (
                        <div className={`p-3 rounded-lg mt-2 ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                          <div className="flex items-center justify-between mb-2">
                            <div className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              Score Breakdown
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleBreakdown(synergy.id);
                              }}
                              className={`text-xs px-2 py-1 rounded ${
                                darkMode
                                  ? 'bg-gray-600 hover:bg-gray-500 text-gray-300'
                                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                              }`}
                            >
                              {showBreakdown.has(synergy.id) ? 'Hide Chart' : 'Show Chart'}
                            </button>
                          </div>
                          {showBreakdown.has(synergy.id) ? (
                            <ScoreBreakdownChart synergy={synergy} darkMode={darkMode} />
                          ) : (
                            <div className="space-y-1">
                              {Object.entries((synergy as any).explanation_breakdown || synergy.explanation?.score_breakdown || {}).map(([key, value]: [string, any]) => (
                                <div key={key} className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                  <span className="font-medium">{key.replace(/_/g, ' ')}:</span>{' '}
                                  {typeof value === 'number' ? `${Math.round(value * 100)}%` : String(value)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </motion.div>
                  )}
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
      )}
    </div>
  );
};

