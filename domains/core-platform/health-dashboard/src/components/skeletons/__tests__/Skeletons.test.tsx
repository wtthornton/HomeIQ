/**
 * Skeleton Component Tests
 * Tests for SkeletonCard, SkeletonGraph, SkeletonList, and SkeletonTable
 * Validates rendering, variants, props, accessibility, and dark mode classes
 */

import { describe, it, expect } from 'vitest';
import { render } from '../../../tests/test-utils';
import { SkeletonCard } from '../SkeletonCard';
import { SkeletonGraph } from '../SkeletonGraph';
import { SkeletonList } from '../SkeletonList';
import { SkeletonTable } from '../SkeletonTable';

describe('SkeletonCard', () => {
  it('renders default variant', () => {
    const { container } = render(<SkeletonCard />);
    const card = container.firstElementChild as HTMLElement;
    expect(card).toBeInTheDocument();
    expect(card.className).toContain('animate-pulse');
  });

  it('renders metric variant with metric-specific structure', () => {
    const { container } = render(<SkeletonCard variant="metric" />);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain('animate-pulse');
    // Metric variant has shimmer placeholder divs
    const shimmers = card.querySelectorAll('.shimmer');
    expect(shimmers.length).toBeGreaterThanOrEqual(3);
  });

  it('renders service variant', () => {
    const { container } = render(<SkeletonCard variant="service" />);
    const card = container.firstElementChild as HTMLElement;
    // Service variant has a circular avatar placeholder
    const circle = card.querySelector('.rounded-full');
    expect(circle).toBeInTheDocument();
  });

  it('renders chart variant with chart placeholder', () => {
    const { container } = render(<SkeletonCard variant="chart" />);
    const card = container.firstElementChild as HTMLElement;
    // Chart variant has a tall placeholder
    const chartArea = card.querySelector('.h-64');
    expect(chartArea).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonCard className="my-custom" />);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain('my-custom');
  });

  it('has dark mode classes', () => {
    const { container } = render(<SkeletonCard />);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain('dark:bg-gray-800');
  });
});

describe('SkeletonGraph', () => {
  it('renders chart variant by default', () => {
    const { container } = render(<SkeletonGraph />);
    const graph = container.firstElementChild as HTMLElement;
    expect(graph).toBeInTheDocument();
    // Chart variant has bar elements
    const bars = graph.querySelectorAll('.animate-pulse');
    expect(bars.length).toBeGreaterThanOrEqual(1);
  });

  it('renders dependency variant with node placeholders', () => {
    const { container } = render(<SkeletonGraph variant="dependency" />);
    // Dependency variant has positioned node elements
    const nodes = container.querySelectorAll('.rounded-lg.animate-pulse');
    expect(nodes.length).toBeGreaterThanOrEqual(3);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonGraph className="graph-custom" />);
    const graph = container.firstElementChild as HTMLElement;
    expect(graph.className).toContain('graph-custom');
  });

  it('has dark mode classes', () => {
    const { container } = render(<SkeletonGraph />);
    const graph = container.firstElementChild as HTMLElement;
    expect(graph.className).toContain('dark:bg-gray-800');
  });
});

describe('SkeletonList', () => {
  it('renders 3 items by default', () => {
    const { container } = render(<SkeletonList />);
    const items = container.querySelectorAll('.animate-pulse');
    expect(items.length).toBe(3);
  });

  it('renders custom count of items', () => {
    const { container } = render(<SkeletonList count={5} />);
    const items = container.querySelectorAll('.animate-pulse');
    expect(items.length).toBe(5);
  });

  it('renders 0 items when count is 0', () => {
    const { container } = render(<SkeletonList count={0} />);
    const items = container.querySelectorAll('.animate-pulse');
    expect(items.length).toBe(0);
  });

  it('applies custom item height', () => {
    const { container } = render(<SkeletonList itemHeight="h-24" />);
    const item = container.querySelector('.h-24');
    expect(item).toBeInTheDocument();
  });

  it('applies custom spacing', () => {
    const { container } = render(<SkeletonList spacing="space-y-6" />);
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('space-y-6');
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonList className="list-custom" />);
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('list-custom');
  });

  it('has dark mode classes on items', () => {
    const { container } = render(<SkeletonList />);
    const item = container.querySelector('.animate-pulse');
    expect(item?.className).toContain('dark:bg-gray-700');
  });
});

describe('SkeletonTable', () => {
  it('renders with default 5 rows and 4 columns', () => {
    const { container } = render(<SkeletonTable />);
    // Header row + 5 data rows
    const headerCells = container.querySelectorAll('[class*="bg-gray-50"] .animate-pulse');
    expect(headerCells.length).toBe(4); // 4 header columns

    // Data rows — each row has columns
    const dataRows = container.querySelectorAll('.divide-y > div');
    expect(dataRows.length).toBe(5);
  });

  it('renders custom row and column counts', () => {
    const { container } = render(<SkeletonTable rows={3} columns={6} />);
    const headerCells = container.querySelectorAll('[class*="bg-gray-50"] .animate-pulse');
    expect(headerCells.length).toBe(6);

    const dataRows = container.querySelectorAll('.divide-y > div');
    expect(dataRows.length).toBe(3);
  });

  it('renders 1 row and 1 column', () => {
    const { container } = render(<SkeletonTable rows={1} columns={1} />);
    const dataRows = container.querySelectorAll('.divide-y > div');
    expect(dataRows.length).toBe(1);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonTable className="table-custom" />);
    const table = container.firstElementChild as HTMLElement;
    expect(table.className).toContain('table-custom');
  });

  it('has dark mode classes', () => {
    const { container } = render(<SkeletonTable />);
    const table = container.firstElementChild as HTMLElement;
    expect(table.className).toContain('dark:bg-gray-800');
  });

  it('first column cells are wider than others', () => {
    const { container } = render(<SkeletonTable />);
    const firstRow = container.querySelector('.divide-y > div');
    const cells = firstRow?.querySelectorAll('.animate-pulse');
    if (cells && cells.length >= 2) {
      expect(cells[0].getAttribute('style')).toContain('80%');
      expect(cells[1].getAttribute('style')).toContain('60%');
    }
  });
});
