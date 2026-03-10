import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import userEvent from '@testing-library/user-event';
import { AlertFilters } from '../AlertFilters';

describe('AlertFilters', () => {
  const mockOnSeverityChange = vi.fn();
  const mockOnServiceChange = vi.fn();
  const mockOnShowAcknowledgedChange = vi.fn();

  const defaultProps = {
    selectedSeverity: 'all',
    selectedService: 'all',
    showAcknowledged: true,
    services: ['data-api', 'websocket-ingestion', 'admin-api'],
    onSeverityChange: mockOnSeverityChange,
    onServiceChange: mockOnServiceChange,
    onShowAcknowledgedChange: mockOnShowAcknowledgedChange,
    darkMode: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders severity filter dropdown', () => {
    render(<AlertFilters {...defaultProps} />);
    expect(screen.getByLabelText('Filter by severity')).toBeInTheDocument();
  });

  it('renders service filter dropdown', () => {
    render(<AlertFilters {...defaultProps} />);
    expect(screen.getByLabelText('Filter by service')).toBeInTheDocument();
  });

  it('renders show acknowledged checkbox', () => {
    render(<AlertFilters {...defaultProps} />);
    expect(screen.getByText('Show Acknowledged')).toBeInTheDocument();
  });

  it('shows all service options', () => {
    render(<AlertFilters {...defaultProps} />);
    const serviceSelect = screen.getByLabelText('Filter by service');
    expect(serviceSelect).toBeInTheDocument();
    // Check all service options are present
    expect(screen.getByText('data-api')).toBeInTheDocument();
    expect(screen.getByText('websocket-ingestion')).toBeInTheDocument();
    expect(screen.getByText('admin-api')).toBeInTheDocument();
  });

  it('calls onSeverityChange when severity changed', async () => {
    const user = userEvent.setup();
    render(<AlertFilters {...defaultProps} />);

    await user.selectOptions(screen.getByLabelText('Filter by severity'), 'critical');
    expect(mockOnSeverityChange).toHaveBeenCalledWith('critical');
  });

  it('calls onServiceChange when service changed', async () => {
    const user = userEvent.setup();
    render(<AlertFilters {...defaultProps} />);

    await user.selectOptions(screen.getByLabelText('Filter by service'), 'data-api');
    expect(mockOnServiceChange).toHaveBeenCalledWith('data-api');
  });

  it('calls onShowAcknowledgedChange when checkbox toggled', async () => {
    const user = userEvent.setup();
    render(<AlertFilters {...defaultProps} />);

    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    expect(mockOnShowAcknowledgedChange).toHaveBeenCalledWith(false);
  });

  it('renders in dark mode without errors', () => {
    render(<AlertFilters {...defaultProps} darkMode={true} />);
    expect(screen.getByLabelText('Filter by severity')).toBeInTheDocument();
  });
});
