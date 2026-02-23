import React, { useEffect, useRef, useState } from 'react';

interface ChartCardProps {
  title: string;
  data: Array<{ timestamp: string; value: number; label?: string }>;
  type: 'line' | 'bar' | 'area' | 'gauge';
  unit?: string;
  color?: string;
  darkMode?: boolean;
  height?: number;
  showLegend?: boolean;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  data,
  type,
  unit = '',
  color = '#3B82F6',
  darkMode = false,
  height = 200,
  showLegend = false,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; value: number; timestamp: string } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.length) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Clear canvas
    ctx.clearRect(0, 0, canvas.offsetWidth, height);

    // Chart dimensions
    const padding = 40;
    const chartWidth = canvas.offsetWidth - padding * 2;
    const chartHeight = height - padding * 2;

    // Find data bounds
    const values = data.map(d => d.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue || 1;

    // Draw grid lines
    ctx.strokeStyle = darkMode ? '#374151' : '#E5E7EB';
    ctx.lineWidth = 1;
    
    // Horizontal grid lines
    for (let i = 0; i <= 4; i++) {
      const y = padding + (chartHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + chartWidth, y);
      ctx.stroke();
    }

    // Vertical grid lines
    for (let i = 0; i <= 4; i++) {
      const x = padding + (chartWidth / 4) * i;
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, padding + chartHeight);
      ctx.stroke();
    }

    // Draw chart based on type
    if (type === 'line' || type === 'area') {
      // Draw area under line
      if (type === 'area') {
        ctx.fillStyle = `${color  }20`;
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);
        
        data.forEach((point, index) => {
          const x = padding + (chartWidth / (data.length - 1)) * index;
          const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
          ctx.lineTo(x, y);
        });
        
        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.closePath();
        ctx.fill();
      }

      // Draw line
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
        
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      
      ctx.stroke();

      // Draw points
      ctx.fillStyle = color;
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
      });
    } else if (type === 'bar') {
      const barWidth = chartWidth / data.length * 0.8;
      const barSpacing = chartWidth / data.length * 0.2;
      
      data.forEach((point, index) => {
        const x = padding + (chartWidth / data.length) * index + barSpacing / 2;
        const barHeight = ((point.value - minValue) / valueRange) * chartHeight;
        const y = padding + chartHeight - barHeight;
        
        ctx.fillStyle = color;
        ctx.fillRect(x, y, barWidth, barHeight);
      });
    } else if (type === 'gauge') {
      // Simple gauge implementation
      const centerX = canvas.offsetWidth / 2;
      const centerY = height / 2;
      const radius = Math.min(chartWidth, chartHeight) / 3;
      const currentValue = data[data.length - 1]?.value || 0;
      const percentage = (currentValue - minValue) / valueRange;
      
      // Background arc
      ctx.strokeStyle = darkMode ? '#374151' : '#E5E7EB';
      ctx.lineWidth = 20;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI);
      ctx.stroke();
      
      // Value arc
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, Math.PI, Math.PI + percentage * Math.PI);
      ctx.stroke();
      
      // Center text
      ctx.fillStyle = darkMode ? '#F3F4F6' : '#111827';
      ctx.font = 'bold 24px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText((currentValue ?? 0).toFixed(1) + unit, centerX, centerY + 8);
    }

    // Draw Y-axis labels
    ctx.fillStyle = darkMode ? '#9CA3AF' : '#6B7280';
    ctx.font = '12px system-ui';
    ctx.textAlign = 'right';
    
    for (let i = 0; i <= 4; i++) {
      const value = minValue + (valueRange / 4) * (4 - i);
      const y = padding + (chartHeight / 4) * i + 4;
      ctx.fillText((value ?? 0).toFixed(1), padding - 10, y);
    }

    // Draw X-axis labels (time)
    ctx.textAlign = 'center';
    const timeLabels = data.filter((_, index) => index % Math.ceil(data.length / 5) === 0);
    
    timeLabels.forEach((point, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * (data.indexOf(point));
      ctx.fillText(
        new Date(point.timestamp).toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }), 
        x, 
        height - 10
      );
    });

  }, [data, type, color, darkMode, height]);

  return (
    <div className={`card-base card-hover content-fade-in ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} ${className}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {title}
        </h3>
        {hoveredPoint && (
          <div className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'} fade-in`}>
            {(hoveredPoint.value ?? 0).toFixed(1)}{unit} at {hoveredPoint.timestamp}
          </div>
        )}
      </div>
      
      <div className="relative">
        <canvas
          ref={canvasRef}
          className="w-full"
          style={{ height: `${height}px` }}
          onMouseMove={(e) => {
            if (type === 'gauge') return;
            
            const canvas = canvasRef.current;
            if (!canvas) return;
            
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Find closest data point
            const padding = 40;
            const chartWidth = canvas.offsetWidth - padding * 2;
            const pointIndex = Math.round(((x - padding) / chartWidth) * (data.length - 1));
            
            if (pointIndex >= 0 && pointIndex < data.length) {
              const point = data[pointIndex];
              setHoveredPoint({
                x,
                y,
                value: point.value,
                timestamp: new Date(point.timestamp).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                })
              });
            }
          }}
          onMouseLeave={() => setHoveredPoint(null)}
        />
        
        {showLegend && (
          <div className="mt-4 flex items-center justify-center space-x-4">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: color }}
              />
              <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                {title}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

