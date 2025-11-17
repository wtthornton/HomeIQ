/**
 * RAG Details Modal Component
 * 
 * Shows detailed RAG metrics and component breakdown
 */

import React, { useEffect, useRef } from 'react';
import { RAGStatus, RAGState } from '../types/rag';

export interface RAGDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  ragStatus: RAGStatus | null;
  darkMode: boolean;
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

export const RAGDetailsModal: React.FC<RAGDetailsModalProps> = ({
  isOpen,
  onClose,
  ragStatus,
  darkMode
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Focus management
  useEffect(() => {
    if (isOpen && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
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

