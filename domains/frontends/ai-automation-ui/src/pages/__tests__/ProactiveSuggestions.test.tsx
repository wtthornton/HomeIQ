/**
 * ProactiveSuggestions Page Tests
 * Story 44.6: Proactive suggestions page coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { ProactiveSuggestions } from '../ProactiveSuggestions';

// Mock the store
vi.mock('../../store', () => ({
  useAppStore: () => ({ darkMode: false }),
}));

// Mock proactiveApi
const mockGetSuggestions = vi.fn();
const mockGetStats = vi.fn();
vi.mock('../../services/proactiveApi', () => ({
  proactiveApi: {
    getSuggestions: (...args: unknown[]) => mockGetSuggestions(...args),
    getStats: (...args: unknown[]) => mockGetStats(...args),
    updateSuggestionStatus: vi.fn(),
    deleteSuggestion: vi.fn(),
    sendToAgent: vi.fn(),
    triggerGeneration: vi.fn().mockResolvedValue({ success: true, results: {} }),
  },
  ProactiveAPIError: class extends Error {
    status = 0;
  },
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
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

// Mock child components
vi.mock('../../components/proactive', () => ({
  ProactiveSuggestionCard: ({ suggestion }: any) => (
    <div data-testid="suggestion-card">{suggestion.prompt}</div>
  ),
  ProactiveStats: ({ stats, loading }: any) => (
    <div data-testid="proactive-stats">{loading ? 'Loading stats...' : stats?.total ?? 0}</div>
  ),
  ProactiveFilters: () => <div data-testid="proactive-filters">Filters</div>,
}));

// Mock LoadingSpinner
vi.mock('../../components/LoadingSpinner', () => ({
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading</div>,
}));

const mockSuggestionData = [
  {
    id: 'ps1',
    prompt: 'Turn off AC when temperature drops',
    context_type: 'weather' as const,
    status: 'pending' as const,
    quality_score: 0.8,
    context_metadata: {},
    prompt_metadata: {},
    created_at: '2026-03-10T00:00:00Z',
    updated_at: '2026-03-10T00:00:00Z',
  },
];

describe('ProactiveSuggestions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetSuggestions.mockResolvedValue({
      suggestions: mockSuggestionData,
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockGetStats.mockResolvedValue({
      total: 5,
      by_status: { pending: 3, approved: 2 },
      by_context_type: { weather: 3, sports: 2 },
    });
  });

  it('renders the page heading', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('Proactive Suggestions')).toBeInTheDocument();
    });
  });

  it('renders suggestion cards from API', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('Turn off AC when temperature drops')).toBeInTheDocument();
    });
  });

  it('renders stats component', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    await waitFor(() => {
      expect(screen.getByTestId('proactive-stats')).toBeInTheDocument();
    });
  });

  it('renders filters component', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    await waitFor(() => {
      expect(screen.getByTestId('proactive-filters')).toBeInTheDocument();
    });
  });

  it('shows loading spinner while fetching', () => {
    mockGetSuggestions.mockReturnValue(new Promise(() => {}));
    mockGetStats.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ProactiveSuggestions />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows empty state when no suggestions', async () => {
    mockGetSuggestions.mockResolvedValue({
      suggestions: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    renderWithProviders(<ProactiveSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('No Proactive Suggestions Yet')).toBeInTheDocument();
    });
  });

  it('renders Generate button', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    // Button contains emoji + "Generate" text, and there's also "Generate Sample Suggestion" in empty state
    // When suggestions exist, it shows the header Generate button
    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      const generateBtn = buttons.find(b => b.textContent?.includes('Generate'));
      expect(generateBtn).toBeTruthy();
    });
  });

  it('renders Refresh button', async () => {
    renderWithProviders(<ProactiveSuggestions />);
    expect(screen.getByText(/Refresh/)).toBeInTheDocument();
  });
});
