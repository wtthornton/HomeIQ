/**
 * Main App Component
 * Routes and layout for AI Automation UI
 */

import React, { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { CustomToaster } from './components/CustomToast';
import { SelectionProvider } from './context/SelectionContext';
import { Sidebar } from './components/Sidebar';
import { PageErrorBoundaryWrapper } from './components/PageErrorBoundary';
import { useAppStore } from './store';

const LazyIdeas = lazy(() => import('./pages/Ideas').then(m => ({ default: m.Ideas })));
const LazyInsights = lazy(() => import('./pages/Insights').then(m => ({ default: m.Insights })));
const LazyDeployed = lazy(() => import('./pages/Deployed').then(m => ({ default: m.Deployed })));
const LazySettings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const LazyDiscovery = lazy(() => import('./pages/Discovery').then(m => ({ default: m.DiscoveryPage })));
const LazyNameEnhancement = lazy(() => import('./components/name-enhancement').then(m => ({ default: m.NameEnhancementDashboard })));
const LazyHAAgentChat = lazy(() => import('./pages/HAAgentChat').then(m => ({ default: m.HAAgentChat })));
const LazyScheduledTasks = lazy(() => import('./components/ScheduledTasks').then(m => ({ default: m.ScheduledTasks })));

const PageLoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-6 py-4">
    <div className="h-8 w-48 rounded bg-[var(--bg-tertiary)]" />
    <div className="space-y-3">
      <div className="h-4 w-full rounded bg-[var(--bg-tertiary)]" />
      <div className="h-4 w-3/4 rounded bg-[var(--bg-tertiary)]" />
      <div className="h-4 w-1/2 rounded bg-[var(--bg-tertiary)]" />
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-32 rounded-lg bg-[var(--bg-tertiary)]" />
      ))}
    </div>
  </div>
);

/** Update document title based on current route */
const TitleUpdater: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    const titles: Record<string, string> = {
      '/': 'Ideas - HomeIQ',
      '/chat': 'Chat - HomeIQ',
      '/explore': 'Explore - HomeIQ',
      '/insights': 'Insights - HomeIQ',
      '/automations': 'Automations - HomeIQ',
      '/scheduled': 'Scheduled Tasks - HomeIQ',
      '/settings': 'Settings - HomeIQ',
      '/name-enhancement': 'Name Enhancement - HomeIQ',
    };
    document.title = titles[location.pathname] || 'HomeIQ';
  }, [location.pathname]);

  return null;
};

export const App: React.FC = () => {
  const { darkMode, initializeDarkMode } = useAppStore();

  // Initialize dark mode on mount
  useEffect(() => {
    initializeDarkMode();
  }, [initializeDarkMode]);

  // Apply dark mode class to document
  useEffect(() => {
    // SECURITY: Only manipulate DOM in browser environment
    if (typeof document !== 'undefined') {
      if (darkMode) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
    }
  }, [darkMode]);

  return (
    <SelectionProvider>
      <Router>
        <TitleUpdater />
        <a href="#main-content" className="skip-to-content">
          Skip to main content
        </a>
        <div className="flex min-h-screen transition-colors ds-bg-gradient-primary">
          <Sidebar />

          <div className="flex-1 flex flex-col min-w-0">
            <main id="main-content" className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <Suspense fallback={<PageLoadingSkeleton />}>
                <Routes>
                  {/* Primary routes */}
                  <Route
                    path="/"
                    element={
                      <PageErrorBoundaryWrapper pageName="Ideas">
                        <LazyIdeas />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/chat"
                    element={
                      <PageErrorBoundaryWrapper pageName="Chat">
                        <LazyHAAgentChat />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/explore"
                    element={
                      <PageErrorBoundaryWrapper pageName="Explore">
                        <LazyDiscovery />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/insights"
                    element={
                      <PageErrorBoundaryWrapper pageName="Insights">
                        <LazyInsights />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/automations"
                    element={
                      <PageErrorBoundaryWrapper pageName="Automations">
                        <LazyDeployed />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/scheduled"
                    element={
                      <PageErrorBoundaryWrapper pageName="Scheduled Tasks">
                        <LazyScheduledTasks />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/settings"
                    element={
                      <PageErrorBoundaryWrapper pageName="Settings">
                        <LazySettings />
                      </PageErrorBoundaryWrapper>
                    }
                  />
                  <Route
                    path="/name-enhancement"
                    element={
                      <PageErrorBoundaryWrapper pageName="Name Enhancement">
                        <LazyNameEnhancement />
                      </PageErrorBoundaryWrapper>
                    }
                  />

                  {/* Legacy redirects */}
                  <Route path="/ask-ai" element={<Navigate to="/chat" replace />} />
                  <Route path="/ha-agent" element={<Navigate to="/chat" replace />} />
                  <Route path="/deployed" element={<Navigate to="/automations" replace />} />
                  <Route path="/discovery" element={<Navigate to="/explore" replace />} />
                  <Route path="/patterns" element={<Navigate to="/insights" replace />} />
                  <Route path="/synergies" element={<Navigate to="/insights" replace />} />
                  <Route path="/admin" element={<Navigate to="/settings?section=system" replace />} />
                  <Route path="/proactive" element={<Navigate to="/?source=context" replace />} />
                  <Route path="/blueprint-suggestions" element={<Navigate to="/?source=blueprints" replace />} />
                </Routes>
              </Suspense>
            </main>

            {/* Footer */}
            <footer className="mt-16 py-8 border-t border-[var(--card-border)] bg-[var(--bg-secondary)]">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center text-sm text-[var(--text-tertiary)]">
                  <div className="mb-2">
                    <strong className="text-[var(--text-primary)]">HomeIQ</strong> - AI-Powered Smart Home Intelligence
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    Powered by OpenAI GPT-4o-mini and Machine Learning Pattern Detection
                  </div>
                  <div className="mt-4 flex justify-center gap-4">
                    <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--accent-primary)] transition-colors">
                      API Docs
                    </a>
                    <a href="https://github.com/wtthornton/HomeIQ" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--accent-primary)] transition-colors">
                      Documentation
                    </a>
                  </div>
                </div>
              </div>
            </footer>

            {/* Spacer for mobile bottom nav */}
            <div className="md:hidden h-14" />
          </div>
        </div>

        {/* Toast Notifications */}
        <CustomToaster darkMode={darkMode} />
      </Router>
    </SelectionProvider>
  );
};

export default App;
