/**
 * Skeleton Component Tests (AI Automation UI)
 * Tests for SkeletonCard, SkeletonCardGrid, SkeletonFilter, and SkeletonStats
 * Validates rendering, variants, props, and dark mode classes
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { SkeletonCard, SkeletonCardGrid } from '../SkeletonCard';
import { SkeletonFilter } from '../SkeletonFilter';
import { SkeletonStats } from '../SkeletonStats';

// Mock framer-motion to avoid animation complexity in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

describe('SkeletonCard', () => {
  it('renders default variant', () => {
    const { container } = render(<SkeletonCard />);
    const card = container.firstElementChild as HTMLElement;
    expect(card).toBeInTheDocument();
    expect(card.className).toContain('rounded-xl');
  });

  it('renders pattern variant with tag placeholders', () => {
    const { container } = render(<SkeletonCard variant="pattern" />);
    // Pattern variant has rounded-full pill placeholders for tags
    const pills = container.querySelectorAll('.rounded-full');
    expect(pills.length).toBeGreaterThanOrEqual(2);
  });

  it('renders synergy variant with device pair placeholders', () => {
    const { container } = render(<SkeletonCard variant="synergy" />);
    // Synergy variant has rounded-lg device blocks
    const blocks = container.querySelectorAll('.rounded-lg');
    expect(blocks.length).toBeGreaterThanOrEqual(2);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonCard className="test-class" />);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain('test-class');
  });

  it('has dark mode gradient classes', () => {
    const { container } = render(<SkeletonCard />);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain('dark:from-gray-800');
    expect(card.className).toContain('dark:to-gray-900');
  });

  it('has shimmer overlay element', () => {
    const { container } = render(<SkeletonCard />);
    // Shimmer overlay is rendered by (mocked) motion.div
    const shimmer = container.querySelector('[class*="via-white"]');
    expect(shimmer).toBeInTheDocument();
  });
});

describe('SkeletonCardGrid', () => {
  it('renders 6 cards by default', () => {
    const { container } = render(<SkeletonCardGrid />);
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBe(6);
  });

  it('renders custom count of cards', () => {
    const { container } = render(<SkeletonCardGrid count={3} />);
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBe(3);
  });

  it('passes variant to child cards', () => {
    const { container } = render(<SkeletonCardGrid count={2} variant="pattern" />);
    // Pattern variant has rounded-full pills inside each card
    const pills = container.querySelectorAll('.rounded-full');
    expect(pills.length).toBeGreaterThanOrEqual(4); // 2 per card
  });

  it('applies responsive grid classes', () => {
    const { container } = render(<SkeletonCardGrid />);
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.className).toContain('grid');
    expect(grid.className).toContain('lg:grid-cols-3');
  });

  it('applies custom className to grid', () => {
    const { container } = render(<SkeletonCardGrid className="grid-custom" />);
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.className).toContain('grid-custom');
  });
});

describe('SkeletonFilter', () => {
  it('renders search bar by default', () => {
    const { container } = render(<SkeletonFilter />);
    // Search bar is a rounded-lg container with inner content
    const searchBar = container.querySelector('.h-12');
    expect(searchBar).toBeInTheDocument();
  });

  it('hides search bar when showSearch is false', () => {
    const { container } = render(<SkeletonFilter showSearch={false} />);
    const searchBar = container.querySelector('.h-12');
    expect(searchBar).not.toBeInTheDocument();
  });

  it('renders 5 filter pills by default', () => {
    const { container } = render(<SkeletonFilter />);
    // Each pill has outer container + inner placeholder, both .rounded-full
    const pillWrappers = container.querySelectorAll('.flex-wrap > div');
    expect(pillWrappers.length).toBe(5);
  });

  it('renders custom pill count', () => {
    const { container } = render(<SkeletonFilter pillCount={3} />);
    const pillWrappers = container.querySelectorAll('.flex-wrap > div');
    expect(pillWrappers.length).toBe(3);
  });

  it('renders sort/view controls', () => {
    const { container } = render(<SkeletonFilter />);
    // Sort/view section has rounded placeholder blocks
    const controls = container.querySelectorAll('.rounded.animate-pulse');
    expect(controls.length).toBeGreaterThanOrEqual(2);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonFilter className="filter-custom" />);
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('filter-custom');
  });

  it('has dark mode classes', () => {
    const { container } = render(<SkeletonFilter />);
    const pill = container.querySelector('.rounded-full');
    expect(pill?.className).toContain('dark:from-gray-800');
  });
});

describe('SkeletonStats', () => {
  it('renders 4 stat cards by default', () => {
    const { container } = render(<SkeletonStats />);
    const statCards = container.querySelectorAll('.rounded-lg.border');
    expect(statCards.length).toBe(4);
  });

  it('renders custom stat count', () => {
    const { container } = render(<SkeletonStats statCount={2} />);
    const statCards = container.querySelectorAll('.rounded-lg.border');
    expect(statCards.length).toBe(2);
  });

  it('does not show charts by default', () => {
    const { container } = render(<SkeletonStats />);
    // Charts section has rounded-xl elements
    const charts = container.querySelectorAll('.rounded-xl');
    expect(charts.length).toBe(0);
  });

  it('shows chart placeholders when showCharts is true', () => {
    const { container } = render(<SkeletonStats showCharts={true} />);
    const charts = container.querySelectorAll('.rounded-xl');
    expect(charts.length).toBe(2);
  });

  it('applies responsive grid for stats', () => {
    const { container } = render(<SkeletonStats />);
    const grid = container.querySelector('.grid');
    expect(grid?.className).toContain('lg:grid-cols-4');
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonStats className="stats-custom" />);
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('stats-custom');
  });

  it('has dark mode classes on stat cards', () => {
    const { container } = render(<SkeletonStats />);
    const card = container.querySelector('.rounded-lg.border');
    expect(card?.className).toContain('dark:from-gray-800');
  });
});
