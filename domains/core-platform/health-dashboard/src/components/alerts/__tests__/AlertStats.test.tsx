import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../../tests/test-utils';
import { AlertStats } from '../AlertStats';

describe('AlertStats', () => {
  const defaultProps = {
    criticalCount: 3,
    warningCount: 5,
    errorCount: 2,
    totalCount: 10,
    darkMode: false,
  };

  it('displays total alerts count', () => {
    render(<AlertStats {...defaultProps} />);
    expect(screen.getByText('Total Alerts')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('displays critical count', () => {
    render(<AlertStats {...defaultProps} />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('displays warning count', () => {
    render(<AlertStats {...defaultProps} />);
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('displays error count', () => {
    render(<AlertStats {...defaultProps} />);
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('handles zero counts', () => {
    render(<AlertStats criticalCount={0} warningCount={0} errorCount={0} totalCount={0} darkMode={false} />);
    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBe(4);
  });

  it('renders in dark mode without errors', () => {
    render(<AlertStats {...defaultProps} darkMode={true} />);
    expect(screen.getByText('Total Alerts')).toBeInTheDocument();
  });
});
