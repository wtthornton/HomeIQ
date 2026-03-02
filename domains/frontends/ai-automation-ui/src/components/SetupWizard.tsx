/**
 * Setup Wizard - First-time onboarding flow
 * Guides users through initial AI automation setup
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';
import { ProcessLoader } from './ask-ai/ReverseEngineeringLoader';

interface SetupWizardProps {
  onComplete: () => void;
  darkMode?: boolean;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete, darkMode = false }) => {
  const [step, setStep] = useState(0);
  const [running, setRunning] = useState(false);

  const steps = [
    {
      title: 'Welcome to HA AutomateAI! 🤖',
      description: 'Your personal AI assistant for smart home automation',
      content: (
        <div className="space-y-4">
          <p className={`text-lg ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            HA AutomateAI analyzes your Home Assistant usage patterns and generates intelligent automation suggestions.
          </p>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <span className="text-3xl">🔍</span>
              <div>
                <div className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Pattern Detection</div>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Discovers when devices turn on/off and which devices are used together
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-3xl">🤖</span>
              <div>
                <div className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>AI Suggestions</div>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Generates automation recommendations using OpenAI GPT-4o-mini
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-3xl">✅</span>
              <div>
                <div className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Review & Deploy</div>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Review suggestions, edit if needed, and deploy to Home Assistant
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'How It Works 📚',
      description: 'Understanding the AI automation process',
      content: (
        <div className="space-y-4">
          <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-blue-50'}`}>
            <div className="text-sm font-semibold mb-2">Daily Automatic Analysis (3 AM)</div>
            <div className="space-y-2 text-sm">
              <div>1️⃣ Fetch 30 days of Home Assistant events</div>
              <div>2️⃣ Detect patterns using machine learning</div>
              <div>3️⃣ Generate suggestions with AI</div>
              <div>4️⃣ Wake up to fresh recommendations!</div>
            </div>
          </div>
          
          <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-green-50'}`}>
            <div className="text-sm font-semibold mb-2">Privacy & Security 🔒</div>
            <div className="space-y-1 text-sm">
              <div>✅ Only device IDs analyzed (e.g., "light.bedroom")</div>
              <div>✅ No personal data sent to OpenAI</div>
              <div>✅ All processing happens on your network</div>
              <div>✅ You review and approve everything</div>
            </div>
          </div>

          <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-teal-50'}`}>
            <div className="text-sm font-semibold mb-2">Cost 💰</div>
            <div className="space-y-1 text-sm">
              <div>• ~$0.0025 per analysis run</div>
              <div>• ~$0.075/month for daily automation</div>
              <div>• ~$0.90/year total cost</div>
              <div>• Uses GPT-4o-mini (most cost-effective)</div>
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Run Your First Analysis 🚀',
      description: 'Generate your first automation suggestions',
      content: (
        <div className="space-y-6">
          <div className={`text-center p-8 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gradient-to-br from-blue-50 to-cyan-50'}`}>
            <div className="text-6xl mb-4">🤖</div>
            <div className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Ready to discover automations?
            </div>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-6`}>
              This will analyze your Home Assistant usage patterns from the last 30 days
              and generate up to 10 automation suggestions.
            </div>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={async () => {
                setRunning(true);
                try {
                  await api.triggerManualJob();
                  alert('✅ Analysis started! This will take 1-2 minutes. We\'ll show you the results when complete.');
                } catch (err) {
                  alert('❌ Failed to start analysis. Please try again.');
                } finally {
                  setRunning(false);
                }
              }}
              disabled={running}
              className="px-8 py-4 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white text-lg font-bold rounded-xl shadow-2xl transition-all disabled:opacity-50"
            >
              {running ? '⏳ Analyzing...' : '🚀 Run First Analysis'}
            </motion.button>

            {running && (
              <div className="mt-6">
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Processing 30 days of events... This may take 1-2 minutes.
                </div>
                <div className="mt-3 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-600"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 90, ease: "linear" }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )
    },
    {
      title: 'All Set! 🎉',
      description: 'You\'re ready to start using HA AutomateAI',
      content: (
        <div className="text-center space-y-6">
          <div className="text-8xl">✨</div>
          <div>
            <div className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Setup Complete!
            </div>
            <div className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Your AI automation system is ready to use
            </div>
          </div>

          <div className={`max-w-md mx-auto text-left space-y-3 p-6 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <div className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              <strong>What happens next:</strong>
            </div>
            <div className="space-y-2 text-sm">
              <div>✅ Analysis runs daily at 3 AM automatically</div>
              <div>🤖 AI generates new suggestions based on patterns</div>
              <div>📱 Review suggestions in this beautiful UI</div>
              <div>✅ Approve suggestions you like</div>
              <div>🚀 Deploy approved automations to Home Assistant</div>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onComplete}
            className="px-8 py-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white text-lg font-bold rounded-xl shadow-2xl"
          >
            ✅ Start Using HA AutomateAI
          </motion.button>
        </div>
      )
    }
  ];

  const currentStep = steps[step];

  return (
    <>
      <ProcessLoader
        isVisible={running}
        processType="setup-wizard"
      />
      <div className={`fixed inset-0 z-50 flex items-center justify-center ${darkMode ? 'bg-gray-900/95' : 'bg-black/50'} backdrop-blur-sm`}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`w-full max-w-3xl mx-4 rounded-2xl shadow-2xl overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}
      >
        {/* Progress Bar */}
        <div className={`h-2 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-600"
            initial={{ width: "0%" }}
            animate={{ width: `${((step + 1) / steps.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Content */}
        <div className="p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <div className="text-center mb-6">
                <h2 className={`text-3xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {currentStep.title}
                </h2>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {currentStep.description}
                </p>
              </div>

              <div className="mb-8">
                {currentStep.content}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex justify-between items-center">
            <div className="flex gap-2">
              {steps.map((_, idx) => (
                <div
                  key={idx}
                  className={`w-2 h-2 rounded-full transition-all ${
                    idx === step
                      ? 'bg-blue-500 w-8'
                      : idx < step
                      ? darkMode ? 'bg-blue-400' : 'bg-blue-300'
                      : darkMode ? 'bg-gray-600' : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>

            <div className="flex gap-3">
              {step > 0 && step < steps.length - 1 && (
                <button
                  onClick={() => setStep(step - 1)}
                  className={`px-6 py-2 rounded-lg font-medium ${
                    darkMode
                      ? 'bg-gray-700 text-white hover:bg-gray-600'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  ← Back
                </button>
              )}

              {step < steps.length - 1 && (
                <button
                  onClick={() => setStep(step + 1)}
                  className="px-6 py-2 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white rounded-lg font-medium"
                >
                  Next →
                </button>
              )}

              {step === 0 && (
                <button
                  onClick={onComplete}
                  className={`px-6 py-2 rounded-lg font-medium ${
                    darkMode
                      ? 'text-gray-400 hover:text-gray-300'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Skip Setup
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>
      </div>
    </>
  );
};

