/**
 * ErrorBoundary Component Tests
 * Tests error catching, fallback rendering, recovery, and accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '../../tests/test-utils';
import { ErrorBoundary } from '../ErrorBoundary';

// Component that throws on render
const ThrowingComponent = ({ shouldThrow = true }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test render error');
  }
  return <div>Normal content</div>;
};

describe('ErrorBoundary', () => {
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
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('renders default fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error page</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom error page')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  // === Error Details ===

  it('displays error message in default fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });

  it('shows error details in expandable section', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Error Details')).toBeInTheDocument();
    expect(screen.getByText(/Test render error/)).toBeInTheDocument();
  });

  // === Callbacks ===

  it('calls onError callback when error is caught', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it('does not call onError when no error occurs', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <div>Safe content</div>
      </ErrorBoundary>
    );
    expect(onError).not.toHaveBeenCalled();
  });

  // === Recovery ===

  it('renders Try Again button in default fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('renders Reload Page button in default fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Reload Page')).toBeInTheDocument();
  });

  // === Accessibility ===

  it('has error state container with data-testid', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
  });

  it('error heading is visible and descriptive', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    const heading = screen.getByText('Something went wrong');
    expect(heading.tagName).toBe('H2');
  });

  // === Console Logging ===

  it('logs error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      'Error caught by boundary:',
      expect.any(Error)
    );
  });
});
