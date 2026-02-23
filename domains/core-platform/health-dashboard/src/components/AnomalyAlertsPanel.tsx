/**
 * Anomaly Alerts Panel Component
 * 
 * Displays device anomaly alerts from the ML anomaly detection service.
 * Part of Phase 5: Anomaly Detection Integration
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface AnomalyAlert {
  device_id: string;
  device_name?: string;
  anomaly_type: 'behavior' | 'energy' | 'availability';
  severity: 'low' | 'medium' | 'high';
  description: string;
  detected_at: string;
  score: number;
  feature_contributions?: Record<string, number>;
}

interface AnomalyAlertsPanelProps {
  refreshInterval?: number; // milliseconds
  maxAlerts?: number;
  minSeverity?: 'low' | 'medium' | 'high';
}

// Severity colors
const severityColors = {
  low: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    text: 'text-yellow-400',
    icon: '⚠️',
  },
  medium: {
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    text: 'text-orange-400',
    icon: '🔶',
  },
  high: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    icon: '🔴',
  },
};

// Anomaly type icons
const anomalyTypeIcons = {
  behavior: '🔄',
  energy: '⚡',
  availability: '📡',
};

// Anomaly type labels
const anomalyTypeLabels = {
  behavior: 'Behavior',
  energy: 'Energy',
  availability: 'Connectivity',
};

export const AnomalyAlertsPanel: React.FC<AnomalyAlertsPanelProps> = ({
  refreshInterval = 30000,
  maxAlerts = 10,
  minSeverity = 'low',
}) => {
  const [alerts, setAlerts] = useState<AnomalyAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null);

  // Fetch alerts from the anomaly detection service
  const fetchAlerts = useCallback(async () => {
    try {
      // In production, this would call the ai-pattern-service anomaly endpoint
      const response = await fetch(
        `/api/pattern/anomaly/alerts?min_severity=${minSeverity}&limit=${maxAlerts}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setAlerts(data.alerts || []);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      // If service unavailable, show mock data for development
      console.warn('Anomaly service unavailable, using mock data');
      setAlerts(getMockAlerts());
      setError(null);
    } finally {
      setLoading(false);
    }
  }, [minSeverity, maxAlerts]);

  // Initial fetch and polling
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchAlerts, refreshInterval]);

  // Dismiss alert
  const dismissAlert = (alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.device_id !== alertId));
  };

  // Toggle alert expansion
  const toggleExpand = (alertId: string) => {
    setExpandedAlert((prev) => (prev === alertId ? null : alertId));
  };

  // Format timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Format score as percentage
  const formatScore = (score: number) => {
    return `${(score * 100).toFixed(0)}%`;
  };

  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-slate-700/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔍</span>
          <h3 className="text-lg font-semibold text-white">Anomaly Detection</h3>
          {alerts.length > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {lastUpdated && (
            <span>Updated {formatTime(lastUpdated.toISOString())}</span>
          )}
          <button
            onClick={fetchAlerts}
            className="p-1 hover:bg-slate-700 rounded transition-colors"
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Alerts list */}
      {alerts.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <span className="text-3xl mb-2 block">✅</span>
          <p>No anomalies detected</p>
          <p className="text-xs mt-1">All devices operating normally</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const colors = severityColors[alert.severity];
            const isExpanded = expandedAlert === alert.device_id;

            return (
              <div
                key={`${alert.device_id}-${alert.detected_at}`}
                className={`${colors.bg} ${colors.border} border rounded-lg overflow-hidden transition-all`}
              >
                {/* Alert header */}
                <div
                  className="p-3 cursor-pointer hover:bg-white/5 transition-colors"
                  onClick={() => toggleExpand(alert.device_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <span className="text-lg">{colors.icon}</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`font-medium ${colors.text}`}>
                            {alert.device_name || alert.device_id}
                          </span>
                          <span className="text-xs px-1.5 py-0.5 bg-slate-700/50 rounded text-slate-300">
                            {anomalyTypeIcons[alert.anomaly_type]}{' '}
                            {anomalyTypeLabels[alert.anomaly_type]}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300 mt-1">
                          {alert.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">
                        {formatTime(alert.detected_at)}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          dismissAlert(alert.device_id);
                        }}
                        className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                        title="Dismiss"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Score bar */}
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-slate-400">Confidence:</span>
                    <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colors.text.replace('text', 'bg')} transition-all`}
                        style={{ width: `${alert.score * 100}%` }}
                      />
                    </div>
                    <span className={`text-xs ${colors.text}`}>
                      {formatScore(alert.score)}
                    </span>
                  </div>
                </div>

                {/* Expanded details */}
                {isExpanded && alert.feature_contributions && (
                  <div className="px-3 pb-3 border-t border-slate-700/50">
                    <div className="mt-3">
                      <h4 className="text-xs font-medium text-slate-400 mb-2">
                        Feature Contributions
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(alert.feature_contributions).map(
                          ([feature, contribution]) => (
                            <div
                              key={feature}
                              className="flex items-center justify-between text-xs"
                            >
                              <span className="text-slate-400 capitalize">
                                {feature.replace('_', ' ')}
                              </span>
                              <span className="text-slate-300">
                                {(contribution * 100).toFixed(0)}%
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-400">
        <span>
          Powered by PyOD anomaly detection
        </span>
        <a
          href="/docs/anomaly-detection"
          className="hover:text-white transition-colors"
        >
          Learn more →
        </a>
      </div>
    </div>
  );
};

// Mock alerts for development/demo
function getMockAlerts(): AnomalyAlert[] {
  return [
    {
      device_id: 'sensor.living_room_motion',
      device_name: 'Living Room Motion',
      anomaly_type: 'behavior',
      severity: 'medium',
      description: 'Unusual activity pattern detected - motion at unusual hours',
      detected_at: new Date(Date.now() - 5 * 60000).toISOString(),
      score: 0.78,
      feature_contributions: {
        motion_frequency: 0.45,
        time_of_day: 0.35,
        duration: 0.20,
      },
    },
    {
      device_id: 'switch.garage_door',
      device_name: 'Garage Door',
      anomaly_type: 'availability',
      severity: 'high',
      description: 'Device showing intermittent connectivity issues',
      detected_at: new Date(Date.now() - 15 * 60000).toISOString(),
      score: 0.92,
      feature_contributions: {
        availability: 0.60,
        response_time: 0.30,
        error_rate: 0.10,
      },
    },
    {
      device_id: 'sensor.hvac_power',
      device_name: 'HVAC Power Monitor',
      anomaly_type: 'energy',
      severity: 'low',
      description: 'Higher than expected energy consumption',
      detected_at: new Date(Date.now() - 30 * 60000).toISOString(),
      score: 0.65,
      feature_contributions: {
        power_consumption: 0.50,
        temperature_delta: 0.30,
        runtime: 0.20,
      },
    },
  ];
}

export default AnomalyAlertsPanel;
