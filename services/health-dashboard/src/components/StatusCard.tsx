import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { StatusIndicator } from './ui/icons';
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

// Map status to StatusIndicator compatible status
const mapStatus = (status: string): 'healthy' | 'warning' | 'critical' | 'offline' => {
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
      return 'offline';
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
      className={cn("", className)}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          <StatusIndicator status={mapStatus(status)} size="sm" />
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            {value !== undefined && (
              <p className="text-2xl font-bold text-foreground font-mono tabular-nums">
                {value}
              </p>
            )}
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
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
