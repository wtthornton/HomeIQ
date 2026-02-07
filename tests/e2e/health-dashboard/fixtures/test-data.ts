/**
 * Health Dashboard Test Data
 * Mock data for testing Health Dashboard components
 */

export const mockServices = [
  {
    id: 'websocket-ingestion',
    name: 'WebSocket Ingestion',
    status: 'healthy',
    port: 8001,
    health: {
      status: 'healthy',
      uptime: 3600,
      last_check: new Date().toISOString(),
    },
  },
  {
    id: 'data-api',
    name: 'Data API',
    status: 'healthy',
    port: 8006,
    health: {
      status: 'healthy',
      uptime: 3600,
      last_check: new Date().toISOString(),
    },
  },
  {
    id: 'ai-automation-service',
    name: 'AI Automation Service',
    status: 'degraded',
    port: 8024,
    health: {
      status: 'degraded',
      uptime: 1800,
      last_check: new Date().toISOString(),
    },
  },
];

export const mockDevices = [
  {
    id: 'device-1',
    name: 'Living Room Light',
    type: 'light',
    manufacturer: 'Philips',
    model: 'Hue',
    area: 'Living Room',
    entities: [
      { entity_id: 'light.living_room', state: 'on', attributes: {} },
    ],
  },
  {
    id: 'device-2',
    name: 'Thermostat',
    type: 'climate',
    manufacturer: 'Nest',
    model: 'Learning Thermostat',
    area: 'Living Room',
    entities: [
      { entity_id: 'climate.thermostat', state: 'heat', attributes: { temperature: 72 } },
    ],
  },
];

export const mockEvents = [
  {
    event_id: 'event-1',
    event_type: 'state_changed',
    entity_id: 'light.living_room',
    state: 'on',
    timestamp: new Date().toISOString(),
    attributes: {},
  },
  {
    event_id: 'event-2',
    event_type: 'state_changed',
    entity_id: 'climate.thermostat',
    state: 'heat',
    timestamp: new Date().toISOString(),
    attributes: { temperature: 72 },
  },
];

export const mockMetrics = {
  total_events: 1000,
  active_devices: 50,
  services_healthy: 12,
  services_total: 15,
  uptime: 86400,
};

export const mockAlerts = [
  {
    id: 'alert-1',
    severity: 'warning',
    message: 'Service degradation detected',
    service: 'ai-automation-service',
    timestamp: new Date().toISOString(),
    acknowledged: false,
  },
  {
    id: 'alert-2',
    severity: 'error',
    message: 'API connection failed',
    service: 'data-api',
    timestamp: new Date().toISOString(),
    acknowledged: true,
  },
];

export const mockSportsData = {
  teams: [
    {
      id: 'team-1',
      name: 'Dallas Cowboys',
      league: 'NFL',
      games: [
        {
          id: 'game-1',
          status: 'completed',
          home_team: 'Dallas Cowboys',
          away_team: 'New York Giants',
          home_score: 28,
          away_score: 14,
          date: new Date().toISOString(),
        },
      ],
    },
  ],
};

export const mockAnalyticsData = {
  metrics: [
    { name: 'Events per hour', value: 100, trend: 'up' },
    { name: 'Active devices', value: 50, trend: 'stable' },
    { name: 'API calls', value: 500, trend: 'up' },
  ],
  timeRange: '24h',
};

export const mockSynergies = [
  {
    id: 'syn-1',
    name: 'Light + Motion',
    confidence: 0.85,
    devices: ['light.living_room', 'binary_sensor.motion'],
    description: 'Lights turn on when motion detected',
  },
  {
    id: 'syn-2',
    name: 'Thermostat + Presence',
    confidence: 0.72,
    devices: ['climate.thermostat', 'device_tracker.person'],
    description: 'Temperature adjusts when someone arrives',
  },
];
