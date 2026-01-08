import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { cn } from '@/lib/utils';

interface StatusCardProps {
  title: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'connected' | 'disconnected';
  value?: string | number;
  subtitle?: string;
  className?: string;
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'healthy':
    case 'connected':
      return 'healthy';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
    case 'disconnected':
      return 'critical';
    default:
      return 'secondary';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'healthy':
    case 'connected':
      return '✅';
    case 'degraded':
      return '⚠️';
    case 'unhealthy':
    case 'disconnected':
      return '❌';
    default:
      return '❓';
  }
};

const getCardVariant = (status: string) => {
  switch (status) {
    case 'healthy':
    case 'connected':
      return 'healthy';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
    case 'disconnected':
      return 'critical';
    default:
      return 'default';
  }
};

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  status,
  value,
  subtitle,
  className = ''
}) => {
  return (
    <Card 
      variant={getCardVariant(status)} 
      className={cn("animate-fade-in", className)}
    >
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          <span className="text-lg">{getStatusIcon(status)}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            {value !== undefined && (
              <p className="text-2xl font-bold text-foreground font-display tabular-nums">
                {value}
              </p>
            )}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          
          <Badge variant={getStatusVariant(status)} size="sm">
            {status}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
};
