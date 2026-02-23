import React from 'react';
import { LogTailViewer } from '../LogTailViewer';
import { TabProps } from './types';

export const LogsTab: React.FC<TabProps> = ({ darkMode }) => {
  return <LogTailViewer darkMode={darkMode} />;
};

