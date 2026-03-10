/**
 * ConversationSidebar Component Tests
 * Story 44.3: Conversation sidebar coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationSidebar } from '../ConversationSidebar';

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => {
        // Strip framer-motion specific props
        const { initial, animate, exit, transition, whileHover, whileTap, ...htmlProps } = props;
        return <div {...htmlProps}>{children}</div>;
      },
    },
  };
});

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

// Mock haAiAgentApi
const mockListConversations = vi.fn();
vi.mock('../../../services/haAiAgentApi', () => ({
  listConversations: (...args: unknown[]) => mockListConversations(...args),
}));

const defaultProps = {
  darkMode: false,
  currentConversationId: null,
  onSelectConversation: vi.fn(),
  onNewConversation: vi.fn(),
  onDeleteConversation: vi.fn(),
  isOpen: true,
  onToggle: vi.fn(),
  refreshTrigger: 0,
};

const mockConversations = [
  {
    conversation_id: 'conv-1',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    state: 'active' as const,
    title: 'Turn on kitchen lights',
    source: 'user' as const,
    message_count: 5,
  },
  {
    conversation_id: 'conv-2',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    state: 'archived' as const,
    title: 'Weather automation',
    source: 'proactive' as const,
    message_count: 3,
  },
];

describe('ConversationSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListConversations.mockResolvedValue({
      conversations: mockConversations,
      total: 2,
      limit: 50,
      offset: 0,
    });
  });

  it('renders the Conversations heading when open', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
    });
  });

  it('renders New Conversation button', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('+ New Conversation')).toBeInTheDocument();
    });
  });

  it('calls onNewConversation when button clicked', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      screen.getByText('+ New Conversation');
    });
    fireEvent.click(screen.getByText('+ New Conversation'));
    expect(defaultProps.onNewConversation).toHaveBeenCalled();
  });

  it('renders conversation list from API', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText(/Turn on kitchen lights/)).toBeInTheDocument();
      expect(screen.getByText(/Weather automation/)).toBeInTheDocument();
    });
  });

  it('calls onSelectConversation when conversation clicked', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      screen.getByText(/Turn on kitchen lights/);
    });
    // Click the conversation option
    const options = screen.getAllByRole('option');
    fireEvent.click(options[0]);
    expect(defaultProps.onSelectConversation).toHaveBeenCalledWith('conv-1');
  });

  it('shows empty state when no conversations', async () => {
    mockListConversations.mockResolvedValue({
      conversations: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });
  });

  it('shows search input', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search conversations...')).toBeInTheDocument();
    });
  });

  it('renders filter buttons (All, Active, Archived)', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('All')).toBeInTheDocument();
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('Archived')).toBeInTheDocument();
    });
  });

  it('shows message count for conversations', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('5 msgs')).toBeInTheDocument();
      expect(screen.getByText('3 msgs')).toBeInTheDocument();
    });
  });

  it('shows delete button for conversations', async () => {
    render(<ConversationSidebar {...defaultProps} />);
    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle('Delete conversation');
      expect(deleteButtons).toHaveLength(2);
    });
  });
});
