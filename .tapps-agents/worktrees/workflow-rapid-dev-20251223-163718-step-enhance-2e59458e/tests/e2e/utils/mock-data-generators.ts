/**
 * Mock Data Generators for AI Automation Testing
 * 
 * Generates realistic test data for suggestions, patterns, automations, and device capabilities
 */

export interface MockDataOptions {
  count?: number;
  category?: 'energy' | 'comfort' | 'security' | 'convenience';
  confidence?: 'high' | 'medium' | 'low';
  approved?: boolean;
  pattern_type?: 'time-of-day' | 'co-occurrence';
}

export interface Suggestion {
  id: string;
  title: string;
  description: string;
  category: 'energy' | 'comfort' | 'security' | 'convenience';
  confidence: 'high' | 'medium' | 'low';
  pattern_type: 'time-of-day' | 'co-occurrence';
  approved: boolean;
  created_at: string;
}

export interface Pattern {
  id: string;
  pattern_type: 'time-of-day' | 'co-occurrence';
  devices: string[];
  time_range?: string;
  confidence: 'high' | 'medium' | 'low';
  occurrences: number;
  created_at: string;
}

export interface Automation {
  id: string;
  suggestion_id: string;
  ha_automation_id: string;
  title: string;
  deployed_at: string;
  status: 'active' | 'inactive';
}

export interface DeviceCapability {
  device_id: string;
  device_name: string;
  model: string;
  manufacturer: string;
  total_capabilities: number;
  used_capabilities: number;
  utilization_percentage: number;
  unused_features: string[];
}

const SUGGESTION_TEMPLATES = [
  {
    title: 'Turn off bedroom lights at bedtime',
    description: 'Detected consistent manual light shutdown at 11 PM every night for the past 30 days. Average bedtime is 11:05 PM with 95% consistency.',
    category: 'energy' as const,
    pattern_type: 'time-of-day' as const,
  },
  {
    title: 'Morning coffee automation',
    description: 'Coffee maker and kitchen lights are turned on together 95% of mornings at 7 AM. Strong co-occurrence pattern detected.',
    category: 'convenience' as const,
    pattern_type: 'co-occurrence' as const,
  },
  {
    title: 'Lower thermostat when away',
    description: 'Temperature is manually lowered when leaving home. Detected 18 times in last 30 days. Could save ~15% on heating costs.',
    category: 'energy' as const,
    pattern_type: 'co-occurrence' as const,
  },
  {
    title: 'Lock doors at night',
    description: 'Front door is manually locked at 10:30 PM every night. Detected consistent pattern for 45 consecutive days.',
    category: 'security' as const,
    pattern_type: 'time-of-day' as const,
  },
  {
    title: 'Dim living room lights at sunset',
    description: 'Living room lights are dimmed to 40% at sunset 85% of the time. Detected seasonal adjustment pattern.',
    category: 'comfort' as const,
    pattern_type: 'time-of-day' as const,
  },
  {
    title: 'Turn on porch light at dusk',
    description: 'Porch light is manually turned on within 15 minutes of sunset 92% of days. Consistent pattern detected.',
    category: 'security' as const,
    pattern_type: 'time-of-day' as const,
  },
  {
    title: 'Close blinds during hot afternoons',
    description: 'Blinds are closed when temperature exceeds 85°F. Detected 23 times in summer months. Reduces cooling costs.',
    category: 'energy' as const,
    pattern_type: 'co-occurrence' as const,
  },
  {
    title: 'Turn off all lights when leaving',
    description: 'All lights are turned off when garage door closes. Detected 156 times over 90 days with 98% consistency.',
    category: 'energy' as const,
    pattern_type: 'co-occurrence' as const,
  },
  {
    title: 'Adjust thermostat for bedtime',
    description: 'Thermostat lowered to 68°F at 10 PM every night. Detected consistent pattern for 60 days.',
    category: 'comfort' as const,
    pattern_type: 'time-of-day' as const,
  },
  {
    title: 'Enable security mode at night',
    description: 'Security system armed when all lights are off after 11 PM. Detected 42 times in last 45 days.',
    category: 'security' as const,
    pattern_type: 'co-occurrence' as const,
  },
];

const DEVICE_NAMES = [
  'Living Room Light',
  'Bedroom Light',
  'Kitchen Light',
  'Front Door Lock',
  'Garage Door',
  'Thermostat',
  'Coffee Maker',
  'Porch Light',
  'Living Room Blinds',
  'Security System',
];

