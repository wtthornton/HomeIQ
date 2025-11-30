# Modern & Manly Design System

**Date:** November 30, 2025  
**Status:** ✅ Active Design Standard  
**Version:** 2.0.0 - Enhanced with 2025 Modern Patterns

## Overview

A bold, tech-focused design system that combines modern aesthetics with industrial strength. Characterized by deep, dark color palettes, geometric accents, and professional typography with subtle technological touches.

## Design Philosophy

- **Bold & Confident**: Strong, assertive visual language
- **Tech-Forward**: Modern technology aesthetic without being gimmicky
- **Professional**: Enterprise-grade polish and attention to detail
- **Functional**: Every visual element serves a purpose

---

## Color Palette

### Primary Colors

```css
/* Dark Backgrounds */
--bg-primary: #0a0e27;           /* Deep navy */
--bg-secondary: #1a1f3a;         /* Dark blue-grey */
--bg-tertiary: #0f1419;          /* Near black */

/* Card/Surface Colors */
--card-bg: rgba(15, 23, 42, 0.95);  /* Slate-900 with transparency */
--card-bg-alt: rgba(30, 41, 59, 0.95); /* Slate-800 with transparency */
--card-border: rgba(51, 65, 85, 0.5);  /* Slate-700/50 */

/* Accent Colors */
--accent-primary: #3b82f6;       /* Blue-500 */
--accent-secondary: #06b6d4;     /* Cyan-500 */
--accent-glow: rgba(59, 130, 246, 0.2); /* Blue glow */

/* Text Colors */
--text-primary: #ffffff;          /* White */
--text-secondary: #cbd5e1;       /* Slate-300 */
--text-tertiary: #94a3b8;        /* Slate-400 */
--text-muted: #64748b;           /* Slate-500 */

/* Gradient Colors */
--gradient-primary: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
--gradient-accent: linear-gradient(to right, #60a5fa, #06b6d4, #3b82f6);
--gradient-text: linear-gradient(to right, #60a5fa, #06b6d4, #60a5fa);
```

### Semantic Colors

```css
/* Status Colors */
--success: #10b981;              /* Emerald-500 */
--success-glow: rgba(16, 185, 129, 0.2);
--warning: #f59e0b;              /* Amber-500 */
--error: #ef4444;                /* Red-500 */
--info: #3b82f6;                 /* Blue-500 */

/* Interactive States */
--hover-bg: rgba(51, 65, 85, 0.3);  /* Slate-700/30 */
--active-bg: rgba(51, 65, 85, 0.5); /* Slate-700/50 */
--focus-ring: rgba(59, 130, 246, 0.5); /* Blue focus ring */
```

---

## Typography

### Font Families
- **Primary**: System font stack (SF Pro, Segoe UI, Roboto, sans-serif)
- **Monospace**: 'Courier New', 'Monaco', monospace (for code/data)

### Font Scales

```css
/* Headings */
--text-4xl: 2.25rem;    /* 36px - Hero titles */
--text-3xl: 1.875rem;   /* 30px - Page titles */
--text-2xl: 1.5rem;     /* 24px - Section titles */
--text-xl: 1.25rem;     /* 20px - Card titles */
--text-lg: 1.125rem;    /* 18px - Large body */
--text-base: 1rem;      /* 16px - Body text */
--text-sm: 0.875rem;    /* 14px - Small text */
--text-xs: 0.75rem;     /* 12px - Labels, captions */

/* Font Weights */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;

/* Letter Spacing */
--tracking-tight: -0.025em;
--tracking-normal: 0;
--tracking-wide: 0.025em;
--tracking-wider: 0.05em;
```

### Typography Styles

#### Hero Title
```css
font-size: 2.25rem;
font-weight: 700;
letter-spacing: -0.025em;
background: linear-gradient(to right, #60a5fa, #06b6d4, #60a5fa);
background-clip: text;
-webkit-background-clip: text;
color: transparent;
text-transform: uppercase;
```

#### Section Title
```css
font-size: 1.5rem;
font-weight: 700;
color: var(--text-primary);
letter-spacing: var(--tracking-tight);
text-transform: uppercase;
```

#### Body Text
```css
font-size: 1rem;
font-weight: 400;
color: var(--text-secondary);
line-height: 1.6;
```

#### Label
```css
font-size: 0.75rem;
font-weight: 600;
color: var(--text-tertiary);
text-transform: uppercase;
letter-spacing: var(--tracking-wider);
```

---

## Component Styles

