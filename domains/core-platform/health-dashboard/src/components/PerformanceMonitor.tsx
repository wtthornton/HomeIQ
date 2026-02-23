import React, { useState, useEffect } from 'react';

interface PerformanceMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: {
    bytes_sent: number;
    bytes_received: number;
  };
  response_times: {
    [service: string]: number;
  };
}

interface PerformanceMonitorProps {
  darkMode: boolean;
  metrics?: PerformanceMetrics[];
  realTime?: boolean;
}

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  darkMode,
  metrics = [],
  realTime = false
}) => {
  const [currentMetrics, setCurrentMetrics] = useState<PerformanceMetrics | null>(null);
  const [timeRange, setTimeRange] = useState<'5m' | '15m' | '1h' | '6h'>('15m');

  // Simulate real-time metrics if no data provided
  useEffect(() => {
    if (!realTime || metrics.length > 0) return;

    const interval = setInterval(() => {
      setCurrentMetrics({
        timestamp: new Date().toISOString(),
        cpu_usage: Math.random() * 100,
        memory_usage: Math.random() * 100,
        disk_usage: Math.random() * 100,
        network_io: {
          bytes_sent: Math.random() * 1000000,
          bytes_received: Math.random() * 1000000,
        },
        response_times: {
          'websocket-ingestion': Math.random() * 100 + 10,
          'data-retention': Math.random() * 200 + 20,
          'admin-api': Math.random() * 30 + 5,
        }
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [realTime, metrics.length]);

  const getUsageColor = (usage: number) => {
    if (usage < 50) return darkMode ? 'text-green-400' : 'text-green-600';
    if (usage < 80) return darkMode ? 'text-yellow-400' : 'text-yellow-600';
    return darkMode ? 'text-red-400' : 'text-red-600';
  };

  const getUsageBarColor = (usage: number) => {
    if (usage < 50) return 'bg-green-500';
    if (usage < 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100  } ${  sizes[i]}`;
  };

  const latestMetrics = currentMetrics || metrics[metrics.length - 1];

  if (!latestMetrics) {
    return (
      <div className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border rounded-lg p-6 transition-colors duration-300`}>
        <div className="text-center py-8">
          <div className="text-4xl mb-4">📊</div>
          <h3 className={`text-lg font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'} mb-2`}>
            Performance Monitor
          </h3>
          <p className={`text-sm ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
            No performance data available
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border rounded-lg p-6 transition-colors duration-300`}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📊 Performance Monitor
          </h2>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
            System resource utilization and performance metrics
          </p>
        </div>

        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as '5m' | '15m' | '1h' | '6h')}
          className={`px-3 py-2 rounded-lg text-sm ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'} border transition-colors duration-200`}
        >
          <option value="5m">Last 5 minutes</option>
          <option value="15m">Last 15 minutes</option>
          <option value="1h">Last hour</option>
          <option value="6h">Last 6 hours</option>
        </select>
      </div>

      {/* Resource Usage Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* CPU Usage */}
        <div className={`${darkMode ? 'bg-gray-700' : 'bg-gray-50'} rounded-lg p-4 transition-colors duration-300`}>
          <div className="flex justify-between items-center mb-3">
            <h3 className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              🖥️ CPU Usage
            </h3>
            <span className={`text-2xl font-bold ${getUsageColor(latestMetrics.cpu_usage)}`}>
              {(latestMetrics.cpu_usage ?? 0).toFixed(1)}%
            </span>
          </div>
          <div className={`w-full ${darkMode ? 'bg-gray-600' : 'bg-gray-200'} rounded-full h-2`}>
            <div
              className={`h-2 rounded-full ${getUsageBarColor(latestMetrics.cpu_usage)} transition-all duration-500`}
              style={{ width: `${latestMetrics.cpu_usage}%` }}
            />
          </div>
        </div>

        {/* Memory Usage */}
        <div className={`${darkMode ? 'bg-gray-700' : 'bg-gray-50'} rounded-lg p-4 transition-colors duration-300`}>
          <div className="flex justify-between items-center mb-3">
            <h3 className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              💾 Memory Usage
            </h3>
            <span className={`text-2xl font-bold ${getUsageColor(latestMetrics.memory_usage)}`}>
              {(latestMetrics.memory_usage ?? 0).toFixed(1)}%
            </span>
          </div>
          <div className={`w-full ${darkMode ? 'bg-gray-600' : 'bg-gray-200'} rounded-full h-2`}>
            <div
              className={`h-2 rounded-full ${getUsageBarColor(latestMetrics.memory_usage)} transition-all duration-500`}
              style={{ width: `${latestMetrics.memory_usage}%` }}
            />
          </div>
        </div>

        {/* Disk Usage */}
        <div className={`${darkMode ? 'bg-gray-700' : 'bg-gray-50'} rounded-lg p-4 transition-colors duration-300`}>
          <div className="flex justify-between items-center mb-3">
            <h3 className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              💿 Disk Usage
            </h3>
            <span className={`text-2xl font-bold ${getUsageColor(latestMetrics.disk_usage)}`}>
              {(latestMetrics.disk_usage ?? 0).toFixed(1)}%
            </span>
          </div>
          <div className={`w-full ${darkMode ? 'bg-gray-600' : 'bg-gray-200'} rounded-full h-2`}>
            <div
              className={`h-2 rounded-full ${getUsageBarColor(latestMetrics.disk_usage)} transition-all duration-500`}
              style={{ width: `${latestMetrics.disk_usage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Network I/O */}
      <div className="mb-8">
        <h3 className={`text-lg font-medium ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          🌐 Network I/O
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`${darkMode ? 'bg-gray-700' : 'bg-gray-50'} rounded-lg p-4 transition-colors duration-300`}>
            <div className="flex items-center space-x-2 mb-2">
              <span className="text-lg">📤</span>
              <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Data Sent
              </span>
            </div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
              {formatBytes(latestMetrics.network_io.bytes_sent)}
            </div>
          </div>
          
          <div className={`${darkMode ? 'bg-gray-700' : 'bg-gray-50'} rounded-lg p-4 transition-colors duration-300`}>
            <div className="flex items-center space-x-2 mb-2">
              <span className="text-lg">📥</span>
              <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Data Received
              </span>
            </div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
              {formatBytes(latestMetrics.network_io.bytes_received)}
            </div>
          </div>
        </div>
      </div>

      {/* Service Response Times */}
      <div>
        <h3 className={`text-lg font-medium ${darkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
          ⚡ Service Response Times
        </h3>
        <div className="space-y-3">
          {Object.entries(latestMetrics.response_times).map(([service, time]) => (
            <div key={service} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  {service.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <div className={`w-24 ${darkMode ? 'bg-gray-600' : 'bg-gray-200'} rounded-full h-2`}>
                  <div
                    className={`h-2 rounded-full ${
                      time < 50 ? 'bg-green-500' : time < 100 ? 'bg-yellow-500' : 'bg-red-500'
                    } transition-all duration-500`}
                    style={{ width: `${Math.min((time / 200) * 100, 100)}%` }}
                  />
                </div>
              </div>
              <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                {(time ?? 0).toFixed(0)}ms
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Last Updated */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'} text-center`}>
          Last updated: {new Date(latestMetrics.timestamp).toLocaleString()}
          {realTime && <span className="ml-2 text-green-500">● Live</span>}
        </div>
      </div>
    </div>
  );
};

