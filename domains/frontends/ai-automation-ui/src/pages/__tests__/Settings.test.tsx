/**
 * Settings Page Tests
 * Verifies rendering and key form elements.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { Settings } from '../Settings';

// Mock API modules
vi.mock('../../api/settings', () => ({
  defaultSettings: {
    scheduleEnabled: true,
    scheduleTime: '03:00',
    minConfidence: 70,
    maxSuggestions: 10,
    enabledCategories: { lighting: true, climate: true, security: true },
    budgetLimit: 10,
    enableParallelModelTesting: false,
    notificationsEnabled: false,
    notificationEmail: '',
    softPromptEnabled: false,
    softPromptModelDir: '',
    softPromptConfidenceThreshold: 0.7,
    guardrailEnabled: false,
    guardrailModelName: '',
    guardrailThreshold: 0.5,
  },
  getSettings: vi.fn().mockResolvedValue({
    scheduleEnabled: true,
    scheduleTime: '03:00',
    minConfidence: 70,
    maxSuggestions: 10,
    enabledCategories: { lighting: true, climate: true, security: true },
    budgetLimit: 10,
    enableParallelModelTesting: false,
    notificationsEnabled: false,
    notificationEmail: '',
    softPromptEnabled: false,
    softPromptModelDir: '',
    softPromptConfidenceThreshold: 0.7,
    guardrailEnabled: false,
    guardrailModelName: '',
    guardrailThreshold: 0.5,
  }),
  updateSettings: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../components/TeamTrackerSettings', () => ({
  TeamTrackerSettings: () => <div data-testid="team-tracker-settings">TeamTracker</div>,
}));

vi.mock('../../components/ModelComparisonMetrics', () => ({
  ModelComparisonMetricsComponent: () => <div data-testid="model-metrics">ModelMetrics</div>,
}));

vi.mock('../../components/PreferenceSettings', () => ({
  PreferenceSettings: () => <div data-testid="preference-settings">Preferences</div>,
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
      button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    },
  };
});

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the settings container', async () => {
    renderWithProviders(<Settings />);
    await waitFor(() => {
      expect(screen.getByTestId('settings-container')).toBeInTheDocument();
    });
  });

  it('shows settings heading', async () => {
    renderWithProviders(<Settings />);
    await waitFor(() => {
      expect(screen.getByText(/Settings/)).toBeInTheDocument();
    });
  });

  it('renders the settings form', async () => {
    renderWithProviders(<Settings />);
    await waitFor(() => {
      expect(screen.getByTestId('settings-form')).toBeInTheDocument();
    });
  });

  it('shows Analysis Schedule section', async () => {
    renderWithProviders(<Settings />);
    await waitFor(() => {
      expect(screen.getByText(/Analysis Schedule/)).toBeInTheDocument();
    });
  });

  it('shows Save Settings button', async () => {
    renderWithProviders(<Settings />);
    await waitFor(() => {
      expect(screen.getByText(/Save Settings/)).toBeInTheDocument();
    });
  });
});
