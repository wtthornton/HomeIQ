import React, { useEffect, useState } from 'react';
import { Card, CardContent } from './ui/card';
import { Icon, TrendIcons, LiveIndicator } from './ui/icons';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  className?: string;
  isLive?: boolean;
}

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
        isLive && "ring-1 ring-primary/30",
        className
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{title}</h3>
          <div className="flex items-center gap-1.5">
            {trend && (
              <Icon 
                icon={TrendIcons[trend]} 
                size="xs" 
                className={getTrendColor(trend)} 
              />
            )}
            {isLive && <LiveIndicator size="sm" />}
          </div>
        </div>
        
        <div className="flex items-baseline">
          <p className={cn(
            "text-2xl font-bold text-foreground font-mono tabular-nums",
            isAnimating && "opacity-70"
          )}>
            {typeof displayValue === 'number' ? Math.round(displayValue).toLocaleString() : displayValue}
          </p>
          {unit && (
            <p className="ml-1.5 text-xs text-muted-foreground">{unit}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