export class MockDataGenerator {
  /**
   * Generate realistic AI automation suggestions
   * @param options - Configuration options
   * @returns Array of mock suggestions
   */
  static generateSuggestions(options: MockDataOptions = {}): Suggestion[] {
    const {
      count = 5,
      category,
      confidence,
      approved = false,
      pattern_type
    } = options;

    return Array.from({ length: count }, (_, i) => {
      const template = SUGGESTION_TEMPLATES[i % SUGGESTION_TEMPLATES.length];
      return {
        id: `sug-${Date.now()}-${i}`,
        title: template.title,
        description: template.description,
        category: category || template.category,
        confidence: confidence || this.randomConfidence(),
        pattern_type: pattern_type || template.pattern_type,
        approved,
        created_at: new Date(Date.now() - i * 86400000).toISOString(),
      };
    });
  }

  /**
   * Generate realistic pattern data
   * @param options - Configuration options
   * @returns Array of mock patterns
   */
  static generatePatterns(options: MockDataOptions = {}): Pattern[] {
    const {
      count = 5,
      confidence,
      pattern_type
    } = options;

    return Array.from({ length: count }, (_, i) => {
      const type = pattern_type || (i % 2 === 0 ? 'time-of-day' : 'co-occurrence');
      const deviceCount = type === 'time-of-day' ? 1 : 2 + (i % 3);
      
      return {
        id: `pattern-${Date.now()}-${i}`,
        pattern_type: type,
        devices: this.randomDevices(deviceCount),
        time_range: type === 'time-of-day' ? this.randomTimeRange() : undefined,
        confidence: confidence || this.randomConfidence(),
        occurrences: 10 + Math.floor(Math.random() * 90),
        created_at: new Date(Date.now() - i * 86400000).toISOString(),
      };
    });
  }

  /**
   * Generate realistic deployed automation data
   * @param options - Configuration options
   * @returns Array of mock automations
   */
  static generateDeployedAutomations(options: MockDataOptions = {}): Automation[] {
    const { count = 5 } = options;

    return Array.from({ length, count }, (_, i) => ({
      id: `auto-${Date.now()}-${i}`,
      suggestion_id: `sug-${i}`,
      ha_automation_id: `automation.ai_generated_${i}`,
      title: SUGGESTION_TEMPLATES[i % SUGGESTION_TEMPLATES.length].title,
      deployed_at: new Date(Date.now() - i * 86400000).toISOString(),
      status: i % 5 === 0 ? 'inactive' : 'active',
    }));
  }

  /**
   * Generate realistic device capability data
   * @param options - Configuration options
   * @returns Array of mock device capabilities
   */
  static generateDeviceCapabilities(options: MockDataOptions = {}): DeviceCapability[] {
    const { count = 5 } = options;

    const manufacturers = ['Inovelli', 'Aqara', 'IKEA', 'Philips', 'Sonoff'];
    const models = ['LZW31-SN', 'WXKG11LM', 'E1743', 'Hue Bulb', 'SNZB-01'];
    const features = [
      'LED indicator',
      'Power monitoring',
      'Scene control',
      'Multi-tap',
      'Long press',
      'Double tap',
      'Temperature sensor',
      'Humidity sensor',
    ];

    return Array.from({ length: count }, (_, i) => {
      const totalCaps = 5 + Math.floor(Math.random() * 10);
      const usedCaps = Math.floor(Math.random() * totalCaps);
      const utilization = Math.round((usedCaps / totalCaps) * 100);

      return {
        device_id: `device-${i}`,
        device_name: DEVICE_NAMES[i % DEVICE_NAMES.length],
        model: models[i % models.length],
        manufacturer: manufacturers[i % manufacturers.length],
        total_capabilities: totalCaps,
        used_capabilities: usedCaps,
        utilization_percentage: utilization,
        unused_features: this.randomFeatures(features, totalCaps - usedCaps),
      };
    });
  }

  /**
   * Generate random confidence level
   */
  private static randomConfidence(): 'high' | 'medium' | 'low' {
    const rand = Math.random();
    if (rand > 0.7) return 'high';
    if (rand > 0.4) return 'medium';
    return 'low';
  }

  /**
   * Select random devices
   */
  private static randomDevices(count: number): string[] {
    const shuffled = [...DEVICE_NAMES].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  }

  /**
   * Generate random time range
   */
  private static randomTimeRange(): string {
    const hours = ['7:00 AM', '10:00 AM', '3:00 PM', '7:00 PM', '10:00 PM', '11:00 PM'];
    return hours[Math.floor(Math.random() * hours.length)];
  }

  /**
   * Select random features
   */
  private static randomFeatures(allFeatures: string[], count: number): string[] {
    const shuffled = [...allFeatures].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(count, allFeatures.length));
  }
}

