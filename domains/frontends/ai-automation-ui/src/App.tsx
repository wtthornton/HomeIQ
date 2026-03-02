/**
 * Main App Component
 * Routes and layout for AI Automation UI
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { CustomToaster } from './components/CustomToast';
import { SelectionProvider } from './context/SelectionContext';
import { Sidebar } from './components/Sidebar';
import { PageErrorBoundaryWrapper } from './components/PageErrorBoundary';
import { Ideas } from './pages/Ideas';
import { Insights } from './pages/Insights';
import { Deployed } from './pages/Deployed';
import { Settings } from './pages/Settings';
import { DiscoveryPage } from './pages/Discovery';
import { NameEnhancementDashboard } from './components/name-enhancement';
import { HAAgentChat } from './pages/HAAgentChat';
import { useAppStore } from './store';

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
              <Routes>
                {/* Primary routes */}
                <Route
                  path="/"
                  element={
                    <PageErrorBoundaryWrapper pageName="Ideas">
                      <Ideas />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/chat"
                  element={
                    <PageErrorBoundaryWrapper pageName="Chat">
                      <HAAgentChat />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/explore"
                  element={
                    <PageErrorBoundaryWrapper pageName="Explore">
                      <DiscoveryPage />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/insights"
                  element={
                    <PageErrorBoundaryWrapper pageName="Insights">
                      <Insights />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/automations"
                  element={
                    <PageErrorBoundaryWrapper pageName="Automations">
                      <Deployed />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <PageErrorBoundaryWrapper pageName="Settings">
                      <Settings />
                    </PageErrorBoundaryWrapper>
                  }
                />
                <Route
                  path="/name-enhancement"
                  element={
                    <PageErrorBoundaryWrapper pageName="Name Enhancement">
                      <NameEnhancementDashboard />
                    </PageErrorBoundaryWrapper>
                  }
                />

                {/* Legacy redirects */}
                <Route path="/ha-agent" element={<Navigate to="/chat" replace />} />
                <Route path="/deployed" element={<Navigate to="/automations" replace />} />
                <Route path="/discovery" element={<Navigate to="/explore" replace />} />
                <Route path="/patterns" element={<Navigate to="/insights" replace />} />
                <Route path="/synergies" element={<Navigate to="/insights" replace />} />
                <Route path="/admin" element={<Navigate to="/settings?section=system" replace />} />
                <Route path="/proactive" element={<Navigate to="/?source=context" replace />} />
                <Route path="/blueprint-suggestions" element={<Navigate to="/?source=blueprints" replace />} />
              </Routes>
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
