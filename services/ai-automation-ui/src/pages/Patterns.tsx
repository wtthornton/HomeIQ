/**
 * Pattern Explorer Page
 * Visualize detected usage patterns
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
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

  const loadPatterns = useCallback(async () => {
    try {
      setError(null);
      const [patternsRes, statsRes] = await Promise.all([
        api.getPatterns(undefined, 0.7),
        api.getPatternStats()
      ]);
      const patternsData = patternsRes.data.patterns || [];
      setPatterns(patternsData);
      setStats(statsRes.data || statsRes);

      // Load device names for the patterns
      if (patternsData.length > 0) {
        const uniqueDeviceIds = [...new Set(patternsData.map(p => p.device_id))];
        const names = await api.getDeviceNames(uniqueDeviceIds);
        setDeviceNames(names);
      }
    } catch (err: any) {
      console.error('Failed to load patterns:', err);
      setError(err.message || 'Failed to load patterns');
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
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-start"
      >
        <div>
          <h1 className={`text-3xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 Detected Patterns
          </h1>
          <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
            Usage patterns detected by machine learning analysis
          </p>
          {scheduleInfo && (
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
              Last analysis: {formatLastRun(scheduleInfo.last_run_time || scheduleInfo.last_run)} • 
              {' '}Next scheduled: {scheduleInfo.next_run_time || '3:00 AM daily'}
            </p>
          )}
        </div>
        <div className="flex gap-2">
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
        </div>
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

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
      )}

      {/* Charts */}
      {!loading && patterns.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <PatternTypeChart patterns={patterns} darkMode={darkMode} />
          </div>
          <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <ConfidenceDistributionChart patterns={patterns} darkMode={darkMode} />
          </div>
          <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg lg:col-span-2`}>
            <TopDevicesChart patterns={patterns} darkMode={darkMode} />
          </div>
        </div>
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
              <div className={`mt-6 text-sm ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                <p>Analysis will detect:</p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Time-of-day patterns (when devices are typically used)</li>
                  <li>Co-occurrence patterns (devices used together)</li>
                  <li>Sequence patterns (multi-step behaviors)</li>
                  <li>Session patterns (user routines)</li>
                  <li>Anomaly patterns (unusual behaviors)</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          patterns.slice(0, 20).map((pattern, idx) => (
            <motion.div
              key={pattern.id}
              data-testid="pattern-item"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow hover:shadow-lg transition-shadow`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="text-3xl">{getPatternIcon(pattern.pattern_type)}</div>
                  <div>
                    <div className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`} data-testid="pattern-devices">
                      {deviceNames[pattern.device_id] || getFallbackName(pattern.device_id)}
                    </div>
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {pattern.pattern_type.replace('_', ' ')} • {pattern.occurrences} occurrences
                    </div>
                    {deviceNames[pattern.device_id] && (
                      <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                        ID: {pattern.device_id}
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-right">
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {Math.round(pattern.confidence * 100)}%
                  </div>
                  <div className="text-xs text-gray-500">confidence</div>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};

