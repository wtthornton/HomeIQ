/**
 * Sidebar Navigation Component (FR-2.1)
 * Replaces top-nav Navigation with collapsible left rail sidebar.
 * Mobile: fixed bottom tab bar with 5 items.
 */

import React, { memo, useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../store';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  ariaLabel: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Create',
    items: [
      { path: '/', label: 'Ideas', icon: '\u{1F4A1}', ariaLabel: 'Navigate to Ideas' },
      { path: '/chat', label: 'Chat', icon: '\u{1F4AC}', ariaLabel: 'Navigate to Chat' },
      { path: '/explore', label: 'Explore', icon: '\u{1F52D}', ariaLabel: 'Navigate to Explore' },
    ],
  },
  {
    title: 'Manage',
    items: [
      { path: '/insights', label: 'Insights', icon: '\u{1F4CA}', ariaLabel: 'Navigate to Insights' },
      { path: '/automations', label: 'Automations', icon: '\u{26A1}', ariaLabel: 'Navigate to Automations' },
    ],
  },
  {
    title: 'Configure',
    items: [
      { path: '/settings', label: 'Settings', icon: '\u{2699}\u{FE0F}', ariaLabel: 'Navigate to Settings' },
    ],
  },
];

const MOBILE_TABS: NavItem[] = [
  { path: '/', label: 'Ideas', icon: '\u{1F4A1}', ariaLabel: 'Navigate to Ideas' },
  { path: '/chat', label: 'Chat', icon: '\u{1F4AC}', ariaLabel: 'Navigate to Chat' },
  { path: '/explore', label: 'Explore', icon: '\u{1F50D}', ariaLabel: 'Navigate to Explore' },
  { path: '/insights', label: 'Insights', icon: '\u{1F4CA}', ariaLabel: 'Navigate to Insights' },
  { path: '/automations', label: 'Automations', icon: '\u{26A1}', ariaLabel: 'Navigate to Automations' },
];

const STORAGE_KEY = 'sidebar-collapsed';

export const Sidebar: React.FC = memo(() => {
  const { darkMode, toggleDarkMode } = useAppStore();
  const location = useLocation();
  const navRef = useRef<HTMLElement>(null);

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === 'true';
    } catch {
      return false;
    }
  });

  // Persist collapsed state
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(collapsed));
    } catch {
      // localStorage unavailable
    }
  }, [collapsed]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => !prev);
  }, []);

  const activePath = useMemo(() => location.pathname, [location.pathname]);

  const isActive = useCallback(
    (path: string) => {
      if (path === '/') return activePath === '/';
      return activePath.startsWith(path);
    },
    [activePath],
  );

  // Keyboard navigation within sidebar
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const nav = navRef.current;
      if (!nav) return;
      const links = Array.from(nav.querySelectorAll<HTMLAnchorElement>('a[data-nav-item]'));
      const currentIndex = links.findIndex((el) => el === document.activeElement);

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          const next = currentIndex < links.length - 1 ? currentIndex + 1 : 0;
          links[next]?.focus();
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          const prev = currentIndex > 0 ? currentIndex - 1 : links.length - 1;
          links[prev]?.focus();
          break;
        }
        case 'Escape':
          if (!collapsed) setCollapsed(true);
          break;
      }
    },
    [collapsed],
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <nav
        ref={navRef}
        role="navigation"
        aria-label="Main navigation"
        onKeyDown={handleKeyDown}
        className={`hidden md:flex flex-col flex-shrink-0 h-screen sticky top-0 border-r border-[var(--card-border)] bg-[var(--bg-secondary)] transition-[width] duration-200 ${
          collapsed ? 'w-16' : 'w-52'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between h-14 px-3 border-b border-[var(--card-border)]">
          {!collapsed && (
            <span className="text-sm font-bold text-[var(--text-primary)] truncate">
              HomeIQ
            </span>
          )}
          <button
            onClick={toggleCollapsed}
            className="p-1.5 rounded text-xs transition-colors bg-[var(--hover-bg)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            type="button"
          >
            {collapsed ? '\u{25B6}' : '\u{25C0}'}
          </button>
        </div>

        {/* Cross-app switcher */}
        {!collapsed && (
          <div className="px-3 py-2 border-b border-[var(--card-border)]">
            <div className="flex gap-1">
              <span className="px-2 py-1 text-xs font-medium rounded bg-[var(--accent-primary)] text-[var(--bg-primary)]">
                HomeIQ
              </span>
              <a
                href={import.meta.env.VITE_HEALTH_DASHBOARD_URL || 'http://localhost:3000'}
                className="px-2 py-1 text-xs font-medium rounded text-[var(--text-tertiary)] hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] transition-colors"
              >
                Health
              </a>
              <a
                href={import.meta.env.VITE_OBSERVABILITY_URL || 'http://localhost:8501'}
                className="px-2 py-1 text-xs font-medium rounded text-[var(--text-tertiary)] hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] transition-colors"
              >
                Ops
              </a>
            </div>
          </div>
        )}

        {/* Nav sections */}
        <div className="flex-1 overflow-y-auto py-2">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-3">
              {!collapsed && (
                <div className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  data-nav-item
                  className={`flex items-center gap-2 mx-2 px-2 py-2 text-sm rounded transition-colors duration-150 ${
                    isActive(item.path)
                      ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)]'
                      : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)]'
                  } ${collapsed ? 'justify-center' : ''}`}
                  aria-label={item.ariaLabel}
                  aria-current={isActive(item.path) ? 'page' : undefined}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="text-base flex-shrink-0">{item.icon}</span>
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              ))}
            </div>
          ))}
        </div>

        {/* Dark mode toggle at bottom */}
        <div className="border-t border-[var(--card-border)] p-3">
          <button
            onClick={toggleDarkMode}
            className={`flex items-center gap-2 w-full p-2 rounded text-sm transition-colors bg-[var(--hover-bg)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] ${
              collapsed ? 'justify-center' : ''
            }`}
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-pressed={darkMode}
            type="button"
          >
            <span className="text-base">{darkMode ? '\u{2600}' : '\u{263E}'}</span>
            {!collapsed && <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>
        </div>
      </nav>

      {/* Mobile Bottom Tab Bar */}
      <nav
        role="navigation"
        aria-label="Mobile navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-[var(--card-border)] bg-[var(--bg-secondary)]"
      >
        <div className="flex justify-around items-center h-14">
          {MOBILE_TABS.map((tab) => (
            <Link
              key={tab.path}
              to={tab.path}
              className={`flex flex-col items-center justify-center flex-1 h-full text-xs transition-colors ${
                isActive(tab.path)
                  ? 'text-[var(--accent-primary)]'
                  : 'text-[var(--text-tertiary)]'
              }`}
              aria-label={tab.ariaLabel}
              aria-current={isActive(tab.path) ? 'page' : undefined}
            >
              <span className="text-lg">{tab.icon}</span>
              <span className="mt-0.5">{tab.label}</span>
              {isActive(tab.path) && (
                <div className="absolute bottom-0 w-8 h-0.5 bg-[var(--accent-primary)] rounded-t" />
              )}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
});

Sidebar.displayName = 'Sidebar';
