import React, { useState } from 'react';

interface Alert {
  id: string;
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  timestamp: string;
  source?: string;
  resolved?: boolean;
}

interface AlertCenterProps {
  alerts: Alert[];
  darkMode: boolean;
  onDismissAlert: (alertId: string) => void;
  onResolveAlert: (alertId: string) => void;
  onClearAllAlerts: () => void;
}

export const AlertCenter: React.FC<AlertCenterProps> = ({
  alerts,
  darkMode,
  onDismissAlert,
  onResolveAlert,
  onClearAllAlerts
}) => {
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'severity'>('timestamp');

  const filteredAlerts = alerts
    .filter(alert => filter === 'all' || alert.severity === filter)
    .sort((a, b) => {
      if (sortBy === 'timestamp') {
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }
      const severityOrder = { error: 3, warning: 2, info: 1 };
      return severityOrder[b.severity] - severityOrder[a.severity];
    });

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error': return '🚨';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '📢';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return darkMode 
          ? 'bg-red-900/20 border-red-800 text-red-300' 
          : 'bg-red-50 border-red-200 text-red-800';
      case 'warning':
        return darkMode 
          ? 'bg-yellow-900/20 border-yellow-800 text-yellow-300' 
          : 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'info':
        return darkMode 
          ? 'bg-blue-900/20 border-blue-800 text-blue-300' 
          : 'bg-blue-50 border-blue-200 text-blue-800';
      default:
        return darkMode 
          ? 'bg-gray-800 border-gray-700 text-gray-300' 
          : 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const alertTime = new Date(timestamp);
    const diffMs = now.getTime() - alertTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border rounded-lg p-6 transition-colors duration-300`}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🚨 Alert Center
          </h2>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
            {alerts.length} total alerts • {alerts.filter(a => !a.resolved).length} active
          </p>
        </div>
        
        {alerts.length > 0 && (
          <button
            onClick={onClearAllAlerts}
            className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-red-600 hover:bg-red-700' : 'bg-red-100 hover:bg-red-200 text-red-800'} transition-colors duration-200`}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex space-x-2">
          {(['all', 'error', 'warning', 'info'] as const).map((filterType) => (
            <button
              key={filterType}
              onClick={() => setFilter(filterType)}
              className={`px-3 py-1 rounded-full text-sm transition-colors duration-200 ${
                filter === filterType
                  ? darkMode
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-100 text-blue-700'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filterType === 'all' ? 'All' : filterType.charAt(0).toUpperCase() + filterType.slice(1)}
              {filterType !== 'all' && (
                <span className="ml-1">
                  ({alerts.filter(a => a.severity === filterType).length})
                </span>
              )}
            </button>
          ))}
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'severity')}
          className={`px-3 py-1 rounded-lg text-sm ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'} border transition-colors duration-200`}
        >
          <option value="timestamp">Sort by Time</option>
          <option value="severity">Sort by Severity</option>
        </select>
      </div>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">✅</div>
          <h3 className={`text-lg font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'} mb-2`}>
            No {filter === 'all' ? '' : filter} alerts
          </h3>
          <p className={`text-sm ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
            {filter === 'all' 
              ? 'Your system is running smoothly!' 
              : `No ${filter} alerts found.`}
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-lg border transition-all duration-200 ${getSeverityColor(alert.severity)} ${
                alert.resolved ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <span className="text-xl flex-shrink-0 mt-0.5">
                    {getSeverityIcon(alert.severity)}
                  </span>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="font-medium truncate">
                        {alert.type}
                      </h4>
                      {alert.source && (
                        <span className={`text-xs px-2 py-1 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                          {alert.source}
                        </span>
                      )}
                    </div>
                    
                    <p className="text-sm opacity-90 mb-2">
                      {alert.message}
                    </p>
                    
                    <div className="flex items-center space-x-4 text-xs opacity-75">
                      <span>{getTimeAgo(alert.timestamp)}</span>
                      <span>
                        {new Date(alert.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {!alert.resolved && (
                    <button
                      onClick={() => onResolveAlert(alert.id)}
                      className={`px-2 py-1 rounded text-xs ${darkMode ? 'bg-green-600 hover:bg-green-700' : 'bg-green-100 hover:bg-green-200 text-green-800'} transition-colors duration-200`}
                      title="Mark as resolved"
                    >
                      ✓
                    </button>
                  )}
                  
                  <button
                    onClick={() => onDismissAlert(alert.id)}
                    className={`px-2 py-1 rounded text-xs ${darkMode ? 'bg-gray-600 hover:bg-gray-500' : 'bg-gray-100 hover:bg-gray-200'} transition-colors duration-200`}
                    title="Dismiss alert"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Alert Statistics */}
      {alerts.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className={`text-2xl font-bold ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
                {alerts.filter(a => a.severity === 'error').length}
              </div>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Errors
              </div>
            </div>
            <div>
              <div className={`text-2xl font-bold ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
                {alerts.filter(a => a.severity === 'warning').length}
              </div>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Warnings
              </div>
            </div>
            <div>
              <div className={`text-2xl font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                {alerts.filter(a => a.severity === 'info').length}
              </div>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Info
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

