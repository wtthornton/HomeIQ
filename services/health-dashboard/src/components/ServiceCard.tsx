import React from 'react';
import type { ServiceStatus } from '../types';

interface ServiceCardProps {
  service: ServiceStatus;
  icon: string;
  darkMode: boolean;
  onViewDetails?: () => void;
  onConfigure?: () => void;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({
  service,
  icon,
  darkMode,
  onViewDetails,
  onConfigure,
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
              {service.metrics.requests_per_minute.toFixed(1)}
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
              {service.metrics.error_rate.toFixed(2)}%
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

      {/* Actions */}
      <div className="flex space-x-2">
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className={`btn-primary flex-1 btn-press`}
          >
            👁️ View Details
          </button>
        )}
        {onConfigure && (
          <button
            onClick={onConfigure}
            className={`btn-secondary flex-1 btn-press`}
          >
            ⚙️ Configure
          </button>
        )}
      </div>
    </div>
  );
};