### Cards

```css
.card {
  background: linear-gradient(135deg, 
    rgba(15, 23, 42, 0.95) 0%, 
    rgba(30, 41, 59, 0.95) 100%);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 0.75rem; /* rounded-xl */
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.8),
    0 0 0 1px rgba(59, 130, 246, 0.2),
    0 0 100px rgba(59, 130, 246, 0.1);
  padding: 2.5rem; /* p-10 */
  backdrop-filter: blur(12px);
  position: relative;
}

/* Corner Accents */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 5rem;
  height: 5rem;
  border-top: 2px solid rgba(59, 130, 246, 0.5);
  border-left: 2px solid rgba(59, 130, 246, 0.5);
}

.card::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 5rem;
  height: 5rem;
  border-top: 2px solid rgba(59, 130, 246, 0.5);
  border-right: 2px solid rgba(59, 130, 246, 0.5);
}
```

### Buttons

#### Primary Button
```css
.btn-primary {
  background: linear-gradient(to right, #3b82f6, #2563eb);
  color: white;
  font-weight: 600;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  border: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
}

.btn-primary:hover {
  background: linear-gradient(to right, #2563eb, #1d4ed8);
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}
```

#### Secondary Button
```css
.btn-secondary {
  background: rgba(30, 41, 59, 0.8);
  color: var(--text-secondary);
  border: 1px solid rgba(51, 65, 85, 0.5);
  font-weight: 600;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.btn-secondary:hover {
  background: rgba(51, 65, 85, 0.5);
  border-color: rgba(59, 130, 246, 0.5);
}
```

### Progress Bars

```css
.progress-bar {
  width: 100%;
  height: 0.5rem;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 9999px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(to right, #2563eb, #06b6d4, #2563eb);
  border-radius: 9999px;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to right, 
    transparent, 
    rgba(255, 255, 255, 0.3), 
    transparent);
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
```

### Modals

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, 
    rgba(10, 14, 39, 0.95) 0%, 
    rgba(26, 31, 58, 0.95) 100%);
  backdrop-filter: blur(12px);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: linear-gradient(135deg, 
    rgba(15, 23, 42, 0.95) 0%, 
    rgba(30, 41, 59, 0.95) 100%);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 1rem;
  padding: 2rem;
  max-width: 28rem;
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.8),
    0 0 0 1px rgba(59, 130, 246, 0.2);
}
```

### Inputs

```css
.input {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  font-size: 1rem;
}

.input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input::placeholder {
  color: var(--text-muted);
}
```

---

## Effects & Animations

### Glow Effects

```css
.glow-primary {
  box-shadow: 
    0 0 20px rgba(59, 130, 246, 0.3),
    0 0 40px rgba(59, 130, 246, 0.2),
    0 0 60px rgba(59, 130, 246, 0.1);
}

.glow-accent {
  box-shadow: 
    0 0 20px rgba(6, 182, 212, 0.3),
    0 0 40px rgba(6, 182, 212, 0.2);
}
```

### Background Patterns

#### Grid Background
```css
.grid-bg {
  background-image: 
    linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  opacity: 0.1;
}
```

### Transitions

```css
/* Standard transitions */
transition: all 0.2s ease-in-out;

/* Spring animations */
transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
```

---

## Spacing Scale

```css
--spacing-xs: 0.25rem;   /* 4px */
--spacing-sm: 0.5rem;    /* 8px */
--spacing-md: 1rem;      /* 16px */
--spacing-lg: 1.5rem;    /* 24px */
--spacing-xl: 2rem;      /* 32px */
--spacing-2xl: 2.5rem;   /* 40px */
--spacing-3xl: 3rem;     /* 48px */
```

---

## Border Radius

```css
--radius-sm: 0.25rem;    /* 4px */
--radius-md: 0.5rem;     /* 8px */
--radius-lg: 0.75rem;    /* 12px */
--radius-xl: 1rem;       /* 16px */
--radius-full: 9999px;   /* Full circle */
```

---

## Shadows

```css
/* Card Shadow */
--shadow-card: 
  0 25px 50px -12px rgba(0, 0, 0, 0.8),
  0 0 0 1px rgba(59, 130, 246, 0.2),
  0 0 100px rgba(59, 130, 246, 0.1);

/* Button Shadow */
--shadow-button: 0 4px 6px -1px rgba(0, 0, 0, 0.3);

