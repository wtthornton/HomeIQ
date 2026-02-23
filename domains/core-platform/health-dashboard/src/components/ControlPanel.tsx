import React, { useState } from 'react';

interface ControlPanelProps {
  darkMode: boolean;
  onRefresh: () => void;
  onExportData: (format: 'json' | 'csv') => void;
  onToggleService: (service: string, enabled: boolean) => void;
  services: { [key: string]: { status: string; enabled?: boolean } };
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  darkMode,
  onRefresh,
  onExportData,
  onToggleService,
  services
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  const handleExport = async (format: 'json' | 'csv') => {
    setExportLoading(true);
    try {
      await onExportData(format);
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div className="relative">
      {/* Control Panel Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'} transition-colors duration-200`}
        title="Control Panel"
      >
        <span className="text-xl">⚙️</span>
      </button>

      {/* Control Panel Dropdown */}
      {isOpen && (
        <div className={`absolute right-0 top-full mt-2 w-80 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border rounded-lg shadow-lg z-50 transition-all duration-200`}>
          <div className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Control Panel
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className={`p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'} transition-colors duration-200`}
              >
                ✕
              </button>
            </div>

            {/* Refresh Controls */}
            <div className="mb-6">
              <h4 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-3`}>
                System Controls
              </h4>
              <div className="space-y-2">
                <button
                  onClick={onRefresh}
                  className={`w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-lg ${darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-600 hover:bg-blue-700'} text-white transition-colors duration-200`}
                >
                  <span>🔄</span>
                  <span>Force Refresh</span>
                </button>
              </div>
            </div>

            {/* Service Controls */}
            <div className="mb-6">
              <h4 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-3`}>
                Service Management
              </h4>
              <div className="space-y-2">
                {Object.entries(services).map(([serviceName, service]) => (
                  <div key={serviceName} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        {serviceName.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        service.status === 'healthy' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : service.status === 'degraded'
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {service.status}
                      </span>
                    </div>
                    {service.enabled !== undefined && (
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={service.enabled}
                          onChange={(e) => onToggleService(serviceName, e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className={`w-11 h-6 ${darkMode ? 'bg-gray-600' : 'bg-gray-200'} peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600`}></div>
                      </label>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Data Export */}
            <div className="mb-4">
              <h4 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-3`}>
                Data Export
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleExport('json')}
                  disabled={exportLoading}
                  className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-gray-700 hover:bg-gray-600 disabled:opacity-50' : 'bg-gray-100 hover:bg-gray-200 disabled:opacity-50'} transition-colors duration-200`}
                >
                  {exportLoading ? '⏳' : '📄'} JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  disabled={exportLoading}
                  className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-gray-700 hover:bg-gray-600 disabled:opacity-50' : 'bg-gray-100 hover:bg-gray-200 disabled:opacity-50'} transition-colors duration-200`}
                >
                  {exportLoading ? '⏳' : '📊'} CSV
                </button>
              </div>
            </div>

            {/* Quick Actions */}
            <div>
              <h4 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-3`}>
                Quick Actions
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => window.open('/api/health', '_blank')}
                  className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'} transition-colors duration-200`}
                >
                  🔗 API Health
                </button>
                <button
                  onClick={() => window.open('/api/statistics', '_blank')}
                  className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'} transition-colors duration-200`}
                >
                  📊 API Stats
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

