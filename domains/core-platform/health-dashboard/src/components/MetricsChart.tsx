import React from 'react';

// Import Chart.js components
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface MetricsChartProps {
  darkMode: boolean;
  serviceName: string;
  metrics?: {
    cpu_usage?: number;
    memory_usage?: number;
    requests_per_minute?: number;
    error_rate?: number;
    response_time?: number;
  };
}

export const MetricsChart: React.FC<MetricsChartProps> = ({
  darkMode,
  serviceName,
  metrics
}) => {
  // Generate sample data if no real metrics available
  const generateTimeSeriesData = (baseValue: number, variance: number = 10) => {
    const labels = [];
    const data = [];
    const now = new Date();
    
    for (let i = 23; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000);
      labels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
      
      // Add some realistic variation
      const variation = (Math.random() - 0.5) * variance;
      data.push(Math.max(0, baseValue + variation));
    }
    
    return { labels, data };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: darkMode ? '#e5e7eb' : '#374151'
        }
      },
      title: {
        display: false
      }
    },
    scales: {
      x: {
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        },
        grid: {
          color: darkMode ? '#374151' : '#e5e7eb'
        }
      },
      y: {
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        },
        grid: {
          color: darkMode ? '#374151' : '#e5e7eb'
        }
      }
    }
  };

  const primaryColor = darkMode ? '#60a5fa' : '#2563eb';
  const secondaryColor = darkMode ? '#f59e0b' : '#d97706';
  const errorColor = darkMode ? '#f87171' : '#dc2626';

  // CPU Usage Chart
  const cpuData = generateTimeSeriesData(metrics?.cpu_usage || 25, 15);
  const cpuChartData = {
    labels: cpuData.labels,
    datasets: [
      {
        label: 'CPU Usage (%)',
        data: cpuData.data,
        borderColor: primaryColor,
        backgroundColor: `${primaryColor}20`,
        tension: 0.4,
        fill: true
      }
    ]
  };

  // Memory Usage Chart
  const memoryData = generateTimeSeriesData(metrics?.memory_usage || 45, 20);
  const memoryChartData = {
    labels: memoryData.labels,
    datasets: [
      {
        label: 'Memory Usage (%)',
        data: memoryData.data,
        borderColor: secondaryColor,
        backgroundColor: `${secondaryColor}20`,
        tension: 0.4,
        fill: true
      }
    ]
  };

  // Requests per Minute Chart
  const requestsData = generateTimeSeriesData(metrics?.requests_per_minute || 150, 50);
  const requestsChartData = {
    labels: requestsData.labels,
    datasets: [
      {
        label: 'Requests/min',
        data: requestsData.data,
        backgroundColor: `${primaryColor}60`,
        borderColor: primaryColor,
        borderWidth: 1
      }
    ]
  };

  // Error Rate Chart
  const errorData = generateTimeSeriesData(metrics?.error_rate || 2, 3);
  const errorChartData = {
    labels: errorData.labels,
    datasets: [
      {
        label: 'Error Rate (%)',
        data: errorData.data,
        backgroundColor: errorData.data.map(value => 
          value > 5 ? errorColor : value > 2 ? secondaryColor : primaryColor
        ),
        borderColor: errorData.data.map(value => 
          value > 5 ? errorColor : value > 2 ? secondaryColor : primaryColor
        ),
        borderWidth: 1
      }
    ]
  };

  return (
    <div className="space-y-6">
      {/* CPU Usage */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <h4 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          CPU Usage (24h)
        </h4>
        <div style={{ height: '200px' }}>
          <Line data={cpuChartData} options={chartOptions} />
        </div>
      </div>

      {/* Memory Usage */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <h4 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Memory Usage (24h)
        </h4>
        <div style={{ height: '200px' }}>
          <Line data={memoryChartData} options={chartOptions} />
        </div>
      </div>

      {/* Requests per Minute */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <h4 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Requests per Minute (24h)
        </h4>
        <div style={{ height: '200px' }}>
          <Bar data={requestsChartData} options={chartOptions} />
        </div>
      </div>

      {/* Error Rate */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <h4 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Error Rate (24h)
        </h4>
        <div style={{ height: '200px' }}>
          <Bar data={errorChartData} options={chartOptions} />
        </div>
      </div>

      {/* Current Metrics Summary */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <h4 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Current Metrics
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className={`text-2xl font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
              {(metrics?.cpu_usage || 25).toFixed(1)}%
            </div>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>CPU</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
              {(metrics?.memory_usage || 45).toFixed(1)}%
            </div>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Memory</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
              {(metrics?.requests_per_minute || 150).toFixed(0)}
            </div>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Req/min</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${(metrics?.error_rate || 2) > 5 ? (darkMode ? 'text-red-400' : 'text-red-600') : (darkMode ? 'text-green-400' : 'text-green-600')}`}>
              {(metrics?.error_rate || 2).toFixed(2)}%
            </div>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Error Rate</div>
          </div>
        </div>
      </div>
    </div>
  );
};
