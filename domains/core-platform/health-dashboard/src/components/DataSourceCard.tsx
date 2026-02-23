import React, { useState, useEffect } from 'react';

interface DataSourceCardProps {
  title: string;
  icon: string;
  status: 'healthy' | 'degraded' | 'offline';
  value: string | number;
  subtitle: string;
  successRate?: number;
  lastFetch?: string | null;
  darkMode?: boolean;
}

export const DataSourceCard: React.FC<DataSourceCardProps> = ({
  title,
  icon,
  status,
  value,
  subtitle,
  successRate,
  lastFetch,
  darkMode = false
}) => {
  const [displayValue, setDisplayValue] = useState(value);

  // Number counting animation for numeric values
  useEffect(() => {
    if (typeof value === 'number' && typeof displayValue === 'number' && value !== displayValue) {
      const duration = 500;
      const steps = 20;
      const stepValue = (value - displayValue) / steps;
      let currentStep = 0;

      const timer = setInterval(() => {
        currentStep++;
        if (currentStep === steps) {
          setDisplayValue(value);
          clearInterval(timer);
        } else {
          setDisplayValue(prev => typeof prev === 'number' ? prev + stepValue : value);
        }
      }, duration / steps);

      return () => clearInterval(timer);
    } else if (value !== displayValue) {
      setDisplayValue(value);
    }
  }, [value, displayValue]);

  const getBadgeClass = (statusType: string) => {
    switch (statusType) {
      case 'healthy':
        return 'badge-success';
      case 'degraded':
        return 'badge-warning';
      case 'offline':
        return 'badge-error';
      default:
        return 'badge-info';
    }
  };

  return (
    <div className={`card-base card-hover content-fade-in ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-l-4 ${
      status === 'healthy' ? 'border-l-green-500' : status === 'degraded' ? 'border-l-yellow-500' : 'border-l-red-500'
    }`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl icon-entrance">{icon}</span>
            <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{title}</h3>
          </div>
          <p className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} number-counter`}>
            {typeof displayValue === 'number' ? Math.round(displayValue).toLocaleString() : displayValue}
          </p>
          <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{subtitle}</p>
        </div>
        <div>
          <span className={`badge-base status-transition ${getBadgeClass(status)} ${status === 'healthy' ? 'live-pulse' : ''}`}>
            {status === 'healthy' && <span className="live-pulse-dot mr-1">🟢</span>}
            {status}
          </span>
        </div>
      </div>
      
      {successRate !== undefined && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">Success Rate</span>
            <span className={`font-semibold ${successRate >= 0.95 ? 'text-green-600' : 'text-yellow-600'}`}>
              {((successRate ?? 0) * 100).toFixed(1)}%
            </span>
          </div>
          {lastFetch && (
            <div className="flex justify-between items-center text-xs text-gray-500 mt-2">
              <span>Last Update</span>
              <span>{new Date(lastFetch).toLocaleTimeString()}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

