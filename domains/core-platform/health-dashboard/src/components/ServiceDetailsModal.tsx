/**
 * Service Details Modal Component
 * Phase 3: Enhanced with accessibility, animations, and keyboard navigation
 * 
 * Shows detailed information about a service when clicking on a CoreSystemCard
 */

import React, { useEffect, useRef } from 'react';
import { ServiceMetrics } from './ServiceMetrics';
import { getServiceMetricsConfig } from '../config/serviceMetricsConfig';

export interface ServiceDetail {
  label: string;
  value: string | number;
  unit?: string;
  status?: 'good' | 'warning' | 'error';
}

export interface ServiceDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon: string;
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  details: ServiceDetail[];
  darkMode: boolean;
}

export const ServiceDetailsModal: React.FC<ServiceDetailsModalProps> = ({
  isOpen,
  onClose,
  title,
  icon,
  service,
  status = 'paused',
  details = [],
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

  if (!isOpen) return null;

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 dark:text-green-400';
      case 'degraded':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'unhealthy':
        return 'text-red-600 dark:text-red-400';
      case 'paused':
        return 'text-gray-600 dark:text-gray-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto animate-modal-backdrop" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
    >
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" 
          aria-hidden="true"
        />

        {/* Modal panel */}
        <div 
          ref={modalRef}
          className={`inline-block align-bottom rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full animate-modal-content ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`px-6 py-5 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-4xl" aria-hidden="true">{icon}</span>
                <div>
                  <h3 
                    id="modal-title"
                    className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}
                  >
                    {title}
                  </h3>
                  <p 
                    id="modal-description"
                    className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}
                  >
                    {service}
                  </p>
                </div>
              </div>
              <button
                ref={closeButtonRef}
                onClick={onClose}
                className={`rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible-ring ${
                  darkMode ? 'text-gray-400' : 'text-gray-500'
                }`}
                aria-label="Close dialog"
              >
                <svg 
                  className="w-5 h-5" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mt-3">
              <span 
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}
                role="status"
                aria-label={`Service status: ${status || 'unknown'}`}
              >
                {(() => {
                  const statusStr = status || 'paused';
                  return typeof statusStr === 'string' && statusStr.length > 0 
                    ? statusStr.charAt(0).toUpperCase() + statusStr.slice(1) 
                    : 'Unknown';
                })()}
              </span>
            </div>
          </div>

          {/* Body */}
          <div className="px-6 py-5">
            {/* Debug: Show service ID */}
            {import.meta.env.DEV && (
              <div className="mb-2 text-xs text-gray-500">
                DEBUG: Service ID = "{service}"
              </div>
            )}
            {/* Service-Specific Metrics (if configured) */}
            {(service === 'websocket-ingestion' || service?.includes('websocket') || getServiceMetricsConfig(service)) ? (
              <ServiceMetrics
                serviceId={service}
                darkMode={darkMode}
                autoRefresh={true}
                refreshInterval={10000}
              />
            ) : (
              /* Fallback to Generic Metrics */
              <>
                <h4 className={`text-sm font-semibold mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Detailed Metrics
                </h4>
                <div className="space-y-3" role="list">
                  {details.map((detail, index) => (
                    <div
                      key={index}
                      className={'flex justify-between items-center stagger-item'}
                      role="listitem"
                    >
                      <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {detail.label}
                      </span>
                      <span className={`text-base font-semibold ${
                        detail.status === 'good'
                          ? 'text-green-600 dark:text-green-400'
                          : detail.status === 'warning'
                            ? 'text-yellow-600 dark:text-yellow-400'
                              : detail.status === 'error'
                                ? 'text-red-600 dark:text-red-400'
                                : darkMode ? 'text-white' : 'text-gray-900'
                      }`}>
                        {detail.value} {detail.unit && <span className="text-sm font-normal">{detail.unit}</span>}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className={`px-6 py-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'} flex justify-end`}>
            <button
              onClick={onClose}
              className={`px-4 py-2 rounded-lg font-medium transition-colors focus-visible-ring ${
                darkMode
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
              aria-label="Close service details dialog"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Memoize for performance
export default React.memo(ServiceDetailsModal);
