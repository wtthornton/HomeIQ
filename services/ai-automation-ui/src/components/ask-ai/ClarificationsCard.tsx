/**
 * Clarifications Card - Timeline Component
 * 
 * Displays clarifications provided by the user in the conversational timeline.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface ClarificationsCardProps {
  clarifications: string[];
  questionsAndAnswers?: Array<{
    question: string;
    answer: string;
    selected_entities?: string[];
  }>;
  darkMode?: boolean;
}

export const ClarificationsCard: React.FC<ClarificationsCardProps> = ({
  clarifications,
  questionsAndAnswers,
  darkMode = false
}) => {
  const [showQADetails, setShowQADetails] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="rounded-lg p-3"
      style={{
        background: darkMode 
          ? 'rgba(245, 158, 11, 0.15)' 
          : 'rgba(245, 158, 11, 0.08)',
        border: `2px solid ${darkMode ? 'rgba(245, 158, 11, 0.4)' : 'rgba(245, 158, 11, 0.3)'}`,
        borderLeftWidth: '4px',
        borderLeftColor: darkMode ? 'rgba(245, 158, 11, 0.6)' : 'rgba(245, 158, 11, 0.5)'
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">✨</span>
        <h4 
          className="font-semibold text-xs uppercase tracking-wider"
          style={{ color: darkMode ? '#fcd34d' : '#92400e' }}
        >
          Clarifications Provided
        </h4>
      </div>
      
      <div className="space-y-1.5 mb-3">
        {clarifications.map((clarification, idx) => (
          <div 
            key={idx}
            className="flex items-start gap-2 text-sm"
            style={{ color: darkMode ? '#cbd5e1' : '#1e293b' }}
          >
            <span className="text-amber-500 mt-0.5">•</span>
            <span className="leading-relaxed flex-1">{clarification}</span>
          </div>
        ))}
      </div>

      {/* Q&A Details Section (Collapsible) */}
      {questionsAndAnswers && questionsAndAnswers.length > 0 && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: darkMode ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.2)' }}>
          <button
            onClick={() => setShowQADetails(!showQADetails)}
            className="flex items-center gap-2 text-xs font-medium transition-colors w-full text-left"
            style={{ 
              color: darkMode ? '#fcd34d' : '#92400e',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = '0.8';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
            }}
          >
            <span>{showQADetails ? '▼' : '▶'}</span>
            <span>View Q&A Details ({questionsAndAnswers.length})</span>
          </button>
          
          {showQADetails && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-2 space-y-2"
            >
              {questionsAndAnswers.map((qa, idx) => (
                <div key={idx} className="text-xs">
                  <div style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>
                    <strong>Q:</strong> {qa.question}
                  </div>
                  <div className="ml-4 mt-1" style={{ color: darkMode ? '#cbd5e1' : '#334155' }}>
                    <strong>A:</strong> {qa.answer}
                    {qa.selected_entities && qa.selected_entities.length > 0 && (
                      <span className="ml-2 opacity-70">
                        (Selected: {qa.selected_entities.join(', ')})
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  );
};

