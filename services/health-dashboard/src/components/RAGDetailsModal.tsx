/**
 * RAG Details Modal Component
 * 
 * Shows detailed RAG metrics and component breakdown
 */

import React, { useEffect, useRef, useState } from 'react';
import { RAGStatus, RAGState } from '../types/rag';
import { Statistics } from '../types';
import { ragApi } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';

export interface RAGDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  ragStatus: RAGStatus | null;
  statistics?: Statistics | null;
  eventsStats?: any | null; // Events stats from /api/v1/events/stats (event_types, unique_entities, etc.)
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

const getRAGConfig = (state: RAGState, darkMode: boolean) => {
  switch (state) {
    case 'green':
      return {
        icon: '🟢',
        label: 'GREEN',
        bgClass: darkMode ? 'bg-green-900/30' : 'bg-green-50',
        textClass: darkMode ? 'text-green-200' : 'text-green-800',
        borderClass: darkMode ? 'border-green-700' : 'border-green-300'
      };
    case 'amber':
      return {
        icon: '🟡',
        label: 'AMBER',
        bgClass: darkMode ? 'bg-yellow-900/30' : 'bg-yellow-50',
        textClass: darkMode ? 'text-yellow-200' : 'text-yellow-800',
        borderClass: darkMode ? 'border-yellow-700' : 'border-yellow-300'
      };
    case 'red':
      return {
        icon: '🔴',
        label: 'RED',
        bgClass: darkMode ? 'bg-red-900/30' : 'bg-red-50',
        textClass: darkMode ? 'text-red-200' : 'text-red-800',
        borderClass: darkMode ? 'border-red-700' : 'border-red-300'
      };
  }
};

const getComponentLabel = (component: string): string => {
  switch (component) {
    case 'websocket':
      return 'WebSocket Connection';
    case 'processing':
      return 'Event Processing';
    case 'storage':
      return 'Data Storage';
    default:
      return component;
  }
};

const formatMetric = (value: number | undefined, unit: string = ''): string => {
  if (value === undefined || value === null) return 'N/A';
  if (typeof value === 'number') {
    return `${value.toFixed(2)}${unit ? ` ${unit}` : ''}`;
  }
  return String(value);
};

const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return 'N/A';
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
  return num.toLocaleString();
};

const formatTimeAgo = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  } catch {
    return 'N/A';
  }
};

