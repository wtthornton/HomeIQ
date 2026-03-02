/**
 * Patterns Page Tests
 * Verifies rendering and key UI elements.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { Patterns } from '../Patterns';

// Mock API module
vi.mock('../../services/api', () => ({
  default: {
    getPatterns: vi.fn().mockResolvedValue({ data: { patterns: [] } }),
    getPatternStats: vi.fn().mockResolvedValue({ total_patterns: 0, unique_devices: 0, avg_confidence: 0, by_type: {} }),
    getAnalysisStatus: vi.fn().mockResolvedValue({ status: 'ready' }),
    getScheduleInfo: vi.fn().mockResolvedValue({ last_run_time: null }),
    getDeviceNames: vi.fn().mockResolvedValue({}),
    triggerManualJob: vi.fn().mockResolvedValue({}),
    repairDatabase: vi.fn().mockResolvedValue({ success: true }),
  },
}));

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
      button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
      span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    },
  };
});

describe('Patterns Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the patterns container', async () => {
    renderWithProviders(<Patterns />);
    await waitFor(() => {
      expect(screen.getByTestId('patterns-container')).toBeInTheDocument();
    });
  });

  it('shows "Detected Patterns" heading', async () => {
    renderWithProviders(<Patterns />);
    await waitFor(() => {
      expect(screen.getByText('Detected Patterns')).toBeInTheDocument();
    });
  });

  it('shows "No patterns yet" when no data', async () => {
    renderWithProviders(<Patterns />);
    await waitFor(() => {
      expect(screen.getByText('No patterns yet')).toBeInTheDocument();
    });
  });

  it('shows Run Analysis button', async () => {
    renderWithProviders(<Patterns />);
    await waitFor(() => {
      expect(screen.getByText(/Run.*Analysis/)).toBeInTheDocument();
    });
  });
});
