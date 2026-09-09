/**
 * Alert Banner Component (REFACTORED with UI Primitives)
 * Epic 17.4: Critical Alerting System
 * 
 * Displays active critical alerts using the new UI component library.
 */

import React, { useState, useEffect } from 'react';
import { Alert, AlertSeverity } from '../constants/alerts';
import { adminApi } from '../services/api';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn } from '@/lib/utils';

interface AlertBannerProps {
  darkMode: boolean;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ darkMode }): JSX.Element => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch active alerts
  useEffect(() => {
    const fetchAlerts = async (): Promise<void> => {
      try {
        const data = await adminApi.getActiveAlerts();
        setAlerts(data);
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  // Handle alert acknowledgment
  const acknowledgeAlert = async (alertId: string): Promise<void> => {
    try {
      await adminApi.acknowledgeAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  // Handle alert resolution
  const resolveAlert = async (alertId: string): Promise<void> => {
    try {
      await adminApi.resolveAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  if (loading || alerts.length === 0) {
    return <></>;
  }

  return (
    <div className="space-y-2 mb-6">
      {alerts.map((alert) => (
        <AlertBannerItem
          key={alert.id}
          alert={alert}
          onAcknowledge={acknowledgeAlert}
          onResolve={resolveAlert}
        />
      ))}
    </div>
  );
};

/**
 * AlertBannerItem Component
 */
interface AlertBannerItemProps {
  alert: Alert;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
}

const AlertBannerItem: React.FC<AlertBannerItemProps> = ({
  alert,
  onAcknowledge,
  onResolve,
}): JSX.Element => {
  const getSeverityVariant = (severity: AlertSeverity) => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return 'critical';
      case AlertSeverity.WARNING:
        return 'warning';
      case AlertSeverity.INFO:
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getSeverityIcon = (severity: AlertSeverity): string => {
    const icons = {
      [AlertSeverity.CRITICAL]: '🔴',
      [AlertSeverity.WARNING]: '⚠️',
      [AlertSeverity.INFO]: 'ℹ️',
    };
    return icons[severity] || 'ℹ️';
  };

  const getCardVariant = (severity: AlertSeverity) => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return 'critical';
      case AlertSeverity.WARNING:
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Card
      variant={getCardVariant(alert.severity)}
      className="animate-slide-in-right"
      role="alert"
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <span className="text-2xl mt-0.5">{getSeverityIcon(alert.severity)}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <Badge variant={getSeverityVariant(alert.severity)} size="sm">
                  {alert.severity}
                </Badge>
                <span className="text-xs text-muted-foreground">{alert.service}</span>
                {alert.metric && (
                  <span className="text-xs text-muted-foreground font-mono">{alert.metric}</span>
                )}
              </div>
              <p className="font-medium text-foreground mb-1">{alert.message}</p>
              <div className="text-xs text-muted-foreground flex items-center gap-3 flex-wrap">
                {alert.created_at && (
                  <span>Triggered: {new Date(alert.created_at).toLocaleString()}</span>
                )}
                {alert.current_value !== undefined && (
                  <span className="font-mono">
                    Current: {(alert.current_value ?? 0).toFixed(1)}
                    {alert.threshold_value !== undefined && ` (threshold: ${alert.threshold_value})`}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Button
              onClick={() => onAcknowledge(alert.id)}
              variant="secondary"
              size="sm"
            >
              Ack
            </Button>
            <Button
              onClick={() => onResolve(alert.id)}
              variant="success"
              size="sm"
            >
              Resolve
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default AlertBanner;
