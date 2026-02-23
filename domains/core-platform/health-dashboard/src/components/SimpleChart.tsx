import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface SimpleChartProps {
  darkMode: boolean;
}

export const SimpleChart: React.FC<SimpleChartProps> = ({ darkMode }) => {
  const data = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'CPU Usage',
        data: [65, 59, 80, 81, 56, 55, 40],
        borderColor: darkMode ? '#60a5fa' : '#2563eb',
        backgroundColor: darkMode ? '#60a5fa20' : '#2563eb20',
        tension: 0.4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: darkMode ? '#e5e7eb' : '#374151'
        }
      },
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
    },
  };

  return (
    <div style={{ height: '300px' }}>
      <Line data={data} options={options} />
    </div>
  );
};
