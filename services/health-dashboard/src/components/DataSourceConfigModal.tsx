import React, { useState, useEffect } from 'react';

interface DataSourceConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  serviceName: string;
  serviceId: string;
  darkMode: boolean;
  onSave?: (config: Record<string, any>) => Promise<void>;
}

// Configuration schemas for each service
const CONFIG_SCHEMAS: Record<string, Array<{ key: string; label: string; type: 'text' | 'password' | 'number' | 'select'; options?: string[]; placeholder?: string }>> = {
  carbonIntensity: [
    { key: 'WATTTIME_USERNAME', label: 'WattTime Username', type: 'text', placeholder: 'your_watttime_username' },
    { key: 'WATTTIME_PASSWORD', label: 'WattTime Password', type: 'password', placeholder: 'your_watttime_password' },
    { key: 'GRID_REGION', label: 'Grid Region', type: 'select', options: ['CAISO_NORTH', 'CAISO_SOUTH', 'ERCOT', 'PJM', 'NYISO', 'ISONE', 'MISO'] },
  ],
  airQuality: [
    { key: 'WEATHER_API_KEY', label: 'OpenWeatherMap API Key', type: 'password', placeholder: 'your_api_key_here' },
    { key: 'LATITUDE', label: 'Latitude', type: 'number', placeholder: '36.1699' },
    { key: 'LONGITUDE', label: 'Longitude', type: 'number', placeholder: '-115.1398' },
  ],
  electricityPricing: [
    { key: 'PRICING_PROVIDER', label: 'Provider', type: 'select', options: ['awattar'] },
    { key: 'PRICING_API_KEY', label: 'API Key (Optional)', type: 'password', placeholder: 'Leave empty for awattar' },
  ],
  calendar: [
    { key: 'CALENDAR_ENTITIES', label: 'Calendar Entities', type: 'text', placeholder: 'calendar.primary' },
    { key: 'CALENDAR_FETCH_INTERVAL', label: 'Fetch Interval (seconds)', type: 'number', placeholder: '900' },
  ],
  smartMeter: [
    { key: 'METER_TYPE', label: 'Meter Type', type: 'select', options: ['home_assistant', 'emporia', 'sense', 'generic'] },
    { key: 'METER_DEVICE_ID', label: 'Device ID', type: 'text', placeholder: 'Optional' },
  ],
  weather: [
    { key: 'WEATHER_API_KEY', label: 'OpenWeatherMap API Key', type: 'password', placeholder: 'your_api_key_here' },
    { key: 'WEATHER_LOCATION', label: 'Location', type: 'text', placeholder: 'Las Vegas' },
  ],
};

export const DataSourceConfigModal: React.FC<DataSourceConfigModalProps> = ({
  isOpen,
  onClose,
  serviceName,
  serviceId,
  darkMode,
  onSave,
}) => {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const schema = CONFIG_SCHEMAS[serviceId] || [];

  useEffect(() => {
    if (isOpen) {
      // Load current configuration (would fetch from API in real implementation)
      setConfig({});
      setError(null);
      setSuccess(false);
    }
  }, [isOpen, serviceId]);

  const handleChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      if (onSave) {
        await onSave(config);
        setSuccess(true);
        setTimeout(() => {
          onClose();
          setSuccess(false);
        }, 1500);
      } else {
        // Show info message that configuration should be updated in .env file
        setSuccess(true);
        setError('Note: Configuration must be updated in the .env file and services restarted. See implementation/EXTERNAL_DATA_SOURCES_FIX.md for details.');
        setTimeout(() => {
          onClose();
          setSuccess(false);
          setError(null);
        }, 3000);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close if clicking the backdrop, not the modal content
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" 
      onClick={handleBackdropClick}
    >
      <div
        className={`rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto ${
          darkMode ? 'bg-gray-800' : 'bg-white'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`p-6 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex items-center justify-between">
            <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Configure {serviceName}
            </h2>
            <button
              onClick={onClose}
              className={`text-2xl leading-none ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {schema.length === 0 ? (
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Configuration schema not available for this service.
            </p>
          ) : (
            <>
              <div className="space-y-4">
                {schema.map((field) => (
                  <div key={field.key}>
                    <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {field.label}
                    </label>
                    {field.type === 'select' ? (
                      <select
                        value={config[field.key] || ''}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      >
                        <option value="">Select {field.label}</option>
                        {field.options?.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={field.type}
                        value={config[field.key] || ''}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        className={`w-full px-3 py-2 rounded-lg border ${
                          darkMode
                            ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-500'
                            : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                        }`}
                      />
                    )}
                  </div>
                ))}
              </div>

              {error && (
                <div className={`mt-4 p-3 rounded-lg ${darkMode ? 'bg-yellow-900/20 border border-yellow-500/30' : 'bg-yellow-50 border border-yellow-200'}`}>
                  <p className={`text-sm ${darkMode ? 'text-yellow-200' : 'text-yellow-800'}`}>
                    <strong>ℹ️ Info:</strong> {error}
                  </p>
                </div>
              )}

              {success && !error && (
                <div className={`mt-4 p-3 rounded-lg ${darkMode ? 'bg-green-900/20 border border-green-500/30' : 'bg-green-50 border border-green-200'}`}>
                  <p className={`text-sm ${darkMode ? 'text-green-200' : 'text-green-800'}`}>
                    ✅ Configuration saved successfully!
                  </p>
                </div>
              )}

              <div className={`mt-6 p-4 rounded-lg ${darkMode ? 'bg-blue-900/20 border border-blue-500/30' : 'bg-blue-50 border border-blue-200'}`}>
                <p className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
                  <strong>Note:</strong> Configuration changes require updating the <code className="px-1 py-0.5 rounded bg-gray-200 dark:bg-gray-700">.env</code> file and restarting the service.
                  See <code className="px-1 py-0.5 rounded bg-gray-200 dark:bg-gray-700">implementation/EXTERNAL_DATA_SOURCES_FIX.md</code> for details.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className={`p-6 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'} flex justify-end gap-3`}>
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded-lg transition-colors ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
            }`}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className={`px-4 py-2 rounded-lg transition-colors ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : darkMode
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
          >
            {loading ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
};

