/**
 * API Configuration
 * Centralized API endpoint management for all services
 */

// Determine if we're running in production (Docker) or development
const isProduction = import.meta.env.MODE === 'production';

// API Base URLs
export const API_CONFIG = {
  // AI Automation Service (main API)
  AI_AUTOMATION: isProduction ? '/api' : 'http://localhost:8018/api',

  // Device Intelligence Service (Team Tracker, Device Capabilities)
  DEVICE_INTELLIGENCE: isProduction ? '/api/device-intelligence' : 'http://localhost:8028/api',

  // Admin API
  ADMIN: isProduction ? '/api/admin' : 'http://localhost:8004/api',

  // Data API
  DATA: isProduction ? '/api/data' : 'http://localhost:8006/api',
};

// Team Tracker specific endpoints
export const TEAM_TRACKER_API = {
  STATUS: `${API_CONFIG.DEVICE_INTELLIGENCE}/team-tracker/status`,
  TEAMS: `${API_CONFIG.DEVICE_INTELLIGENCE}/team-tracker/teams`,
  DETECT: `${API_CONFIG.DEVICE_INTELLIGENCE}/team-tracker/detect`,
  SYNC: `${API_CONFIG.DEVICE_INTELLIGENCE}/team-tracker/sync-from-ha`,
};

// Helper function to get full API URL
export const getApiUrl = (service: keyof typeof API_CONFIG, path: string = ''): string => {
  const baseUrl = API_CONFIG[service];
  return path ? `${baseUrl}${path.startsWith('/') ? '' : '/'}${path}` : baseUrl;
};

export default API_CONFIG;
