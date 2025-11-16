import React, { useState, useEffect } from 'react';
import { withCsrfHeader } from '../utils/security';

interface ServiceStatus {
  service: string;
  running: boolean;
  status: string;
  timestamp?: string;
  error?: string;
}

export const ServiceControl: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [restarting, setRestarting] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadServices();
    const interval = setInterval(loadServices, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadServices = async () => {
    try {
      const response = await fetch('/api/v1/services');
      if (!response.ok) throw new Error('Failed to load services');
      
      const data = await response.json();
      setServices(data.services || []);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load services');
    }
  };

    const restartService = async (service: string) => {
    if (!confirm(`Restart ${service}?`)) return;
    
    setRestarting({ ...restarting, [service]: true });
    try {
        const response = await fetch(`/api/v1/services/${service}/restart`, {
          method: 'POST',
          headers: withCsrfHeader()
        });
      
      if (!response.ok) throw new Error('Failed to restart service');
      
      await loadServices();
    } catch (err: any) {
      alert(err.message || 'Failed to restart service');
    } finally {
      setRestarting({ ...restarting, [service]: false });
    }
  };

    const restartAll = async () => {
    if (!confirm('Restart all services? This may take a few minutes.')) return;
    
    setLoading(true);
    try {
        const response = await fetch('/api/v1/services/restart-all', {
          method: 'POST',
          headers: withCsrfHeader()
        });
      
      if (!response.ok) throw new Error('Failed to restart services');
      
      alert('All services restarted successfully!');
      await loadServices();
    } catch (err: any) {
      alert(err.message || 'Failed to restart all services');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return '🟢';
      case 'stopped':
        return '🔴';
      case 'error':
        return '⚠️';
      default:
        return '⚪';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 dark:text-green-400';
      case 'stopped':
        return 'text-red-600 dark:text-red-400';
      case 'error':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Service Control
          </h3>
          <button
            onClick={restartAll}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Restarting...' : 'Restart All'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Service
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {services.map((service) => (
                <tr key={service.service}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {service.service}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`inline-flex items-center ${getStatusColor(service.status)}`}>
                      {getStatusIcon(service.status)} 
                      <span className="ml-2 capitalize">{service.status}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => restartService(service.service)}
                      disabled={restarting[service.service]}
                      className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {restarting[service.service] ? 'Restarting...' : 'Restart'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          <p>Status refreshes every 5 seconds automatically.</p>
        </div>
      </div>
    </div>
  );
};

