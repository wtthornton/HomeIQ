import React from 'react';
import type { ServiceStatus } from '../types';

interface ServiceCardProps {
  service: ServiceStatus;
  icon: string;
  darkMode: boolean;
  onViewDetails?: () => void;
  onConfigure?: () => void;
  onStart?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
  containerStatus?: string;
  isOperating?: boolean;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({
  service,
  icon,
  darkMode,
  onViewDetails,
  onConfigure,
  onStart,
  onStop,
  onRestart,
  containerStatus,
  isOperating = false,
}) => {
  const getStatusBadgeClass = (status: string, isDark: boolean) => {
    switch (status) {
      case 'running':
        return isDark ? 'badge-success' : 'badge-success';
      case 'stopped':
        return isDark ? 'badge-info' : 'badge-info';
      case 'error':
        return isDark ? 'badge-error' : 'badge-error';
      case 'degraded':
        return isDark ? 'badge-warning' : 'badge-warning';
      default:
        return isDark ? 'badge-info' : 'badge-info';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return '🟢';
      case 'stopped':
        return '⚪';
      case 'error':
        return '🔴';
      case 'degraded':
        return '🟡';
      default:
        return '⚪';
    }
  };

  return (
    <div
      className={`card-base card-hover content-fade-in ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="text-3xl icon-entrance">{icon}</div>
          <div>
            <h3 className={`font-semibold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {service.service}
            </h3>
            {service.port && (
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Port {service.port}
              </p>
            )}
          </div>
        </div>
        <span className={`badge-base status-transition flex items-center space-x-1 ${getStatusBadgeClass(service.status, darkMode)}`}>
          <span className={service.status === 'running' ? 'live-pulse-dot' : ''}>{getStatusIcon(service.status)}</span>
          <span className="capitalize">{service.status}</span>
        </span>
      </div>

      {/* Metrics */}
      <div className="space-y-2 mb-4">
        {service.uptime && (
          <div className="flex justify-between items-center">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Uptime
            </span>
            <span className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {service.uptime}
            </span>
          </div>
        )}
        
        {service.metrics?.requests_per_minute !== undefined && (
          <div className="flex justify-between items-center">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Requests/min
            </span>
            <span className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {(service.metrics.requests_per_minute ?? 0).toFixed(1)}
            </span>
          </div>
        )}
        
        {service.metrics?.error_rate !== undefined && (
          <div className="flex justify-between items-center">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Error Rate
            </span>
            <span className={`text-sm font-medium ${
              service.metrics.error_rate > 5 
                ? 'text-red-600' 
                : darkMode ? 'text-green-400' : 'text-green-600'
            }`}>
              {(service.metrics.error_rate ?? 0).toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* Error Message */}
      {service.error && (
        <div className={`mb-4 p-3 rounded-md text-sm ${
          darkMode ? 'bg-red-900/30 text-red-200' : 'bg-red-50 text-red-800'
        }`}>
          {service.error}
        </div>
      )}

      {/* Container Status - Only show if different from service status or if service status is unknown */}
      {containerStatus && containerStatus !== 'unknown' && containerStatus !== service.status && (
        <div className="mb-3">
          <div className="flex justify-between items-center">
            <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Container:
            </span>
            <span className={`text-xs font-medium ${
              containerStatus === 'running' 
                ? 'text-green-600 dark:text-green-400' 
                : containerStatus === 'stopped' || containerStatus === 'exited'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-gray-600 dark:text-gray-400'
            }`}>
              {containerStatus === 'running' ? '🟢 Running' : 
                containerStatus === 'stopped' || containerStatus === 'exited' ? '🔴 Stopped' : 
                  '⚪ Unknown'}
            </span>
          </div>
        </div>
      )}

      {/* Container Actions */}
      {(onStart || onStop || onRestart) && (
        <div className="mb-3 space-y-2">
          <div className="flex space-x-1">
            {containerStatus === 'stopped' && onStart && (
              <button
                onClick={onStart}
                disabled={isOperating}
                className={`px-2 py-1 text-xs rounded font-medium transition-colors duration-200 ${
                  isOperating
                    ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {isOperating ? 'Starting...' : '▶️ Start'}
              </button>
            )}
            
            {containerStatus === 'running' && onStop && (
              <button
                onClick={onStop}
                disabled={isOperating}
                className={`px-2 py-1 text-xs rounded font-medium transition-colors duration-200 ${
                  isOperating
                    ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
                    : 'bg-red-600 hover:bg-red-700 text-white'
                }`}
              >
                {isOperating ? 'Stopping...' : '⏹️ Stop'}
              </button>
            )}
            
            {containerStatus === 'running' && onRestart && (
              <button
                onClick={onRestart}
                disabled={isOperating}
                className={`px-2 py-1 text-xs rounded font-medium transition-colors duration-200 ${
                  isOperating
                    ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {isOperating ? 'Restarting...' : '🔄 Restart'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex space-x-2">
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className={'btn-primary flex-1 btn-press'}
          >
            👁️ View Details
          </button>
        )}
        {onConfigure && (
          <button
            onClick={onConfigure}
            className={'btn-secondary flex-1 btn-press'}
          >
            ⚙️ Configure
          </button>
        )}
      </div>
    </div>
  );
};

