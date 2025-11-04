/**
 * Admin Page
 * 
 * System administration and management interface.
 * Matches the styling of the suggestions page.
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../store';

export const Admin: React.FC = () => {
  const { darkMode } = useAppStore();
  
  const [stats] = useState({
    totalSuggestions: 0,
    activeAutomations: 0,
    systemHealth: 'healthy',
    apiStatus: 'online'
  });

  useEffect(() => {
    // Component mounted
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'} pb-4`}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🔧 Admin Dashboard
            </h1>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              System administration and management
            </p>
          </div>
          <div className="text-sm text-gray-500">
            System Status: {stats.systemHealth}
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-blue-900/30 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">🔧</span>
          <div className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-900'}`}>
            <strong>Admin Access:</strong> Manage system settings, view statistics, and monitor system health.
            Access to advanced features and configuration options.
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Suggestions', value: stats.totalSuggestions, icon: '💡', color: 'blue' },
          { label: 'Active Automations', value: stats.activeAutomations, icon: '🚀', color: 'green' },
          { label: 'System Health', value: stats.systemHealth, icon: '💚', color: 'green' },
          { label: 'API Status', value: stats.apiStatus, icon: '🔌', color: 'blue' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`rounded-lg p-4 border ${
              darkMode 
                ? 'bg-gray-800 border-gray-700' 
                : 'bg-white border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{stat.icon}</span>
              <span className={`text-xs px-2 py-1 rounded ${
                stat.color === 'blue'
                  ? darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-800'
                  : darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-800'
              }`}>
                {stat.value}
              </span>
            </div>
            <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {stat.label}
            </h3>
          </motion.div>
        ))}
      </div>

      {/* Admin Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`rounded-lg p-6 border ${
            darkMode 
              ? 'bg-gray-800 border-gray-700' 
              : 'bg-white border-gray-200'
          }`}
        >
          <h2 className={`text-lg font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            ⚙️ System Settings
          </h2>
          <div className="space-y-3">
            {[
              'API Configuration',
              'Database Settings',
              'Security Settings',
              'Logging Configuration'
            ].map((setting) => (
              <button
                key={setting}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  darkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {setting}
              </button>
            ))}
          </div>
        </motion.div>

        {/* System Monitoring */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`rounded-lg p-6 border ${
            darkMode 
              ? 'bg-gray-800 border-gray-700' 
              : 'bg-white border-gray-200'
          }`}
        >
          <h2 className={`text-lg font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 System Monitoring
          </h2>
          <div className="space-y-3">
            {[
              'Service Health',
              'Performance Metrics',
              'Error Logs',
              'Activity Logs'
            ].map((monitor) => (
              <button
                key={monitor}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  darkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {monitor}
              </button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Footer Info */}
      <div className={`rounded-lg p-6 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'} border`}>
        <div className={`text-sm space-y-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <p>
            <strong>🔧 Admin Functions:</strong> This page provides access to system administration features.
          </p>
          <p>
            <strong>📊 Monitoring:</strong> View system health, performance metrics, and activity logs.
          </p>
          <p>
            <strong>⚙️ Configuration:</strong> Manage system settings, API keys, and security options.
          </p>
          <p className="text-xs opacity-70">
            💡 For detailed system monitoring, visit the health dashboard at http://localhost:3000
          </p>
        </div>
      </div>
    </div>
  );
};

