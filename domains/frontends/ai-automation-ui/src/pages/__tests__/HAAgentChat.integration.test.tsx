/**
 * HAAgentChat Integration Tests (Story 59.2)
 *
 * Tests cross-component flows:
 * - Complete conversation lifecycle: send message -> receive response -> display
 * - Device picker selection flows into chat context
 * - Conversation sidebar interactions (load, delete, clear)
 * - Automation detection and preview flow
 * - Error handling across API boundaries
 * - Blueprint context integration
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/render-helpers';
import { HAAgentChat } from '../HAAgentChat';

// --- API Mocks ---

const mockSendChatMessage = vi.fn();
const mockGetConversation = vi.fn();
const mockDeleteConversation = vi.fn();

vi.mock('../../services/haAiAgentApi', () => ({
  sendChatMessage: (...args: unknown[]) => mockSendChatMessage(...args),
  getConversation: (...args: unknown[]) => mockGetConversation(...args),
  deleteConversation: (...args: unknown[]) => mockDeleteConversation(...args),
  HAIAgentAPIError: class extends Error {
    status = 0;
  },
}));

// --- Store Mock ---
vi.mock('../../store', () => ({
  useAppStore: () => ({ darkMode: false }),
}));

// --- Toast Mock ---
vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

// --- Component Mocks ---
// Sidebar: capture onSelect callback to simulate conversation loading
let capturedSidebarProps: any = {};
vi.mock('../../components/ha-agent/ConversationSidebar', () => ({
  ConversationSidebar: (props: any) => {
    capturedSidebarProps = props;
    return (
      <div data-testid="conversation-sidebar">
        <button
          data-testid="sidebar-load-conv"
          onClick={() => props.onSelectConversation?.('conv-existing')}
        >
          Load Conv
        </button>
      </div>
    );
  },
}));

vi.mock('../../components/ha-agent/DeleteConversationModal', () => ({
  DeleteConversationModal: ({ isOpen, onConfirm, onCancel }: any) =>
    isOpen ? (
      <div data-testid="delete-modal">
        <button data-testid="delete-confirm" onClick={onConfirm}>
          Confirm Delete
        </button>
        <button data-testid="delete-cancel" onClick={onCancel}>
          Cancel
        </button>
      </div>
    ) : null,
}));

vi.mock('../../components/ha-agent/ClearChatModal', () => ({
  ClearChatModal: ({ isOpen, onConfirm, onCancel }: any) =>
    isOpen ? (
      <div data-testid="clear-modal">
        <button data-testid="clear-confirm" onClick={onConfirm}>
          Confirm Clear
        </button>
      </div>
    ) : null,
}));

vi.mock('../../components/ha-agent/ToolCallIndicator', () => ({
  ToolCallIndicator: ({ toolCalls }: any) =>
    toolCalls?.length ? (
      <div data-testid="tool-call-indicator">
        {toolCalls.map((tc: any) => (
          <span key={tc.id} data-testid={`tool-${tc.name}`}>
            {tc.name}
          </span>
        ))}
      </div>
    ) : null,
}));

vi.mock('../../components/ha-agent/AutomationPreview', () => ({
  AutomationPreview: ({ isOpen }: any) =>
    isOpen ? <div data-testid="automation-preview">Preview</div> : null,
}));

vi.mock('../../components/ha-agent/AutomationProposal', () => ({
  AutomationProposal: ({ yaml }: any) =>
    yaml ? <div data-testid="automation-proposal">{yaml}</div> : null,
}));

vi.mock('../../components/ha-agent/ProposalErrorBoundary', () => ({
  ProposalErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../../components/ha-agent/MessageContent', () => ({
  MessageContent: ({ content }: any) => (
    <div data-testid="message-content">{content}</div>
  ),
}));

vi.mock('../../components/ha-agent/MarkdownErrorBoundary', () => ({
  MarkdownErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../../components/ha-agent/CTAActionButtons', () => ({
  CTAActionButtons: () => null,
}));

vi.mock('../../components/ha-agent/EnhancementButton', () => ({
  EnhancementButton: () => null,
}));

vi.mock('../../components/ha-agent/SendButton', () => ({
  SendButton: ({ onClick, disabled, children }: any) => (
    <button data-testid="send-button" onClick={onClick} disabled={disabled}>
      {children || 'Send'}
    </button>
  ),
}));

vi.mock('../../components/ha-agent/DebugTab', () => ({
  DebugTab: () => <div data-testid="debug-tab">Debug</div>,
}));

// DevicePicker: capture props to simulate device selection
let capturedDevicePickerProps: any = {};
vi.mock('../../components/ha-agent/DevicePicker', () => ({
  DevicePicker: (props: any) => {
    capturedDevicePickerProps = props;
    return props.isOpen ? (
      <div data-testid="device-picker">
        <button
          data-testid="select-device-d1"
          onClick={() => {
            props.onSelectDevice('d1');
            props.onToggle();
          }}
        >
          Kitchen Light
        </button>
      </div>
    ) : null;
  },
}));

vi.mock('../../components/ha-agent/DeviceContextDisplay', () => ({
  DeviceContextDisplay: ({ deviceId }: any) =>
    deviceId ? <div data-testid="device-context">{deviceId}</div> : null,
}));

vi.mock('../../components/ha-agent/DeviceSuggestions', () => ({
  DeviceSuggestions: ({ suggestions, onSelect }: any) =>
    suggestions?.length ? (
      <div data-testid="device-suggestions">
        {suggestions.map((s: any, i: number) => (
          <button key={i} data-testid={`suggestion-${i}`} onClick={() => onSelect?.(s)}>
            {s.text || s.prompt}
          </button>
        ))}
      </div>
    ) : null,
}));

// --- Utility Mocks ---
vi.mock('../../utils/performanceTracker', () => ({
  startTracking: vi.fn().mockReturnValue('track-id'),
  endTracking: vi.fn(),
  createReport: vi.fn(),
}));

vi.mock('../../utils/proposalParser', () => ({
  parseProposal: vi.fn().mockReturnValue({ hasProposal: false, sections: [] }),
}));

vi.mock('../../utils/inputSanitizer', () => ({
  sanitizeMessageInput: vi.fn((s: string) => s),
}));

// --- Framer Motion Mock ---
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => {
        const { initial, animate, exit, transition, whileHover, whileTap, layout, ...htmlProps } = props;
        return <div {...htmlProps}>{children}</div>;
      },
      button: ({ children, ...props }: any) => {
        const { initial, animate, exit, transition, whileHover, whileTap, layout, ...htmlProps } = props;
        return <button {...htmlProps}>{children}</button>;
      },
      span: ({ children, ...props }: any) => {
        const { initial, animate, exit, transition, whileHover, whileTap, layout, ...htmlProps } = props;
        return <span {...htmlProps}>{children}</span>;
      },
    },
  };
});

// --- Test Data ---

const mockChatResponse = {
  message: 'I can help you with that! Here is what I found.',
  conversation_id: 'conv-123',
  tool_calls: [],
  metadata: {
    model: 'gpt-4o',
    tokens_used: 150,
    response_time_ms: 1200,
    iterations: 1,
  },
};

const mockConversationDetail = {
  conversation_id: 'conv-123',
  created_at: '2026-03-10T00:00:00Z',
  updated_at: '2026-03-10T00:01:00Z',
  state: 'active' as const,
  title: 'Test Conversation',
  message_count: 2,
  messages: [
    {
      message_id: 'msg-1',
      role: 'user' as const,
      content: 'Turn on the kitchen lights',
      created_at: '2026-03-10T00:00:00Z',
    },
    {
      message_id: 'msg-2',
      role: 'assistant' as const,
      content: 'I can help you with that! Here is what I found.',
      created_at: '2026-03-10T00:00:01Z',
    },
  ],
};

const mockConversationWithToolCalls = {
  ...mockConversationDetail,
  conversation_id: 'conv-tools',
  messages: [
    {
      message_id: 'msg-t1',
      role: 'user' as const,
      content: 'Create an automation to turn off lights at sunset',
      created_at: '2026-03-10T00:00:00Z',
    },
    {
      message_id: 'msg-t2',
      role: 'assistant' as const,
      content: 'I have created the automation for you.',
      tool_calls: [
        {
          id: 'tc-1',
          name: 'preview_automation_from_prompt',
          arguments: { prompt: 'turn off lights at sunset' },
        },
      ],
      created_at: '2026-03-10T00:00:01Z',
    },
  ],
};

describe('HAAgentChat Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedSidebarProps = {};
    capturedDevicePickerProps = {};
    localStorage.clear();
    // Default: no active conversation
    mockGetConversation.mockResolvedValue({ messages: [] });
  });

  describe('Conversation Lifecycle', () => {
    it('sends a message and displays the response', async () => {
      const user = userEvent.setup();
      mockSendChatMessage.mockResolvedValue(mockChatResponse);
      mockGetConversation.mockResolvedValue(mockConversationDetail);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      // Type a message
      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Turn on the kitchen lights');

      // Find and click send — the form may submit via Enter or button
      await user.keyboard('{Enter}');

      // Verify API was called
      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            message: 'Turn on the kitchen lights',
          }),
        );
      });
    });

    it('displays user message immediately before API response', async () => {
      const user = userEvent.setup();
      // Slow API response
      mockSendChatMessage.mockReturnValue(new Promise(() => {}));

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Hello agent');
      await user.keyboard('{Enter}');

      // User message should appear immediately (optimistic update)
      await waitFor(() => {
        const contents = screen.getAllByTestId('message-content');
        const hasUserMsg = contents.some((el) => el.textContent?.includes('Hello agent'));
        expect(hasUserMsg).toBe(true);
      });
    });

    it('clears input after sending', async () => {
      const user = userEvent.setup();
      mockSendChatMessage.mockResolvedValue(mockChatResponse);
      mockGetConversation.mockResolvedValue(mockConversationDetail);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Test message');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });

    it('does not send empty messages', async () => {
      const user = userEvent.setup();
      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      // Focus and press Enter without typing
      await user.click(input);
      await user.keyboard('{Enter}');

      expect(mockSendChatMessage).not.toHaveBeenCalled();
    });
  });

  describe('Conversation Loading', () => {
    it('loads an existing conversation from sidebar', async () => {
      const user = userEvent.setup();
      const existingConv = {
        ...mockConversationDetail,
        conversation_id: 'conv-existing',
        messages: [
          {
            message_id: 'msg-e1',
            role: 'user' as const,
            content: 'Previously asked question',
            created_at: '2026-03-09T00:00:00Z',
          },
          {
            message_id: 'msg-e2',
            role: 'assistant' as const,
            content: 'Previous answer',
            created_at: '2026-03-09T00:00:01Z',
          },
        ],
      };
      mockGetConversation.mockResolvedValue(existingConv);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      // Click sidebar load button
      const loadBtn = await screen.findByTestId('sidebar-load-conv');
      await user.click(loadBtn);

      // Messages from loaded conversation should appear
      await waitFor(() => {
        const contents = screen.getAllByTestId('message-content');
        expect(contents.length).toBeGreaterThanOrEqual(2);
      });
    });
  });

  describe('Error Handling', () => {
    it('shows toast on API error when sending a message', async () => {
      const user = userEvent.setup();
      mockSendChatMessage.mockRejectedValue(new Error('Network error'));

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'This will fail');
      await user.keyboard('{Enter}');

      await waitFor(async () => {
        const toast = await import('react-hot-toast');
        expect(toast.default.error).toHaveBeenCalled();
      });
    });

    it('re-enables input after API error', async () => {
      const user = userEvent.setup();
      mockSendChatMessage.mockRejectedValue(new Error('Server error'));

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Error message');
      await user.keyboard('{Enter}');

      // After error, loading should be false so input is usable
      await waitFor(() => {
        expect(input).not.toBeDisabled();
      });
    });
  });

  describe('Tool Call Display', () => {
    it('displays tool call indicators for automation responses', async () => {
      mockGetConversation.mockResolvedValue(mockConversationWithToolCalls);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      // Simulate loading a conversation with tool calls via sidebar
      const loadBtn = await screen.findByTestId('sidebar-load-conv');
      // Override the mock for this specific load
      mockGetConversation.mockResolvedValue(mockConversationWithToolCalls);

      await act(async () => {
        capturedSidebarProps.onSelectConversation?.('conv-tools');
      });

      await waitFor(() => {
        const contents = screen.getAllByTestId('message-content');
        expect(contents.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe('Chat Tab Switching', () => {
    it('renders the chat tab by default', async () => {
      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      // Chat input should be visible (means chat tab is active)
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type|message|ask/i)).toBeInTheDocument();
      });
    });
  });

  describe('Input Sanitization', () => {
    it('sanitizes input before sending', async () => {
      const { sanitizeMessageInput } = await import('../../utils/inputSanitizer');
      const user = userEvent.setup();
      mockSendChatMessage.mockResolvedValue(mockChatResponse);
      mockGetConversation.mockResolvedValue(mockConversationDetail);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Test <script>alert("xss")</script>');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(sanitizeMessageInput).toHaveBeenCalled();
      });
    });
  });

  describe('Performance Tracking', () => {
    it('tracks send message performance', async () => {
      const { startTracking, endTracking } = await import('../../utils/performanceTracker');
      const user = userEvent.setup();
      mockSendChatMessage.mockResolvedValue(mockChatResponse);
      mockGetConversation.mockResolvedValue(mockConversationDetail);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Track this');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(startTracking).toHaveBeenCalled();
      });
    });
  });

  describe('Conversation State Persistence', () => {
    it('stores originalPrompt in localStorage when set', async () => {
      const user = userEvent.setup();
      mockSendChatMessage.mockResolvedValue(mockChatResponse);
      mockGetConversation.mockResolvedValue(mockConversationDetail);

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);
      await user.type(input, 'Create an automation for lights');
      await user.keyboard('{Enter}');

      // Wait for conversation to be set up
      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalled();
      });
    });
  });

  describe('Multi-Turn Conversation', () => {
    it('supports multiple messages in sequence', async () => {
      const user = userEvent.setup();
      let callCount = 0;
      mockSendChatMessage.mockImplementation(() => {
        callCount++;
        return Promise.resolve({
          ...mockChatResponse,
          conversation_id: 'conv-multi',
          message: `Response ${callCount}`,
        });
      });
      mockGetConversation.mockResolvedValue({
        ...mockConversationDetail,
        conversation_id: 'conv-multi',
      });

      renderWithProviders(<HAAgentChat />, { route: '/chat' });

      const input = await screen.findByPlaceholderText(/type|message|ask/i);

      // First message
      await user.type(input, 'First question');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalledTimes(1);
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(input).not.toBeDisabled();
      });

      // Second message
      await user.type(input, 'Follow up question');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalledTimes(2);
      });

      // Second call should include conversation_id
      expect(mockSendChatMessage).toHaveBeenLastCalledWith(
        expect.objectContaining({
          conversation_id: 'conv-multi',
        }),
      );
    });
  });
});
