/**
 * Core System Card Component
 * Phase 1: Critical Fixes - Overview Tab Redesign
 * 
 * Displays one of the three core system pillars: Ingestion, Processing, or Storage
 * with status, key metrics, and uptime information.
 */

import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

export interface CoreSystemCardProps {
  title: string;
  icon: string;
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  metrics: {
    primary: { label: string; value: string | number; unit?: string };
    secondary: { label: string; value: string | number; unit?: string };
  };
  uptime: string;
  darkMode: boolean;
  onExpand?: () => void;
  loading?: boolean;
}

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'healthy':
      return {
        icon: '✅',
        label: 'Healthy',
        borderClass: 'border-green-500 dark:border-green-600',
        bgClass: 'bg-green-50 dark:bg-green-900/20',
        textClass: 'text-green-700 dark:text-green-300',
        badgeClass: 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      };
    case 'degraded':
      return {
        icon: '⚠️',
        label: 'Degraded',
        borderClass: 'border-yellow-500 dark:border-yellow-600',
        bgClass: 'bg-yellow-50 dark:bg-yellow-900/20',
        textClass: 'text-yellow-700 dark:text-yellow-300',
        badgeClass: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
      };
    case 'unhealthy':
      return {
        icon: '❌',
        label: 'Unhealthy',
        borderClass: 'border-red-500 dark:border-red-600',
        bgClass: 'bg-red-50 dark:bg-red-900/20',
        textClass: 'text-red-700 dark:text-red-300',
        badgeClass: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
      };
    case 'paused':
      return {
        icon: '⏸️',
        label: 'Paused',
        borderClass: 'border-gray-400 dark:border-gray-600',
        bgClass: 'bg-gray-50 dark:bg-gray-800/50',
        textClass: 'text-gray-700 dark:text-gray-300',
        badgeClass: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
      };
    default:
      return {
        icon: '❓',
        label: 'Unknown',
        borderClass: 'border-gray-400 dark:border-gray-600',
        bgClass: 'bg-gray-50 dark:bg-gray-800/50',
        textClass: 'text-gray-700 dark:text-gray-300',
        badgeClass: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
      };
  }
};

export const CoreSystemCard: React.FC<CoreSystemCardProps> = ({
  title,
  icon,
  service,
  status,
  metrics,
  uptime,
  darkMode,
  onExpand,
  loading = false
}) => {
  const statusConfig = getStatusConfig(status);

  return (
    <div 
      className={`
        rounded-xl shadow-lg p-6 border-2 transition-all-smooth hover:shadow-xl card-hover-lift animate-fade-in-scale
        ${statusConfig.borderClass}
        ${darkMode ? 'bg-gray-800' : 'bg-white'}
        ${onExpand ? 'cursor-pointer' : ''}
      `}
      onClick={onExpand}
      onKeyDown={(e) => {
        if (onExpand && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onExpand();
        }
      }}
      role={onExpand ? 'button' : 'article'}
      tabIndex={onExpand ? 0 : undefined}
      aria-label={`${title} system component - ${status}. Click for details.`}
      data-testid="health-card"
      data-status={status}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className="text-3xl">{icon}</span>
          <div>
            <h3 className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {title}
            </h3>
            <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {service}
            </p>
          </div>
        </div>
        
        {/* Status Badge */}
        <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${statusConfig.badgeClass}`}>
          <span>{statusConfig.icon}</span>
          <span>{statusConfig.label}</span>
        </span>
      </div>

      {/* Status Background Highlight */}
      <div className={`rounded-lg p-4 mb-4 ${statusConfig.bgClass}`}>
        {/* Primary Metric */}
        <div className="mb-3">
          <div className={`text-xs font-medium mb-1 ${statusConfig.textClass}`}>
            {metrics.primary.label}
          </div>
          {loading ? (
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} flex items-center space-x-2`}>
              <LoadingSpinner variant="dots" size="md" color="default" />
              <span className="text-sm font-normal">Loading...</span>
            </div>
          ) : (
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {typeof metrics.primary.value === 'number' 
                ? metrics.primary.value.toLocaleString() 
                : metrics.primary.value}
              {metrics.primary.unit && (
                <span className="text-sm font-normal ml-1">{metrics.primary.unit}</span>
              )}
            </div>
          )}
        </div>

        {/* Secondary Metric */}
        <div>
          <div className={`text-xs font-medium mb-1 ${statusConfig.textClass}`}>
            {metrics.secondary.label}
          </div>
          {loading ? (
            <div className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} flex items-center space-x-2`}>
              <LoadingSpinner variant="dots" size="sm" color="default" />
              <span className="text-xs font-normal">Loading...</span>
            </div>
          ) : (
            <div className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              {typeof metrics.secondary.value === 'number'
                ? metrics.secondary.value.toLocaleString()
                : metrics.secondary.value}
              {metrics.secondary.unit && (
                <span className="text-xs font-normal ml-1">{metrics.secondary.unit}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Uptime Footer */}
      <div className={`flex items-center justify-between text-xs pt-3 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <span className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Uptime
        </span>
        <span className={`font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {uptime}
        </span>
      </div>
    </div>
  );
};

// Memoize for performance optimization
export default React.memo(CoreSystemCard);

