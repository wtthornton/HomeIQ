/**
 * AlertCard Component
 * 
 * Display a single alert with actions
 */

import React from 'react';
import { Alert } from '../../types/alerts';
import { getSeverityColor, getSeverityIcon, formatTimestamp } from '../../utils/alertHelpers';

interface AlertCardProps {
  alert: Alert;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
  darkMode: boolean;
}

export const AlertCard: React.FC<AlertCardProps> = ({
  alert,
  onAcknowledge,
  onResolve,
  darkMode
}): JSX.Element => {
  const colorClass = getSeverityColor(alert.severity, darkMode);
  const icon = getSeverityIcon(alert.severity);

  return (
    <div className={`rounded-lg border p-4 ${colorClass}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{icon}</span>
            <h4 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {alert.message}
            </h4>
          </div>
          
          <div className={`text-sm mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            <p>Service: {alert.service}</p>
            <p>Time: {alert.created_at ? formatTimestamp(alert.created_at) : 'Unknown'}</p>
            {alert.metadata && <p className="mt-1">Details: {JSON.stringify(alert.metadata)}</p>}
          </div>
        </div>

        <div className="flex gap-2">
          {alert.status === 'active' && (
            <>
              <button
                onClick={() => onAcknowledge(alert.id)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                Acknowledge
              </button>
              <button
                onClick={() => onResolve(alert.id)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  darkMode
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                Resolve
              </button>
            </>
          )}
          
          {alert.status === 'acknowledged' && (
            <button
              onClick={() => onResolve(alert.id)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              Resolve
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

