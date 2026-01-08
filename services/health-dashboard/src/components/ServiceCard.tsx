import React from 'react';
import type { ServiceStatus } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Icon, StatusIndicator, TabIcons } from './ui/icons';
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

  // Map status for StatusIndicator
  const indicatorStatus = (status: string): 'healthy' | 'warning' | 'critical' | 'offline' => {
    switch (status) {
      case 'running': return 'healthy';
      case 'degraded': return 'warning';
      case 'error': return 'critical';
      case 'stopped': return 'offline';
      default: return 'offline';
    }
  };

  return (
    <Card variant={getCardVariant(service.status)} hover>
      {/* Header - Compact */}
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Icon icon={TabIcons.services} size="sm" className="text-muted-foreground flex-shrink-0" />
            <div className="min-w-0">
              <CardTitle className="truncate">{service.service}</CardTitle>
              {service.port && (
                <CardDescription className="font-mono">:{service.port}</CardDescription>
              )}
            </div>
          </div>
          <StatusIndicator status={indicatorStatus(service.status)} size="sm" />
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        {/* Metrics - Compact table */}
        <div className="space-y-1">
          {service.uptime && (
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Uptime</span>
              <span className="font-mono">{service.uptime}</span>
            </div>
          )}
          
          {service.metrics?.requests_per_minute !== undefined && (
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Req/min</span>
              <span className="font-mono">
                {(service.metrics.requests_per_minute ?? 0).toFixed(1)}
              </span>
            </div>
          )}
          
          {service.metrics?.error_rate !== undefined && (
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Errors</span>
              <span className={cn(
                "font-mono",
                service.metrics.error_rate > 5 
                  ? "text-status-critical" 
                  : "text-status-healthy"
              )}>
                {(service.metrics.error_rate ?? 0).toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Error Message - Compact */}
        {service.error && (
          <div className="p-2 rounded bg-destructive/10 text-destructive text-xs">
            {service.error}
          </div>
        )}

        {/* Container Status */}
        {containerStatus && containerStatus !== 'unknown' && containerStatus !== service.status && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground">Container</span>
            <Badge 
              variant={containerStatus === 'running' ? 'healthy' : 'critical'} 
              size="sm"
            >
              {containerStatus === 'running' ? 'Up' : 'Down'}
            </Badge>
          </div>
        )}

        {/* Container Actions - Compact */}
        {(onStart || onStop || onRestart) && (
          <div className="flex gap-1 pt-1">
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

      {/* Actions - Compact */}
      {(onViewDetails || onConfigure) && (
        <CardFooter>
          {onViewDetails && (
            <Button onClick={onViewDetails} size="sm" className="flex-1">
              Details
            </Button>
          )}
          {onConfigure && (
            <Button onClick={onConfigure} variant="secondary" size="sm" className="flex-1">
              Config
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
};
