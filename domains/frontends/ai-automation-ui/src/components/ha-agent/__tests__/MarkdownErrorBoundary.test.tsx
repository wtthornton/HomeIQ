/**
 * MarkdownErrorBoundary Tests
 * Tests error catching for malformed markdown, fallback rendering, and content-change recovery
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownErrorBoundary } from '../MarkdownErrorBoundary';

// Component that throws on render
const ThrowingChild = () => {
  throw new Error('Markdown parse error');
};

const SafeChild = () => <div>Rendered markdown</div>;

describe('MarkdownErrorBoundary', () => {
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
      <MarkdownErrorBoundary content="Hello world" darkMode={false}>
        <SafeChild />
      </MarkdownErrorBoundary>
    );
    expect(screen.getByText('Rendered markdown')).toBeInTheDocument();
  });

  it('falls back to plain text when child throws', () => {
    render(
      <MarkdownErrorBoundary content="Fallback content here" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    expect(screen.getByText('Fallback content here')).toBeInTheDocument();
  });

  it('does not show children content in fallback mode', () => {
    render(
      <MarkdownErrorBoundary content="Plain text fallback" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    expect(screen.queryByText('Rendered markdown')).not.toBeInTheDocument();
  });

  // === Dark Mode ===

  it('applies light mode text color in fallback', () => {
    render(
      <MarkdownErrorBoundary content="Light text" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    const fallback = screen.getByText('Light text');
    expect(fallback.className).toContain('text-gray-700');
  });

  it('applies dark mode text color in fallback', () => {
    render(
      <MarkdownErrorBoundary content="Dark text" darkMode={true}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    const fallback = screen.getByText('Dark text');
    expect(fallback.className).toContain('text-gray-300');
  });

  // === Accessibility ===

  it('fallback has role="text" and accessible label', () => {
    render(
      <MarkdownErrorBoundary content="Accessible fallback" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    const fallback = screen.getByText('Accessible fallback');
    expect(fallback).toHaveAttribute('role', 'text');
    expect(fallback).toHaveAttribute('aria-label', 'Message content (fallback rendering)');
  });

  // === Recovery on content change ===

  it('resets error state when content prop changes', () => {
    const { rerender } = render(
      <MarkdownErrorBoundary content="original" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    // Error state — shows plain text fallback
    expect(screen.getByText('original')).toBeInTheDocument();

    // Re-render with new content and safe child
    rerender(
      <MarkdownErrorBoundary content="updated" darkMode={false}>
        <SafeChild />
      </MarkdownErrorBoundary>
    );
    // Should recover and render children
    expect(screen.getByText('Rendered markdown')).toBeInTheDocument();
  });

  // === Console Logging ===

  it('logs markdown rendering error to console', () => {
    render(
      <MarkdownErrorBoundary content="test" darkMode={false}>
        <ThrowingChild />
      </MarkdownErrorBoundary>
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      'Markdown rendering error:',
      expect.any(Error),
      expect.anything()
    );
  });
});
