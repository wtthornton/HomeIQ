/**
 * Main App Component
 * Routes and layout for AI Automation UI
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CustomToaster } from './components/CustomToast';
import { SelectionProvider } from './context/SelectionContext';
import { Navigation } from './components/Navigation';
import { PageErrorBoundaryWrapper } from './components/PageErrorBoundary';
import { ConversationalDashboard } from './pages/ConversationalDashboard';  // Story AI1.23 - Conversational UI
import { Patterns } from './pages/Patterns';
import { Synergies } from './pages/Synergies';  // Epic AI-3, Story AI3.8
import { Deployed } from './pages/Deployed';
import { Settings } from './pages/Settings';
import { DiscoveryPage } from './pages/Discovery';  // Epic AI-4, Story AI4.3
import { Admin } from './pages/Admin';
import { NameEnhancementDashboard } from './components/name-enhancement';  // Device Name Enhancement
import { HAAgentChat } from './pages/HAAgentChat';  // Epic AI-20, Story AI20.7
import { ProactiveSuggestions } from './pages/ProactiveSuggestions';  // Epic AI-21: Context-aware suggestions
import { useAppStore } from './store';

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
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  }, [darkMode]);

  return (
    <SelectionProvider>
      <Router>
        <div className="min-h-screen transition-colors ds-bg-gradient-primary">
          <Navigation />
        
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route 
              path="/" 
              element={
                <PageErrorBoundaryWrapper pageName="Dashboard">
                  <ConversationalDashboard />
                </PageErrorBoundaryWrapper>
              } 
            />
            <Route 
              path="/proactive" 
              element={
                <PageErrorBoundaryWrapper pageName="Proactive Suggestions">
                  <ProactiveSuggestions />
                </PageErrorBoundaryWrapper>
              } 
            />
            <Route 
              path="/patterns" 
              element={
                <PageErrorBoundaryWrapper pageName="Patterns">
                  <Patterns />
                </PageErrorBoundaryWrapper>
              } 
            />
            <Route 
              path="/synergies" 
              element={
                <PageErrorBoundaryWrapper pageName="Synergies">
                  <Synergies />
                </PageErrorBoundaryWrapper>
              } 
            />
            <Route 
              path="/deployed" 
              element={
                <PageErrorBoundaryWrapper pageName="Deployed">
                  <Deployed />
                </PageErrorBoundaryWrapper>
              } 
            />
            <Route 
              path="/discovery" 
              element={
                <PageErrorBoundaryWrapper pageName="Discovery">
                  <DiscoveryPage />
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
            <Route 
              path="/ha-agent" 
              element={
                <PageErrorBoundaryWrapper pageName="HA Agent Chat">
                  <HAAgentChat />
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
              path="/admin" 
              element={
                <PageErrorBoundaryWrapper pageName="Admin">
                  <Admin />
                </PageErrorBoundaryWrapper>
              } 
            />
          </Routes>
        </main>

        {/* Footer */}
        <footer className={`mt-16 py-8 border-t ${darkMode ? 'border-gray-800 bg-gray-900' : 'border-gray-200 bg-white'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className={`text-center text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <div className="mb-2">
                <strong>HA AutomateAI</strong> - AI-Powered Smart Home Automation
              </div>
              <div className="text-xs">
                Powered by OpenAI GPT-4o-mini • Machine Learning Pattern Detection • Cost: ~$0.075/month
              </div>
              <div className="mt-4 flex justify-center gap-4">
                <a href="/admin" className="hover:text-blue-500 transition-colors">
                  🔧 Admin Panel
                </a>
                <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">
                  📚 API Docs
                </a>
                <a href="https://github.com/wtthornton/HomeIQ" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">
                  📖 Documentation
                </a>
              </div>
            </div>
          </div>
        </footer>

        {/* Toast Notifications */}
        <CustomToaster darkMode={darkMode} />
        </div>
      </Router>
    </SelectionProvider>
  );
};

export default App;

