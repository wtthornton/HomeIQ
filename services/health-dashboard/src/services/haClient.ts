/**
 * Home Assistant API Client
 * 
 * Provides methods to interact with Home Assistant REST API
 * for reading sensor states and entity data
 */

interface HAConfig {
  baseUrl?: string;
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

  constructor(config?: HAConfig) {
    this.baseUrl = config?.baseUrl || '/api/v1/ha-proxy';
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HA API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  private async fetchStates(query: string = ''): Promise<HASensor[]> {
    return this.request<HASensor[]>(`/states${query}`);
  }

  /**
   * Get all states from Home Assistant
   */
  async getAllStates(): Promise<HASensor[]> {
    return this.fetchStates();
  }

  /**
   * Get specific sensor state
   */
  async getSensorState(entityId: string): Promise<HASensor> {
    return this.request<HASensor>(`/states/${encodeURIComponent(entityId)}`);
  }

  /**
   * Get sensors matching a pattern
   * Useful for filtering Team Tracker or NHL sensors
   */
  async getSensorsByPattern(pattern: string): Promise<HASensor[]> {
    const states = await this.getAllStates();
    try {
      // Escape special regex characters if pattern contains them unexpectedly
      const regex = new RegExp(pattern);
      return states.filter(sensor => regex.test(sensor.entity_id));
    } catch (e) {
      // If pattern is invalid regex, fall back to string includes
      console.warn(`Invalid regex pattern "${pattern}", falling back to string match`);
      return states.filter(sensor => sensor.entity_id.includes(pattern));
    }
  }

  /**
   * Get Team Tracker sensors
   * Filters for sensors with entity_id starting with "sensor.team_tracker_"
   */
  async getTeamTrackerSensors(): Promise<HASensor[]> {
    return this.fetchStates('?entity_prefix=sensor.team_tracker_');
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
