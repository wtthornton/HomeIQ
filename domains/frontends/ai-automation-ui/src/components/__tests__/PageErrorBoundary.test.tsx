/**
 * PageErrorBoundary Tests
 * Tests page-level error catching with dark mode, page name, and recovery actions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PageErrorBoundary } from '../PageErrorBoundary';

const ThrowingChild = () => {
  throw new Error('Page crashed');
};

const SafeChild = () => <div>Page content</div>;

describe('PageErrorBoundary', () => {
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
      <PageErrorBoundary>
        <SafeChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('renders error UI when child throws', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('displays error message from thrown error', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText('Page crashed')).toBeInTheDocument();
  });

  // === Page Name ===

  it('shows page name in error message when provided', () => {
    render(
      <PageErrorBoundary pageName="Dashboard">
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText(/error occurred while loading Dashboard/i)).toBeInTheDocument();
  });

  it('does not show page context when pageName is omitted', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.queryByText(/error occurred while loading/i)).not.toBeInTheDocument();
  });

  // === Dark Mode ===

  it('applies light mode styling by default', () => {
    const { container } = render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('bg-gray-50');
  });

  it('applies dark mode styling when darkMode is true', () => {
    const { container } = render(
      <PageErrorBoundary darkMode={true}>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('bg-gray-900');
  });

  // === Actions ===

  it('renders Reload Page button', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText(/Reload Page/i)).toBeInTheDocument();
  });

  it('renders Go Home button', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(screen.getByText(/Go Home/i)).toBeInTheDocument();
  });

  // === Accessibility ===

  it('error heading is an h1 element', () => {
    render(
      <PageErrorBoundary>
        <ThrowingChild />
      </PageErrorBoundary>
    );
    const heading = screen.getByText('Something went wrong');
    expect(heading.tagName).toBe('H1');
  });

  // === Console Logging ===

  it('logs error with page name context', () => {
    render(
      <PageErrorBoundary pageName="Settings">
        <ThrowingChild />
      </PageErrorBoundary>
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Settings'),
      expect.any(Error),
      expect.anything()
    );
  });
});
