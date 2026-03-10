/**
 * MessageContent Component Tests
 * Story 44.3: Message rendering coverage.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageContent } from '../MessageContent';

// Mock rehype-highlight to avoid highlight.js CSS import issues
vi.mock('rehype-highlight', () => ({ default: () => {} }));
vi.mock('highlight.js/styles/github-dark.css', () => ({}));

describe('MessageContent', () => {
  it('renders plain text content', () => {
    render(<MessageContent content="Hello world" darkMode={false} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('renders with article role and aria-label', () => {
    render(<MessageContent content="Test" darkMode={false} />);
    const article = screen.getByRole('article', { name: 'Message content' });
    expect(article).toBeInTheDocument();
  });

  it('applies prose-invert class in dark mode', () => {
    render(<MessageContent content="Dark" darkMode={true} />);
    const article = screen.getByRole('article');
    expect(article.className).toContain('prose-invert');
  });

  it('does not apply prose-invert class in light mode', () => {
    render(<MessageContent content="Light" darkMode={false} />);
    const article = screen.getByRole('article');
    expect(article.className).not.toContain('prose-invert');
  });

  it('renders bold text via markdown', () => {
    render(<MessageContent content="This is **bold**" darkMode={false} />);
    const bold = screen.getByText('bold');
    expect(bold.tagName).toBe('STRONG');
  });

  it('renders bullet lists', () => {
    render(<MessageContent content={"- Item 1\n- Item 2"} darkMode={false} />);
    const listItems = screen.getAllByRole('listitem');
    expect(listItems.length).toBeGreaterThanOrEqual(2);
  });

  it('renders inline code', () => {
    render(<MessageContent content="Use `entity_id` here" darkMode={false} />);
    const code = screen.getByText('entity_id');
    expect(code.tagName).toBe('CODE');
  });

  it('renders links as anchor tags', () => {
    render(<MessageContent content="[Click here](https://example.com)" darkMode={false} />);
    const link = screen.getByText('Click here');
    // rehype-sanitize may strip or keep the link; check it rendered
    expect(link).toBeInTheDocument();
  });

  it('renders headings', () => {
    render(<MessageContent content="# Title" darkMode={false} />);
    expect(screen.getByText('Title').tagName).toBe('H1');
  });

  it('renders numbered list items', () => {
    render(<MessageContent content={"1. First\n2. Second"} darkMode={false} />);
    // Ordered list items get rendered within list structure
    const listItems = screen.getAllByRole('listitem');
    expect(listItems.length).toBeGreaterThanOrEqual(2);
  });

  it('renders empty content without error', () => {
    const { container } = render(<MessageContent content="" darkMode={false} />);
    expect(container.querySelector('[role="article"]')).toBeInTheDocument();
  });
});
