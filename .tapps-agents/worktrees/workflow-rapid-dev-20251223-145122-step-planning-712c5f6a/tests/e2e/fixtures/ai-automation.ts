/**
 * Test Fixtures for AI Automation Testing
 * 
 * Centralized mock data and fixtures for consistent testing
 */

import { MockDataGenerator, Suggestion, Pattern, Automation, DeviceCapability } from '../utils/mock-data-generators';

/**
 * Default suggestion fixtures for testing
 */
export const DEFAULT_SUGGESTIONS: Suggestion[] = MockDataGenerator.generateSuggestions({
  count: 10,
});

/**
 * High confidence energy suggestions
 */
export const HIGH_CONFIDENCE_ENERGY_SUGGESTIONS: Suggestion[] = MockDataGenerator.generateSuggestions({
  count: 5,
  category: 'energy',
  confidence: 'high',
});

/**
 * Default pattern fixtures
 */
export const DEFAULT_PATTERNS: Pattern[] = MockDataGenerator.generatePatterns({
  count: 8,
});

/**
 * Default deployed automations
 */
export const DEFAULT_AUTOMATIONS: Automation[] = MockDataGenerator.generateDeployedAutomations({
  count: 5,
});

/**
 * Default device capabilities
 */
export const DEFAULT_DEVICE_CAPABILITIES: DeviceCapability[] = MockDataGenerator.generateDeviceCapabilities({
  count: 10,
});

/**
 * Export all mock data generators for custom usage
 */
export { MockDataGenerator };
export type { Suggestion, Pattern, Automation, DeviceCapability };