export const RAGDetailsModal: React.FC<RAGDetailsModalProps> = ({
  isOpen,
  onClose,
  ragStatus,
  statistics,
  eventsStats,
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

  if (!isOpen || !ragStatus) return null;

  const overallConfig = getRAGConfig(ragStatus.overall, darkMode);

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
                Component Health Breakdown
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
          {/* Overall Status */}
          <div className={`
            rounded-lg p-4 border-2
            ${overallConfig.bgClass} ${overallConfig.borderClass}
          `}>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-sm font-medium ${overallConfig.textClass}`}>
                Overall Status
              </span>
              <span className={`text-xl font-bold ${overallConfig.textClass}`}>
                {overallConfig.icon} {overallConfig.label}
              </span>
            </div>
            <p className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Last updated: {ragStatus.lastUpdated.toLocaleString()}
            </p>
          </div>

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

          {/* Data Metrics Section */}
          {statistics && (
            <div className={`
              rounded-lg p-4 border-2
              ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
            `}>
              <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Data Metrics
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {/* Total Events */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Total Events
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(statistics.metrics?.['websocket-ingestion']?.total_events_received)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Period: {statistics.period || '1h'}
                  </div>
                </div>

                {/* Events per Minute */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Throughput
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {statistics.metrics?.['websocket-ingestion']?.events_per_minute?.toFixed(1) || 'N/A'}
                    <span className="text-sm font-normal ml-1">evt/min</span>
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Current rate
                  </div>
                </div>

                {/* Connection Attempts */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Connection Attempts
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {statistics.metrics?.['websocket-ingestion']?.connection_attempts || 'N/A'}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Total attempts
                  </div>
                </div>

                {/* Error Rate */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Error Rate
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {statistics.metrics?.['websocket-ingestion']?.error_rate?.toFixed(2) || 'N/A'}%
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Percentage
                  </div>
                </div>

                {/* Response Time */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Response Time
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {statistics.metrics?.['websocket-ingestion']?.response_time_ms?.toFixed(1) || 'N/A'}
                    <span className="text-sm font-normal ml-1">ms</span>
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Average latency
                  </div>
                </div>

                {/* Last Data Refresh */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Last Data Refresh
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {statistics.timestamp ? formatTimeAgo(statistics.timestamp) : 'N/A'}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    {statistics.timestamp ? new Date(statistics.timestamp).toLocaleString() : ''}
                  </div>
                </div>
              </div>

              {/* Data Source */}
              {statistics.source && (
                <div className={`mt-4 pt-4 border-t ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                  <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Data Source: <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{statistics.source}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Additional Data Metrics (Event Types, Entities, etc.) */}
          {eventsStats && (
            <div className={`
              rounded-lg p-4 border-2
              ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
            `}>
              <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Data Breakdown
              </h3>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                {/* Events Processed Count (Data Read Count) */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Events Processed
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(eventsStats.total_events || statistics?.metrics?.['websocket-ingestion']?.total_events_received)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Total processed
                  </div>
                </div>

                {/* Unique Entities Count */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Unique Entities
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatNumber(eventsStats.unique_entities)}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Distinct entities
                  </div>
                </div>

                {/* Events per Entity */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Events per Entity
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {eventsStats.unique_entities && eventsStats.total_events
                      ? (eventsStats.total_events / eventsStats.unique_entities).toFixed(1)
                      : eventsStats.unique_entities && statistics?.metrics?.['websocket-ingestion']?.total_events_received
                      ? (statistics.metrics['websocket-ingestion'].total_events_received / eventsStats.unique_entities).toFixed(1)
                      : 'N/A'}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Average
                  </div>
                </div>

                {/* Events per Minute (from eventsStats) */}
                <div>
                  <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Events/Minute
                  </div>
                  <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {eventsStats.events_per_minute?.toFixed(1) || statistics?.metrics?.['websocket-ingestion']?.events_per_minute?.toFixed(1) || 'N/A'}
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    Processing rate
                  </div>
                </div>
              </div>

              {/* Event Types Breakdown */}
              {eventsStats.event_types && Object.keys(eventsStats.event_types).length > 0 && (
                <div className={`mt-4 pt-4 border-t ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                  <h4 className={`text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Event Types Breakdown
                  </h4>
                  <div className={`space-y-2 max-h-64 overflow-y-auto ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {(() => {
                      const eventTypes = eventsStats.event_types;
                      const totalEvents = eventsStats.total_events || Object.values(eventTypes).reduce((sum: number, count: any) => sum + (typeof count === 'number' ? count : 0), 0);
                      const sortedTypes = Object.entries(eventTypes)
                        .map(([type, count]) => ({ type, count: typeof count === 'number' ? count : 0 }))
                        .sort((a, b) => b.count - a.count)
                        .slice(0, 10); // Top 10
                      
                      return sortedTypes.map(({ type, count }) => {
                        const percentage = totalEvents > 0 ? ((count / totalEvents) * 100).toFixed(1) : '0.0';
                        return (
                          <div key={type} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-700/30">
                            <div className="flex-1 min-w-0">
                              <div className={`text-sm font-medium truncate ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                                {type}
                              </div>
                            </div>
                            <div className="flex items-center space-x-3 ml-4">
                              <span className={`text-sm font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                {formatNumber(count)}
                              </span>
                              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                                {percentage}%
                              </span>
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Component Details */}
          {Object.entries(ragStatus.components).map(([key, component]) => {
            const componentConfig = getRAGConfig(component.state, darkMode);
            return (
              <div
                key={key}
                className={`
                  rounded-lg p-4 border-2
                  ${componentConfig.bgClass} ${componentConfig.borderClass}
                `}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className={`font-semibold ${componentConfig.textClass}`}>
                    {getComponentLabel(key)}
                  </h3>
                  <span className={`text-lg font-bold ${componentConfig.textClass}`}>
                    {componentConfig.icon} {componentConfig.label}
                  </span>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  {component.metrics.latency !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Latency
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.latency, 'ms')}
                      </p>
                    </div>
                  )}
                  {component.metrics.errorRate !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Error Rate
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.errorRate, '%')}
                      </p>
                    </div>
                  )}
                  {component.metrics.throughput !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Throughput
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.throughput, 'evt/min')}
                      </p>
                    </div>
                  )}
                  {component.metrics.queueSize !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Queue Size
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.queueSize, 'items')}
                      </p>
                    </div>
                  )}
                  {component.metrics.availability !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Availability
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.availability, '%')}
                      </p>
                    </div>
                  )}
                  {component.metrics.responseTime !== undefined && (
                    <div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Response Time
                      </span>
                      <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {formatMetric(component.metrics.responseTime, 'ms')}
                      </p>
                    </div>
                  )}
                </div>

                {/* Reasons */}
                {component.reasons.length > 0 && (
                  <div className={`mt-3 pt-3 border-t ${componentConfig.borderClass}`}>
                    <p className={`text-xs font-medium mb-2 ${componentConfig.textClass}`}>
                      Status Reasons:
                    </p>
                    <ul className="space-y-1">
                      {component.reasons.map((reason, index) => (
                        <li 
                          key={index}
                          className={`text-xs ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
                        >
                          • {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
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

