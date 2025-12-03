import React, { useState, useEffect } from 'react';
import { withCsrfHeader } from '../utils/security';

interface ConfigField {
  type: string;
  required: boolean;
  sensitive: boolean;
  description: string;
  placeholder?: string;
  default?: string;
  options?: string[];
}

interface ConfigFormProps {
  service: string;
  onSave?: () => void;
}

interface ServiceConfig {
  settings: Record<string, string>;
  template: Record<string, ConfigField>;
}

export const ConfigForm: React.FC<ConfigFormProps> = ({ service, onSave }) => {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [template, setTemplate] = useState<Record<string, ConfigField>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string>('');
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadConfig();
  }, [service]);

  const loadConfig = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/v1/integrations/${service}/config`);
      if (!response.ok) throw new Error('Failed to load configuration');
      
      const data: ServiceConfig = await response.json();
      setConfig(data.settings);
      setTemplate(data.template);
    } catch (err: any) {
      setError(err.message || 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSaved(false);
    
    try {
      const response = await fetch(`/api/v1/integrations/${service}/config`, {
        method: 'PUT',
        headers: withCsrfHeader({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ settings: config })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Failed to save configuration');
      }
      
      setSaved(true);
      if (onSave) onSave();
      
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async () => {
    if (!confirm(`Restart ${service} service to apply new configuration?`)) {
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`/api/v1/services/${service}/restart`, {
        method: 'POST',
        headers: withCsrfHeader()
      });
      
      if (!response.ok) throw new Error('Failed to restart service');
      
      alert(`${service} restarted successfully!`);
    } catch (err: any) {
      setError(err.message || 'Failed to restart service');
    } finally {
      setLoading(false);
    }
  };

  const updateValue = (key: string, value: string) => {
    setConfig({ ...config, [key]: value });
  };

  const toggleShowSensitive = (key: string) => {
    setShowSensitive({ ...showSensitive, [key]: !showSensitive[key] });
  };

  const maskValue = (value: string) => {
    if (!value) return '';
    return `••••••••${  value.slice(-4)}`;
  };

  const renderField = (key: string, field: ConfigField) => {
    const value = config[key] || field.default || '';
    const isSensitive = field.sensitive && !showSensitive[key];
    const displayValue = isSensitive ? maskValue(value) : value;

    if (field.type === 'boolean' || field.type === 'select') {
      return (
        <select
          value={value}
          onChange={(e) => updateValue(key, e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          disabled={loading || saving}
        >
          {field.type === 'boolean' ? (
            <>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </>
          ) : (
            field.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))
          )}
        </select>
      );
    }

    return (
      <div className="relative">
        <input
          type={field.sensitive && !showSensitive[key] ? 'password' : field.type === 'number' ? 'number' : 'text'}
          value={displayValue}
          onChange={(e) => updateValue(key, e.target.value)}
          placeholder={field.placeholder}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white pr-20"
          required={field.required}
          disabled={loading || saving}
        />
        {field.sensitive && (
          <button
            type="button"
            onClick={() => toggleShowSensitive(key)}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
            disabled={loading || saving}
          >
            {showSensitive[key] ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {service} Configuration
          </h3>
          {saved && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              ✓ Saved
            </span>
          )}
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          {Object.entries(template).map(([key, field]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {field.description}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderField(key, field)}
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Changes require service restart to take effect
          </p>
          <div className="flex space-x-3">
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Changes'}
            </button>
            <button
              onClick={handleRestart}
              disabled={loading || saving}
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md shadow-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Restart Service
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

