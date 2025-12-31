/**
 * LoadingSpinner Component Tests
 * Tests for loading indicator component following 2025 best practices
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders spinner variant by default', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<LoadingSpinner label="Loading data..." />);
    const spinner = screen.getByRole('status', { name: 'Loading data...' });
    expect(spinner).toBeInTheDocument();
  });

  it('renders small size spinner', () => {
    const { container } = render(<LoadingSpinner size="sm" />);
    // Check for size class in the spinner element
    const spinner = container.querySelector('.w-4');
    expect(spinner).toBeInTheDocument();
  });

  it('renders medium size spinner (default)', () => {
    const { container } = render(<LoadingSpinner size="md" />);
    // Check for size class in the spinner element
    const spinner = container.querySelector('.w-6');
    expect(spinner).toBeInTheDocument();
  });

  it('renders large size spinner', () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    // Check for size class in the spinner element
    const spinner = container.querySelector('.w-8');
    expect(spinner).toBeInTheDocument();
  });

  it('renders spinner variant', () => {
    const { container } = render(<LoadingSpinner variant="spinner" />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('renders dots variant', () => {
    const { container } = render(<LoadingSpinner variant="dots" />);
    // Dots variant has multiple bouncing elements
    const dots = container.querySelectorAll('[class*="animate-bounce"]');
    expect(dots.length).toBeGreaterThanOrEqual(3); // Should have at least 3 dots
  });

  it('renders pulse variant', () => {
    const { container } = render(<LoadingSpinner variant="pulse" />);
    const pulse = container.querySelector('.animate-pulse');
    expect(pulse).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-class" />);
    const spinner = container.querySelector('.custom-class');
    expect(spinner).toBeInTheDocument();
  });

  it('has accessible aria-label', () => {
    render(<LoadingSpinner label="Custom loading message" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveAttribute('aria-label', 'Custom loading message');
  });

  it('has screen reader only text for label', () => {
    render(<LoadingSpinner label="Loading..." />);
    const srText = screen.getByText('Loading...', { selector: '.sr-only' });
    expect(srText).toBeInTheDocument();
  });
});
