import React from 'react';
import { Chart as ChartJS } from 'chart.js';

// Simple test component to verify Chart.js is working
export const ChartTest: React.FC = () => {
  try {
    // Check if Chart.js is available
    const chartVersion = ChartJS.version || 'Unknown';
    
    return (
      <div className="p-4">
        <h3 className="text-lg font-bold mb-4">Chart.js Test</h3>
        <div className="bg-green-100 p-4 rounded">
          <p className="text-green-800">✅ Chart.js is working!</p>
          <p className="text-sm text-green-600">Version: {chartVersion}</p>
        </div>
      </div>
    );
  } catch (error: any) {
    return (
      <div className="p-4">
        <h3 className="text-lg font-bold mb-4">Chart.js Test</h3>
        <div className="bg-red-100 p-4 rounded">
          <p className="text-red-800">❌ Chart.js Error:</p>
          <p className="text-sm text-red-600">{error?.message || 'Unknown error'}</p>
        </div>
      </div>
    );
  }
};
