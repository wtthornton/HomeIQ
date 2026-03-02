/**
 * Pattern Explorer Page
 * Visualize detected usage patterns
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import { PatternTypeChart, ConfidenceDistributionChart, TopDevicesChart } from '../components/PatternChart';
import { SkeletonCardGrid } from '../components/SkeletonCard';
import { SkeletonStats } from '../components/SkeletonStats';
import { ErrorBanner } from '../components/ErrorBanner';
import { PatternDetailsModal } from '../components/PatternDetailsModal';
import { exportPatternsToCSV, exportPatternsToJSON } from '../utils/exportUtils';
import {
  usePatternData,
  getPatternIcon,
  getPatternStatus,
  getPatternTypeInfo,
  formatLastRun,
} from '../hooks/usePatternData';

export const Patterns: React.FC = () => {
  const { darkMode } = useAppStore();
  const {
    patterns,
    stats,
    loading,
    deviceNames,
    analysisRunning,
    scheduleInfo,
    error,
    isDatabaseCorrupted,
    repairing,
    selectedPattern,
    setSelectedPattern,
    selectedPatternIds,
    setSelectedPatternIds,
    searchQuery,
    setSearchQuery,
    filterType,
    setFilterType,
    sortBy,
    setSortBy,
    loadPatterns,
    handleRepairDatabase,
    handleRunAnalysis,
    getFallbackName,
    filteredAndSortedPatterns,
    availablePatternTypes,
    setError,
    setIsDatabaseCorrupted,
  } = usePatternData();
  const [showPatternGuide, setShowPatternGuide] = useState(false);
  const [showStatsAndCharts, setShowStatsAndCharts] = useState(true);

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
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Detected Patterns
              </h2>
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
                    {['time_of_day', 'co_occurrence', 'multi_factor', 'sequence', 'contextual', 'room_based', 'session', 'duration', 'day_type', 'seasonal', 'anomaly'].map((type) => {
                      const info = getPatternTypeInfo(type);
                      const status = getPatternStatus(type);
                      return (
                        <div
                          key={type}
                          className={`p-4 rounded-lg border ${
                            darkMode 
                              ? status === 'active' 
                                ? 'bg-gray-800/30 border-green-700/50' 
                                : 'bg-gray-800/20 border-gray-700/50 opacity-75'
                              : status === 'active'
                                ? 'bg-white border-green-200'
                                : 'bg-gray-50 border-gray-200 opacity-75'
                          }`}
                        >
                          <div className="flex items-start gap-3 mb-2">
                            <span className="text-2xl">{getPatternIcon(type)}</span>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                  {info.name}
                                </h4>
                                {status === 'active' ? (
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    darkMode 
                                      ? 'bg-green-900/30 text-green-300 border border-green-700/50' 
                                      : 'bg-green-100 text-green-800 border border-green-200'
                                  }`}>
                                    ✓ Active
                                  </span>
                                ) : (
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    darkMode 
                                      ? 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/50' 
                                      : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                                  }`}>
                                    🔜 Coming Soon
                                  </span>
                                )}
                              </div>
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
        <div className="mb-6">
          <ErrorBanner 
            error={error} 
            onRetry={loadPatterns}
            onDismiss={() => {
              setError(null);
              setIsDatabaseCorrupted(false);
            }}
            variant="banner"
          />
          {isDatabaseCorrupted && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-4 rounded-xl border-l-4 bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 border-purple-500 shadow-lg"
            >
              <div className="flex items-start gap-4">
                <div className="text-2xl flex-shrink-0">🔧</div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold mb-1 text-purple-900 dark:text-purple-200">
                    Database Corruption Detected
                  </h3>
                  <p className="text-sm text-purple-800 dark:text-purple-300 mb-3">
                    The database appears to be corrupted. You can attempt to repair it automatically.
                  </p>
                  <button
                    onClick={handleRepairDatabase}
                    disabled={repairing}
                    className="px-4 py-2 rounded-lg text-sm font-medium transition-all bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {repairing ? '🔄 Repairing...' : '🔧 Repair Database'}
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </div>
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

                  {/* Stats Skeleton */}
                  {loading && (
                    <SkeletonStats statCount={4} showCharts={false} className="mt-6" />
                  )}

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


      {/* Phase 8: Pattern Filtering and Search */}
      {patterns.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800/50 border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg`}
        >
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search Input */}
            <div className="flex-1">
              <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                🔍 Search Patterns
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by device name or pattern type..."
                className={`w-full px-4 py-2 rounded-lg border ${
                  darkMode 
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                    : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              />
            </div>

            {/* Filter by Type */}
            <div className="md:w-48">
              <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                📊 Filter by Type
              </label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className={`w-full px-4 py-2 rounded-lg border ${
                  darkMode 
                    ? 'bg-gray-700 border-gray-600 text-white' 
                    : 'bg-white border-gray-300 text-gray-900'
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              >
                <option value="all">All Types</option>
                {availablePatternTypes.map(type => {
                  const info = getPatternTypeInfo(type);
                  return (
                    <option key={type} value={type}>
                      {info.name}
                    </option>
                  );
                })}
              </select>
            </div>

            {/* Sort By */}
            <div className="md:w-48">
              <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                🔄 Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'confidence' | 'occurrences' | 'recent')}
                className={`w-full px-4 py-2 rounded-lg border ${
                  darkMode 
                    ? 'bg-gray-700 border-gray-600 text-white' 
                    : 'bg-white border-gray-300 text-gray-900'
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              >
                <option value="confidence">Confidence (High → Low)</option>
                <option value="occurrences">Occurrences (Most → Least)</option>
                <option value="recent">Most Recent</option>
              </select>
            </div>
          </div>

          {/* Bulk Actions Toolbar */}
          {selectedPatternIds.size > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mt-3 p-4 rounded-xl ${darkMode ? 'bg-blue-900/20 border border-blue-700/30' : 'bg-blue-50 border border-blue-200'}`}
            >
              <div className="flex items-center justify-between">
                <div className={`text-sm font-medium ${darkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                  {selectedPatternIds.size} pattern{selectedPatternIds.size !== 1 ? 's' : ''} selected
                </div>
                <div className="flex gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      const selected = filteredAndSortedPatterns.filter(p => selectedPatternIds.has(p.id));
                      exportPatternsToCSV(selected, deviceNames);
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      darkMode
                        ? 'bg-blue-700 hover:bg-blue-600 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    }`}
                  >
                    📥 Export Selected
                  </motion.button>
                  <motion.button
                    disabled
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-not-allowed opacity-50 ${
                      darkMode
                        ? 'bg-red-700 text-white'
                        : 'bg-red-500 text-white'
                    }`}
                    title="Delete patterns (coming soon)"
                  >
                    🗑️ Delete Selected
                  </motion.button>
                  <button
                    onClick={() => setSelectedPatternIds(new Set())}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-white'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                  >
                    Clear Selection
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Results Count and Export */}
          <div className="mt-3 flex items-center justify-between">
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Showing {filteredAndSortedPatterns.length} of {patterns.length} pattern{patterns.length !== 1 ? 's' : ''}
              {(filterType !== 'all' || searchQuery.trim()) && (
                <button
                  onClick={() => {
                    setFilterType('all');
                    setSearchQuery('');
                  }}
                  className={`ml-2 underline hover:no-underline ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}
                >
                  Clear filters
                </button>
              )}
            </div>
            
            {/* Export Buttons */}
            {!loading && filteredAndSortedPatterns.length > 0 && (
              <div className="flex gap-2">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => exportPatternsToCSV(filteredAndSortedPatterns, deviceNames)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-white'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                  }`}
                  title="Export to CSV"
                >
                  📥 Export CSV
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => exportPatternsToJSON(filteredAndSortedPatterns, deviceNames)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-white'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                  }`}
                  title="Export to JSON"
                >
                  📥 Export JSON
                </motion.button>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Pattern List */}
      <div className="grid gap-4">
        {loading ? (
          <SkeletonCardGrid count={6} variant="pattern" />
        ) : patterns.length === 0 ? (
          <div className={`text-center py-12 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <div className="text-6xl mb-4">📊</div>
            <div className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              No patterns yet
            </div>
            <p className={`mt-2 mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              We need at least 30 days of events to detect usage patterns. Run an analysis to check your data.
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
        ) : filteredAndSortedPatterns.length === 0 ? (
          <div className={`text-center py-12 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
            <div className="text-6xl mb-4">🔍</div>
            <div className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              No patterns match your filters
            </div>
            <p className={`mt-2 mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Try adjusting your search query or filter settings
            </p>
            <button
              onClick={() => {
                setFilterType('all');
                setSearchQuery('');
              }}
              className={`px-6 py-2 rounded-lg font-medium ${
                darkMode 
                  ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              } transition-colors`}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          filteredAndSortedPatterns.slice(0, 50).map((pattern, idx) => {
            const patternInfo = getPatternTypeInfo(pattern.pattern_type);
            const status = getPatternStatus(pattern.pattern_type);
            const deviceName = deviceNames[pattern.device_id] || getFallbackName(pattern.device_id);
            
            // Phase 7: Enhanced pattern display with better metadata
            return (
              <motion.div
                key={pattern.id}
                data-testid="pattern-item"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-5 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow hover:shadow-lg transition-all border ${
                  selectedPatternIds.has(pattern.id)
                    ? darkMode ? 'border-blue-500 bg-blue-900/20' : 'border-blue-500 bg-blue-50'
                    : darkMode ? 'border-gray-700 hover:border-gray-600' : 'border-gray-200 hover:border-gray-300'
                } ${selectedPatternIds.has(pattern.id) ? '' : 'cursor-pointer'}`}
                onClick={(e) => {
                  // Don't open modal if clicking checkbox
                  const target = e.target as HTMLElement;
                  const isInput = target instanceof HTMLInputElement && target.type === 'checkbox';
                  if (!isInput && !target.closest('input[type="checkbox"]')) {
                    setSelectedPattern(pattern);
                  }
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Selection Checkbox */}
                  <div className="flex-shrink-0 pt-1">
                    <input
                      type="checkbox"
                      checked={selectedPatternIds.has(pattern.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        const newSet = new Set(selectedPatternIds);
                        if (e.target.checked) {
                          newSet.add(pattern.id);
                        } else {
                          newSet.delete(pattern.id);
                        }
                        setSelectedPatternIds(newSet);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="w-5 h-5 rounded cursor-pointer"
                    />
                  </div>
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-4xl flex-shrink-0">{getPatternIcon(pattern.pattern_type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <div className={`font-semibold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`} data-testid="pattern-devices">
                          {deviceName}
                        </div>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                          darkMode 
                            ? 'bg-blue-900/30 text-blue-300 border border-blue-700/50' 
                            : 'bg-blue-100 text-blue-800 border border-blue-200'
                        }`}>
                          {patternInfo.name}
                        </span>
                        {status === 'active' && (
                          <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                            darkMode 
                              ? 'bg-green-900/30 text-green-300 border border-green-700/50' 
                              : 'bg-green-100 text-green-800 border border-green-200'
                          }`}>
                            ✓ Active
                          </span>
                        )}
                      </div>
                      <p className={`text-sm mb-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {patternInfo.description}
                      </p>
                      
                      {/* Phase 7: Enhanced metadata display */}
                      <div className="flex items-center gap-4 text-xs mb-3 flex-wrap">
                        <span className={`flex items-center gap-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          <span>📊</span>
                          <span className="font-medium">{pattern.occurrences}</span>
                          <span>occurrence{pattern.occurrences !== 1 ? 's' : ''}</span>
                        </span>
                        {pattern.pattern_type === 'time_of_day' && pattern.pattern_metadata?.time && (
                          <span className={`flex items-center gap-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            <span>⏰</span>
                            <span>{pattern.pattern_metadata.time}</span>
                          </span>
                        )}
                        {pattern.pattern_type === 'co_occurrence' && pattern.device_id.includes('+') && (
                          <span className={`flex items-center gap-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            <span>🔗</span>
                            <span>Multi-device pattern</span>
                          </span>
                        )}
                        {deviceNames[pattern.device_id] && (
                          <span className={`flex items-center gap-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                            <span>🔑</span>
                            <span className="font-mono text-xs">{pattern.device_id.substring(0, 8)}...</span>
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
                    <div className={`text-xs mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      confidence
                    </div>
                    <div className={`w-24 h-2 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                      <div
                        className={`h-full transition-all ${
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

      {/* Pattern Details Modal */}
      <PatternDetailsModal
        pattern={selectedPattern}
        deviceName={selectedPattern ? (deviceNames[selectedPattern.device_id] || getFallbackName(selectedPattern.device_id)) : ''}
        onClose={() => setSelectedPattern(null)}
      />
    </div>
  );
};

