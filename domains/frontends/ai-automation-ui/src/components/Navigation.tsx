/**
 * Navigation Component - Industrial Design System
 * Clean, icon-free navigation with subtle styling
 */

import React, { memo, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../store';

// PERFORMANCE: Memoize Navigation component
export const Navigation: React.FC = memo(() => {
  const { darkMode, toggleDarkMode } = useAppStore();
  const location = useLocation();

  // PERFORMANCE: Memoize nav items to prevent recreation on every render
  const navItems = useMemo(() => [
    { path: '/blueprint-suggestions', label: 'Blueprint Suggestions', shortLabel: 'Blueprints', ariaLabel: 'Navigate to Blueprint Suggestions' },
    { path: '/', label: 'Suggestions', shortLabel: 'Suggest', ariaLabel: 'Navigate to Suggestions' },
    { path: '/proactive', label: 'Proactive', shortLabel: 'Proactive', ariaLabel: 'Navigate to Proactive Suggestions' },
    { path: '/ha-agent', label: 'Agent', shortLabel: 'Agent', ariaLabel: 'Navigate to HA Agent' },
    { path: '/patterns', label: 'Patterns', shortLabel: 'Patterns', ariaLabel: 'Navigate to Patterns' },
    { path: '/synergies', label: 'Synergies', shortLabel: 'Synergy', ariaLabel: 'Navigate to Synergies' },
    { path: '/deployed', label: 'Deployed', shortLabel: 'Deployed', ariaLabel: 'Navigate to Deployed Automations' },
    { path: '/discovery', label: 'Discovery', shortLabel: 'Discover', ariaLabel: 'Navigate to Discovery' },
    { path: '/name-enhancement', label: 'Names', shortLabel: 'Names', ariaLabel: 'Navigate to Name Enhancement' },
    { path: '/settings', label: 'Settings', shortLabel: 'Settings', ariaLabel: 'Navigate to Settings' },
    { path: '/admin', label: 'Admin', shortLabel: 'Admin', ariaLabel: 'Navigate to Admin' },
  ], []);

  // PERFORMANCE: Memoize active path
  const activePath = useMemo(() => location.pathname, [location.pathname]);
  
  const isActive = (path: string) => {
    return activePath === path;
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--card-border)] bg-[var(--bg-secondary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-10">
          {/* Logo - Simple text */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-sm font-bold text-[var(--text-primary)]">
              HA AutomateAI
            </span>
          </Link>

          {/* Nav Links - Desktop */}
          <div className="hidden md:flex items-center gap-0.5">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-2.5 py-1 text-xs font-medium transition-colors duration-150 rounded ${
                  isActive(item.path)
                    ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)]'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)]'
                }`}
                aria-label={item.ariaLabel}
                aria-current={isActive(item.path) ? 'page' : undefined}
              >
                {item.label}
              </Link>
            ))}

            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-1.5 rounded ml-2 min-w-[28px] min-h-[28px] flex items-center justify-center text-xs transition-colors duration-150 bg-[var(--hover-bg)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
              aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-pressed={darkMode}
              type="button"
            >
              {darkMode ? '☀' : '☾'}
            </button>
          </div>

          {/* Mobile Menu */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className="p-1.5 rounded min-w-[28px] min-h-[28px] flex items-center justify-center text-xs bg-[var(--hover-bg)] text-[var(--text-secondary)]"
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀' : '☾'}
            </button>
          </div>
        </div>

        {/* Mobile Nav - Horizontal scroll */}
        <div className="md:hidden flex gap-1 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex-shrink-0 px-2.5 py-1 text-xs font-medium rounded transition-colors duration-150 ${
                isActive(item.path)
                  ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)]'
                  : 'text-[var(--text-tertiary)] hover:bg-[var(--hover-bg)]'
              }`}
              aria-label={item.ariaLabel}
              aria-current={isActive(item.path) ? 'page' : undefined}
            >
              {item.shortLabel}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
});

Navigation.displayName = 'Navigation';
