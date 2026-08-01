import React from 'react';
import { AlertsPanel } from '../AlertsPanel';
import { TabProps } from './types';

export const AlertsTab: React.FC<TabProps> = ({ darkMode }) => {
  return (
    <div className="space-y-6" data-testid="alert-list">
      <AlertsPanel darkMode={darkMode} />
    </div>
  );
};