/* Hover Shadow */
--shadow-hover: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
```

---

## Icon Guidelines

### Icon Sizes
- **Small**: 16px (text-sm)
- **Medium**: 24px (text-base)
- **Large**: 48px (text-4xl)
- **XLarge**: 64px (text-6xl)

### Icon Style
- Use emoji or icon fonts
- Add glow effect for important icons
- Animate icons for loading/processing states

---

## Usage Examples

### Card Component
```tsx
<div className="card">
  <h2 className="section-title">Title</h2>
  <p className="body-text">Content here</p>
</div>
```

### Button Component
```tsx
<button className="btn-primary">Action</button>
<button className="btn-secondary">Cancel</button>
```

### Modal Component
```tsx
<div className="modal-overlay">
  <div className="modal-content">
    {/* Modal content */}
  </div>
</div>
```

---

## Accessibility

- **Color Contrast**: Minimum 4.5:1 for text
- **Focus States**: Visible focus rings on all interactive elements
- **Animation**: Respect `prefers-reduced-motion` media query
- **Typography**: Minimum 16px for body text

---

## Implementation Notes

- Use CSS custom properties (CSS variables) for easy theming
- All colors should work in both light and dark modes (this system is dark-first)
- Animations should be subtle and purposeful
- Glassmorphism effects use `backdrop-filter` with fallbacks

---

## 2025 Modern Design Patterns (NEW)

### Collapsible Sections

**Pattern**: Space-efficient sections that can be collapsed/expanded

**Implementation**:
```tsx
// Header with toggle button
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  className="bg-gradient-to-r from-blue-600 to-purple-600 
    text-white shadow-lg shadow-blue-500/30"
>
  <motion.span animate={{ rotate: isOpen ? 180 : 0 }}>
    {isOpen ? '▲' : '▼'}
  </motion.span>
</motion.button>

// Collapsible content with smooth animation
<AnimatePresence>
  {isOpen && (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Content */}
    </motion.div>
  )}
</AnimatePresence>
```

### Glassmorphism Effects

**Pattern**: Frosted glass appearance with backdrop blur

```css
/* Dark Mode */
.glass-dark {
  background: rgba(15, 23, 42, 0.4);  /* slate-900/40 */
  backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.2);  /* blue-500/20 */
}

/* Light Mode */
.glass-light {
  background: rgba(255, 255, 255, 0.6);  /* white/60 */
  backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.2);  /* blue-200/50 */
}
```

### Enhanced Gradient System

**Card Gradients**:
```css
/* Dark Mode Card */
.card-gradient-dark {
  background: linear-gradient(
    135deg,
    rgba(15, 23, 42, 0.95) 0%,      /* slate-900/95 */
    rgba(30, 58, 138, 0.2) 50%,     /* blue-900/20 */
    rgba(88, 28, 135, 0.2) 100%    /* purple-900/20 */
  );
  border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.8),
    0 0 0 1px rgba(59, 130, 246, 0.2),
    0 0 100px rgba(59, 130, 246, 0.1);
}

/* Light Mode Card */
.card-gradient-light {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 1) 0%,
    rgba(239, 246, 255, 0.5) 50%,   /* blue-50/50 */
    rgba(250, 245, 255, 0.5) 100%   /* purple-50/50 */
  );
  border: 1px solid rgba(191, 219, 254, 0.5);  /* blue-200/50 */
  box-shadow: 
    0 20px 25px -5px rgba(59, 130, 246, 0.1),
    0 10px 10px -5px rgba(59, 130, 246, 0.04);
}
```

**Button Gradients**:
```css
.btn-gradient-primary {
  background: linear-gradient(to right, #3b82f6, #9333ea);
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
}

.btn-gradient-primary:hover {
  background: linear-gradient(to right, #2563eb, #7e22ce);
  box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.4);
}
```

### Modern Animation System

**Smooth Transitions**:
```css
/* Standard smooth transition */
.transition-smooth {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Height animation for collapsible */
.animate-height {
  transition: height 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Framer Motion Patterns**:
```tsx
// Hover effects
<motion.div
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>

// Rotating icons
<motion.span
  animate={{ rotate: isOpen ? 180 : 0 }}
  transition={{ duration: 0.3, ease: "easeInOut" }}
>

// Stagger animations
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: index * 0.1 }}
>
```

## Version History

- **2.0.0** (Nov 30, 2025): Enhanced with 2025 modern patterns (collapsible sections, glassmorphism, enhanced gradients)
- **1.0.0** (Nov 1, 2025): Initial design system extracted from ReverseEngineeringLoader

