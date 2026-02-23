/**
 * Proactive Suggestion Card Component
 * Epic AI-21: Displays context-aware automation suggestions
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { ProactiveSuggestion } from '../../types/proactive';
import { CONTEXT_TYPE_CONFIG, STATUS_CONFIG } from '../../types/proactive';

interface ProactiveSuggestionCardProps {
  suggestion: ProactiveSuggestion;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  onSendToAgent?: (id: string) => Promise<ProactiveSuggestion>;
  darkMode: boolean;
}

export const ProactiveSuggestionCard: React.FC<ProactiveSuggestionCardProps> = ({
  suggestion,
  onApprove,
  onReject,
  onDelete,
  onSendToAgent,
  darkMode,
}) => {
  const navigate = useNavigate();
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Safe access with fallback for unknown context types
  const contextConfig = CONTEXT_TYPE_CONFIG[suggestion.context_type] || {
    icon: '📌',
    label: suggestion.context_type || 'Unknown',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
  };
  const statusConfig = STATUS_CONFIG[suggestion.status] || {
    label: suggestion.status || 'Unknown',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
  };

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await onApprove(suggestion.id);
      toast.success('Suggestion approved!');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to approve suggestion:', errorMessage, error);
      toast.error('Failed to approve suggestion');
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject(suggestion.id);
      toast.success('Suggestion rejected');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to reject suggestion:', errorMessage, error);
      toast.error('Failed to reject suggestion');
    } finally {
      setIsRejecting(false);
    }
  };

  const handleDeleteClick = () => {
    if (!onDelete) return;
    setShowDeleteConfirm(true);
    // Auto-reset confirmation after 3 seconds
    setTimeout(() => setShowDeleteConfirm(false), 3000);
  };

  const handleDeleteConfirm = async () => {
    if (!onDelete) return;
    
    setIsDeleting(true);
    setShowDeleteConfirm(false);
    try {
      await onDelete(suggestion.id);
      toast.success('Suggestion deleted');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to delete suggestion:', errorMessage, error);
      toast.error('Failed to delete suggestion');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSendToAgent = async () => {
    if (!onSendToAgent) return;
    
    setIsSending(true);
    try {
      const updated = await onSendToAgent(suggestion.id);
      
      // Navigate to agent screen with conversation_id if available
      const conversationId = (updated.agent_response as any)?.conversation_id;
      if (conversationId) {
        navigate(`/ha-agent?conversation=${conversationId}`);
      } else {
        navigate('/ha-agent');
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to send suggestion to agent:', errorMessage, error);
      // Error toast is handled by parent component
    } finally {
      setIsSending(false);
    }
  };

  /**
   * Format relative time with validation
   * @param dateString - ISO 8601 date string
   * @returns Formatted relative time string or fallback
   */
  const formatRelativeTime = (dateString: string): string => {
    if (!dateString || typeof dateString !== 'string') {
      return 'Invalid date';
    }
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  /**
   * Format date string safely with validation
   * @param dateString - ISO 8601 date string
   * @returns Formatted date string or fallback
   */
  const formatDate = (dateString: string): string => {
    if (!dateString || typeof dateString !== 'string') {
      return 'Invalid date';
    }
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    return date.toLocaleString();
  };

  // Quality score color
  const getQualityColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const isActionable = suggestion.status === 'pending';
  const isProcessing = isApproving || isRejecting || isDeleting || isSending;
  
  // Get conversation ID from agent_response for link
  const conversationId = suggestion.agent_response && 
    typeof suggestion.agent_response === 'object' && 
    'conversation_id' in suggestion.agent_response
    ? (suggestion.agent_response as any).conversation_id
    : null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={`
        rounded-xl p-4 mb-4 border transition-all duration-200
        ${darkMode 
          ? 'bg-slate-800/80 border-slate-700 hover:border-slate-600' 
          : 'bg-white border-gray-200 hover:border-gray-300 shadow-sm'
        }
      `}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-3">
        {/* Context Type Badge */}
        <div className={`
          flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium
          ${contextConfig.bgColor} ${contextConfig.color}
        `}>
          <span>{contextConfig.icon}</span>
          <span>{contextConfig.label.toUpperCase()}</span>
        </div>

        {/* Quality Score */}
        <div className="flex items-center gap-2">
          <span className={`text-sm ${darkMode ? 'text-slate-400' : 'text-gray-500'}`}>
            Quality:
          </span>
          <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getQualityColor(suggestion.quality_score)} transition-all`}
              style={{ width: `${suggestion.quality_score * 100}%` }}
            />
          </div>
          <span className={`text-sm font-medium ${darkMode ? 'text-slate-300' : 'text-gray-700'}`}>
            {Math.round(suggestion.quality_score * 100)}%
          </span>
        </div>
      </div>

      {/* Prompt Content */}
      <div className={`
        text-base leading-relaxed mb-4 
        ${darkMode ? 'text-slate-200' : 'text-gray-800'}
      `}>
        "{suggestion.prompt}"
      </div>

      {/* Context Metadata (if available) */}
      {suggestion.context_metadata && Object.keys(suggestion.context_metadata).length > 0 && (
        <div className={`
          text-xs mb-4 p-2 rounded-lg
          ${darkMode ? 'bg-slate-900/50 text-slate-400' : 'bg-gray-50 text-gray-500'}
        `}>
          <details>
            <summary className="cursor-pointer hover:underline">Context Details</summary>
            <pre className="mt-2 overflow-x-auto">
              {JSON.stringify(suggestion.context_metadata, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Footer Row */}
      <div className="flex items-center justify-between">
        {/* Status & Time */}
        <div className="flex items-center gap-3">
          <span className={`
            px-2 py-1 rounded-full text-xs font-medium
            ${statusConfig.bgColor} ${statusConfig.color}
          `}>
            {statusConfig.label}
          </span>
          <span className={`text-xs ${darkMode ? 'text-slate-500' : 'text-gray-400'}`}>
            Created {formatRelativeTime(suggestion.created_at)} ({formatDate(suggestion.created_at)})
          </span>
          {suggestion.sent_at && (
            <>
              <span className={`text-xs ${darkMode ? 'text-slate-500' : 'text-gray-400'}`}>
                · Sent {formatRelativeTime(suggestion.sent_at)}
              </span>
              {conversationId && (
                <a
                  href={`/ha-agent?conversation=${conversationId}`}
                  onClick={(e) => {
                    e.preventDefault();
                    navigate(`/ha-agent?conversation=${conversationId}`);
                  }}
                  className={`
                    text-xs underline hover:no-underline transition-all
                    ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'}
                  `}
                >
                  View in Agent →
                </a>
              )}
            </>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {isActionable && onSendToAgent && (
            <button
              onClick={handleSendToAgent}
              disabled={isProcessing}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${isSending 
                  ? 'bg-blue-600 text-white cursor-wait' 
                  : 'bg-blue-500 text-white hover:bg-blue-600'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
            >
              {isSending ? 'Sending...' : '📤 Send to Agent'}
            </button>
          )}
          {isActionable && (
            <>
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${isApproving 
                    ? 'bg-green-600 text-white cursor-wait' 
                    : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                {isApproving ? '...' : '✓ Approve'}
              </button>
              <button
                onClick={handleReject}
                disabled={isProcessing}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${isRejecting 
                    ? 'bg-red-600 text-white cursor-wait' 
                    : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                {isRejecting ? '...' : '✗ Reject'}
              </button>
            </>
          )}
          
          {onDelete && (
            <div className="relative">
              {showDeleteConfirm ? (
                <button
                  onClick={handleDeleteConfirm}
                  disabled={isProcessing}
                  className={`
                    px-3 py-2 rounded-lg text-sm font-medium transition-all
                    bg-red-500/20 text-red-400 hover:bg-red-500/30
                    disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                  title="Confirm deletion"
                >
                  Confirm
                </button>
              ) : (
                <button
                  onClick={handleDeleteClick}
                  disabled={isProcessing}
                  className={`
                    px-3 py-2 rounded-lg text-sm transition-all
                    ${darkMode 
                      ? 'text-slate-500 hover:text-red-400 hover:bg-red-500/10' 
                      : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                    }
                    disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                  title="Delete suggestion"
                >
                  🗑️
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default ProactiveSuggestionCard;
