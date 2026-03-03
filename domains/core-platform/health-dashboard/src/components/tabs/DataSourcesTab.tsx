import React from 'react';
import { DataSourcesPanel } from '../DataSourcesPanel';
import { TabProps } from './types';

export const DataSourcesTab: React.FC<TabProps> = ({ darkMode }) => {
  return (
    <div data-testid="data-source">
      <DataSourcesPanel darkMode={darkMode} />
    </div>
  );
};

