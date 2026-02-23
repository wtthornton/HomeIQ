/**
 * MiniChart Component
 * 
 * Reusable SVG-based mini chart for time-series data visualization
 * Extracted per QA recommendation for improved reusability
 */

import React from 'react';

export interface TimeSeriesData {
  timestamp: string;
  value: number;
}

interface MiniChartProps {
  data: TimeSeriesData[];
  color: string;
  className?: string;
  ariaLabel?: string;
}

export const MiniChart: React.FC<MiniChartProps> = ({ 
  data, 
  color, 
  className = 'w-full h-24',
  ariaLabel = 'Time series chart'
}) => {
  if (!data || data.length === 0) {
    return (
      <div className={className} role="img" aria-label="No chart data available">
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          No data
        </div>
      </div>
    );
  }

  const max = Math.max(...data.map(d => d.value));
  const min = Math.min(...data.map(d => d.value));
  const range = max - min || 1;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - ((d.value - min) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  // Create accessible description
  const description = `Chart showing ${data.length} data points. Range from ${min.toFixed(1)} to ${max.toFixed(1)}.`;

  return (
    <div className={`${className} relative`} role="img" aria-label={ariaLabel}>
      <svg 
        viewBox="0 0 100 100" 
        className="w-full h-full" 
        preserveAspectRatio="none"
        aria-describedby="chart-description"
      >
        <title>{ariaLabel}</title>
        <desc id="chart-description">{description}</desc>
        
        {/* Area fill */}
        <polyline
          points={`0,100 ${points} 100,100`}
          fill={color}
          opacity="0.1"
        />
        
        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
};

