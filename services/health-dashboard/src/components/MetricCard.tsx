import React, { useEffect, useState } from 'react';
import { Card, CardContent } from './ui/card';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  className?: string;
  isLive?: boolean;
}

const getTrendIcon = (trend?: string) => {
  switch (trend) {
    case 'up':
      return '📈';
    case 'down':
      return '📉';
    case 'stable':
      return '➡️';
    default:
      return null;
  }
};

const getTrendColor = (trend?: string) => {
  switch (trend) {
    case 'up':
      return 'text-status-healthy';
    case 'down':
      return 'text-status-critical';
    default:
      return 'text-muted-foreground';
  }
};

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  trend,
  className = '',
  isLive = false
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const [isAnimating, setIsAnimating] = useState(false);

  // Number counting animation when value changes
  useEffect(() => {
    if (typeof value === 'number' && typeof displayValue === 'number' && value !== displayValue) {
      setIsAnimating(true);
      const duration = 500;
      const steps = 20;
      const stepValue = (value - displayValue) / steps;
      let currentStep = 0;

      const timer = setInterval(() => {
        currentStep++;
        if (currentStep === steps) {
          setDisplayValue(value);
          clearInterval(timer);
          setIsAnimating(false);
        } else {
          setDisplayValue(prev => typeof prev === 'number' ? prev + stepValue : value);
        }
      }, duration / steps);

      return () => clearInterval(timer);
    } else if (value !== displayValue) {
      setDisplayValue(value);
    }
  }, [value, displayValue]);

  return (
    <Card 
      hover 
      className={cn(
        "animate-fade-in",
        isLive && "ring-2 ring-primary/20",
        className
      )}
    >
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          <div className="flex items-center gap-2">
            {trend && (
              <span className={cn("text-lg", getTrendColor(trend))}>
                {getTrendIcon(trend)}
              </span>
            )}
            {isLive && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-baseline">
          <p className={cn(
            "text-3xl font-bold text-foreground font-display metric-value",
            isAnimating && "animate-pulse"
          )}>
            {typeof displayValue === 'number' ? Math.round(displayValue).toLocaleString() : displayValue}
          </p>
          {unit && (
            <p className="ml-2 text-sm text-muted-foreground">{unit}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
