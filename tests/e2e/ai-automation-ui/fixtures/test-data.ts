/**
 * AI Automation UI Test Data
 * Mock data for testing AI Automation UI components
 */

export const mockSuggestions = [
  {
    id: 'suggestion-1',
    description: 'Turn on living room lights at 7:00am every morning',
    status: 'draft',
    confidence: 0.85,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'suggestion-2',
    description: 'Turn off all lights when leaving home',
    status: 'refining',
    confidence: 0.92,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'suggestion-3',
    description: 'Set thermostat to 72°F when home',
    status: 'yaml_generated',
    confidence: 0.88,
    yaml: `alias: Set Thermostat When Home
trigger:
  - platform: state
    entity_id: binary_sensor.home_presence
    to: 'on'
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 72`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'suggestion-4',
    description: 'Turn on porch light at sunset',
    status: 'deployed',
    confidence: 0.95,
    yaml: `alias: Porch Light at Sunset
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.porch`,
    automation_id: 'automation-123',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export const mockConversations = [
  {
    id: 'conv-1',
    title: 'Living Room Automation',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    message_count: 5,
  },
  {
    id: 'conv-2',
    title: 'Thermostat Control',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    message_count: 3,
  },
];

export const mockMessages = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'Turn on the living room lights at 7am',
    timestamp: new Date().toISOString(),
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'I can help you create an automation for that. Let me generate the YAML.',
    timestamp: new Date().toISOString(),
    tool_calls: [
      {
        id: 'tool-1',
        name: 'create_automation',
        arguments: { entity_id: 'light.living_room', time: '07:00:00' },
      },
    ],
  },
];

export const mockPatterns = [
  {
    id: 'pattern-1',
    type: 'time_of_day',
    description: 'Lights turn on at 7:00am',
    frequency: 30,
    confidence: 0.9,
    entities: ['light.living_room'],
  },
  {
    id: 'pattern-2',
    type: 'co_occurrence',
    description: 'Thermostat adjusts when lights turn on',
    frequency: 25,
    confidence: 0.85,
    entities: ['light.living_room', 'climate.thermostat'],
  },
];

export const mockSynergies = [
  {
    id: 'synergy-1',
    devices: ['light.living_room', 'light.kitchen'],
    room: 'Living Room',
    type: 'lighting',
    confidence: 0.92,
    recommendation: 'Group these lights for coordinated control',
  },
  {
    id: 'synergy-2',
    devices: ['climate.thermostat', 'sensor.temperature'],
    room: 'Living Room',
    type: 'climate',
    confidence: 0.88,
    recommendation: 'Use temperature sensor for thermostat control',
  },
];

export const mockDeployedAutomations = [
  {
    id: 'automation-1',
    alias: 'Porch Light at Sunset',
    status: 'active',
    yaml: `alias: Porch Light at Sunset
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.porch`,
    created_at: new Date().toISOString(),
  },
  {
    id: 'automation-2',
    alias: 'Morning Lights',
    status: 'active',
    yaml: `alias: Morning Lights
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room`,
    created_at: new Date().toISOString(),
  },
];
