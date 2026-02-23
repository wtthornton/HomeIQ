/**
 * Simple App Component for Testing
 * Minimal version to isolate the issue
 */

import React from 'react';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="text-3xl">🤖</div>
              <div>
                <div className="text-lg font-bold text-gray-900">
                  HA AutomateAI
                </div>
                <div className="text-xs text-gray-500">
                  Smart Home Intelligence
                </div>
              </div>
            </div>
            <div className="text-sm text-gray-600">
              AI Automation Interface
            </div>
          </div>
        </div>
      </nav>
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            AI Automation Dashboard
          </h1>
          <p className="text-gray-600 mb-6">
            Welcome to the AI-powered Home Assistant automation system.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-900">🤖 Suggestions</h3>
              <p className="text-blue-700 text-sm">AI-generated automation ideas</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-900">📊 Patterns</h3>
              <p className="text-green-700 text-sm">Usage pattern analysis</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="font-semibold text-purple-900">🚀 Deployed</h3>
              <p className="text-purple-700 text-sm">Active automations</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900">⚙️ Settings</h3>
              <p className="text-gray-700 text-sm">Configuration options</p>
            </div>
          </div>
        </div>
      </main>

      <footer className="mt-16 py-8 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-600">
            <div className="mb-2">
              <strong>HA AutomateAI</strong> - AI-Powered Smart Home Automation
            </div>
            <div className="text-xs">
              Powered by OpenAI GPT-4o-mini • Machine Learning Pattern Detection
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
