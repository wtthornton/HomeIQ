/**
 * RAG Status Card Component
 * 
 * Displays Red/Amber/Green status indicators for system components
 * Option 1: Integrated RAG Status Card
 */

import React from 'react';
import { RAGStatus, RAGState } from '../types/rag';
import { Statistics } from '../types';
import { LoadingSpinner } from './LoadingSpinner';

export interface RAGStatusCardProps {
  ragStatus: RAGStatus | null;
  statistics?: Statistics | null;
  loading?: boolean;
  darkMode: boolean;
  onExpand?: () => void;
}

const getRAGConfig = (state: RAGState, darkMode: boolean) => {
  switch (state) {
    case 'green':
      return {
        icon: '🟢',
        label: 'GREEN',
        borderClass: darkMode ? 'border-green-600' : 'border-green-500',
        bgClass: darkMode ? 'bg-green-900/30' : 'bg-green-50',
        textClass: darkMode ? 'text-green-200' : 'text-green-800',
        badgeClass: darkMode ? 'bg-green-900 text-green-200' : 'bg-green-100 text-green-800'
      };
    case 'amber':
      return {
        icon: '🟡',
        label: 'AMBER',
        borderClass: darkMode ? 'border-yellow-600' : 'border-yellow-500',
        bgClass: darkMode ? 'bg-yellow-900/30' : 'bg-yellow-50',
        textClass: darkMode ? 'text-yellow-200' : 'text-yellow-800',
        badgeClass: darkMode ? 'bg-yellow-900 text-yellow-200' : 'bg-yellow-100 text-yellow-800'
      };
    case 'red':
      return {
        icon: '🔴',
        label: 'RED',
        borderClass: darkMode ? 'border-red-600' : 'border-red-500',
        bgClass: darkMode ? 'bg-red-900/30' : 'bg-red-50',
        textClass: darkMode ? 'text-red-200' : 'text-red-800',
        badgeClass: darkMode ? 'bg-red-900 text-red-200' : 'bg-red-100 text-red-800'
      };
  }
};

const getComponentLabel = (component: string): string => {
  switch (component) {
    case 'websocket':
      return 'WebSocket';
    case 'processing':
      return 'Processing';
    case 'storage':
      return 'Storage';
    default:
      return component;
  }
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

export const RAGStatusCard: React.FC<RAGStatusCardProps> = ({
  ragStatus,
  statistics,
  loading = false,
  darkMode,
  onExpand
}) => {
  if (loading && !ragStatus) {
    return (
      <div className={`
        rounded-xl shadow-lg p-6 border-2 transition-all-smooth
        ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
      `}>
        <div className="flex items-center justify-center h-48">
          <LoadingSpinner variant="dots" size="md" color="default" />
          <span className={`ml-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Loading RAG status...
          </span>
        </div>
      </div>
    );
  }

  if (!ragStatus) {
    return (
      <div className={`
        rounded-xl shadow-lg p-6 border-2 transition-all-smooth
        ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
      `}>
        <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          <p className="text-lg mb-2">🚦</p>
          <p>RAG status unavailable</p>
        </div>
      </div>
    );
  }

  const overallConfig = getRAGConfig(ragStatus.overall, darkMode);

  return (
    <div 
      className={`
        rounded-xl shadow-lg p-6 border-2 transition-all-smooth hover:shadow-xl card-hover-lift animate-fade-in-scale
        ${overallConfig.borderClass}
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
      aria-label={`RAG Status Monitor - Overall: ${overallConfig.label}. Click for details.`}
      data-testid="rag-status-card"
      data-rag-state={ragStatus.overall}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className="text-3xl">🚦</span>
          <div>
            <h3 className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              RAG Status Monitor
            </h3>
            <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              System Health Indicators
            </p>
          </div>
        </div>
        
        {/* Overall Status Badge */}
        <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${overallConfig.badgeClass}`}>
          <span>{overallConfig.icon}</span>
          <span>{overallConfig.label}</span>
        </span>
      </div>

      {/* Overall Status Background */}
      <div className={`rounded-lg p-4 mb-4 ${overallConfig.bgClass}`}>
        <div className="flex items-center justify-between mb-3">
          <div className={`text-sm font-medium ${overallConfig.textClass}`}>
            Overall Status
          </div>
          <div className={`text-2xl font-bold ${overallConfig.textClass}`}>
            {overallConfig.icon} {overallConfig.label}
          </div>
        </div>
      </div>

      {/* Component Breakdown */}
      <div className="space-y-2 mb-4">
        {Object.entries(ragStatus.components).map(([key, component]) => {
          const componentConfig = getRAGConfig(component.state, darkMode);
          return (
            <div
              key={key}
              className={`flex items-center justify-between p-2 rounded-lg ${
                darkMode ? 'bg-gray-700/50' : 'bg-gray-50'
              }`}
            >
              <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {getComponentLabel(key)}
              </span>
              <div className="flex items-center space-x-2">
                <span className="text-lg">{componentConfig.icon}</span>
                <span className={`text-xs font-semibold ${componentConfig.textClass}`}>
                  {componentConfig.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Data Metrics Section */}
      {statistics && (
        <div className={`mt-4 pt-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h4 className={`text-xs font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Data Metrics
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {/* Total Events */}
            <div className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Total Events
              </div>
              <div className={`text-sm font-semibold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {formatNumber(statistics.metrics?.['websocket-ingestion']?.total_events_received)}
              </div>
              <div className={`text-xs mt-0.5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                {statistics.period || '1h'}
              </div>
            </div>

            {/* Events per Minute */}
            <div className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Throughput
              </div>
              <div className={`text-sm font-semibold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics.metrics?.['websocket-ingestion']?.events_per_minute?.toFixed(1) || 'N/A'} <span className="text-xs font-normal">evt/min</span>
              </div>
              <div className={`text-xs mt-0.5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                Current rate
              </div>
            </div>

            {/* Connection Attempts (Read Count) */}
            <div className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Connections
              </div>
              <div className={`text-sm font-semibold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics.metrics?.['websocket-ingestion']?.connection_attempts || 'N/A'}
              </div>
              <div className={`text-xs mt-0.5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                Total attempts
              </div>
            </div>

            {/* Last Refresh */}
            <div className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Last Refresh
              </div>
              <div className={`text-sm font-semibold mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics.timestamp ? formatTimeAgo(statistics.timestamp) : 'N/A'}
              </div>
              <div className={`text-xs mt-0.5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                {statistics.timestamp ? new Date(statistics.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : ''}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className={`flex items-center justify-between text-xs pt-3 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'} ${!statistics ? 'mt-4' : ''}`}>
        <span className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Last updated
        </span>
        <span className={`font-semibold ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {ragStatus.lastUpdated.toLocaleTimeString('en-US', {
            hour12: true,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </span>
      </div>

      {/* Expand Indicator */}
      {onExpand && (
        <div className={`mt-3 text-center text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Click for detailed metrics →
        </div>
      )}
    </div>
  );
};

// Memoize for performance optimization
export default React.memo(RAGStatusCard);

