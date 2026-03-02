import { describe, it, expect } from 'vitest';
import { render } from '../../tests/test-utils';
import { LoadingSkeleton } from '../LoadingSkeleton';

describe('LoadingSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<LoadingSkeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('has the animate-pulse class for skeleton animation', () => {
    const { container } = render(<LoadingSkeleton />);
    expect(container.firstChild).toHaveClass('animate-pulse');
  });

  it('renders multiple skeleton cards', () => {
    const { container } = render(<LoadingSkeleton />);
    const cards = container.querySelectorAll('.rounded-lg');
    expect(cards.length).toBeGreaterThanOrEqual(2);
  });
});
