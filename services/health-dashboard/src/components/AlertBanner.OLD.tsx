/**
 * Alert Banner Component
 * Epic 17.4: Critical Alerting System
 * 
 * Displays active critical alerts. Stale alerts are automatically cleaned up by the backend.
 */

import React, { useState, useEffect } from 'react';
import { Alert, AlertSeverity } from '../constants/alerts';
import { withCsrfHeader } from '../utils/security';

interface AlertBannerProps {
  darkMode: boolean;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ darkMode }): JSX.Element => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch active alerts
  useEffect(() => {
    const fetchAlerts = async (): Promise<void> => {
      try {
        const response = await fetch('/api/v1/alerts/active');
        if (response.ok) {
          const data = await response.json();
          setAlerts(data);
        }
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000); // Refresh every 10s

    return () => clearInterval(interval);
  }, []);

  // Handle alert acknowledgment
  const acknowledgeAlert = async (alertId: string): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: withCsrfHeader()
      });
      
      if (response.ok) {
        setAlerts(prev => prev.filter(a => a.id !== alertId));
      }
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  // Handle alert resolution
  const resolveAlert = async (alertId: string): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: withCsrfHeader()
      });
      
      if (response.ok) {
        setAlerts(prev => prev.filter(a => a.id !== alertId));
      }
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  // Get severity styling
  const getSeverityStyle = (severity: AlertSeverity): string => {
    const styles = {
      [AlertSeverity.CRITICAL]: darkMode 
        ? 'bg-red-900/50 border-red-500 text-red-200' 
        : 'bg-red-50 border-red-500 text-red-900',
      [AlertSeverity.WARNING]: darkMode 
        ? 'bg-yellow-900/50 border-yellow-500 text-yellow-200' 
        : 'bg-yellow-50 border-yellow-500 text-yellow-900',
      [AlertSeverity.INFO]: darkMode 
        ? 'bg-blue-900/50 border-blue-500 text-blue-200' 
        : 'bg-blue-50 border-blue-500 text-blue-900'
    };
    
    return styles[severity] || styles[AlertSeverity.INFO];
  };

  // Get severity icon
  const getSeverityIcon = (severity: AlertSeverity): string => {
    const icons = {
      [AlertSeverity.CRITICAL]: '🚨',
      [AlertSeverity.WARNING]: '⚠️',
      [AlertSeverity.INFO]: 'ℹ️'
    };
    
    return icons[severity] || 'ℹ️';
  };


  if (loading || alerts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 mb-6">
      {alerts.map(alert => (
        <div
          key={alert.id}
          className={`border-l-4 p-4 rounded-lg ${getSeverityStyle(alert.severity)} shadow-sm`}
          role="alert"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <span className="text-2xl mt-0.5">{getSeverityIcon(alert.severity)}</span>
              
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm uppercase tracking-wide">
                    {alert.severity}
                  </span>
                  <span className="text-xs opacity-75">•</span>
                  <span className="text-xs opacity-75">
                    {alert.service}
                  </span>
                  {alert.metric && (
                    <>
                      <span className="text-xs opacity-75">•</span>
                      <span className="text-xs opacity-75 font-mono">
                        {alert.metric}
                      </span>
                    </>
                  )}
                </div>
                
                <p className="font-medium mb-1">{alert.message}</p>
                
                <div className="text-xs opacity-75 flex items-center gap-3">
                  {alert.created_at && (
                    <span>
                      Triggered: {new Date(alert.created_at).toLocaleString()}
                    </span>
                  )}
                  {alert.current_value !== undefined && (
                    <span>
                      Current: {(alert.current_value ?? 0).toFixed(1)}
                      {alert.threshold_value !== undefined && ` (threshold: ${alert.threshold_value})`}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-2 flex-shrink-0">
              <button
                onClick={() => acknowledgeAlert(alert.id)}
                className={`px-3 py-1 text-xs rounded transition-colors min-h-[32px] ${
                  darkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
                title="Acknowledge alert"
              >
                ✓ Ack
              </button>
              
              <button
                onClick={() => resolveAlert(alert.id)}
                className={`px-3 py-1 text-xs rounded transition-colors min-h-[32px] ${
                  darkMode
                    ? 'bg-green-700 hover:bg-green-600 text-white'
                    : 'bg-green-100 hover:bg-green-200 text-green-700'
                }`}
                title="Resolve alert"
              >
                ✓ Resolve
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AlertBanner;

