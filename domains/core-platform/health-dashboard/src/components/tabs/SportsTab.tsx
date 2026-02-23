import React from 'react';
import { SportsTab as SportsTabComponent } from '../sports/SportsTab';
import { TabProps } from './types';

export const SportsTab: React.FC<TabProps> = ({ darkMode }) => {
  return <SportsTabComponent darkMode={darkMode} />;
};

