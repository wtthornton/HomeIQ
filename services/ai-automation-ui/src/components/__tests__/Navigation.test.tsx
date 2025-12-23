/**
 * Unit Tests for Navigation Component
 * 
 * Tests navigation functionality, dark mode toggle, and accessibility features.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Navigation } from '../Navigation';
import { useAppStore } from '../../store';

// Mock the store
vi.mock('../../store', () => ({
  useAppStore: vi.fn(),
}));

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}));

describe('Navigation', () => {
  const mockToggleDarkMode = vi.fn();
  const mockDarkMode = false;

  beforeEach(() => {
    vi.clearAllMocks();
    (useAppStore as any).mockReturnValue({
      darkMode: mockDarkMode,
      toggleDarkMode: mockToggleDarkMode,
    });
  });

  const renderNavigation = () => {
    return render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );
  };

  describe('Rendering', () => {
    it('should render navigation component', () => {
      renderNavigation();
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should render all navigation links', () => {
      renderNavigation();
      expect(screen.getByLabelText('Navigate to Suggestions')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to HA Agent')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Patterns')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Synergies')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Deployed Automations')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Discovery')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Name Enhancement')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Settings')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Admin')).toBeInTheDocument();
    });

    it('should render dark mode toggle button', () => {
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to dark mode');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toHaveAttribute('type', 'button');
    });

    it('should display light mode icon when in light mode', () => {
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to dark mode');
      expect(toggleButton).toHaveTextContent('🌙');
    });

    it('should display dark mode icon when in dark mode', () => {
      (useAppStore as any).mockReturnValue({
        darkMode: true,
        toggleDarkMode: mockToggleDarkMode,
      });
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to light mode');
      expect(toggleButton).toHaveTextContent('☀️');
    });
  });

  describe('Dark Mode Toggle', () => {
    it('should call toggleDarkMode when button is clicked', () => {
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to dark mode');
      fireEvent.click(toggleButton);
      expect(mockToggleDarkMode).toHaveBeenCalledTimes(1);
    });

    it('should have aria-pressed attribute set correctly', () => {
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to dark mode');
      expect(toggleButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('should have aria-pressed="true" when in dark mode', () => {
      (useAppStore as any).mockReturnValue({
        darkMode: true,
        toggleDarkMode: mockToggleDarkMode,
      });
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to light mode');
      expect(toggleButton).toHaveAttribute('aria-pressed', 'true');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels on all navigation links', () => {
      renderNavigation();
      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link).toHaveAttribute('aria-label');
      });
    });

    it('should have aria-current="page" for active link', () => {
      // Mock useLocation to return active path
      vi.mock('react-router-dom', async () => {
        const actual = await vi.importActual('react-router-dom');
        return {
          ...actual,
          useLocation: () => ({ pathname: '/' }),
        };
      });
      
      renderNavigation();
      const suggestionsLink = screen.getByLabelText('Navigate to Suggestions');
      expect(suggestionsLink).toHaveAttribute('aria-current', 'page');
    });

    it('should have focus styles on dark mode toggle', () => {
      renderNavigation();
      const toggleButton = screen.getByLabelText('Switch to dark mode');
      expect(toggleButton).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-blue-500');
    });
  });

  describe('Navigation Links', () => {
    it('should have correct href attributes', () => {
      renderNavigation();
      expect(screen.getByLabelText('Navigate to Suggestions')).toHaveAttribute('href', '/');
      expect(screen.getByLabelText('Navigate to HA Agent')).toHaveAttribute('href', '/ha-agent');
      expect(screen.getByLabelText('Navigate to Patterns')).toHaveAttribute('href', '/patterns');
    });

    it('should render mobile navigation on small screens', () => {
      renderNavigation();
      // Mobile nav should be present (hidden on desktop)
      const mobileNav = screen.getByRole('navigation').querySelector('.md\\:hidden');
      expect(mobileNav).toBeInTheDocument();
    });
  });
});

