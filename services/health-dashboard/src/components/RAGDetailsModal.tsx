/**
 * RAG Details Modal Component
 * 
 * Shows detailed RAG (Retrieval-Augmented Generation) metrics only
 */

import React, { useEffect, useRef, useState } from 'react';
import { ragApi } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';

export interface RAGDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  darkMode: boolean;
}

export interface RAGServiceMetrics {
  total_calls: number;
  store_calls: number;
  retrieve_calls: number;
  search_calls: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  errors: number;
  embedding_errors: number;
  storage_errors: number;
  error_rate: number;
  avg_success_score: number;
}

const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return 'N/A';
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
  return num.toLocaleString();
};

export const RAGDetailsModal: React.FC<RAGDetailsModalProps> = ({
  isOpen,
  onClose,
  darkMode
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  
  // RAG service metrics state
  const [ragMetrics, setRagMetrics] = useState<RAGServiceMetrics | null>(null);
  const [ragMetricsLoading, setRagMetricsLoading] = useState(false);
  const [ragMetricsError, setRagMetricsError] = useState(false);

  // Focus management
  useEffect(() => {
    if (isOpen && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [isOpen]);

  // Fetch RAG service metrics when modal opens
  useEffect(() => {
    const fetchRAGMetrics = async () => {
      if (!isOpen) return;
      
      try {
        setRagMetricsLoading(true);
        setRagMetricsError(false);
        const metrics = await ragApi.getMetrics();
        setRagMetrics(metrics);
      } catch (error) {
        console.error('Failed to fetch RAG service metrics:', error);
        setRagMetricsError(true);
        setRagMetrics(null);
      } finally {
        setRagMetricsLoading(false);
      }
    };

    fetchRAGMetrics();
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }

      // Trap focus within modal
      if (event.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement?.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="rag-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className={`
          relative w-full max-w-2xl max-h-[90vh] overflow-y-auto
          rounded-xl shadow-2xl transform transition-all
          ${darkMode ? 'bg-gray-800' : 'bg-white'}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`
          sticky top-0 z-10 flex items-center justify-between p-6 border-b
          ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
        `}>
          <div className="flex items-center space-x-3">
            <span className="text-3xl">🚦</span>
            <div>
              <h2 
                id="rag-modal-title"
                className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}
              >
                RAG Status Details
              </h2>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                RAG Operations Metrics
              </p>
            </div>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className={`
              p-2 rounded-lg transition-colors
              ${darkMode 
      ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
      : 'hover:bg-gray-100 text-gray-500 hover:text-gray-900'
    }
            `}
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* RAG Operations Metrics Section */}
          {ragMetricsLoading && (
            <div className={`
              rounded-lg p-4 border-2
              ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
            `}>
              <div className="flex items-center justify-center py-4">
                <LoadingSpinner variant="dots" size="sm" color="default" />
                <span className={`ml-3 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Loading RAG metrics...
                </span>
              </div>
            </div>
          )}

          {ragMetricsError && !ragMetricsLoading && (
            <div className={`
              rounded-lg p-4 border-2
              ${darkMode ? 'bg-yellow-900/30 border-yellow-600' : 'bg-yellow-50 border-yellow-200'}
            `}>
              <div className="flex items-start">
                <span className="text-xl mr-2">⚠️</span>
                <div>
                  <h4 className={`text-sm font-semibold mb-1 ${darkMode ? 'text-yellow-200' : 'text-yellow-800'}`}>
                    RAG Service Metrics Unavailable
                  </h4>
                  <p className={`text-xs ${darkMode ? 'text-yellow-300' : 'text-yellow-700'}`}>
                    The RAG service may not be running or configured. RAG Operations metrics cannot be displayed.
                  </p>
                </div>
              </div>
            </div>
          )}

          {ragMetrics && !ragMetricsLoading && !ragMetricsError && (
            <div className={`
              rounded-lg p-4 border-2
              ${darkMode ? 'bg-blue-900/30 border-blue-600' : 'bg-blue-50 border-blue-200'}
            `}>
              <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                RAG Operations
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Total RAG Calls */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Total RAG Calls
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(ragMetrics.total_calls)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Operations
                  </div>
                </div>

                {/* Store Calls */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Store Operations
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(ragMetrics.store_calls)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Knowledge stored
                  </div>
                </div>

                {/* Retrieve Calls */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Retrieve Operations
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(ragMetrics.retrieve_calls)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Knowledge retrieved
                  </div>
                </div>

                {/* Search Calls */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Search Operations
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(ragMetrics.search_calls)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Semantic searches
                  </div>
                </div>

                {/* Cache Hit Rate */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Cache Hit Rate
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {(ragMetrics.cache_hit_rate * 100).toFixed(1)}%
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    {formatNumber(ragMetrics.cache_hits)} hits / {formatNumber(ragMetrics.cache_misses)} misses
                  </div>
                </div>

                {/* Avg Latency */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Avg Latency
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {ragMetrics.avg_latency_ms.toFixed(1)}ms
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    {ragMetrics.min_latency_ms.toFixed(1)}-{ragMetrics.max_latency_ms.toFixed(1)}ms
                  </div>
                </div>

                {/* Error Rate */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Error Rate
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {(ragMetrics.error_rate * 100).toFixed(2)}%
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    {formatNumber(ragMetrics.errors)} errors
                  </div>
                </div>

                {/* Success Score */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Avg Success Score
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {ragMetrics.avg_success_score.toFixed(2)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Quality metric
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={`
          sticky bottom-0 flex justify-end p-6 border-t
          ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
        `}>
          <button
            onClick={onClose}
            className={`
              px-4 py-2 rounded-lg font-medium transition-colors
              ${darkMode
      ? 'bg-gray-700 hover:bg-gray-600 text-white'
      : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
    }
            `}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

