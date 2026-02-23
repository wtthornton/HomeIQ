import React from 'react';
import { AnalyticsPanel } from '../AnalyticsPanel';
import { TabProps } from './types';

export const AnalyticsTab: React.FC<TabProps> = ({ darkMode }) => {
  return <AnalyticsPanel darkMode={darkMode} />;
};

