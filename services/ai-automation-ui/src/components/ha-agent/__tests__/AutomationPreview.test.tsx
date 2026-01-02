/**
 * AutomationPreview Component Tests
 * Tests for automation preview with Debug tab functionality
 * Epic AI-20 Story AI20.10: Automation Preview & Creation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AutomationPreview } from '../AutomationPreview';
import { DebugTab } from '../DebugTab';

// Mock DebugTab component
vi.mock('../DebugTab', () => ({
  DebugTab: vi.fn(({ conversationId, darkMode }) => (
    <div data-testid="debug-tab">
      Debug Tab Content
      <div data-testid="debug-conversation-id">{conversationId}</div>
      <div data-testid="debug-dark-mode">{darkMode ? 'dark' : 'light'}</div>
    </div>
  )),
}));

// Mock framer-motion for animations
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock react-syntax-highlighter
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children, ...props }: any) => (
    <pre data-testid="syntax-highlighter" {...props}>
      {children}
    </pre>
  ),
}));

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock API services
vi.mock('../../services/haAiAgentApi', () => ({
  executeToolCall: vi.fn(),
}));

vi.mock('../../services/api-v2', () => ({
  apiV2: {
    validateYAML: vi.fn(),
  },
}));

describe('AutomationPreview', () => {
  const defaultProps = {
    automationYaml: 'alias: Test Automation\ndescription: Test description',
    darkMode: false,
    onClose: vi.fn(),
    conversationId: 'test-conversation-id',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial Render', () => {
    it('renders automation preview modal', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.getByText('⚙️ Automation Preview')).toBeInTheDocument();
    });

    it('displays automation alias when provided', () => {
      render(<AutomationPreview {...defaultProps} alias="Custom Alias" />);
      expect(screen.getByText('Custom Alias')).toBeInTheDocument();
    });

    it('extracts and displays alias from YAML', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.getByText('Test Automation')).toBeInTheDocument();
    });

    it('displays description when present in YAML', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.getByText(/Test description/)).toBeInTheDocument();
    });
  });

  describe('Tab Navigation', () => {
    it('renders Preview tab by default', () => {
      render(<AutomationPreview {...defaultProps} />);
      const previewTab = screen.getByText('Preview');
      expect(previewTab).toBeInTheDocument();
      // Preview tab should be active (check for active styling)
      expect(previewTab.closest('button')).toHaveClass('border-blue-600');
    });

    it('renders Debug tab button', () => {
      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      expect(debugTab).toBeInTheDocument();
    });

    it('shows YAML content when Preview tab is active', () => {
      render(<AutomationPreview {...defaultProps} />);
      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toBeInTheDocument();
      expect(syntaxHighlighter).toHaveTextContent('alias: Test Automation');
    });

    it('switches to Debug tab when clicked', async () => {
      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(screen.getByTestId('debug-tab')).toBeInTheDocument();
      });
    });

    it('switches back to Preview tab when clicked', async () => {
      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      const previewTab = screen.getByText('Preview');
      
      // Switch to Debug
      fireEvent.click(debugTab);
      await waitFor(() => {
        expect(screen.getByTestId('debug-tab')).toBeInTheDocument();
      });
      
      // Switch back to Preview
      fireEvent.click(previewTab);
      await waitFor(() => {
        expect(screen.getByTestId('syntax-highlighter')).toBeInTheDocument();
      });
    });

    it('highlights active tab correctly', async () => {
      render(<AutomationPreview {...defaultProps} />);
      const previewTab = screen.getByText('Preview');
      const debugTab = screen.getByText('🐛 Debug');
      
      // Preview should be active initially
      expect(previewTab.closest('button')).toHaveClass('border-blue-600');
      expect(debugTab.closest('button')).not.toHaveClass('border-blue-600');
      
      // Switch to Debug
      fireEvent.click(debugTab);
      await waitFor(() => {
        expect(debugTab.closest('button')).toHaveClass('border-blue-600');
        expect(previewTab.closest('button')).not.toHaveClass('border-blue-600');
      });
    });
  });

  describe('DebugTab Integration', () => {
    it('passes conversationId to DebugTab', async () => {
      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(screen.getByTestId('debug-conversation-id')).toHaveTextContent('test-conversation-id');
      });
    });

    it('passes darkMode prop to DebugTab', async () => {
      render(<AutomationPreview {...defaultProps} darkMode={true} />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(screen.getByTestId('debug-dark-mode')).toHaveTextContent('dark');
      });
    });

    it('passes null conversationId when not provided', async () => {
      render(<AutomationPreview {...defaultProps} conversationId="" />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(screen.getByTestId('debug-conversation-id')).toHaveTextContent('');
      });
    });

    it('renders DebugTab component when Debug tab is active', async () => {
      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(DebugTab).toHaveBeenCalledWith(
          expect.objectContaining({
            conversationId: 'test-conversation-id',
            darkMode: false,
          }),
          expect.anything()
        );
      });
    });
  });

  describe('Existing Functionality Preservation', () => {
    it('displays validation feedback when validation result exists', async () => {
      const { apiV2 } = await import('../../services/api-v2');
      vi.mocked(apiV2.validateYAML).mockResolvedValue({
        valid: true,
        errors: [],
        warnings: [],
        score: 85,
      });

      render(<AutomationPreview {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(/Valid \(Score: 85.0\/100\)/)).toBeInTheDocument();
      });
    });

    it('displays validation errors when validation fails', async () => {
      const { apiV2 } = await import('../../services/api-v2');
      vi.mocked(apiV2.validateYAML).mockResolvedValue({
        valid: false,
        errors: ['Entity not found: sensor.test'],
        warnings: [],
        score: 45,
      });

      render(<AutomationPreview {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(/Invalid \(Score: 45.0\/100\)/)).toBeInTheDocument();
        expect(screen.getByText('Entity not found: sensor.test')).toBeInTheDocument();
      });
    });

    it('renders Create Automation button', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.getByText('Create Automation')).toBeInTheDocument();
    });

    it('renders Cancel button', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('calls onClose when Cancel button is clicked', () => {
      const onClose = vi.fn();
      render(<AutomationPreview {...defaultProps} onClose={onClose} />);
      
      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);
      
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('renders Edit button when onEdit prop is provided', () => {
      const onEdit = vi.fn();
      render(<AutomationPreview {...defaultProps} onEdit={onEdit} />);
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    it('does not render Edit button when onEdit prop is not provided', () => {
      render(<AutomationPreview {...defaultProps} />);
      expect(screen.queryByText('Edit')).not.toBeInTheDocument();
    });
  });

  describe('Dark Mode Support', () => {
    it('applies dark mode styles when darkMode is true', () => {
      render(<AutomationPreview {...defaultProps} darkMode={true} />);
      const modal = screen.getByText('⚙️ Automation Preview').closest('.bg-gray-800');
      expect(modal).toBeInTheDocument();
    });

    it('applies light mode styles when darkMode is false', () => {
      render(<AutomationPreview {...defaultProps} darkMode={false} />);
      const modal = screen.getByText('⚙️ Automation Preview').closest('.bg-white');
      expect(modal).toBeInTheDocument();
    });

    it('applies dark mode styles to tab buttons', () => {
      render(<AutomationPreview {...defaultProps} darkMode={true} />);
      const previewTab = screen.getByText('Preview');
      // Check for dark mode classes
      expect(previewTab.closest('button')).toHaveClass('text-gray-400');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty automation YAML', () => {
      render(<AutomationPreview {...defaultProps} automationYaml="" />);
      expect(screen.getByText('⚙️ Automation Preview')).toBeInTheDocument();
    });

    it('handles YAML with markdown code blocks', () => {
      const yamlWithMarkdown = '```yaml\nalias: Test\n```';
      render(<AutomationPreview {...defaultProps} automationYaml={yamlWithMarkdown} />);
      // Should strip markdown and extract alias
      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    it('handles missing conversationId gracefully', async () => {
      render(<AutomationPreview {...defaultProps} conversationId="" />);
      const debugTab = screen.getByText('🐛 Debug');
      
      fireEvent.click(debugTab);
      
      await waitFor(() => {
        expect(DebugTab).toHaveBeenCalledWith(
          expect.objectContaining({
            conversationId: null,
          }),
          expect.anything()
        );
      });
    });

    it('maintains tab state during validation', async () => {
      const { apiV2 } = await import('../../services/api-v2');
      vi.mocked(apiV2.validateYAML).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          valid: true,
          errors: [],
          warnings: [],
          score: 100,
        }), 100))
      );

      render(<AutomationPreview {...defaultProps} />);
      const debugTab = screen.getByText('🐛 Debug');
      
      // Switch to Debug tab
      fireEvent.click(debugTab);
      
      // Tab should remain on Debug even during validation
      await waitFor(() => {
        expect(screen.getByTestId('debug-tab')).toBeInTheDocument();
      });
    });
  });

  describe('Entity Extraction', () => {
    it('extracts entities from entity_id fields', () => {
      const yamlWithEntities = `
alias: Test
trigger:
  - platform: state
    entity_id: sensor.test1
action:
  - service: light.turn_on
    target:
      entity_id: light.test2
      `;
      render(<AutomationPreview {...defaultProps} automationYaml={yamlWithEntities} />);
      // Should display entities in the metadata section
      expect(screen.getByText(/sensor.test1/)).toBeInTheDocument();
    });
  });
});
