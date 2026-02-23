import React from 'react';
import { ServicesTab as ServicesTabComponent } from '../ServicesTab';
import { TabProps } from './types';

export const ServicesTab: React.FC<TabProps> = ({ darkMode }) => {
  return <ServicesTabComponent darkMode={darkMode} />;
};

