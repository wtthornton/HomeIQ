/**
 * HAAgentChat Page Render Tests
 * Verifies the chat page renders and shows key UI elements.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/render-helpers';
import { HAAgentChat } from '../HAAgentChat';

// Mock API modules
vi.mock('../../services/haAiAgentApi', () => ({
  sendChatMessage: vi.fn(),
  getConversation: vi.fn().mockResolvedValue({ messages: [] }),
  deleteConversation: vi.fn(),
  HAIAgentAPIError: class extends Error { status = 0; },
}));

// Mock child components to isolate page tests
vi.mock('../../components/ha-agent/ConversationSidebar', () => ({
  ConversationSidebar: () => <div data-testid="conversation-sidebar">Sidebar</div>,
}));

vi.mock('../../components/ha-agent/DeleteConversationModal', () => ({
  DeleteConversationModal: () => null,
}));

vi.mock('../../components/ha-agent/ClearChatModal', () => ({
  ClearChatModal: () => null,
}));

vi.mock('../../components/ha-agent/ToolCallIndicator', () => ({
  ToolCallIndicator: () => null,
}));

vi.mock('../../components/ha-agent/AutomationPreview', () => ({
  AutomationPreview: () => null,
}));

vi.mock('../../components/ha-agent/AutomationProposal', () => ({
  AutomationProposal: () => null,
}));

vi.mock('../../components/ha-agent/ProposalErrorBoundary', () => ({
  ProposalErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../../components/ha-agent/MessageContent', () => ({
  MessageContent: () => <div data-testid="message-content">Content</div>,
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
  SendButton: ({ children }: any) => <button data-testid="send-button">{children || 'Send'}</button>,
}));

vi.mock('../../components/ha-agent/DebugTab', () => ({
  DebugTab: () => null,
}));

vi.mock('../../components/ha-agent/DevicePicker', () => ({
  DevicePicker: () => null,
}));

vi.mock('../../components/ha-agent/DeviceContextDisplay', () => ({
  DeviceContextDisplay: () => null,
}));

vi.mock('../../components/ha-agent/DeviceSuggestions', () => ({
  DeviceSuggestions: () => null,
}));

vi.mock('../../utils/performanceTracker', () => ({
  startTracking: vi.fn().mockReturnValue('track-id'),
  endTracking: vi.fn(),
  createReport: vi.fn(),
}));

vi.mock('../../utils/proposalParser', () => ({
  parseProposal: vi.fn().mockReturnValue(null),
}));

vi.mock('../../utils/inputSanitizer', () => ({
  sanitizeMessageInput: vi.fn((s: string) => s),
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
      button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
      span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    },
  };
});

describe('HAAgentChat Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the conversation sidebar', async () => {
    renderWithProviders(<HAAgentChat />, { route: '/chat' });
    await waitFor(() => {
      expect(screen.getByTestId('conversation-sidebar')).toBeInTheDocument();
    });
  });

  it('renders the chat input area', async () => {
    renderWithProviders(<HAAgentChat />, { route: '/chat' });
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/type|message|ask/i);
      expect(textarea).toBeInTheDocument();
    });
  });

  // === Accessibility ===

  it('chat input is a textarea or input element', async () => {
    renderWithProviders(<HAAgentChat />, { route: '/chat' });
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/type|message|ask/i);
      expect(textarea.tagName).toMatch(/TEXTAREA|INPUT/i);
    });
  });

  it('send button is present and interactive', async () => {
    renderWithProviders(<HAAgentChat />, { route: '/chat' });
    await waitFor(() => {
      expect(screen.getByTestId('send-button')).toBeInTheDocument();
    });
  });
});
