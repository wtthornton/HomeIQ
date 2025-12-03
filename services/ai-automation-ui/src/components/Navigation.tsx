/**
 * Navigation Component - Fixed Version
 * Without framer-motion dependency
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAppStore } from '../store';

export const Navigation: React.FC = () => {
  const { darkMode, toggleDarkMode } = useAppStore();
  const location = useLocation();

  const navItems = [
    { path: '/', label: '🤖 Suggestions', icon: '🤖' },
    { path: '/ask-ai', label: '💬 Ask AI', icon: '💬' },
    { path: '/patterns', label: '📊 Patterns', icon: '📊' },
    { path: '/synergies', label: '🔮 Synergies', icon: '🔮' },  // Epic AI-3, Story AI3.8
    { path: '/deployed', label: '🚀 Deployed', icon: '🚀' },
    { path: '/discovery', label: '🔍 Discovery', icon: '🔍' },  // Epic AI-4, Story AI4.3
    { path: '/name-enhancement', label: '✏️ Names', icon: '✏️' },  // Device Name Enhancement
    { path: '/settings', label: '⚙️ Settings', icon: '⚙️' },
    { path: '/admin', label: '🔧 Admin', icon: '🔧' },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="sticky top-0 z-50 border-b shadow-sm transition-colors" style={{
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
      borderColor: 'rgba(51, 65, 85, 0.5)',
      backdropFilter: 'blur(12px)'
    }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-1.5">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
              className="text-lg"
            >
              🤖
            </motion.div>
            <div className="ds-title-card text-xs" style={{ color: '#ffffff' }}>
              HA AUTOMATEAI
            </div>
          </Link>

          {/* Nav Links - Desktop */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3 py-0.5 text-xs font-medium transition-all rounded-xl ${
                  isActive(item.path)
                    ? darkMode
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                    : darkMode
                    ? 'text-gray-300 hover:bg-gray-700/50'
                    : 'text-gray-700 hover:bg-gray-100/50'
                }`}
                style={{
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}
              >
                {item.label}
              </Link>
            ))}

            {/* Dark Mode Toggle - 44x44px minimum touch target */}
              <button
              onClick={toggleDarkMode}
              className="p-1 rounded-xl ml-2 min-w-[28px] min-h-[28px] flex items-center justify-center text-sm transition-all hover:scale-105 active:scale-95"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)'
              }}
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>

          </div>

          {/* Mobile Menu */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className={`p-1 rounded-xl min-w-[28px] min-h-[28px] flex items-center justify-center text-sm transition-all hover:scale-105 active:scale-95 ${
                darkMode ? 'bg-gray-800/60 backdrop-blur-sm border border-gray-700/50' : 'bg-white/80 backdrop-blur-sm border border-gray-200/50'
              }`}
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>

        {/* Mobile Nav - Bottom */}
        <div className="md:hidden flex justify-around pb-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all ${
                isActive(item.path)
                  ? darkMode
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-400/30'
                  : darkMode
                  ? 'text-gray-400 hover:bg-gray-700/50'
                  : 'text-gray-600 hover:bg-gray-100/50'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-[10px] font-medium uppercase" style={{ letterSpacing: '0.05em' }}>
                {item.label.replace(/[\u{1F916}\u{1F4AC}\u{1F4CA}\u{1F52E}\u{1F680}\u{1F50D}\u{2699}\u{1F527}]/gu, '').trim()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};
