import React from 'react';
import { GroupsTab as GroupsTabComponent } from '../GroupsTab';
import { TabProps } from './types';

export const GroupsTab: React.FC<TabProps> = ({ darkMode }) => {
  return <GroupsTabComponent darkMode={darkMode} />;
};
