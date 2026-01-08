import React from 'react';
import type { ServiceStatus } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn } from '@/lib/utils';

interface ServiceCardProps {
  service: ServiceStatus;
  icon: string;
  darkMode: boolean;
  onViewDetails?: () => void;
  onConfigure?: () => void;
  onStart?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
  containerStatus?: string;
  isOperating?: boolean;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({
  service,
  icon,
  onViewDetails,
  onConfigure,
  onStart,
  onStop,
  onRestart,
  containerStatus,
  isOperating = false,
}) => {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'healthy';
      case 'stopped':
        return 'offline';
      case 'error':
        return 'critical';
      case 'degraded':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  const getCardVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'healthy';
      case 'error':
        return 'critical';
      case 'degraded':
        return 'warning';
      case 'stopped':
        return 'offline';
      default:
        return 'default';
    }
  };

  return (
    <Card variant={getCardVariant(service.status)} hover className="animate-fade-in">
      {/* Header */}
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="text-3xl">{icon}</div>
            <div>
              <CardTitle className="text-lg">{service.service}</CardTitle>
              {service.port && (
                <CardDescription>Port {service.port}</CardDescription>
              )}
            </div>
          </div>
          <Badge variant={getStatusVariant(service.status)} dot={service.status === 'running'}>
            {service.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Metrics */}
        <div className="space-y-2">
          {service.uptime && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Uptime</span>
              <span className="text-sm font-medium font-mono">{service.uptime}</span>
            </div>
          )}
          
          {service.metrics?.requests_per_minute !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Requests/min</span>
              <span className="text-sm font-medium font-mono">
                {(service.metrics.requests_per_minute ?? 0).toFixed(1)}
              </span>
            </div>
          )}
          
          {service.metrics?.error_rate !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Error Rate</span>
              <span className={cn(
                "text-sm font-medium font-mono",
                service.metrics.error_rate > 5 
                  ? "text-status-critical" 
                  : "text-status-healthy"
              )}>
                {(service.metrics.error_rate ?? 0).toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Error Message */}
        {service.error && (
          <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm">
            {service.error}
          </div>
        )}

        {/* Container Status */}
        {containerStatus && containerStatus !== 'unknown' && containerStatus !== service.status && (
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Container:</span>
            <Badge 
              variant={containerStatus === 'running' ? 'healthy' : 'critical'} 
              size="sm"
            >
              {containerStatus === 'running' ? 'Running' : 'Stopped'}
            </Badge>
          </div>
        )}

        {/* Container Actions */}
        {(onStart || onStop || onRestart) && (
          <div className="flex gap-1">
            {containerStatus === 'stopped' && onStart && (
              <Button
                onClick={onStart}
                disabled={isOperating}
                variant="success"
                size="sm"
                loading={isOperating}
              >
                Start
              </Button>
            )}
            
            {containerStatus === 'running' && onStop && (
              <Button
                onClick={onStop}
                disabled={isOperating}
                variant="destructive"
                size="sm"
                loading={isOperating}
              >
                Stop
              </Button>
            )}
            
            {containerStatus === 'running' && onRestart && (
              <Button
                onClick={onRestart}
                disabled={isOperating}
                variant="secondary"
                size="sm"
                loading={isOperating}
              >
                Restart
              </Button>
            )}
          </div>
        )}
      </CardContent>

      {/* Actions */}
      <CardFooter className="gap-2">
        {onViewDetails && (
          <Button onClick={onViewDetails} className="flex-1">
            View Details
          </Button>
        )}
        {onConfigure && (
          <Button onClick={onConfigure} variant="secondary" className="flex-1">
            Configure
          </Button>
        )}
      </CardFooter>
    </Card>
  );
};
