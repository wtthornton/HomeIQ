/**
 * Mock Data for Alerts Panel
 * 
 * Provides realistic alert history for demonstration
 * TODO: Replace with actual API calls to /api/v1/alerts
 */

export interface Alert {
  id: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  service: string;
  title: string;
  message: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
}

export const getMockAlerts = (): Alert[] => {
  return [
    {
      id: '1',
      timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
      severity: 'warning',
      service: 'weather-api',
      title: 'High API Response Time',
      message: 'Weather API response time exceeded threshold (2.5s > 1s)',
      acknowledged: true,
      acknowledgedBy: 'admin',
      acknowledgedAt: new Date(Date.now() - 1.5 * 3600000).toISOString()
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
      severity: 'error',
      service: 'carbon-intensity',
      title: 'API Connection Failed',
      message: 'Failed to connect to Carbon Intensity API (timeout after 30s)',
      acknowledged: true,
      acknowledgedBy: 'admin',
      acknowledgedAt: new Date(Date.now() - 4 * 3600000).toISOString()
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
      severity: 'info',
      service: 'influxdb',
      title: 'Database Backup Completed',
      message: 'Automated backup completed successfully (2.4 GB)',
      acknowledged: false
    },
    {
      id: '5',
      timestamp: new Date(Date.now() - 12 * 3600000).toISOString(),
      severity: 'warning',
      service: 'websocket-ingestion',
      title: 'Event Processing Lag',
      message: 'Event processing queue building up (250 events pending)',
      acknowledged: true,
      acknowledgedBy: 'admin',
      acknowledgedAt: new Date(Date.now() - 11 * 3600000).toISOString()
    }
  ];
};

