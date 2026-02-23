import React, { useState } from 'react';
import { ThresholdConfig } from '../ThresholdConfig';
import { ServiceControl } from '../ServiceControl';
import { ConfigForm } from '../ConfigForm';
import { ContainerManagement } from '../ContainerManagement';
import { APIKeyManagement } from '../APIKeyManagement';
import { TabProps } from './types';

type ConfigView = 'main' | 'websocket' | 'weather' | 'influxdb' | 'containers' | 'api-keys';

export const ConfigurationTab: React.FC<TabProps> = ({ darkMode }) => {
  const [configView, setConfigView] = useState<ConfigView>('main');

  if (configView === 'websocket') {
    return (
      <div>
        <button
          onClick={() => setConfigView('main')}
          className="mb-4 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          ← Back to Configuration
        </button>
        <ConfigForm service="websocket" onSave={() => {}} />
      </div>
    );
  }

  if (configView === 'weather') {
    return (
      <div>
        <button
          onClick={() => setConfigView('main')}
          className="mb-4 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          ← Back to Configuration
        </button>
        <ConfigForm service="weather" onSave={() => {}} />
      </div>
    );
  }

  if (configView === 'influxdb') {
    return (
      <div>
        <button
          onClick={() => setConfigView('main')}
          className="mb-4 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          ← Back to Configuration
        </button>
        <ConfigForm service="influxdb" onSave={() => {}} />
      </div>
    );
  }

  if (configView === 'containers') {
    return (
      <div>
        <button
          onClick={() => setConfigView('main')}
          className="mb-4 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          ← Back to Configuration
        </button>
        <ContainerManagement darkMode={darkMode} />
      </div>
    );
  }

  if (configView === 'api-keys') {
    return (
      <div>
        <button
          onClick={() => setConfigView('main')}
          className="mb-4 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          ← Back to Configuration
        </button>
        <APIKeyManagement darkMode={darkMode} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Preferences & Thresholds */}
      <ThresholdConfig darkMode={darkMode} onSave={(prefs) => console.log('Preferences saved:', prefs)} />
      
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          ⚙️ Integration Configuration
        </h2>
        <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} mb-6`}>
          Manage external API credentials and service settings
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <button
            onClick={() => setConfigView('containers')}
            className="bg-green-50 dark:bg-green-900 p-6 rounded-lg hover:shadow-lg transition-shadow duration-200 text-left"
          >
            <div className="text-4xl mb-2">🐳</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Container Management</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Start, stop, restart containers</p>
          </button>
          
          <button
            onClick={() => setConfigView('api-keys')}
            className="bg-purple-50 dark:bg-purple-900 p-6 rounded-lg hover:shadow-lg transition-shadow duration-200 text-left"
          >
            <div className="text-4xl mb-2">🔑</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">API Key Management</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Configure external service keys</p>
          </button>
          
          <button
            onClick={() => setConfigView('websocket')}
            className="bg-blue-50 dark:bg-blue-900 p-6 rounded-lg hover:shadow-lg transition-shadow duration-200 text-left"
          >
            <div className="text-4xl mb-2">🏠</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Home Assistant</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">WebSocket connection</p>
          </button>
          
          <button
            onClick={() => setConfigView('weather')}
            className="bg-blue-50 dark:bg-blue-900 p-6 rounded-lg hover:shadow-lg transition-shadow duration-200 text-left"
          >
            <div className="text-4xl mb-2">☁️</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Weather API</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">OpenWeatherMap</p>
          </button>
          
          <button
            onClick={() => setConfigView('influxdb')}
            className="bg-blue-50 dark:bg-blue-900 p-6 rounded-lg hover:shadow-lg transition-shadow duration-200 text-left"
          >
            <div className="text-4xl mb-2">💾</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">InfluxDB</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Time-series database</p>
          </button>
        </div>
        
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
            Service Control
          </h2>
          <ServiceControl />
        </div>
      </div>
    </div>
  );
};

