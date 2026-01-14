import type { MockResponse } from '../../../shared/helpers/api-helpers';
import {
  mockSuggestions,
  mockConversations,
  mockMessages,
  mockPatterns,
  mockSynergies,
  mockDeployedAutomations,
} from './test-data';

/**
 * AI Automation UI API Mocks
 * Pre-configured API response mocks for AI Automation UI endpoints
 */

export const automationMocks: Record<string, MockResponse> = {
  '/api/suggestions': {
    status: 200,
    body: {
      suggestions: mockSuggestions,
      total: mockSuggestions.length,
    },
  },
  '/api/suggestions/draft': {
    status: 200,
    body: {
      suggestions: mockSuggestions.filter((s) => s.status === 'draft'),
      total: 1,
    },
  },
  '/api/suggestions/refining': {
    status: 200,
    body: {
      suggestions: mockSuggestions.filter((s) => s.status === 'refining'),
      total: 1,
    },
  },
  '/api/suggestions/yaml_generated': {
    status: 200,
    body: {
      suggestions: mockSuggestions.filter((s) => s.status === 'yaml_generated'),
      total: 1,
    },
  },
  '/api/suggestions/deployed': {
    status: 200,
    body: {
      suggestions: mockSuggestions.filter((s) => s.status === 'deployed'),
      total: 1,
    },
  },
  '/api/conversations': {
    status: 200,
    body: {
      conversations: mockConversations,
      total: mockConversations.length,
    },
  },
  '/api/conversations/*/messages': {
    status: 200,
    body: {
      messages: mockMessages,
      total: mockMessages.length,
    },
  },
  '/api/patterns': {
    status: 200,
    body: {
      patterns: mockPatterns,
      total: mockPatterns.length,
    },
  },
  '/api/synergies': {
    status: 200,
    body: {
      synergies: mockSynergies,
      total: mockSynergies.length,
    },
  },
  '/api/automations/deployed': {
    status: 200,
    body: {
      automations: mockDeployedAutomations,
      total: mockDeployedAutomations.length,
    },
  },
  '/api/deploy/automations': {
    status: 200,
    body: {
      automations: mockDeployedAutomations,
    },
  },
  '/api/chat': {
    status: 200,
    body: {
      message: {
        role: 'assistant',
        content: 'I can help you create that automation.',
        tool_calls: [],
      },
    },
  },
};

export const errorMocks: Record<string, MockResponse> = {
  '/api/suggestions': {
    status: 500,
    body: {
      error: 'Internal Server Error',
      message: 'Failed to fetch suggestions',
    },
  },
  '/api/chat': {
    status: 503,
    body: {
      error: 'Service Unavailable',
      message: 'AI service is temporarily unavailable',
    },
  },
};

export const loadingMocks: Record<string, MockResponse> = {
  '/api/suggestions': {
    status: 200,
    body: {
      suggestions: [],
      total: 0,
    },
    delay: 5000, // Simulate slow response
  },
};
