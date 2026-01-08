import React from 'react';
import { AlertsPanel } from '../AlertsPanel';
import { AnomalyAlertsPanel } from '../AnomalyAlertsPanel';
import { TabProps } from './types';

export const AlertsTab: React.FC<TabProps> = ({ darkMode }) => {
  return (
    <div className="space-y-6">
      {/* ML-Powered Anomaly Detection Alerts */}
      <AnomalyAlertsPanel 
        refreshInterval={30000}
        maxAlerts={10}
        minSeverity="low"
      />
      
      {/* Standard System Alerts */}
      <AlertsPanel darkMode={darkMode} />
    </div>
  );
};

