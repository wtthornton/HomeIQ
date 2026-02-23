import React from 'react';

interface ContainerManagementProps {
  darkMode: boolean;
}

export const ContainerManagement: React.FC<ContainerManagementProps> = ({ darkMode }) => {
  return (
    <div className="space-y-6">
      <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
        <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🐳 Container Management
        </h3>
        <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Container management interface will be available in a future update.
        </p>
        <p className={`mt-2 text-sm ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Use the Services tab to view and manage running containers.
        </p>
      </div>
    </div>
  );
};

