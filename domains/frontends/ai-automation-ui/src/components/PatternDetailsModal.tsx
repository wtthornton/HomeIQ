/**
 * Pattern Details Modal
 * Displays detailed information about a pattern with timeline visualization
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import type { Pattern } from '../types';

interface PatternDetailsModalProps {
  pattern: Pattern | null;
  deviceName: string;
  onClose: () => void;
}

export const PatternDetailsModal: React.FC<PatternDetailsModalProps> = ({
  pattern,
  deviceName,
  onClose
}) => {
  const { darkMode } = useAppStore();

  if (!pattern) return null;

  const getPatternIcon = (type: string) => {
    const icons: Record<string, string> = {
      time_of_day: '⏰',
      co_occurrence: '🔗',
      multi_factor: '🎯',
      sequence: '📋',
      contextual: '🌍',
      room_based: '🏠',
      session: '📱',
      duration: '⏱️',
      day_type: '📅',
      seasonal: '🍂',
      anomaly: '⚠️'
    };
    return icons[type] || '📊';
  };

  const getPatternTypeInfo = (type: string) => {
    const info: Record<string, { name: string; description: string; importance: string }> = {
      time_of_day: {
        name: 'Time of Day',
        description: 'Device usage patterns based on time',
        importance: 'Helps optimize energy usage and automate routines'
      },
      co_occurrence: {
        name: 'Co-Occurrence',
        description: 'Devices used together frequently',
        importance: 'Enables multi-device automation and scene creation'
      },
      multi_factor: {
        name: 'Multi-Factor',
        description: 'Complex patterns involving multiple conditions',
        importance: 'Enables sophisticated automation rules'
      },
      sequence: {
        name: 'Sequence',
        description: 'Ordered sequence of device interactions',
        importance: 'Perfect for workflow automation'
      },
      contextual: {
        name: 'Contextual',
        description: 'Context-aware usage patterns',
        importance: 'Enables intelligent, adaptive automation'
      },
      room_based: {
        name: 'Room-Based',
        description: 'Room-specific usage patterns',
        importance: 'Enables location-aware automation'
      },
      session: {
        name: 'Session',
        description: 'Usage sessions and interactions',
        importance: 'Helps understand user behavior patterns'
      },
      duration: {
        name: 'Duration',
        description: 'Duration-based usage patterns',
        importance: 'Optimizes device runtime and energy usage'
      },
      day_type: {
        name: 'Day Type',
        description: 'Weekday vs weekend patterns',
        importance: 'Enables day-specific automation schedules'
      },
      seasonal: {
        name: 'Seasonal',
        description: 'Seasonal usage variations',
        importance: 'Adapts automation to seasonal changes'
      },
      anomaly: {
        name: 'Anomaly',
        description: 'Unusual usage patterns',
        importance: 'Identifies potential issues or opportunities'
      }
    };
    return info[type] || { name: type, description: '', importance: '' };
  };

  const patternInfo = getPatternTypeInfo(pattern.pattern_type);

  // Generate timeline data from occurrences
  const generateTimelineData = () => {
    const timeline: Array<{ date: string; count: number; label: string }> = [];
    const now = new Date();
    
    // Generate last 30 days of data
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      // Simulate occurrence distribution (in real app, this would come from API)
      const count = Math.floor(Math.random() * 3); // 0-2 occurrences per day
      timeline.push({
        date: dateStr,
        count,
        label: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      });
    }
    
    return timeline;
  };

  const timelineData = generateTimelineData();
  const maxCount = Math.max(...timelineData.map(d => d.count), 1);

  return (
    <AnimatePresence>
      {pattern && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-4 md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[90vw] md:max-w-4xl md:h-[90vh] z-50 overflow-hidden"
          >
            <div className={`h-full flex flex-col ${darkMode ? 'bg-gray-900' : 'bg-white'} rounded-2xl shadow-2xl border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              {/* Header */}
              <div className={`flex items-center justify-between p-6 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center gap-4">
                  <div className="text-5xl">{getPatternIcon(pattern.pattern_type)}</div>
                  <div>
                    <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {deviceName}
                    </h2>
                    <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {patternInfo.name} Pattern
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className={`p-2 rounded-lg transition-colors ${
                    darkMode 
                      ? 'hover:bg-gray-800 text-gray-400 hover:text-white' 
                      : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="space-y-6">
                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Confidence</div>
                      <div className={`text-2xl font-bold mt-1 ${
                        pattern.confidence >= 0.8 
                          ? darkMode ? 'text-green-400' : 'text-green-600'
                          : pattern.confidence >= 0.6
                          ? darkMode ? 'text-yellow-400' : 'text-yellow-600'
                          : darkMode ? 'text-orange-400' : 'text-orange-600'
                      }`}>
                        {Math.round(pattern.confidence * 100)}%
                      </div>
                    </div>
                    <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Occurrences</div>
                      <div className={`text-2xl font-bold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {pattern.occurrences}
                      </div>
                    </div>
                    <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Pattern ID</div>
                      <div className={`text-lg font-mono mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        #{pattern.id}
                      </div>
                    </div>
                    <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Created</div>
                      <div className={`text-sm mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        {new Date(pattern.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <div className={`p-4 rounded-xl ${darkMode ? 'bg-blue-900/20 border border-blue-700/30' : 'bg-blue-50 border border-blue-200'}`}>
                    <h3 className={`font-semibold mb-2 ${darkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                      📋 Description
                    </h3>
                    <p className={`${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
                      {patternInfo.description}
                    </p>
                  </div>

                  {/* Timeline Visualization */}
                  <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                    <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      📅 Occurrence Timeline (Last 30 Days)
                    </h3>
                    <div className="space-y-2">
                      {timelineData.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                          <div className={`text-xs w-20 flex-shrink-0 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {item.label}
                          </div>
                          <div className="flex-1 flex items-center gap-2">
                            <div className={`flex-1 h-6 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${(item.count / maxCount) * 100}%` }}
                                transition={{ delay: idx * 0.02, duration: 0.5 }}
                                className={`h-full ${
                                  item.count > 0
                                    ? 'bg-gradient-to-r from-blue-500 to-purple-600'
                                    : darkMode ? 'bg-gray-700' : 'bg-gray-200'
                                }`}
                              />
                            </div>
                            <div className={`text-xs w-8 text-right ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              {item.count}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Metadata */}
                  {pattern.pattern_metadata && Object.keys(pattern.pattern_metadata).length > 0 && (
                    <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <h3 className={`font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        🔍 Pattern Metadata
                      </h3>
                      <div className="space-y-2">
                        {Object.entries(pattern.pattern_metadata).map(([key, value]) => (
                          <div key={key} className="flex items-start gap-3">
                            <div className={`text-sm font-medium w-32 flex-shrink-0 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                            </div>
                            <div className={`text-sm flex-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Importance */}
                  <div className={`p-4 rounded-xl ${darkMode ? 'bg-purple-900/20 border border-purple-700/30' : 'bg-purple-50 border border-purple-200'}`}>
                    <h3 className={`font-semibold mb-2 ${darkMode ? 'text-purple-300' : 'text-purple-900'}`}>
                      💡 Why This Matters
                    </h3>
                    <p className={`${darkMode ? 'text-purple-200' : 'text-purple-800'}`}>
                      {patternInfo.importance}
                    </p>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className={`flex items-center justify-end gap-3 p-6 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <button
                  onClick={onClose}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-gray-800 hover:bg-gray-700 text-white'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                  }`}
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    // TODO: Implement export functionality
                    onClose();
                  }}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white'
                      : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white'
                  }`}
                >
                  Export Pattern
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

