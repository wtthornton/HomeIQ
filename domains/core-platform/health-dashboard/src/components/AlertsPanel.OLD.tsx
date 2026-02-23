/**
 * AlertsPanel Component
 * 
 * Alert management system with history, filtering, and configuration
 * Epic 13.3: Alert Management System
 */

import React, { useState, useMemo } from 'react';
import type { Alert } from '../types/alerts';
import { useAlerts } from '../hooks/useAlerts';
import { SkeletonCard, SkeletonList } from './skeletons';

interface AlertsPanelProps {
  darkMode: boolean;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ darkMode }) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedService, setSelectedService] = useState<string>('all');
  const [showAcknowledged, setShowAcknowledged] = useState(true);

  // Fetch alerts with real API
  const { alerts, summary, loading, error, lastUpdate, refresh, acknowledgeAlert, resolveAlert } = useAlerts({
    pollInterval: 60000,
    autoRefresh: true
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return darkMode ? 'text-red-400 bg-red-900/30 border-red-500/50' : 'text-red-700 bg-red-50 border-red-200';
      case 'error':
        return darkMode ? 'text-red-300 bg-red-900/20 border-red-500/30' : 'text-red-600 bg-red-50 border-red-200';
      case 'warning':
        return darkMode ? 'text-yellow-300 bg-yellow-900/20 border-yellow-500/30' : 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'info':
        return darkMode ? 'text-blue-300 bg-blue-900/20 border-blue-500/30' : 'text-blue-700 bg-blue-50 border-blue-200';
      default:
        return darkMode ? 'text-gray-300 bg-gray-800 border-gray-600' : 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '🔴';
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'info':
        return 'ℹ️';
      default:
        return '•';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffHours < 1) {
      return `${diffMins} minutes ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hours ago`;
    } else {
      return `${date.toLocaleDateString()  } ${  date.toLocaleTimeString()}`;
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    await acknowledgeAlert(alertId);
  };

  const handleResolve = async (alertId: string) => {
    await resolveAlert(alertId);
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      if (selectedSeverity !== 'all' && alert.severity !== selectedSeverity) return false;
      if (selectedService !== 'all' && alert.service !== selectedService) return false;
      if (!showAcknowledged && alert.status === 'acknowledged') return false;
      return true;
    });
  }, [alerts, selectedSeverity, selectedService, showAcknowledged]);

  const services = useMemo(() => [...new Set(alerts.map(a => a.service))], [alerts]);
  
  const criticalCount = summary?.critical || alerts.filter(a => a.severity === 'critical' && a.status === 'active').length;
  const warningCount = summary?.warning || alerts.filter(a => a.severity === 'warning' && a.status === 'active').length;
  const errorCount = alerts.filter(a => a.severity === 'warning' && a.status !== 'resolved').length; // Using warning for error count since API doesn't have 'error' severity

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-4 shimmer"></div>
          <div className="flex gap-4 mb-6">
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32 shimmer"></div>
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32 shimmer"></div>
          </div>
        </div>
        {/* Alerts List Skeleton */}
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <SkeletonList count={5} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border border-red-200'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <h3 className={`font-semibold ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
              Error Loading Alerts
            </h3>
            <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
              {error}
            </p>
          </div>
          <button
            onClick={refresh}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Status Summary */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} flex items-center gap-2`}>
              <span>🚨</span>
              System Alerts & Notifications
            </h2>
            <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Monitor and manage system alerts and notifications
            </p>
          </div>
          <div className={`text-right ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <p className="text-sm">Last updated</p>
            <p className="text-sm font-medium">{lastUpdate?.toLocaleTimeString() || 'Never'}</p>
          </div>
        </div>

        {/* Status Banner */}
        {criticalCount === 0 && errorCount === 0 ? (
          <div className={`flex items-center gap-3 p-4 rounded-lg ${
            darkMode ? 'bg-green-900/20 border border-green-500/30' : 'bg-green-50 border border-green-200'
          }`}>
            <span className="text-2xl">✅</span>
            <div className={darkMode ? 'text-green-200' : 'text-green-800'}>
              <p className="font-semibold">No Critical Alerts</p>
              <p className="text-sm">System is healthy and operating normally</p>
            </div>
          </div>
        ) : (
          <div className={`flex items-center gap-3 p-4 rounded-lg ${
            darkMode ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border border-red-200'
          }`}>
            <span className="text-2xl">⚠️</span>
            <div className={darkMode ? 'text-red-200' : 'text-red-800'}>
              <p className="font-semibold">Active Alerts Require Attention</p>
              <p className="text-sm">
                {criticalCount} critical, {errorCount} errors, {warningCount} warnings
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Severity:
            </label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              aria-label="Filter alerts by severity level"
              className={`px-3 py-2 rounded-lg border ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
              } transition-colors`}
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Service:
            </label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              aria-label="Filter alerts by service"
              className={`px-3 py-2 rounded-lg border ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
              } transition-colors`}
            >
              <option value="all">All Services</option>
              {services.map(service => (
                <option key={service} value={service}>{service}</option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showAcknowledged}
              onChange={(e) => setShowAcknowledged(e.target.checked)}
              className="w-4 h-4 rounded"
              aria-label="Toggle display of acknowledged alerts"
            />
            <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Show acknowledged
            </span>
          </label>

          <div className="ml-auto">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {filteredAlerts.length} of {alerts.length} alerts
            </span>
          </div>
        </div>
      </div>

      {/* Alert List */}
      <div className="space-y-3">
        {filteredAlerts.length === 0 ? (
          <div className={`rounded-lg shadow-md p-12 text-center ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="text-6xl mb-4">🎉</div>
            <h3 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'} mb-2`}>
              No Alerts Found
            </h3>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {selectedSeverity !== 'all' || selectedService !== 'all'
                ? 'Try adjusting your filters'
                : 'Everything is running smoothly!'}
            </p>
          </div>
        ) : (
          filteredAlerts.map(alert => (
            <div
              key={alert.id}
              className={`rounded-lg shadow-md p-6 border ${getSeverityColor(alert.severity)} ${
                alert.status === 'acknowledged' || alert.status === 'resolved' ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <span className="text-2xl">{getSeverityIcon(alert.severity)}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {alert.name}
                      </h3>
                      <span className={`text-xs px-2 py-1 rounded uppercase ${
                        darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                      }`}>
                        {alert.severity}
                      </span>
                      {alert.status !== 'active' && (
                        <span className={`text-xs px-2 py-1 rounded uppercase ${
                          alert.status === 'resolved' 
                            ? (darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700')
                            : (darkMode ? 'bg-yellow-900/30 text-yellow-300' : 'bg-yellow-100 text-yellow-700')
                        }`}>
                          {alert.status}
                        </span>
                      )}
                    </div>
                    <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>
                      {alert.message}
                    </p>
                    <div className={`flex items-center gap-4 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      <span>🏷️ {alert.service}</span>
                      {alert.created_at && <span>🕐 {formatTimestamp(alert.created_at)}</span>}
                      {alert.metric && <span>📊 {alert.metric}</span>}
                      {alert.status === 'acknowledged' && alert.acknowledged_at && (
                        <span className="text-green-500">
                          ✓ Acknowledged {formatTimestamp(alert.acknowledged_at)}
                        </span>
                      )}
                      {alert.status === 'resolved' && alert.resolved_at && (
                        <span className="text-blue-500">
                          ✓ Resolved {formatTimestamp(alert.resolved_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {alert.status === 'active' && (
                    <>
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        aria-label={`Acknowledge alert: ${alert.name}`}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                          darkMode
                            ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                            : 'bg-yellow-500 hover:bg-yellow-600 text-white'
                        }`}
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => handleResolve(alert.id)}
                        aria-label={`Resolve alert: ${alert.name}`}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                          darkMode
                            ? 'bg-green-600 hover:bg-green-700 text-white'
                            : 'bg-green-500 hover:bg-green-600 text-white'
                        }`}
                      >
                        Resolve
                      </button>
                    </>
                  )}
                  {alert.status === 'acknowledged' && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      aria-label={`Resolve alert: ${alert.name}`}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                        darkMode
                          ? 'bg-green-600 hover:bg-green-700 text-white'
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      }`}
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Alert Configuration */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          📋 Alert Configuration
        </h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className={`font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Email Notifications
              </p>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Receive email alerts for critical events
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className={`font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Error Rate Threshold
              </p>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Alert when error rate exceeds 5%
              </p>
            </div>
            <input
              type="number"
              defaultValue={5}
              min={1}
              max={100}
              className={`w-20 px-3 py-2 rounded-lg border ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
              }`}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className={`font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Check Interval
              </p>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                How often to check for alerts
              </p>
            </div>
            <select
              defaultValue={30}
              className={`px-3 py-2 rounded-lg border ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value={10}>10 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>1 minute</option>
              <option value={300}>5 minutes</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

