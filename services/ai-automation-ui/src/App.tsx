/**
 * Main App Component
 * Routes and layout for AI Automation UI
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CustomToaster } from './components/CustomToast';
import { SelectionProvider } from './context/SelectionContext';
import { Navigation } from './components/Navigation';
import { ConversationalDashboard } from './pages/ConversationalDashboard';  // Story AI1.23 - Conversational UI
import { AskAI } from './pages/AskAI';  // Ask AI Tab - Natural Language Query Interface
import { Patterns } from './pages/Patterns';
import { Synergies } from './pages/Synergies';  // Epic AI-3, Story AI3.8
import { Deployed } from './pages/Deployed';
import { Settings } from './pages/Settings';
import { DiscoveryPage } from './pages/Discovery';  // Epic AI-4, Story AI4.3
import { useAppStore } from './store';

export const App: React.FC = () => {
  const { darkMode } = useAppStore();

  // Apply dark mode class to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  return (
    <SelectionProvider>
      <Router>
        <div className="min-h-screen transition-colors ds-bg-gradient-primary">
          <Navigation />
        
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<ConversationalDashboard />} />
            <Route path="/ask-ai" element={<AskAI />} />
            <Route path="/patterns" element={<Patterns />} />
            <Route path="/synergies" element={<Synergies />} />
            <Route path="/deployed" element={<Deployed />} />
            <Route path="/discovery" element={<DiscoveryPage />} />
            <Route path="/settings" element={<Settings />} />
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
                <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">
                  🔧 Admin Dashboard
                </a>
                <a href="http://localhost:8018/docs" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">
                  📚 API Docs
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

