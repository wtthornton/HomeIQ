/**
 * ConversationalDashboard Tests
 * Verifies rendering and key UI elements.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { ConversationalDashboard } from '../ConversationalDashboard';

// Mock API module
vi.mock('../../services/api', () => ({
  default: {
    getSuggestions: vi.fn().mockResolvedValue({ data: { suggestions: [] } }),
    getRefreshStatus: vi.fn().mockResolvedValue({ allowed: true, next_allowed_at: null }),
    getAnalysisStatus: vi.fn().mockResolvedValue({ analysis_run: null }),
    refreshSuggestions: vi.fn().mockResolvedValue({ success: true }),
    generateSuggestion: vi.fn().mockResolvedValue({}),
    refineSuggestion: vi.fn().mockResolvedValue({}),
    approveAndGenerateYAML: vi.fn().mockResolvedValue({}),
    redeploySuggestion: vi.fn().mockResolvedValue({}),
    rejectSuggestion: vi.fn().mockResolvedValue({}),
  },
  APIError: class extends Error { status = 0; },
}));

// Mock child components to isolate page tests
vi.mock('../../components/ConversationalSuggestionCard', () => ({
  ConversationalSuggestionCard: () => <div data-testid="suggestion-card">Card</div>,
}));

vi.mock('../../components/ask-ai/ReverseEngineeringLoader', () => ({
  ProcessLoader: () => null,
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

describe('ConversationalDashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page heading', async () => {
    renderWithProviders(<ConversationalDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/Automation Suggestions/)).toBeInTheDocument();
    });
  });

  it('shows status tab buttons', async () => {
    renderWithProviders(<ConversationalDashboard />);
    await waitFor(() => {
      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });
  });

  it('shows Refresh Suggestions button', async () => {
    renderWithProviders(<ConversationalDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Refresh Suggestions')).toBeInTheDocument();
    });
  });

  // === Accessibility ===

  it('page heading uses correct heading element', async () => {
    renderWithProviders(<ConversationalDashboard />);
    await waitFor(() => {
      const heading = screen.getByText(/Automation Suggestions/);
      expect(heading.tagName).toMatch(/^H[1-3]$/);
    });
  });

  it('Refresh button is a button element', async () => {
    renderWithProviders(<ConversationalDashboard />);
    await waitFor(() => {
      const btn = screen.getByText('Refresh Suggestions');
      expect(btn.closest('button')).toBeInTheDocument();
    });
  });
});
