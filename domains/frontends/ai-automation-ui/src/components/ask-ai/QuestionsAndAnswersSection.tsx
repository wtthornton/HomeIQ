/**
 * Questions and Answers Section Component
 * 
 * Displays Q&A pairs in a clean, scannable format with better visual hierarchy.
 * Replaces the hard-to-read text block format.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface QAPair {
  question: string;
  answer: string;
  selected_entities?: string[];
}

interface QuestionsAndAnswersSectionProps {
  questionsAndAnswers?: QAPair[];
  darkMode?: boolean;
  title?: string;
}

export const QuestionsAndAnswersSection: React.FC<QuestionsAndAnswersSectionProps> = ({
  questionsAndAnswers,
  darkMode = false,
  title = "How Your Questions Were Answered"
}) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [allExpanded, setAllExpanded] = useState(false);

  if (!questionsAndAnswers || questionsAndAnswers.length === 0) {
    return null;
  }

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const toggleAll = () => {
    setAllExpanded(!allExpanded);
    setExpandedIndex(null);
  };

  return (
    <div className="mt-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <h4 
            className="font-semibold text-sm"
            style={{ color: darkMode ? '#e2e8f0' : '#1e293b' }}
          >
            {title}
          </h4>
          <span 
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: darkMode ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
              color: darkMode ? '#93c5fd' : '#1e40af'
            }}
          >
            {questionsAndAnswers.length} {questionsAndAnswers.length === 1 ? 'question' : 'questions'}
          </span>
        </div>
        <button
          onClick={toggleAll}
          className="text-xs font-medium px-2 py-1 rounded transition-colors"
          style={{
            color: darkMode ? '#93c5fd' : '#3b82f6',
            background: darkMode ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = darkMode 
              ? 'rgba(59, 130, 246, 0.2)' 
              : 'rgba(59, 130, 246, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = darkMode 
              ? 'rgba(59, 130, 246, 0.1)' 
              : 'rgba(59, 130, 246, 0.05)';
          }}
        >
          {allExpanded ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      {/* Q&A Cards */}
      <div className="space-y-2">
        {questionsAndAnswers.map((qa, index) => {
          const isExpanded = allExpanded || expandedIndex === index;
          
          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
              className="rounded-lg border overflow-hidden"
              style={{
                background: darkMode 
                  ? 'rgba(30, 41, 59, 0.6)' 
                  : 'rgba(248, 250, 252, 0.8)',
                borderColor: darkMode 
                  ? 'rgba(51, 65, 85, 0.5)' 
                  : 'rgba(226, 232, 240, 0.8)',
                transition: 'all 0.2s ease'
              }}
            >
              {/* Question Header (Always Visible) */}
              <button
                onClick={() => toggleExpand(index)}
                className="w-full text-left p-3 flex items-start justify-between gap-3 hover:opacity-90 transition-opacity"
                style={{
                  background: darkMode 
                    ? 'rgba(30, 41, 59, 0.8)' 
                    : 'rgba(241, 245, 249, 0.9)'
                }}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  {/* Question Number Badge */}
                  <div
                    className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{
                      background: darkMode 
                        ? 'rgba(59, 130, 246, 0.3)' 
                        : 'rgba(59, 130, 246, 0.2)',
                      color: darkMode ? '#93c5fd' : '#3b82f6'
                    }}
                  >
                    {index + 1}
                  </div>
                  
                  {/* Question Text */}
                  <div className="flex-1 min-w-0">
                    <div 
                      className="font-medium text-sm leading-snug"
                      style={{ color: darkMode ? '#e2e8f0' : '#1e293b' }}
                    >
                      {qa.question}
                    </div>
                  </div>
                </div>

                {/* Expand/Collapse Icon */}
                <div className="flex-shrink-0">
                  <motion.svg
                    animate={{ rotate: isExpanded ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    style={{ color: darkMode ? '#94a3b8' : '#64748b' }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </motion.svg>
                </div>
              </button>

              {/* Answer Content (Expandable) */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div 
                      className="p-3 pt-0 pl-12 border-t"
                      style={{
                        borderColor: darkMode 
                          ? 'rgba(51, 65, 85, 0.5)' 
                          : 'rgba(226, 232, 240, 0.8)',
                        background: darkMode 
                          ? 'rgba(15, 23, 42, 0.4)' 
                          : 'rgba(255, 255, 255, 0.5)'
                      }}
                    >
                      {/* Answer Text */}
                      <div 
                        className="text-sm leading-relaxed mb-2"
                        style={{ color: darkMode ? '#cbd5e1' : '#475569' }}
                      >
                        {qa.answer}
                      </div>

                      {/* Selected Entities (if any) */}
                      {qa.selected_entities && qa.selected_entities.length > 0 && (
                        <div className="mt-2 pt-2 border-t" style={{ borderColor: darkMode ? 'rgba(51, 65, 85, 0.3)' : 'rgba(226, 232, 240, 0.6)' }}>
                          <div 
                            className="text-xs font-medium mb-1.5"
                            style={{ color: darkMode ? '#94a3b8' : '#64748b' }}
                          >
                            Selected Devices:
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {qa.selected_entities.map((entity, entityIdx) => (
                              <span
                                key={entityIdx}
                                className="px-2 py-0.5 rounded text-xs font-medium"
                                style={{
                                  background: darkMode 
                                    ? 'rgba(16, 185, 129, 0.2)' 
                                    : 'rgba(16, 185, 129, 0.1)',
                                  color: darkMode ? '#6ee7b7' : '#059669',
                                  border: `1px solid ${darkMode ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.2)'}`
                                }}
                              >
                                {entity}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

