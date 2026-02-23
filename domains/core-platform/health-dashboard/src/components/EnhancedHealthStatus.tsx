/**
 * Enhanced Health Status Component
 * Epic 17.2: Enhanced Service Health Monitoring
 * 
 * Displays detailed service health with dependency status
 */

import React from 'react';
import {
  ServiceHealthResponse,
  DependencyHealth,
  getStatusColor,
  getStatusIcon,
  getDependencyTypeIcon,
  formatResponseTime,
  formatUptime
} from '../types/health';

interface EnhancedHealthStatusProps {
  health: ServiceHealthResponse;
  darkMode: boolean;
}

export const EnhancedHealthStatus: React.FC<EnhancedHealthStatusProps> = ({ health, darkMode }) => {
  const statusColor = getStatusColor(health.status, darkMode);
  const statusIcon = getStatusIcon(health.status);

  return (
    <div className={`card-base p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
      {/* Service Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{statusIcon}</span>
          <div>
            <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {health.service}
            </h3>
            <span className={`badge-base ${statusColor} text-xs px-2 py-0.5`}>
              {health.status.toUpperCase()}
            </span>
          </div>
        </div>
        
        {health.uptime_seconds !== undefined && (
          <div className={`text-right ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div className="text-xs">Uptime</div>
            <div className="text-sm font-semibold">
              {formatUptime(health.uptime_seconds)}
            </div>
          </div>
        )}
      </div>

      {/* Metrics Summary */}
      {health.metrics && (
        <div className={`grid grid-cols-2 gap-3 mb-4 p-3 rounded ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
          {health.metrics.uptime_human && (
            <div>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Uptime
              </div>
              <div className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {health.metrics.uptime_human}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Dependencies */}
      {health.dependencies && health.dependencies.length > 0 && (
        <div>
          <h4 className={`text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Dependencies ({health.dependencies.length})
          </h4>
          <div className="space-y-2">
            {health.dependencies.map((dep, index) => (
              <DependencyCard key={index} dependency={dep} darkMode={darkMode} />
            ))}
          </div>
        </div>
      )}

      {/* Timestamp */}
      <div className={`mt-4 text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        Last checked: {new Date(health.timestamp).toLocaleString()}
      </div>
    </div>
  );
};

interface DependencyCardProps {
  dependency: DependencyHealth;
  darkMode: boolean;
}

const DependencyCard: React.FC<DependencyCardProps> = ({ dependency, darkMode }) => {
  const statusColor = getStatusColor(dependency.status, darkMode);
  const statusIcon = getStatusIcon(dependency.status);
  const typeIcon = getDependencyTypeIcon(dependency.type);

  return (
    <div className={`p-3 rounded border ${darkMode ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-gray-50'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <span className="text-lg">{typeIcon}</span>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className={`font-medium text-sm ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {dependency.name}
              </span>
              <span className={`badge-base ${statusColor} text-xs px-2 py-0.5`}>
                {statusIcon} {dependency.status}
              </span>
            </div>
            <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {dependency.type}
            </div>
          </div>
        </div>

        {dependency.response_time_ms !== undefined && (
          <div className={`text-right ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <div className="text-xs">Response</div>
            <div className="text-sm font-mono">
              {formatResponseTime(dependency.response_time_ms)}
            </div>
          </div>
        )}
      </div>

      {dependency.error_message && (
        <div className={`mt-2 text-xs ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
          {dependency.error_message}
        </div>
      )}
    </div>
  );
};

export default EnhancedHealthStatus;

