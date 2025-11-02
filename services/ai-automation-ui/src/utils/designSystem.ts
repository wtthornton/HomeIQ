/**
 * Modern & Manly Design System - TypeScript Utilities
 * 
 * Helper functions and constants for the design system
 */

export const DesignSystem = {
  colors: {
    bg: {
      primary: '#0a0e27',
      secondary: '#1a1f3a',
      tertiary: '#0f1419',
    },
    card: {
      bg: 'rgba(15, 23, 42, 0.95)',
      bgAlt: 'rgba(30, 41, 59, 0.95)',
      border: 'rgba(51, 65, 85, 0.5)',
    },
    accent: {
      primary: '#3b82f6',
      secondary: '#06b6d4',
      glow: 'rgba(59, 130, 246, 0.2)',
    },
    text: {
      primary: '#ffffff',
      secondary: '#cbd5e1',
      tertiary: '#94a3b8',
      muted: '#64748b',
    },
    status: {
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6',
    },
  },
  
  gradients: {
    background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)',
    accent: 'linear-gradient(to right, #60a5fa, #06b6d4, #60a5fa)',
    text: 'linear-gradient(to right, #60a5fa, #06b6d4, #60a5fa)',
    buttonPrimary: 'linear-gradient(to right, #3b82f6, #2563eb)',
    buttonDanger: 'linear-gradient(to right, #ef4444, #dc2626)',
  },
  
  shadows: {
    card: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(59, 130, 246, 0.2), 0 0 100px rgba(59, 130, 246, 0.1)',
    button: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
    hover: '0 10px 15px -3px rgba(59, 130, 246, 0.3)',
  },
  
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '2.5rem',
    '3xl': '3rem',
  },
  
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    full: '9999px',
  },
  
  transitions: {
    standard: 'all 0.2s ease-in-out',
    spring: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
};

/**
 * Get card style object for inline styles
 */
export const getCardStyles = (additionalStyles?: React.CSSProperties) => ({
  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: DesignSystem.borderRadius.lg,
  boxShadow: DesignSystem.shadows.card,
  padding: DesignSystem.spacing['2xl'],
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  position: 'relative' as const,
  ...additionalStyles,
});

/**
 * Get button style object for inline styles
 */
export const getButtonStyles = (
  variant: 'primary' | 'secondary' | 'danger' = 'primary',
  additionalStyles?: React.CSSProperties
) => {
  const baseStyles = {
    fontWeight: 500,
    padding: '0.375rem 0.75rem',
    fontSize: '0.6875rem', // 11px - slightly smaller
    borderRadius: DesignSystem.borderRadius.md,
    border: 'none',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.025em',
    transition: DesignSystem.transitions.standard,
    cursor: 'pointer' as const,
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    gap: '0.375rem',
    height: 'auto',
    minHeight: 'unset',
    lineHeight: '1.2',
    ...additionalStyles,
  };

  switch (variant) {
    case 'primary':
      return {
        ...baseStyles,
        background: DesignSystem.gradients.buttonPrimary,
        color: 'white',
        boxShadow: DesignSystem.shadows.button,
      };
    case 'danger':
      return {
        ...baseStyles,
        background: DesignSystem.gradients.buttonDanger,
        color: 'white',
        boxShadow: DesignSystem.shadows.button,
      };
    case 'secondary':
    default:
      return {
        ...baseStyles,
        background: 'rgba(30, 41, 59, 0.8)',
        color: DesignSystem.colors.text.secondary,
        border: `1px solid ${DesignSystem.colors.card.border}`,
      };
  }
};

/**
 * Get modal overlay style
 */
export const getModalOverlayStyles = () => ({
  position: 'fixed' as const,
  inset: 0,
  background: DesignSystem.gradients.background,
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

/**
 * Get gradient text style
 */
export const getGradientTextStyles = () => ({
  background: DesignSystem.gradients.text,
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  color: 'transparent',
});

/**
 * Get corner accent style
 */
export const getCornerAccentStyles = (position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right') => {
  const base = {
    position: 'absolute' as const,
    width: '5rem',
    height: '5rem',
    borderWidth: '2px',
    borderStyle: 'solid' as const,
    borderColor: 'rgba(59, 130, 246, 0.5)',
  };

  switch (position) {
    case 'top-left':
      return { ...base, top: 0, left: 0, borderBottom: 'none', borderRight: 'none' };
    case 'top-right':
      return { ...base, top: 0, right: 0, borderBottom: 'none', borderLeft: 'none' };
    case 'bottom-left':
      return { ...base, bottom: 0, left: 0, borderTop: 'none', borderRight: 'none' };
    case 'bottom-right':
      return { ...base, bottom: 0, right: 0, borderTop: 'none', borderLeft: 'none' };
  }
};

