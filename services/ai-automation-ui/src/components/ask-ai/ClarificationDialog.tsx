/**
 * ClarificationDialog Component
 * 
 * Displays clarification questions and collects user answers.
 * Supports multiple question types: multiple choice, text, entity selection, boolean.
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

interface ClarificationQuestion {
  id: string;
  category: string;
  question_text: string;
  question_type: 'multiple_choice' | 'text' | 'entity_selection' | 'boolean';
  options?: string[];
  priority: number;
  related_entities?: string[];
}

interface ClarificationDialogProps {
  questions: ClarificationQuestion[];
  sessionId: string;
  currentConfidence: number;
  confidenceThreshold: number;
  previousConfidence?: number;
  confidenceDelta?: number;
  confidenceSummary?: string;
  onAnswer: (answers: Array<{
    question_id: string;
    answer_text: string;
    selected_entities?: string[];
  }>) => Promise<void>;
  onCancel: () => void;
  darkMode?: boolean;
}

export const ClarificationDialog: React.FC<ClarificationDialogProps> = ({
  questions,
  currentConfidence,
  confidenceThreshold,
  previousConfidence,
  confidenceDelta,
  confidenceSummary,
  onAnswer,
  onCancel
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedEntities, setSelectedEntities] = useState<Record<string, string[]>>({});
  const [optionDescriptions, setOptionDescriptions] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize answers
  useEffect(() => {
    const initialAnswers: Record<string, string> = {};
    const initialEntities: Record<string, string[]> = {};
    
    questions.forEach(q => {
      if (q.question_type === 'entity_selection') {
        initialEntities[q.id] = [];
      } else if (q.question_type === 'boolean') {
        initialAnswers[q.id] = '';
      } else if (q.question_type === 'multiple_choice' && q.options && q.options.length > 0) {
        initialAnswers[q.id] = '';
      } else {
        initialAnswers[q.id] = '';
      }
    });
    
    setAnswers(initialAnswers);
    setSelectedEntities(initialEntities);
  }, [questions]);

  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    // Clear description when option changes
    const descriptionKey = `${questionId}_desc`;
    setOptionDescriptions(prev => {
      const newState = { ...prev };
      delete newState[descriptionKey];
      return newState;
    });
  };

  const handleDescriptionChange = (questionId: string, description: string) => {
    const descriptionKey = `${questionId}_desc`;
    setOptionDescriptions(prev => ({ ...prev, [descriptionKey]: description }));
  };

  const handleEntityToggle = (questionId: string, entityId: string) => {
    setSelectedEntities(prev => {
      const current = prev[questionId] || [];
      const updated = current.includes(entityId)
        ? current.filter(id => id !== entityId)
        : [...current, entityId];
      return { ...prev, [questionId]: updated };
    });
  };

  // Check if an option requires additional description
  const requiresDescription = (option: string): boolean => {
    if (!option) return false;
    const lowerOption = option.toLowerCase();
    return lowerOption.includes('(please describe)') ||
           lowerOption.includes('(please specify)') ||
           lowerOption.includes('(describe)') ||
           lowerOption.includes('(specify)') ||
           lowerOption.includes('please describe') ||
           lowerOption.includes('please specify');
  };

  const handleSubmit = async () => {
    // Validate all questions are answered
    const unanswered = questions.filter(q => {
      if (q.question_type === 'entity_selection') {
        return !selectedEntities[q.id] || selectedEntities[q.id].length === 0;
      }
      
      const answer = answers[q.id];
      if (!answer || answer.trim() === '') {
        return true;
      }
      
      // Check if option requires description and it's missing
      if (q.question_type === 'multiple_choice' && q.options) {
        const selectedOption = answer;
        if (requiresDescription(selectedOption)) {
          const descriptionKey = `${q.id}_desc`;
          const description = optionDescriptions[descriptionKey] || '';
          if (!description || description.trim() === '') {
            return true;
          }
        }
      }
      
      return false;
    });

    if (unanswered.length > 0) {
      toast.error(`Please answer all ${questions.length} questions`);
      return;
    }

    setIsSubmitting(true);
    try {
      const answerPayload = questions.map(q => {
        if (q.question_type === 'entity_selection') {
          return {
            question_id: q.id,
            answer_text: selectedEntities[q.id]?.join(', ') || '',
            selected_entities: selectedEntities[q.id] || []
          };
        } else {
          let answerText = answers[q.id] || '';
          
          // Append description if option requires it
          if (q.question_type === 'multiple_choice' && requiresDescription(answerText)) {
            const descriptionKey = `${q.id}_desc`;
            const description = optionDescriptions[descriptionKey] || '';
            if (description && description.trim() !== '') {
              answerText = `${answerText}: ${description.trim()}`;
            }
          }
          
          return {
            question_id: q.id,
            answer_text: answerText,
            selected_entities: undefined
          };
        }
      });

      await onAnswer(answerPayload);
    } catch (error: any) {
      // Extract error message from various error formats
      let errorMessage = 'Unknown error';
      if (error?.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (detail?.message) {
          errorMessage = detail.message;
        }
      } else if (error?.message) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      toast.error(`Failed to submit answers: ${errorMessage}`);
      // Re-throw error so parent can handle it if needed
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderQuestion = (question: ClarificationQuestion) => {
    const answer = answers[question.id] || '';
    const entities = selectedEntities[question.id] || [];

    switch (question.question_type) {
      case 'multiple_choice':
        const descriptionKey = `${question.id}_desc`;
        const description = optionDescriptions[descriptionKey] || '';
        const needsDescription = answer && requiresDescription(answer);
        
        return (
          <div className="space-y-2">
            {question.options?.map((option, idx) => (
              <div key={idx}>
                <label
                  className="flex items-center space-x-2 p-3 rounded-lg cursor-pointer transition-colors"
                  style={{
                    background: answer === option
                      ? 'rgba(59, 130, 246, 0.2)'
                      : 'rgba(30, 41, 59, 0.6)',
                    border: `1px solid ${answer === option ? 'rgba(59, 130, 246, 0.5)' : 'rgba(51, 65, 85, 0.5)'}`
                  }}
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={option}
                    checked={answer === option}
                    onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span style={{ color: '#cbd5e1' }}>{option}</span>
                </label>
                {answer === option && needsDescription && (
                  <div className="mt-2 ml-7">
                    <input
                      type="text"
                      value={description}
                      onChange={(e) => handleDescriptionChange(question.id, e.target.value)}
                      placeholder="Please provide details..."
                      className="w-full px-4 py-2 rounded-lg border transition-colors"
                      style={{
                        background: 'rgba(30, 41, 59, 0.6)',
                        borderColor: 'rgba(59, 130, 246, 0.5)',
                        color: '#cbd5e1'
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        );

      case 'entity_selection':
        return (
          <div className="space-y-2">
            {question.related_entities?.map((entityId) => (
              <label
                key={entityId}
                className="flex items-center space-x-2 p-3 rounded-lg cursor-pointer transition-colors"
                style={{
                  background: entities.includes(entityId)
                    ? 'rgba(59, 130, 246, 0.2)'
                    : 'rgba(30, 41, 59, 0.6)',
                  border: `1px solid ${entities.includes(entityId) ? 'rgba(59, 130, 246, 0.5)' : 'rgba(51, 65, 85, 0.5)'}`
                }}
              >
                <input
                  type="checkbox"
                  checked={entities.includes(entityId)}
                  onChange={() => handleEntityToggle(question.id, entityId)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span style={{ color: '#cbd5e1' }}>{entityId}</span>
              </label>
            ))}
            {question.options?.map((option, idx) => (
              <label
                key={idx}
                className="flex items-center space-x-2 p-3 rounded-lg cursor-pointer transition-colors"
                style={{
                  background: answer === option
                    ? 'rgba(59, 130, 246, 0.2)'
                    : 'rgba(30, 41, 59, 0.6)',
                  border: `1px solid ${answer === option ? 'rgba(59, 130, 246, 0.5)' : 'rgba(51, 65, 85, 0.5)'}`
                }}
              >
                <input
                  type="radio"
                  name={question.id}
                  value={option}
                  checked={answer === option}
                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                  className="w-4 h-4 text-blue-600"
                />
                <span style={{ color: '#cbd5e1' }}>{option}</span>
              </label>
            ))}
          </div>
        );

      case 'boolean':
        return (
          <div className="flex space-x-4">
            <button
              onClick={() => handleAnswerChange(question.id, 'yes')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                answer === 'yes'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Yes
            </button>
            <button
              onClick={() => handleAnswerChange(question.id, 'no')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                answer === 'no'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              No
            </button>
          </div>
        );

      default: // text
        return (
          <input
            type="text"
            value={answer}
            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
            placeholder="Type your answer..."
            className="w-full px-4 py-2 rounded-lg border transition-colors"
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              borderColor: 'rgba(51, 65, 85, 0.5)',
              color: '#cbd5e1'
            }}
          />
        );
    }
  };

  const confidencePercent = Math.round(currentConfidence * 100);
  const thresholdPercent = Math.round(confidenceThreshold * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        background: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(4px)'
      }}
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        className="w-full max-w-2xl rounded-lg shadow-xl"
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
      >
        {/* Header */}
        <div className="p-6 border-b" style={{ borderColor: 'rgba(51, 65, 85, 0.5)' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold" style={{ color: '#ffffff' }}>
              Clarification Needed
            </h2>
            <button
              onClick={onCancel}
              className="p-1 rounded hover:bg-gray-700 transition-colors"
              style={{ color: '#cbd5e1' }}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Confidence Meter */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span style={{ color: '#94a3b8' }}>Confidence:</span>
              <div className="flex items-center space-x-2">
                {/* Confidence Delta Indicator */}
                {previousConfidence !== undefined && previousConfidence > 0 && confidenceDelta !== undefined && confidenceDelta > 0 && (
                  <span 
                    className="text-xs font-medium px-2 py-0.5 rounded"
                    style={{ 
                      color: '#10b981',
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.3)'
                    }}
                  >
                    {Math.round(previousConfidence * 100)}% → {confidencePercent}% (+{Math.round(confidenceDelta * 100)}% ↑)
                  </span>
                )}
                <span style={{ color: confidencePercent >= thresholdPercent ? '#10b981' : '#f59e0b' }}>
                  {confidencePercent}% / {thresholdPercent}%
                </span>
              </div>
            </div>
            <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'rgba(51, 65, 85, 0.5)' }}>
              <div
                className="h-full transition-all duration-300"
                style={{
                  width: `${Math.min(100, (currentConfidence / confidenceThreshold) * 100)}%`,
                  background: confidencePercent >= thresholdPercent
                    ? 'linear-gradient(to right, #10b981, #059669)'
                    : 'linear-gradient(to right, #f59e0b, #d97706)'
                }}
              />
            </div>
            {/* Smart Summary Message */}
            {confidenceSummary && (
              <div 
                className="mt-2 p-3 rounded-lg text-sm"
                style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  color: '#6ee7b7'
                }}
              >
                <div className="flex items-start space-x-2">
                  <span className="text-base">✨</span>
                  <span>{confidenceSummary}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Questions */}
        <div className="p-6 space-y-6">
          <p style={{ color: '#cbd5e1', marginBottom: '1.5rem' }}>
            I found some ambiguities in your request. Please answer these questions to help me create the automation accurately.
          </p>

          {questions.map((question, index) => (
            <div key={question.id} className="space-y-3">
              <div className="flex items-start space-x-3">
                <span
                  className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
                  style={{
                    background: question.priority === 1 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                    color: question.priority === 1 ? '#fca5a5' : '#93c5fd'
                  }}
                >
                  {index + 1}
                </span>
                <div className="flex-1">
                  <p className="font-medium mb-2" style={{ color: '#ffffff' }}>
                    {question.question_text}
                  </p>
                  {renderQuestion(question)}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-6 border-t flex items-center justify-end space-x-3" style={{ borderColor: 'rgba(51, 65, 85, 0.5)' }}>
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg font-medium transition-colors"
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(51, 65, 85, 0.5)',
              color: '#cbd5e1'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-6 py-2 rounded-lg font-medium transition-colors text-white"
            style={{
              background: isSubmitting ? '#4b5563' : '#3b82f6',
              opacity: isSubmitting ? 0.6 : 1,
              cursor: isSubmitting ? 'not-allowed' : 'pointer'
            }}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Answers'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

