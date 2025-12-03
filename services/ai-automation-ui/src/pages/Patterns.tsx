/**
 * Pattern Explorer Page
 * Visualize detected usage patterns
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import api from '../services/api';
import type { Pattern } from '../types';
import { PatternTypeChart, ConfidenceDistributionChart, TopDevicesChart } from '../components/PatternChart';

export const Patterns: React.FC = () => {
  const { darkMode } = useAppStore();
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [deviceNames, setDeviceNames] = useState<Record<string, string>>({});
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [scheduleInfo, setScheduleInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPatternGuide, setShowPatternGuide] = useState(false);
  const [showStatsAndCharts, setShowStatsAndCharts] = useState(true); // Collapsible stats

  const loadPatterns = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const [patternsRes, statsRes] = await Promise.all([
        api.getPatterns(undefined, 0.7),
        api.getPatternStats()
      ]);
      
      const patternsData = patternsRes.data?.patterns || [];
      setPatterns(patternsData);
      setStats(statsRes);

      // Load device names for the patterns
      if (patternsData.length > 0) {
        const uniqueDeviceIds = [...new Set(patternsData.map(p => p.device_id))];
        try {
          const names = await api.getDeviceNames(uniqueDeviceIds);
          setDeviceNames(names);
        } catch (nameError: any) {
          console.warn('Failed to load device names (non-critical):', nameError);
          // Don't fail the entire load if device names fail
        }
      }
    } catch (err: any) {
      console.error('Failed to load patterns:', err);
      
      // Provide more specific error messages
      let errorMessage = 'Failed to load patterns';
      if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Network error: Unable to connect to the server. Please check your connection.';
      } else if (err.message) {
        errorMessage = err.message;
      } else if (err.toString && err.toString() !== '[object Object]') {
        errorMessage = err.toString();
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAnalysisStatus = useCallback(async () => {
    try {
      const [, schedule] = await Promise.all([
        api.getAnalysisStatus(),
        api.getScheduleInfo()
      ]);
      setScheduleInfo(schedule);
    } catch (err) {
      console.error('Failed to load analysis status:', err);
    }
  }, []);

  useEffect(() => {
    loadPatterns();
    loadAnalysisStatus();

    // Refresh patterns every 30 seconds if analysis is running
    let interval: ReturnType<typeof setInterval> | null = null;
    if (analysisRunning) {
      interval = setInterval(() => {
        loadPatterns();
        loadAnalysisStatus();
      }, 10000); // Check every 10 seconds during analysis
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [analysisRunning, loadPatterns, loadAnalysisStatus]);

  const handleRunAnalysis = async () => {
    try {
      setAnalysisRunning(true);
      setError(null);
      await api.triggerManualJob();
      
      // Start polling for completion
      const pollInterval = setInterval(async () => {
        try {
          await loadPatterns();
          await loadAnalysisStatus();
          
          // Check if analysis completed (patterns increased or status changed)
          const status = await api.getAnalysisStatus();
          if (status.status === 'ready') {
            clearInterval(pollInterval);
            setAnalysisRunning(false);
          }
        } catch (err) {
          console.error('Failed to poll analysis status:', err);
        }
      }, 5000);

      // Stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        setAnalysisRunning(false);
      }, 300000);
    } catch (err: any) {
      console.error('Failed to trigger analysis:', err);
      setError(err.message || 'Failed to start analysis');
      setAnalysisRunning(false);
    }
  };

  const formatLastRun = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } catch {
      return 'Unknown';
    }
  };

  const getPatternIcon = (type: string) => {
    const icons: Record<string, string> = {
      time_of_day: '⏰',
      co_occurrence: '🔗',
      sequence: '➡️',
      contextual: '🌍',
      room_based: '🏠',
      session: '👤',
      duration: '⏱️',
      day_type: '📅',
      seasonal: '🍂',
      anomaly: '⚠️',
    };
    return icons[type] || '📊';
  };

  const getPatternTypeInfo = (type: string) => {
    const info: Record<string, { name: string; description: string; importance: string; example: string }> = {
      time_of_day: {
        name: 'Time-of-Day Patterns',
        description: 'Detects when devices are consistently used at specific times throughout the day.',
        importance: 'These patterns reveal your daily routines and help create time-based automations that match your natural behavior.',
        example: 'Bedroom light turns on at 7:00 AM every morning, or thermostat adjusts at 6:00 PM in the evening.'
      },
      co_occurrence: {
        name: 'Co-Occurrence Patterns',
        description: 'Identifies devices that are used together within a short time window (typically 5-30 minutes).',
        importance: 'Shows device relationships and enables coordinated automations. When one device activates, related devices can automatically respond.',
        example: 'Motion sensor triggers → Light turns on (within 30 seconds), or Door opens → Alarm activates (within 2 minutes).'
      },
      sequence: {
        name: 'Sequence Patterns',
        description: 'Detects multi-step behaviors where devices activate in a specific order over time.',
        importance: 'Captures complex routines that involve multiple devices. Perfect for creating automation chains that replicate your natural behavior.',
        example: 'Coffee maker starts → Kitchen light turns on → Music plays (all within 10 minutes).'
      },
      contextual: {
        name: 'Contextual Patterns',
        description: 'Identifies behaviors that depend on external factors like weather, presence, or time context.',
        importance: 'Enables smart, adaptive automations that respond to your environment. Makes your home truly intelligent and context-aware.',
        example: 'Lights turn on at 6 PM when it\'s cloudy, or thermostat adjusts when you arrive home.'
      },
      room_based: {
        name: 'Room-Based Patterns',
        description: 'Detects device interactions within specific rooms or areas of your home.',
        importance: 'Helps create room-specific automations and understand spatial relationships between devices.',
        example: 'Living room motion sensor → Living room lights, or Bedroom door opens → Bedroom lights activate.'
      },
      session: {
        name: 'Session Patterns',
        description: 'Identifies user routine patterns that occur during specific activity sessions.',
        importance: 'Captures your personal routines and habits, enabling automations that adapt to your lifestyle.',
        example: 'Morning routine: Coffee → News → Lights, or Evening routine: Dim lights → Music → Thermostat.'
      },
      duration: {
        name: 'Duration Patterns',
        description: 'Detects how long devices typically stay in a certain state or how long activities last.',
        importance: 'Helps optimize device usage and create auto-off timers that match your actual usage patterns.',
        example: 'Lights typically stay on for 30 minutes after motion, or TV is watched for 2 hours in the evening.'
      },
      day_type: {
        name: 'Day-Type Patterns',
        description: 'Identifies differences between weekday and weekend behaviors.',
        importance: 'Enables different automation schedules for workdays vs. weekends, making your home adapt to your schedule.',
        example: 'Weekday: Alarm at 7 AM, Weekend: No alarm, or Weekday: Lights off at 10 PM, Weekend: Lights off at midnight.'
      },
      seasonal: {
        name: 'Seasonal Patterns',
        description: 'Detects behavior changes across seasons (summer vs. winter, daylight changes).',
        importance: 'Allows automations to adapt to seasonal changes automatically, maintaining comfort year-round.',
        example: 'Lights turn on earlier in winter (5 PM) vs. summer (8 PM), or thermostat settings change with seasons.'
      },
      anomaly: {
        name: 'Anomaly Patterns',
        description: 'Identifies unusual behaviors that deviate from normal patterns.',
        importance: 'Helps detect potential issues, security concerns, or opportunities to optimize unusual device usage.',
        example: 'Device activated at unusual time, or device left on longer than normal, or unexpected device combination.'
      }
    };
    return info[type] || {
      name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      description: 'Pattern detected in your smart home usage.',
      importance: 'Helps create intelligent automations based on your behavior.',
      example: 'Device usage pattern detected.'
    };
  };

  const getFallbackName = (deviceId: string) => {
    if (deviceId.includes('+')) {
      const parts = deviceId.split('+');
      if (parts.length === 2) {
        return `Co-occurrence (${parts[0].substring(0, 8)}... + ${parts[1].substring(0, 8)}...)`;
      }
    }
    
    // Try to create a more descriptive name based on the device ID pattern
    if (deviceId.length === 32) {
      // Looks like a hash - create a more friendly name
      return `Device ${deviceId.substring(0, 8)}...`;
    }
    
    return deviceId.length > 20 ? `${deviceId.substring(0, 20)}...` : deviceId;
  };

  return (
    <div className="space-y-6" data-testid="patterns-container">
      {/* Hero Section with Pattern Information - Modern 2025 Design */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex justify-between items-center gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                📊 Detected Patterns
              </h1>
            </div>
            <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Usage patterns detected by machine learning analysis
            </p>
          </div>
        </div>

        {/* What Are Patterns Section */}
        <div className={`mt-4 p-4 rounded-lg border ${darkMode ? 'bg-gray-800/60 border-gray-700' : 'bg-white/80 border-gray-200'}`}>
          <h2 className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            What Are Patterns?
          </h2>
          <p className={`mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Patterns are recurring behaviors detected in your smart home device usage. Our AI analyzes your Home Assistant events 
            over the past 30 days to identify when, how, and why you use your devices. These patterns form the foundation for 
            intelligent automation suggestions.
          </p>
          <div className={`p-3 rounded ${darkMode ? 'bg-blue-900/30 border border-blue-700/50' : 'bg-blue-100 border border-blue-200'}`}>
            <p className={`font-semibold mb-1 ${darkMode ? 'text-blue-300' : 'text-blue-900'}`}>
              Why Patterns Matter:
            </p>
            <ul className={`list-disc list-inside space-y-1 text-sm ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
              <li><strong>Personalized Automations:</strong> Patterns reflect YOUR actual behavior, not generic templates</li>
              <li><strong>Energy Savings:</strong> Identify opportunities to optimize device usage and reduce waste</li>
              <li><strong>Convenience:</strong> Automate repetitive actions you do manually every day</li>
              <li><strong>Intelligence:</strong> Your home learns your routines and adapts automatically</li>
              <li><strong>Discovery:</strong> Find relationships between devices you might not have noticed</li>
            </ul>
          </div>

          {/* Pattern Type Guide Toggle - Modern 2025 Design */}
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => setShowPatternGuide(!showPatternGuide)}
            className={`w-full mt-4 p-2 rounded-lg text-xs font-medium transition-all ${
              darkMode 
                ? 'bg-gray-700/50 hover:bg-gray-600/50 text-gray-300' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            }`}
          >
            <span className="flex items-center justify-between">
              <span>
                {showPatternGuide ? '▼' : '▶'} Pattern Type Guide
              </span>
              <span className="text-xs opacity-75">
                {showPatternGuide ? 'Hide' : 'Show Details'}
              </span>
            </span>
          </motion.button>

          {/* Pattern Type Guide - Collapsible */}
          <AnimatePresence>
            {showPatternGuide && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className={`mt-2 p-3 rounded-lg ${darkMode ? 'bg-gray-800/40' : 'bg-gray-50'} max-h-80 overflow-y-auto`}>
                  <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Pattern Types Explained
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['time_of_day', 'co_occurrence', 'sequence', 'contextual', 'room_based', 'session', 'duration', 'day_type', 'seasonal', 'anomaly'].map((type) => {
                      const info = getPatternTypeInfo(type);
                      return (
                        <div
                          key={type}
                          className={`p-4 rounded-lg border ${darkMode ? 'bg-gray-800/30 border-gray-700' : 'bg-white border-gray-200'}`}
                        >
                          <div className="flex items-start gap-3 mb-2">
                            <span className="text-2xl">{getPatternIcon(type)}</span>
                            <div className="flex-1">
                              <h4 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                {info.name}
                              </h4>
                              <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                {info.description}
                              </p>
                            </div>
                          </div>
                          <div className={`mt-2 p-2 rounded text-xs ${darkMode ? 'bg-blue-900/20 text-blue-200' : 'bg-blue-50 text-blue-800'}`}>
                            <p className="font-semibold mb-1">Why it matters:</p>
                            <p>{info.importance}</p>
                          </div>
                          <div className={`mt-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            <p className="font-semibold">Example:</p>
                            <p className="italic">{info.example}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {scheduleInfo && (
          <p className={`text-sm mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Last analysis: {formatLastRun(scheduleInfo.last_run_time || scheduleInfo.last_run)} • 
            {' '}Next scheduled: {scheduleInfo.next_run_time || '3:00 AM daily'}
          </p>
        )}
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end gap-2"
      >
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={loadPatterns}
          disabled={loading || analysisRunning}
          className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
            darkMode 
              ? 'bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-50' 
              : 'bg-gray-200 hover:bg-gray-300 text-gray-900 disabled:opacity-50'
          }`}
        >
          🔄 Refresh
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleRunAnalysis}
          disabled={analysisRunning || loading}
          className={`px-4 py-1.5 text-xs rounded-lg font-medium transition-all ${
            analysisRunning
              ? 'bg-blue-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700'
          } text-white disabled:opacity-50`}
        >
          {analysisRunning ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Analyzing...
            </span>
          ) : (
            '🚀 Run Analysis'
          )}
        </motion.button>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 rounded-lg ${darkMode ? 'bg-red-900/30 border border-red-700' : 'bg-red-50 border border-red-200'}`}
        >
          <p className={`font-medium ${darkMode ? 'text-red-300' : 'text-red-800'}`}>
            ⚠️ Error: {error}
          </p>
        </motion.div>
      )}

      {analysisRunning && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`p-4 rounded-lg ${darkMode ? 'bg-blue-900/30 border border-blue-700' : 'bg-blue-50 border border-blue-200'}`}
        >
          <div className="flex items-center gap-3">
            <span className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <div>
              <p className={`font-medium ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>
                Analysis in progress...
              </p>
              <p className={`text-sm ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                This may take 1-3 minutes. Patterns will appear automatically when complete.
              </p>
            </div>
          </div>
        </motion.div>
      )}

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
            className={`p-4 ${showStatsAndCharts ? 'border-b' : ''} ${
              darkMode ? 'border-blue-500/20' : 'border-blue-200/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl">📊</span>
                <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Statistics & Charts
                </h2>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowStatsAndCharts(!showStatsAndCharts)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all duration-300 ${
                  showStatsAndCharts
                    ? darkMode
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                    : darkMode
                    ? 'bg-slate-800/60 hover:bg-slate-700/60 text-gray-300 hover:text-white border border-slate-700/50'
                    : 'bg-white/80 hover:bg-white text-gray-700 hover:text-gray-900 border border-gray-200 shadow-sm hover:shadow-md'
                }`}
              >
                <motion.span
                  animate={{ rotate: showStatsAndCharts ? 180 : 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                  className="text-lg"
                >
                  {showStatsAndCharts ? '▲' : '▼'}
                </motion.span>
                <span className="hidden sm:inline">
                  {showStatsAndCharts ? 'Hide' : 'Show'}
                </span>
              </motion.button>
            </div>
          </motion.div>

          {/* Collapsible Stats Content */}
          <AnimatePresence>
            {showStatsAndCharts && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                className="overflow-hidden"
              >
                <div className={`p-6 ${darkMode ? 'bg-slate-900/40' : 'bg-white/60'} backdrop-blur-sm`}>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                    >
            <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {stats.total_patterns || 0}
            </div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Total Patterns
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 }}
                      className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                    >
            <div className="text-3xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              {stats.unique_devices || 0}
            </div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Devices
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                    >
            <div className="text-3xl font-bold bg-gradient-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
              {Math.round((stats.avg_confidence || 0) * 100)}%
            </div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Avg Confidence
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                    >
            <div className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              {Object.keys(stats.by_type || {}).length}
            </div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Pattern Types
                      </div>
                    </motion.div>
                  </div>

                  {/* Charts Section */}
                  {!loading && patterns.length > 0 && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                      >
                        <div className="mb-4">
                          <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            📊 Pattern Distribution
                          </h3>
                          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            Breakdown of patterns by type. Hover over bars for detailed counts.
                          </p>
                        </div>
                        <PatternTypeChart patterns={patterns} darkMode={darkMode} />
                      </motion.div>
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}
                      >
                        <div className="mb-4">
                          <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            🎯 Confidence Levels
                          </h3>
                          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            Quality distribution of detected patterns. Higher confidence = more reliable automations.
                          </p>
                        </div>
                        <ConfidenceDistributionChart patterns={patterns} darkMode={darkMode} />
                      </motion.div>
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7 }}
                        className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg lg:col-span-2`}
                      >
                        <div className="mb-4">
                          <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            🔝 Top Devices with Patterns
                          </h3>
                          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            Devices that appear most frequently in detected patterns. These are prime candidates for automation.
                          </p>
                        </div>
                        <TopDevicesChart patterns={patterns} darkMode={darkMode} />
                      </motion.div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Detected Pattern Types - Prominent Display */}
      {stats && stats.by_type && Object.keys(stats.by_type).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className={`p-6 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-blue-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200'} shadow-xl`}
        >
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl">🎯</span>
            <div>
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Detected Pattern Types
              </h2>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Your smart home is showing {Object.keys(stats.by_type).length} distinct pattern types
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            {Object.entries(stats.by_type)
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([type, count], idx) => {
                const info = getPatternTypeInfo(type);
                const percentage = stats.total_patterns > 0 
                  ? Math.round(((count as number) / stats.total_patterns) * 100) 
                  : 0;
                return (
                  <motion.div
                    key={type}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.5 + idx * 0.1 }}
                    className={`p-4 rounded-lg border-2 ${
                      darkMode 
                        ? 'bg-gray-800/50 border-purple-700/50 hover:border-purple-500/70' 
                        : 'bg-white border-purple-200 hover:border-purple-300'
                    } transition-all hover:shadow-lg`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-3xl flex-shrink-0">{getPatternIcon(type)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            {info.name}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent`}>
                            {count as number}
                          </span>
                          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            patterns ({percentage}%)
                          </span>
                        </div>
                        <p className={`text-xs mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'} line-clamp-2`}>
                          {info.description}
                        </p>
                        <div className={`mt-2 p-2 rounded text-xs ${darkMode ? 'bg-purple-900/30 text-purple-200' : 'bg-purple-50 text-purple-800'}`}>
                          <p className="font-semibold">💡 {info.importance}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
          </div>

          <div className={`mt-4 p-3 rounded-lg ${darkMode ? 'bg-blue-900/20 border border-blue-700/30' : 'bg-blue-50 border border-blue-200'}`}>
            <p className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
              <strong>💡 Insight:</strong> These pattern types are the foundation for intelligent automation suggestions. 
              Each type represents a different aspect of how you interact with your smart home devices. 
              The more patterns detected, the more personalized and accurate your automation suggestions will be.
            </p>
          </div>
        </motion.div>
      )}


      {/* Pattern List */}
      <div className="grid gap-4">
        {loading ? (
          <div className={`text-center py-12 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Loading patterns...
          </div>
        ) : patterns.length === 0 ? (
          <div className={`text-center py-12 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <div className="text-6xl mb-4">📊</div>
            <div className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              No patterns detected yet
            </div>
            <p className={`mt-2 mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Run an analysis to detect patterns in your smart home usage from the last 30 days
            </p>
            <div className="flex flex-col items-center gap-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleRunAnalysis}
                disabled={analysisRunning}
                className={`px-8 py-3 rounded-lg font-semibold text-lg transition-all ${
                  analysisRunning
                    ? 'bg-blue-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700'
                } text-white disabled:opacity-50 shadow-lg`}
              >
                {analysisRunning ? (
                  <span className="flex items-center gap-2">
                    <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing...
                  </span>
                ) : (
                  '🚀 Run Pattern Analysis'
                )}
              </motion.button>
              {analysisRunning && (
                <div className="mt-4 w-full max-w-md">
                  <div className={`h-2 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                    <motion.div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
                      initial={{ width: "0%" }}
                      animate={{ width: "100%" }}
                      transition={{ duration: 90, ease: "linear", repeat: Infinity }}
                    />
                  </div>
                  <p className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Processing 30 days of events... This may take 1-3 minutes.
                  </p>
                </div>
              )}
              <div className={`mt-6 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                <p className="font-semibold mb-2">Analysis will detect patterns including:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-left">
                  <div className="flex items-start gap-2">
                    <span>⏰</span>
                    <span><strong>Time-of-Day:</strong> When devices are consistently used</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>🔗</span>
                    <span><strong>Co-Occurrence:</strong> Devices used together</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>➡️</span>
                    <span><strong>Sequence:</strong> Multi-step behaviors</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>🌍</span>
                    <span><strong>Contextual:</strong> Weather/presence-aware patterns</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>🏠</span>
                    <span><strong>Room-Based:</strong> Room-specific interactions</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>👤</span>
                    <span><strong>Session:</strong> User routine patterns</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>⏱️</span>
                    <span><strong>Duration:</strong> How long devices stay active</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>📅</span>
                    <span><strong>Day-Type:</strong> Weekday vs weekend differences</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>🍂</span>
                    <span><strong>Seasonal:</strong> Seasonal behavior changes</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span>⚠️</span>
                    <span><strong>Anomaly:</strong> Unusual behaviors</span>
                  </div>
                </div>
                <p className="mt-4 text-xs italic">
                  Click "Pattern Type Guide" above to learn more about each pattern type and why they matter for automation.
                </p>
              </div>
            </div>
          </div>
        ) : (
          patterns.slice(0, 20).map((pattern, idx) => {
            const patternInfo = getPatternTypeInfo(pattern.pattern_type);
            return (
              <motion.div
                key={pattern.id}
                data-testid="pattern-item"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-5 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow hover:shadow-lg transition-shadow border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-4xl">{getPatternIcon(pattern.pattern_type)}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`font-semibold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`} data-testid="pattern-devices">
                          {deviceNames[pattern.device_id] || getFallbackName(pattern.device_id)}
                        </div>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          darkMode 
                            ? 'bg-blue-900/30 text-blue-300 border border-blue-700/50' 
                            : 'bg-blue-100 text-blue-800 border border-blue-200'
                        }`}>
                          {patternInfo.name}
                        </span>
                      </div>
                      <p className={`text-sm mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {patternInfo.description}
                      </p>
                      <div className="flex items-center gap-4 text-xs">
                        <span className={`${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                          📊 {pattern.occurrences} occurrence{pattern.occurrences !== 1 ? 's' : ''}
                        </span>
                        {deviceNames[pattern.device_id] && (
                          <span className={`${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                            🔑 ID: {pattern.device_id.substring(0, 8)}...
                          </span>
                        )}
                      </div>
                      <div className={`mt-2 p-2 rounded text-xs ${darkMode ? 'bg-purple-900/20 text-purple-200 border border-purple-700/30' : 'bg-purple-50 text-purple-800 border border-purple-200'}`}>
                        <p className="font-semibold mb-0.5">💡 Why this matters:</p>
                        <p>{patternInfo.importance}</p>
                      </div>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <div className={`text-2xl font-bold mb-1 ${
                      pattern.confidence >= 0.8 
                        ? darkMode ? 'text-green-400' : 'text-green-600'
                        : pattern.confidence >= 0.6
                        ? darkMode ? 'text-yellow-400' : 'text-yellow-600'
                        : darkMode ? 'text-orange-400' : 'text-orange-600'
                    }`}>
                      {Math.round(pattern.confidence * 100)}%
                    </div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                      confidence
                    </div>
                    <div className={`mt-2 w-20 h-2 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                      <div
                        className={`h-full ${
                          pattern.confidence >= 0.8 
                            ? 'bg-green-500'
                            : pattern.confidence >= 0.6
                            ? 'bg-yellow-500'
                            : 'bg-orange-500'
                        }`}
                        style={{ width: `${pattern.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
};

