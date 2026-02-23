/**
 * EvalAlertBanner — Alert banner for evaluation threshold violations
 * E4.S4/E4.S6: Shows active alerts with count badge and acknowledgement
 */

import React from 'react';
import { AlertCircle, AlertTriangle } from 'lucide-react';

export interface EvalAlertData {
  alert_id: string;
  agent_name: string;
  evaluator_name: string;
  level: string;
  metric: string;
  threshold: number;
  actual_score: number;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
  acknowledged_by?: string | null;
  note?: string | null;
}

interface EvalAlertBannerProps {
  alerts: EvalAlertData[];
  onAcknowledge?: (alertId: string) => void;
  darkMode: boolean;
}

export const EvalAlertBanner: React.FC<EvalAlertBannerProps> = ({
  alerts,
  onAcknowledge,
  darkMode,
}) => {
  const activeAlerts = alerts.filter(a => a.status === 'active');
  const acknowledgedAlerts = alerts.filter(a => a.status === 'acknowledged');

  if (activeAlerts.length === 0 && acknowledgedAlerts.length === 0) {
    return null;
  }

  const criticalCount = activeAlerts.filter(a => a.priority === 'critical').length;

  return (
    <div className={`rounded-lg border p-4 mb-6 ${
      criticalCount > 0
        ? 'border-red-500/50 bg-red-500/10'
        : 'border-yellow-500/50 bg-yellow-500/10'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {criticalCount > 0
            ? <AlertCircle className="w-5 h-5 text-red-500" />
            : <AlertTriangle className="w-5 h-5 text-yellow-500" />
          }
          <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Evaluation Alerts
          </h3>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            criticalCount > 0
              ? 'bg-red-500 text-white'
              : 'bg-yellow-500 text-white'
          }`}>
            {activeAlerts.length} active
          </span>
          {acknowledgedAlerts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500 text-white">
              {acknowledgedAlerts.length} ack'd
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {activeAlerts.map(alert => (
          <div
            key={alert.alert_id}
            className={`flex items-center justify-between p-2 rounded ${
              darkMode ? 'bg-gray-800/50' : 'bg-white/50'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                alert.priority === 'critical'
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-yellow-500/20 text-yellow-600'
              }`}>
                {alert.priority.toUpperCase()}
              </span>
              <span className={`text-xs font-mono ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                {alert.level}
              </span>
              <span className={`text-sm ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                {alert.metric}
              </span>
              <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                {alert.actual_score.toFixed(2)} / {alert.threshold.toFixed(2)}
              </span>
            </div>
            {onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.alert_id)}
                className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
              >
                Acknowledge
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
