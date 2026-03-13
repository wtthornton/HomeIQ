/**
 * ProposalErrorBoundary Tests
 * Tests error catching for malformed automation proposals
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProposalErrorBoundary } from '../ProposalErrorBoundary';

const ThrowingChild = () => {
  throw new Error('YAML parse failed');
};

const SafeChild = () => <div>Proposal content</div>;

describe('ProposalErrorBoundary', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  // === Rendering ===

  it('renders children when no error occurs', () => {
    render(
      <ProposalErrorBoundary>
        <SafeChild />
      </ProposalErrorBoundary>
    );
    expect(screen.getByText('Proposal content')).toBeInTheDocument();
  });

  it('renders default error UI when child throws', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    expect(screen.getByText(/Unable to display automation proposal/i)).toBeInTheDocument();
  });

  it('shows help text in default error UI', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    expect(screen.getByText(/could not be parsed/i)).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ProposalErrorBoundary fallback={<div>Custom proposal error</div>}>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    expect(screen.getByText('Custom proposal error')).toBeInTheDocument();
    expect(screen.queryByText(/Unable to display/i)).not.toBeInTheDocument();
  });

  // === Accessibility ===

  it('default error UI has role="alert"', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('error UI has visible error icon indicator', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    // Contains warning emoji as visual indicator
    expect(screen.getByText(/⚠️/)).toBeInTheDocument();
  });

  // === Styling ===

  it('error container has red border styling', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    const alert = screen.getByRole('alert');
    expect(alert.className).toContain('border-red-500');
  });

  // === Console Logging ===

  it('logs proposal rendering error to console', () => {
    render(
      <ProposalErrorBoundary>
        <ThrowingChild />
      </ProposalErrorBoundary>
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      'Proposal rendering error:',
      expect.any(Error),
      expect.anything()
    );
  });
});
