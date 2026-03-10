/**
 * BlueprintSuggestions Page Tests
 * Story 44.6: Blueprint suggestions page coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { BlueprintSuggestions } from '../BlueprintSuggestions';

// Mock blueprintSuggestionsApi
const mockGetSuggestions = vi.fn();
const mockGetStats = vi.fn();
vi.mock('../../services/blueprintSuggestionsApi', () => ({
  getSuggestions: (...args: unknown[]) => mockGetSuggestions(...args),
  acceptSuggestion: vi.fn(),
  declineSuggestion: vi.fn(),
  getStats: (...args: unknown[]) => mockGetStats(...args),
  deleteAllSuggestions: vi.fn(),
  generateSuggestions: vi.fn(),
  BlueprintSuggestionsAPIError: class extends Error {
    status = 0;
  },
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

const mockSuggestions = [
  {
    id: 's1',
    blueprint_id: 'bp1',
    blueprint_name: 'Motion Light',
    blueprint_description: 'Turn on lights with motion',
    suggestion_score: 0.85,
    matched_devices: [
      { entity_id: 'light.kitchen', domain: 'light', friendly_name: 'Kitchen Light' },
    ],
    use_case: 'convenience',
    status: 'pending',
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  },
];

const mockStats = {
  total_suggestions: 10,
  pending_count: 5,
  accepted_count: 3,
  declined_count: 2,
  average_score: 0.75,
  min_score: 0.5,
  max_score: 0.95,
};

describe('BlueprintSuggestions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetSuggestions.mockResolvedValue({
      suggestions: mockSuggestions,
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockGetStats.mockResolvedValue(mockStats);
  });

  it('renders the page heading', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('Blueprint Suggestions')).toBeInTheDocument();
    });
  });

  it('renders suggestion list from API', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('Motion Light')).toBeInTheDocument();
    });
  });

  it('shows suggestion score', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument();
    });
  });

  it('shows matched devices', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText(/Kitchen Light/)).toBeInTheDocument();
    });
  });

  it('shows stats when loaded', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument(); // total
      expect(screen.getByText('5')).toBeInTheDocument(); // pending
    });
  });

  it('shows loading state', async () => {
    // Never resolve the promise to keep loading
    mockGetSuggestions.mockReturnValue(new Promise(() => {}));
    mockGetStats.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<BlueprintSuggestions />);
    expect(screen.getByText('Loading suggestions...')).toBeInTheDocument();
  });

  it('shows empty state when no suggestions', async () => {
    mockGetSuggestions.mockResolvedValue({
      suggestions: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('No Blueprint Suggestions Yet')).toBeInTheDocument();
    });
  });

  it('renders Generate Suggestions button', async () => {
    renderWithProviders(<BlueprintSuggestions />);
    await waitFor(() => {
      expect(screen.getByText('Generate Suggestions')).toBeInTheDocument();
    });
  });
});
