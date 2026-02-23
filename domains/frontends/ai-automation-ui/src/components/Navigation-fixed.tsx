/**
 * Navigation Component - Fixed Version
 * Without framer-motion dependency
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../store';

export const Navigation: React.FC = () => {
  const { darkMode, toggleDarkMode } = useAppStore();
  const location = useLocation();

  const navItems = [
    { path: '/', label: '🤖 Suggestions', icon: '🤖' },
    { path: '/patterns', label: '📊 Patterns', icon: '📊' },
    { path: '/deployed', label: '🚀 Deployed', icon: '🚀' },
    { path: '/settings', label: '⚙️ Settings', icon: '⚙️' },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className={`sticky top-0 z-50 ${darkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'} border-b shadow-sm transition-colors`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3">
            <div className="text-3xl">🤖</div>
            <div>
              <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                HA AutomateAI
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Smart Home Intelligence
              </div>
            </div>
          </Link>

          {/* Nav Links - Desktop */}
          <div className="hidden md:flex items-center gap-2">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  isActive(item.path)
                    ? darkMode
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-500 text-white'
                    : darkMode
                    ? 'text-gray-300 hover:bg-gray-800'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </Link>
            ))}

            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg ml-2 ${
                darkMode
                  ? 'bg-gray-800 hover:bg-gray-700'
                  : 'bg-gray-100 hover:bg-gray-200'
              }`}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>

            {/* Link to Admin Dashboard */}
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noopener noreferrer"
              className={`ml-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🔧 Admin
            </a>
          </div>

          {/* Mobile Menu */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg ${
                darkMode ? 'bg-gray-800' : 'bg-gray-100'
              }`}
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
              className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg ${
                isActive(item.path)
                  ? darkMode
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-500 text-white'
                  : darkMode
                  ? 'text-gray-400'
                  : 'text-gray-600'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-xs font-medium">
                {item.label.replace(/[\u{1F916}\u{1F4CA}\u{1F680}\u{2699}]/gu, '').trim()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};
