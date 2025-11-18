/**
 * Response Handler Component
 * 
 * Handles different response types from v2 conversation API.
 * Renders appropriate UI based on response_type.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { ConversationalSuggestionCard } from '../ConversationalSuggestionCard';
import { ClarificationDialog } from './ClarificationDialog';
import type {
  ConversationTurnResponse,
  ResponseType,
  AutomationSuggestion,
  ClarificationQuestion,
} from '../../services/api-v2';

interface ResponseHandlerProps {
  response: ConversationTurnResponse;
  onSuggestionApprove?: (suggestion: AutomationSuggestion) => void;
  onSuggestionReject?: (suggestion: AutomationSuggestion) => void;
  onSuggestionRefine?: (suggestion: AutomationSuggestion, refinement: string) => void;
  onClarificationAnswer?: (
    questions: ClarificationQuestion[],
    answers: Array<{ question_id: string; answer_text: string; selected_entities?: string[] }>
  ) => void;
  darkMode?: boolean;
}

export const ResponseHandler: React.FC<ResponseHandlerProps> = ({
  response,
  onSuggestionApprove,
  onSuggestionReject,
  onSuggestionRefine,
  onClarificationAnswer,
  darkMode = false,
}) => {
  const { response_type, content, suggestions, clarification_questions, confidence } = response;

  // Render based on response type
  switch (response_type) {
    case ResponseType.AUTOMATION_GENERATED:
      return (
        <div className="response-handler automation-generated">
          {/* Main content message */}
          <div className={`response-content ${darkMode ? 'dark' : ''}`}>
            <p>{content}</p>
            {confidence && (
              <div className="confidence-indicator">
                <span className="confidence-label">Confidence:</span>
                <span className="confidence-value">{Math.round(confidence.overall * 100)}%</span>
                {confidence.explanation && (
                  <span className="confidence-explanation">{confidence.explanation}</span>
                )}
              </div>
            )}
          </div>

          {/* Suggestions */}
          {suggestions && suggestions.length > 0 && (
            <div className="suggestions-container">
              {suggestions.map((suggestion) => (
                <motion.div
                  key={suggestion.suggestion_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <ConversationalSuggestionCard
                    suggestion={{
                      suggestion_id: suggestion.suggestion_id,
                      description: suggestion.description,
                      title: suggestion.title,
                      confidence: suggestion.confidence,
                      status: suggestion.status,
                      automation_yaml: suggestion.automation_yaml,
                      validated_entities: suggestion.validated_entities,
                    }}
                    onApprove={() => onSuggestionApprove?.(suggestion)}
                    onReject={() => onSuggestionReject?.(suggestion)}
                    onRefine={(refinement) => onSuggestionRefine?.(suggestion, refinement)}
                  />
                </motion.div>
              ))}
            </div>
          )}

          {/* Next actions */}
          {response.next_actions && response.next_actions.length > 0 && (
            <div className="next-actions">
              <p className="next-actions-label">Suggested next steps:</p>
              <ul>
                {response.next_actions.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );

    case ResponseType.CLARIFICATION_NEEDED:
      return (
        <div className="response-handler clarification-needed">
          <div className={`response-content ${darkMode ? 'dark' : ''}`}>
            <p>{content}</p>
          </div>

          {clarification_questions && clarification_questions.length > 0 && (
            <ClarificationDialog
              questions={clarification_questions}
              sessionId={response.conversation_id}
              confidence={confidence?.overall || 0}
              threshold={0.7}
              onAnswer={(answers) => {
                if (onClarificationAnswer) {
                  onClarificationAnswer(clarification_questions, answers);
                }
              }}
            />
          )}
        </div>
      );

    case ResponseType.ACTION_DONE:
      return (
        <div className="response-handler action-done">
          <div className={`response-content success ${darkMode ? 'dark' : ''}`}>
            <div className="action-icon">✓</div>
            <p>{content}</p>
            {response.processing_time_ms && (
              <span className="processing-time">
                Completed in {response.processing_time_ms}ms
              </span>
            )}
          </div>
        </div>
      );

    case ResponseType.INFORMATION_PROVIDED:
      return (
        <div className="response-handler information-provided">
          <div className={`response-content info ${darkMode ? 'dark' : ''}`}>
            <div className="info-icon">ℹ</div>
            <p>{content}</p>
          </div>
        </div>
      );

    case ResponseType.ERROR:
      return (
        <div className="response-handler error">
          <div className={`response-content error ${darkMode ? 'dark' : ''}`}>
            <div className="error-icon">✗</div>
            <p>{content}</p>
            {response.next_actions && response.next_actions.length > 0 && (
              <div className="error-suggestions">
                <p>Try:</p>
                <ul>
                  {response.next_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      );

    case ResponseType.NO_INTENT_MATCH:
      return (
        <div className="response-handler no-intent-match">
          <div className={`response-content warning ${darkMode ? 'dark' : ''}`}>
            <div className="warning-icon">⚠</div>
            <p>{content}</p>
            {response.next_actions && response.next_actions.length > 0 && (
              <div className="suggestions">
                <p>You might want to:</p>
                <ul>
                  {response.next_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      );

    default:
      return (
        <div className="response-handler unknown">
          <div className={`response-content ${darkMode ? 'dark' : ''}`}>
            <p>{content}</p>
          </div>
        </div>
      );
  }
};

