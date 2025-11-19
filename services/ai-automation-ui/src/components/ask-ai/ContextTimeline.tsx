/**
 * Context Timeline - Conversation Flow Component
 * 
 * Displays the conversational timeline: Original Request → Clarifications → Suggestion
 * This component creates a visual flow showing how user input leads to automation suggestions.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { OriginalRequestCard } from './OriginalRequestCard';
import { ClarificationsCard } from './ClarificationsCard';

interface ContextTimelineProps {
  originalRequest: string;
  clarifications: string[];
  questionsAndAnswers?: Array<{
    question: string;
    answer: string;
    selected_entities?: string[];
  }>;
  children: React.ReactNode; // The suggestion card(s)
  darkMode?: boolean;
}

export const ContextTimeline: React.FC<ContextTimelineProps> = ({
  originalRequest,
  clarifications,
  questionsAndAnswers,
  children,
  darkMode = false
}) => {
  // Extract clarifications from questionsAndAnswers if clarifications array is empty
  const displayClarifications = clarifications.length > 0 
    ? clarifications 
    : (questionsAndAnswers?.map(qa => qa.answer) || []);

  // Don't render timeline if there's no context to show
  if (!originalRequest && displayClarifications.length === 0) {
    return <>{children}</>;
  }

  return (
    <div className="space-y-4">
      {/* Original Request Card */}
      {originalRequest && (
        <OriginalRequestCard 
          originalRequest={originalRequest} 
          darkMode={darkMode}
        />
      )}

      {/* Visual Connector */}
      {(originalRequest && displayClarifications.length > 0) && (
        <motion.div
          initial={{ opacity: 0, scaleY: 0 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="flex justify-center"
        >
          <div 
            className="w-0.5 h-6"
            style={{
              background: `linear-gradient(to bottom, ${
                darkMode ? 'rgba(59, 130, 246, 0.4)' : 'rgba(59, 130, 246, 0.3)'
              }, ${
                darkMode ? 'rgba(245, 158, 11, 0.4)' : 'rgba(245, 158, 11, 0.3)'
              })`
            }}
          >
            <div 
              className="relative w-full h-full flex items-center justify-center"
              style={{ marginTop: '-4px' }}
            >
              <div
                className="w-0 h-0"
                style={{
                  borderLeft: '4px solid transparent',
                  borderRight: '4px solid transparent',
                  borderTop: `6px solid ${darkMode ? 'rgba(245, 158, 11, 0.5)' : 'rgba(245, 158, 11, 0.4)'}`
                }}
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Clarifications Card */}
      {displayClarifications.length > 0 && (
        <ClarificationsCard 
          clarifications={displayClarifications}
          questionsAndAnswers={questionsAndAnswers}
          darkMode={darkMode}
        />
      )}

      {/* Visual Connector to Suggestion */}
      {displayClarifications.length > 0 && (
        <motion.div
          initial={{ opacity: 0, scaleY: 0 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={{ duration: 0.3, delay: 0.25 }}
          className="flex justify-center"
        >
          <div 
            className="w-0.5 h-6"
            style={{
              background: `linear-gradient(to bottom, ${
                darkMode ? 'rgba(245, 158, 11, 0.4)' : 'rgba(245, 158, 11, 0.3)'
              }, ${
                darkMode ? 'rgba(16, 185, 129, 0.4)' : 'rgba(16, 185, 129, 0.3)'
              })`
            }}
          >
            <div 
              className="relative w-full h-full flex items-center justify-center"
              style={{ marginTop: '-4px' }}
            >
              <div
                className="w-0 h-0"
                style={{
                  borderLeft: '4px solid transparent',
                  borderRight: '4px solid transparent',
                  borderTop: `6px solid ${darkMode ? 'rgba(16, 185, 129, 0.5)' : 'rgba(16, 185, 129, 0.4)'}`
                }}
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Suggestion Card(s) */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.35 }}
      >
        {children}
      </motion.div>
    </div>
  );
};

