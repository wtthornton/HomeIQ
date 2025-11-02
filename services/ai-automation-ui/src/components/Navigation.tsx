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
    { path: '/settings', label: '⚙️ Settings', icon: '⚙️' },
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
        <div className="flex justify-between items-center h-12">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
              className="text-xl"
            >
              🤖
            </motion.div>
            <div className="ds-title-card text-sm" style={{ color: '#ffffff' }}>
              HA AUTOMATEAI
            </div>
          </Link>

          {/* Nav Links - Desktop */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className="px-3 py-1 text-sm font-medium transition-colors"
                style={{
                  background: isActive(item.path) ? 'linear-gradient(to right, #3b82f6, #2563eb)' : 'transparent',
                  color: isActive(item.path) ? '#ffffff' : '#cbd5e1',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  borderRadius: '0.375rem'
                }}
                onMouseEnter={(e) => {
                  if (!isActive(item.path)) {
                    e.currentTarget.style.background = 'rgba(51, 65, 85, 0.3)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive(item.path)) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                {item.label}
              </Link>
            ))}

            {/* Dark Mode Toggle - 44x44px minimum touch target */}
            <button
              onClick={toggleDarkMode}
              className="p-3 rounded-lg ml-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
              }}
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>

            {/* Link to Admin Dashboard */}
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 px-4 py-2 rounded-lg font-medium transition-colors"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
              }}
            >
              🔧 ADMIN
            </a>
          </div>

          {/* Mobile Menu */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className={`p-3 rounded-lg min-w-[44px] min-h-[44px] flex items-center justify-center ${
                darkMode ? 'bg-gray-800' : 'bg-gray-100'
              }`}
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>

        {/* Mobile Nav - Bottom */}
        <div className="md:hidden flex justify-around pb-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className="flex flex-col items-center gap-1 px-3 py-2 rounded-lg"
              style={{
                background: isActive(item.path) ? 'linear-gradient(to right, #3b82f6, #2563eb)' : 'transparent',
                color: isActive(item.path) ? '#ffffff' : '#94a3b8'
              }}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-xs font-medium uppercase" style={{ letterSpacing: '0.05em' }}>
                {item.label.replace(/[🤖💬📊🔮🚀🔍⚙️]/g, '').trim()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};
