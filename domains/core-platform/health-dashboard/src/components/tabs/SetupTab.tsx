/**
 * Setup & Health Monitoring Tab
 * 
 * Integrates environment health monitoring into the HA Ingestor dashboard
 */
import React from 'react';
import { EnvironmentHealthCard } from '../EnvironmentHealthCard';
import { MqttConfigForm } from '../setup/MqttConfigForm';

export const SetupTab: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Tab Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          🔧 Setup & Health Monitoring
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Monitor your Home Assistant environment health, integration status, and system performance.
          The health status updates automatically every 30 seconds.
        </p>
      </div>

      {/* Environment Health Card */}
      <EnvironmentHealthCard />

      <MqttConfigForm />

      {/* Additional Information */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start">
          <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              About Health Monitoring
            </h3>
            <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
              <p className="mb-2">
                The HA Setup Service continuously monitors your environment and provides:
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Real-time health scoring (0-100 based on weighted components)</li>
                <li>Integration status verification (MQTT, device discovery)</li>
                <li>Performance metrics tracking (response time, resource usage)</li>
                <li>Automatic issue detection with actionable recommendations</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

