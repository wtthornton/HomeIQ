/**
 * Deployed Page Tests
 * Verifies rendering and key UI elements.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { Deployed } from '../Deployed';

// Mock API modules
vi.mock('../../services/api', () => ({
  default: {
    getSuggestions: vi.fn().mockResolvedValue({ data: { suggestions: [] } }),
    getDeployedAutomations: vi.fn().mockResolvedValue({ automations: [] }),
  },
  APIError: class extends Error { status = 0; },
}));

vi.mock('../../services/haAiAgentApi', () => ({
  getDeployedAutomations: vi.fn().mockResolvedValue({ automations: [] }),
}));

vi.mock('../../components/LoadingSpinner', () => ({
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading</div>,
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
      button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    },
  };
});

describe('Deployed Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the deployed page heading', async () => {
    renderWithProviders(<Deployed />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });
  });
});
