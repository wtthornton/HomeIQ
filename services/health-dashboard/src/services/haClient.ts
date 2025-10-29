/**
 * Home Assistant API Client
 * 
 * Provides methods to interact with Home Assistant REST API
 * for reading sensor states and entity data
 */

interface HAConfig {
  baseUrl: string;
  token: string;
}

interface HASensor {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
  last_changed: string;
  last_updated: string;
}

export class HAClient {
  private baseUrl: string;
  private token: string;

  constructor(config?: HAConfig) {
    // Get from environment variables or config
    this.baseUrl = config?.baseUrl || import.meta.env.VITE_HA_URL || 'http://192.168.1.86:8123';
    this.token = config?.token || import.meta.env.VITE_HA_TOKEN || '';
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HA API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get all states from Home Assistant
   */
  async getAllStates(): Promise<HASensor[]> {
    return this.request<HASensor[]>('/api/states');
  }

  /**
   * Get specific sensor state
   */
  async getSensorState(entityId: string): Promise<HASensor> {
    return this.request<HASensor>(`/api/states/${entityId}`);
  }

  /**
   * Get sensors matching a pattern
   * Useful for filtering Team Tracker or NHL sensors
   */
  async getSensorsByPattern(pattern: string): Promise<HASensor[]> {
    const allStates = await this.getAllStates();
    const regex = new RegExp(pattern);
    
    return allStates.filter(sensor => regex.test(sensor.entity_id));
  }

  /**
   * Get Team Tracker sensors
   * Filters for sensors with entity_id starting with "sensor.team_tracker_"
   */
  async getTeamTrackerSensors(): Promise<HASensor[]> {
    return this.getSensorsByPattern('^sensor\\.team_tracker_');
  }

  /**
   * Get NHL sensors (from hass-nhlapi integration)
   * Filters for sensors with entity_id starting with "sensor.nhl_"
   */
  async getNHLSensors(): Promise<HASensor[]> {
    return this.getSensorsByPattern('^sensor\\.nhl_');
  }
}

// Export singleton instance
export const haClient = new HAClient();
