import React from 'react';

interface APIKeyManagementProps {
  darkMode: boolean;
}

export const APIKeyManagement: React.FC<APIKeyManagementProps> = ({ darkMode }) => {
  return (
    <div className="space-y-6">
      <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
        <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🔑 API Key Management
        </h3>
        <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          API key management interface will be available in a future update.
        </p>
        <p className={`mt-2 text-sm ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Configure API keys through the Configuration tab for each service.
        </p>
      </div>
    </div>
  );
};

