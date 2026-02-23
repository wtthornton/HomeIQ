/**
 * AlertsPanel Component (REFACTORED)
 * 
 * Alert management system with history, filtering, and configuration
 * Epic 13.3: Alert Management System
 * 
 * REFACTORING: Story 32.1
 * - Extracted helper functions to alertHelpers
 * - Created sub-components (AlertStats, AlertFilters, AlertCard)
 * - Reduced complexity from 44 to <15
 */

import React, { useState, useMemo } from 'react';
import { useAlerts } from '../hooks/useAlerts';
import { AlertStats } from './alerts/AlertStats';
import { AlertFilters } from './alerts/AlertFilters';
import { AlertCard } from './alerts/AlertCard';
import { AlertsLoadingState } from './alerts/AlertsLoadingState';
import { AlertsErrorState } from './alerts/AlertsErrorState';

interface AlertsPanelProps {
  darkMode: boolean;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ darkMode }): JSX.Element => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedService, setSelectedService] = useState<string>('all');
  const [showAcknowledged, setShowAcknowledged] = useState<boolean>(true);

  // Fetch alerts with real API
  const { 
    alerts, 
    summary, 
    loading, 
    error, 
    lastUpdate, 
    refresh, 
    acknowledgeAlert, 
    resolveAlert 
  } = useAlerts({
    pollInterval: 60000,
    autoRefresh: true
  });

  // Filter alerts based on selected criteria
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      if (selectedSeverity !== 'all' && alert.severity !== selectedSeverity) {
        return false;
      }
      if (selectedService !== 'all' && alert.service !== selectedService) {
        return false;
      }
      if (!showAcknowledged && alert.status === 'acknowledged') {
        return false;
      }
      return true;
    });
  }, [alerts, selectedSeverity, selectedService, showAcknowledged]);

  // Get unique services for filter dropdown
  const services = useMemo(() => {
    return [...new Set(alerts.map((a) => a.service))];
  }, [alerts]);

  // Calculate alert counts
  const criticalCount = summary?.critical || 
    alerts.filter((a) => a.severity === 'critical' && a.status === 'active').length;
  const warningCount = summary?.warning || 
    alerts.filter((a) => a.severity === 'warning' && a.status === 'active').length;
  const errorCount = alerts.filter((a) => a.severity === 'warning' && a.status !== 'resolved').length;

  // Handle acknowledge action
  const handleAcknowledge = async (alertId: string): Promise<void> => {
    await acknowledgeAlert(alertId);
  };

  // Handle resolve action
  const handleResolve = async (alertId: string): Promise<void> => {
    await resolveAlert(alertId);
  };

  // Handle loading and error states
  if (loading) return <AlertsLoadingState darkMode={darkMode} />;
  if (error) return <AlertsErrorState message={error} onRetry={refresh} darkMode={darkMode} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              🚨 Alert Management
            </h2>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Last updated: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
            </p>
          </div>
          <button
            onClick={refresh}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            Refresh
          </button>
        </div>

        {/* Statistics */}
        <AlertStats
          criticalCount={criticalCount}
          warningCount={warningCount}
          errorCount={errorCount}
          totalCount={alerts.length}
          darkMode={darkMode}
        />

        {/* Filters */}
        <AlertFilters
          selectedSeverity={selectedSeverity}
          selectedService={selectedService}
          showAcknowledged={showAcknowledged}
          services={services}
          onSeverityChange={setSelectedSeverity}
          onServiceChange={setSelectedService}
          onShowAcknowledgedChange={setShowAcknowledged}
          darkMode={darkMode}
        />
      </div>

      {/* Alerts List */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Alerts ({filteredAlerts.length})
        </h3>

        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8">
            <p className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              No alerts match the current filters
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
                darkMode={darkMode}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

