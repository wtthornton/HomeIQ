/**
 * HomeIQ Design System - Color Configuration
 * 
 * Centralized color tokens for consistent theming across the dashboard.
 * Based on HSL color space for easy manipulation.
 */

export const colors = {
  // Primary color scale - HomeIQ Blue
  primary: {
    50: 'hsl(217, 91%, 97%)',
    100: 'hsl(217, 91%, 94%)',
    200: 'hsl(217, 91%, 86%)',
    300: 'hsl(217, 91%, 74%)',
    400: 'hsl(217, 91%, 60%)',
    500: 'hsl(217, 91%, 50%)',   // Main brand color
    600: 'hsl(217, 91%, 44%)',
    700: 'hsl(217, 91%, 36%)',
    800: 'hsl(217, 91%, 28%)',
    900: 'hsl(217, 91%, 20%)',
    950: 'hsl(217, 91%, 12%)',
  },

  // Secondary color scale - Neutral Slate
  secondary: {
    50: 'hsl(210, 40%, 98%)',
    100: 'hsl(210, 40%, 96%)',
    200: 'hsl(214, 32%, 91%)',
    300: 'hsl(213, 27%, 84%)',
    400: 'hsl(215, 20%, 65%)',
    500: 'hsl(215, 16%, 47%)',
    600: 'hsl(215, 19%, 35%)',
    700: 'hsl(215, 25%, 27%)',
    800: 'hsl(217, 33%, 17%)',
    900: 'hsl(222, 47%, 11%)',
    950: 'hsl(229, 84%, 5%)',
  },

  // Semantic status colors for service health
  status: {
    healthy: {
      light: 'hsl(142, 76%, 94%)',
      main: 'hsl(142, 76%, 36%)',
      dark: 'hsl(142, 76%, 26%)',
    },
    warning: {
      light: 'hsl(38, 92%, 94%)',
      main: 'hsl(38, 92%, 50%)',
      dark: 'hsl(38, 92%, 40%)',
    },
    critical: {
      light: 'hsl(0, 84%, 94%)',
      main: 'hsl(0, 84%, 60%)',
      dark: 'hsl(0, 84%, 50%)',
    },
    offline: {
      light: 'hsl(220, 9%, 94%)',
      main: 'hsl(220, 9%, 46%)',
      dark: 'hsl(220, 9%, 36%)',
    },
  },

  // Smart home accent colors for different service categories
  accent: {
    weather: {
      light: 'hsl(199, 89%, 94%)',
      main: 'hsl(199, 89%, 48%)',
      dark: 'hsl(199, 89%, 38%)',
    },
    sports: {
      light: 'hsl(262, 83%, 94%)',
      main: 'hsl(262, 83%, 58%)',
      dark: 'hsl(262, 83%, 48%)',
    },
    automation: {
      light: 'hsl(25, 95%, 94%)',
      main: 'hsl(25, 95%, 53%)',
      dark: 'hsl(25, 95%, 43%)',
    },
    energy: {
      light: 'hsl(142, 71%, 94%)',
      main: 'hsl(142, 71%, 45%)',
      dark: 'hsl(142, 71%, 35%)',
    },
  },

  // Surface and background colors
  surface: {
    light: {
      background: 'hsl(0, 0%, 100%)',
      backgroundSecondary: 'hsl(210, 40%, 98%)',
      backgroundTertiary: 'hsl(210, 40%, 96%)',
      card: 'hsl(0, 0%, 100%)',
      cardHover: 'hsl(210, 40%, 98%)',
      border: 'hsl(214, 32%, 91%)',
      borderHover: 'hsl(215, 20%, 65%)',
    },
    dark: {
      background: 'hsl(222, 47%, 11%)',
      backgroundSecondary: 'hsl(217, 33%, 17%)',
      backgroundTertiary: 'hsl(215, 25%, 22%)',
      card: 'hsl(217, 33%, 17%)',
      cardHover: 'hsl(215, 25%, 22%)',
      border: 'hsl(215, 25%, 27%)',
      borderHover: 'hsl(215, 16%, 47%)',
    },
    ambient: {
      background: 'hsl(222, 40%, 8%)',
      backgroundSecondary: 'hsl(217, 33%, 12%)',
      backgroundTertiary: 'hsl(215, 25%, 16%)',
      card: 'hsl(217, 33%, 12%)',
      cardHover: 'hsl(215, 25%, 16%)',
      border: 'hsl(215, 25%, 20%)',
      borderHover: 'hsl(215, 16%, 35%)',
    },
  },

  // Text colors
  text: {
    light: {
      primary: 'hsl(222, 47%, 11%)',
      secondary: 'hsl(215, 16%, 47%)',
      tertiary: 'hsl(215, 20%, 65%)',
      inverse: 'hsl(0, 0%, 100%)',
    },
    dark: {
      primary: 'hsl(210, 40%, 98%)',
      secondary: 'hsl(215, 20%, 65%)',
      tertiary: 'hsl(215, 16%, 47%)',
      inverse: 'hsl(222, 47%, 11%)',
    },
    ambient: {
      primary: 'hsl(0, 0%, 85%)',
      secondary: 'hsl(0, 0%, 60%)',
      tertiary: 'hsl(0, 0%, 45%)',
      inverse: 'hsl(222, 40%, 8%)',
    },
  },
} as const;

// Type exports for TypeScript usage
export type ColorScale = typeof colors.primary;
export type StatusColor = typeof colors.status.healthy;
export type AccentColor = typeof colors.accent.weather;
export type SurfaceColors = typeof colors.surface.light;
export type TextColors = typeof colors.text.light;

// CSS variable mapping for easy integration
export const cssVariableMapping = {
  '--color-primary': colors.primary[500],
  '--color-primary-hover': colors.primary[600],
  '--color-primary-light': colors.primary[100],
  '--color-primary-dark': colors.primary[700],
  
  '--color-status-healthy': colors.status.healthy.main,
  '--color-status-warning': colors.status.warning.main,
  '--color-status-critical': colors.status.critical.main,
  '--color-status-offline': colors.status.offline.main,
  
  '--color-accent-weather': colors.accent.weather.main,
  '--color-accent-sports': colors.accent.sports.main,
  '--color-accent-automation': colors.accent.automation.main,
  '--color-accent-energy': colors.accent.energy.main,
} as const;
