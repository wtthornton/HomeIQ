/**
 * Mock Data for Data Sources Panel
 * 
 * Provides realistic mock data for demonstration and development
 * TODO: Replace with actual API calls to /api/v1/data-sources/status
 */

export interface DataSource {
  id: string;
  name: string;
  icon: string;
  status: 'healthy' | 'degraded' | 'error' | 'unknown';
  api_usage?: {
    calls_today: number;
    quota_limit?: number;
    quota_percentage?: number;
  };
  performance: {
    avg_response_time_ms: number;
    last_success?: string;
    retry_count?: number;
    error_count_24h: number;
  };
  cache?: {
    hit_rate_percentage: number;
    size_bytes: number;
    item_count: number;
  };
}

export const getMockDataSources = (): DataSource[] => {
  return [
    {
      id: 'weather-api',
      name: 'Weather API',
      icon: '☁️',
      status: 'healthy',
      api_usage: {
        calls_today: 47,
        quota_limit: 100,
        quota_percentage: 47
      },
      performance: {
        avg_response_time_ms: 245,
        last_success: new Date(Date.now() - 2 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      },
      cache: {
        hit_rate_percentage: 85,
        size_bytes: 524288,
        item_count: 42
      }
    },
    {
      id: 'carbon-intensity',
      name: 'Carbon Intensity',
      icon: '🌱',
      status: 'degraded',
      api_usage: {
        calls_today: 23,
        quota_percentage: 0
      },
      performance: {
        avg_response_time_ms: 2500,
        last_success: new Date(Date.now() - 15 * 60000).toISOString(),
        retry_count: 2,
        error_count_24h: 1
      },
      cache: {
        hit_rate_percentage: 72,
        size_bytes: 262144,
        item_count: 18
      }
    },
    {
      id: 'air-quality',
      name: 'Air Quality',
      icon: '💨',
      status: 'healthy',
      api_usage: {
        calls_today: 18,
        quota_limit: 50,
        quota_percentage: 36
      },
      performance: {
        avg_response_time_ms: 180,
        last_success: new Date(Date.now() - 5 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      },
      cache: {
        hit_rate_percentage: 90,
        size_bytes: 196608,
        item_count: 28
      }
    },
    {
      id: 'electricity-pricing',
      name: 'Electricity Pricing',
      icon: '⚡',
      status: 'healthy',
      api_usage: {
        calls_today: 12,
        quota_percentage: 0
      },
      performance: {
        avg_response_time_ms: 150,
        last_success: new Date(Date.now() - 10 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      }
    },
    {
      id: 'calendar',
      name: 'Calendar Service',
      icon: '📅',
      status: 'unknown',
      api_usage: {
        calls_today: 0,
        quota_percentage: 0
      },
      performance: {
        avg_response_time_ms: 0,
        error_count_24h: 0
      }
    },
    {
      id: 'smart-meter',
      name: 'Smart Meter',
      icon: '📈',
      status: 'healthy',
      api_usage: {
        calls_today: 35,
        quota_limit: 200,
        quota_percentage: 17.5
      },
      performance: {
        avg_response_time_ms: 220,
        last_success: new Date(Date.now() - 1 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      },
      cache: {
        hit_rate_percentage: 78,
        size_bytes: 409600,
        item_count: 52
      }
    },
    {
      id: 'blueprint-index',
      name: 'Blueprint Index',
      icon: '📘',
      status: 'healthy',
      api_usage: {
        calls_today: 156,
        quota_percentage: 0  // No quota limit for GitHub API with token
      },
      performance: {
        avg_response_time_ms: 320,
        last_success: new Date(Date.now() - 30 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      },
      cache: {
        hit_rate_percentage: 95,
        size_bytes: 2097152,  // 2MB cache of indexed blueprints
        item_count: 5247
      }
    },
    {
      id: 'rule-recommendation',
      name: 'Rule Recommendations',
      icon: '🤖',
      status: 'healthy',
      api_usage: {
        calls_today: 89,
        quota_percentage: 0  // Local ML model, no external API
      },
      performance: {
        avg_response_time_ms: 45,  // Fast local inference
        last_success: new Date(Date.now() - 3 * 60000).toISOString(),
        retry_count: 0,
        error_count_24h: 0
      },
      cache: {
        hit_rate_percentage: 82,
        size_bytes: 1048576,  // 1MB for cached recommendations
        item_count: 1024
      }
    }
  ];
};

