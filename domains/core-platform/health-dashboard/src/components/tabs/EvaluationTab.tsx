import React from 'react';
import { AgentEvaluationTab } from '../evaluation/AgentEvaluationTab';
import { TabProps } from './types';

export const EvaluationTab: React.FC<TabProps> = ({ darkMode }) => {
  return <AgentEvaluationTab darkMode={darkMode} />;
};
