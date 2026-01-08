/** @type {import('tailwindcss').Config} */

import tailwindcssAnimate from 'tailwindcss-animate';

export default {
  darkMode: ['class'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      // Font families
      fontFamily: {
        sans: ['var(--font-sans)'],
        display: ['var(--font-display)'],
        mono: ['var(--font-mono)'],
      },

      // Colors using CSS variables for theme switching
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
          hover: "hsl(var(--primary-hover))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        
        // Status colors for service health
        status: {
          healthy: "hsl(var(--status-healthy))",
          "healthy-light": "hsl(var(--status-healthy-light))",
          warning: "hsl(var(--status-warning))",
          "warning-light": "hsl(var(--status-warning-light))",
          critical: "hsl(var(--status-critical))",
          "critical-light": "hsl(var(--status-critical-light))",
          offline: "hsl(var(--status-offline))",
          "offline-light": "hsl(var(--status-offline-light))",
        },
        
        // Smart home accent colors
        "accent-weather": "hsl(var(--accent-weather))",
        "accent-sports": "hsl(var(--accent-sports))",
        "accent-automation": "hsl(var(--accent-automation))",
        "accent-energy": "hsl(var(--accent-energy))",
      },

      // Border radius
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      // Box shadows
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },

      // Height-aware breakpoints
      screens: {
        // Standard width breakpoints (Tailwind defaults)
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
        
        // Height-based breakpoints
        'tall-sm': { 'raw': '(min-height: 640px)' },
        'tall-md': { 'raw': '(min-height: 768px)' },
        'tall-lg': { 'raw': '(min-height: 1024px)' },
        
        // Combined queries for dashboard optimization
        'dashboard': { 'raw': '(min-width: 1024px) and (min-height: 768px)' },
        'dashboard-wide': { 'raw': '(min-width: 1280px) and (min-height: 800px)' },
        
        // Portrait/landscape detection
        'portrait': { 'raw': '(orientation: portrait)' },
        'landscape': { 'raw': '(orientation: landscape)' },
      },

      // Keyframes
      keyframes: {
        // Existing animations (preserved)
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInFromRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInFromLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        scaleOut: {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '100%': { transform: 'scale(0.95)', opacity: '0' },
        },
        
        // New animations (from vibe-coding-starter)
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseRing: {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(1.5)', opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        glow: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-3deg)' },
          '50%': { transform: 'rotate(3deg)' },
        },
        tilt: {
          '0%, 50%, 100%': { transform: 'rotate(0deg)' },
          '25%': { transform: 'rotate(0.5deg)' },
          '75%': { transform: 'rotate(-0.5deg)' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        pulseGlow: {
          '0%, 100%': { 
            boxShadow: '0 0 5px hsl(var(--primary)), 0 0 10px hsl(var(--primary)), 0 0 15px hsl(var(--primary))' 
          },
          '50%': { 
            boxShadow: '0 0 10px hsl(var(--primary)), 0 0 20px hsl(var(--primary)), 0 0 30px hsl(var(--primary))' 
          },
        },
        spin: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        ping: {
          '75%, 100%': { transform: 'scale(2)', opacity: '0' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        bounce: {
          '0%, 100%': { 
            transform: 'translateY(-25%)',
            animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)',
          },
          '50%': {
            transform: 'translateY(0)',
            animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)',
          },
        },
        
        // Accordion animations (for shadcn/ui)
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        
        // Collapsible animations
        "collapsible-down": {
          from: { height: "0" },
          to: { height: "var(--radix-collapsible-content-height)" },
        },
        "collapsible-up": {
          from: { height: "var(--radix-collapsible-content-height)" },
          to: { height: "0" },
        },
      },

      // Animation utilities with speed variants
      animation: {
        // Fade variants
        'fade-in-faster': 'fadeIn 0.15s ease-out',
        'fade-in-fast': 'fadeIn 0.2s ease-out',
        'fade-in': 'fadeIn 0.4s ease-out',
        'fade-in-slow': 'fadeIn 0.8s ease-out',
        'fade-out': 'fadeOut 0.3s ease-out',
        
        // Slide variants
        'slide-up-fast': 'slideUp 0.15s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-up-slow': 'slideUp 0.5s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'slide-in-right': 'slideInFromRight 0.3s ease-out',
        'slide-in-left': 'slideInFromLeft 0.3s ease-out',
        
        // Scale variants
        'scale-in': 'scaleIn 0.2s ease-out',
        'scale-out': 'scaleOut 0.2s ease-out',
        
        // Effect animations
        'shimmer': 'shimmer 2s linear infinite',
        'pulse-ring': 'pulseRing 1.5s ease-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'wiggle': 'wiggle 1s ease-in-out infinite',
        'tilt': 'tilt 10s linear infinite',
        'bounce-subtle': 'bounceSubtle 0.6s ease-in-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        
        // Utility animations
        'spin': 'spin 1s linear infinite',
        'spin-slow': 'spin 3s linear infinite',
        'ping': 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite',
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce': 'bounce 1s infinite',
        
        // Accordion/Collapsible
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "collapsible-down": "collapsible-down 0.2s ease-out",
        "collapsible-up": "collapsible-up 0.2s ease-out",
      },

      // Transition timing functions
      transitionTimingFunction: {
        'ease-spring': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'ease-bounce': 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
}
