# Design Tokens - Health Dashboard

**Epic 14: Dashboard UX Polish**  
**Version:** 1.0  
**Last Updated:** October 12, 2025  
**Status:** Finalized

---

## Overview

This document defines the complete design token system for the Health Dashboard. All components should use these standardized classes for consistency, maintainability, and dark mode support.

---

## 🎨 Color Palette

### Status Colors
```css
/* Success/Healthy */
Light: bg-green-100 text-green-800 border-green-200
Dark:  bg-green-900 text-green-200 border-green-700

/* Warning/Degraded */
Light: bg-yellow-100 text-yellow-800 border-yellow-200
Dark:  bg-yellow-900 text-yellow-200 border-yellow-700

/* Error/Offline */
Light: bg-red-100 text-red-800 border-red-200
Dark:  bg-red-900 text-red-200 border-red-700

/* Info/Neutral */
Light: bg-blue-100 text-blue-800 border-blue-200
Dark:  bg-blue-900 text-blue-200 border-blue-700
```

### Background Colors
```css
/* Primary Background */
Light: bg-gray-50
Dark:  bg-gray-900

/* Card Background */
Light: bg-white
Dark:  bg-gray-800

/* Elevated/Hover */
Light: bg-gray-100
Dark:  bg-gray-700
```

### Text Colors
```css
/* Primary Text */
Light: text-gray-900
Dark:  text-white

/* Secondary Text */
Light: text-gray-600
Dark:  text-gray-400

/* Tertiary/Muted */
Light: text-gray-500
Dark:  text-gray-500
```

### Border Colors
```css
/* Primary Border */
Light: border-gray-200
Dark:  border-gray-700

/* Subtle Border */
Light: border-gray-100
Dark:  border-gray-800
```

---

## 📏 Spacing Scale (4px/8px Grid)

### Component Classes
```css
.spacing-sm   /* space-y-2  = 8px  (2 * 4px) */
.spacing-md   /* space-y-4  = 16px (4 * 4px) */
.spacing-lg   /* space-y-6  = 24px (6 * 4px) */
.spacing-xl   /* space-y-8  = 32px (8 * 4px) */
```

### Tailwind Utilities
```css
p-2  = 8px    /* Small padding */
p-4  = 16px   /* Medium padding */
p-6  = 24px   /* Large padding */
p-8  = 32px   /* XL padding */

gap-2  = 8px  /* Small gap */
gap-4  = 16px /* Medium gap */
gap-6  = 24px /* Large gap */
gap-8  = 32px /* XL gap */
```

---

## 🔘 Buttons

### Primary Button (.btn-primary)
```css
/* Usage: Main actions, submit, confirm */
.btn-primary {
  px-4 py-2           /* Padding: 16px x 8px */
  bg-blue-600         /* Background */
  hover:bg-blue-700   /* Hover state */
  text-white          /* Text color */
  rounded-lg          /* Border radius: 8px */
  font-medium         /* Font weight: 500 */
  shadow-sm           /* Subtle shadow */
  hover:shadow-md     /* Elevated shadow on hover */
  active:scale-95     /* Press animation */
}
```

### Secondary Button (.btn-secondary)
```css
/* Usage: Cancel, back, alternative actions */
.btn-secondary {
  px-4 py-2                        /* Padding */
  bg-gray-200 dark:bg-gray-700     /* Background */
  hover:bg-gray-300 dark:hover:bg-gray-600
  text-gray-800 dark:text-gray-200 /* Text */
  rounded-lg font-medium
  shadow-sm
  active:scale-95
}
```

### Success Button (.btn-success)
```css
/* Usage: Positive actions, enable, start */
.btn-success {
  px-4 py-2
  bg-green-600 hover:bg-green-700
  text-white
  rounded-lg font-medium
  shadow-sm hover:shadow-md
  active:scale-95
}
```

### Danger Button (.btn-danger)
```css
/* Usage: Delete, stop, disable */
.btn-danger {
  px-4 py-2
  bg-red-600 hover:bg-red-700
  text-white
  rounded-lg font-medium
  shadow-sm hover:shadow-md
  active:scale-95
}
```

### Button Press Animation (.btn-press)
```css
/* Add to any button for press feedback */
.btn-press {
  active:scale-98    /* Slight scale down */
  transition: transform 100ms
}
```

---

## 🏷️ Badges

### Success Badge (.badge-success)
```css
.badge-success {
  inline-flex items-center
  px-2.5 py-0.5           /* Padding: 10px x 2px */
  rounded-full            /* Fully rounded */
  text-xs font-medium     /* Small, medium weight */
  bg-green-100 text-green-800
  dark:bg-green-900 dark:text-green-200
}
```

### Warning Badge (.badge-warning)
```css
.badge-warning {
  /* Same structure */
  bg-yellow-100 text-yellow-800
  dark:bg-yellow-900 dark:text-yellow-200
}
```

### Error Badge (.badge-error)
```css
.badge-error {
  /* Same structure */
  bg-red-100 text-red-800
  dark:bg-red-900 dark:text-red-200
}
```

### Info Badge (.badge-info)
```css
.badge-info {
  /* Same structure */
  bg-blue-100 text-blue-800
  dark:bg-blue-900 dark:text-blue-200
}
```

---

## 🃏 Cards

### Base Card (.card-base)
```css
.card-base {
  bg-white dark:bg-gray-800    /* Background */
  rounded-lg                    /* Border radius: 8px */
  shadow-md                     /* Medium shadow */
  transition-all duration-200   /* Smooth transitions */
}
```

### Hoverable Card (.card-hover)
```css
.card-hover {
  /* Includes all .card-base styles, plus: */
  hover:shadow-lg          /* Elevated shadow */
  hover:-translate-y-0.5   /* Lift effect: 2px up */
  cursor-pointer           /* Pointer cursor */
}
```

---

## 📝 Forms

### Input Field (.input-base)
```css
.input-base {
  w-full                              /* Full width */
  px-3 py-2                           /* Padding */
  border border-gray-300 dark:border-gray-600
  rounded-lg                          /* Border radius */
  bg-white dark:bg-gray-800           /* Background */
  text-gray-900 dark:text-gray-100    /* Text color */
  focus:outline-none                  /* Remove default outline */
  focus:ring-2 focus:ring-blue-500    /* Custom focus ring */
  focus:border-transparent            /* Hide border on focus */
  transition-all duration-150
}
```

---

## 📰 Typography

### Display (.text-display)
```css
/* Usage: Hero headlines, main titles */
.text-display {
  text-4xl            /* 36px */
  font-bold           /* 700 weight */
  tracking-tight      /* -0.025em */
}
```

### Heading 1 (.text-h1)
```css
/* Usage: Page titles */
.text-h1 {
  text-3xl            /* 30px */
  font-bold           /* 700 weight */
}
```

### Heading 2 (.text-h2)
```css
/* Usage: Section titles */
.text-h2 {
  text-2xl            /* 24px */
  font-semibold       /* 600 weight */
}
```

### Heading 3 (.text-h3)
```css
/* Usage: Subsection titles */
.text-h3 {
  text-xl             /* 20px */
  font-semibold       /* 600 weight */
}
```

### Body (.text-body)
```css
/* Usage: Paragraph text */
.text-body {
  text-base           /* 16px */
  leading-relaxed     /* 1.625 line height */
}
```

### Small (.text-small)
```css
/* Usage: Captions, helper text */
.text-small {
  text-sm             /* 14px */
  text-gray-600 dark:text-gray-400
}
```

### Tiny (.text-tiny)
```css
/* Usage: Timestamps, metadata */
.text-tiny {
  text-xs             /* 12px */
  text-gray-500 dark:text-gray-500
}
```

---

## 🎬 Animations

### Content Fade-In (.content-fade-in)
```css
/* Usage: New content appearing */
animation: fadeIn 0.3s ease-in-out;

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Icon Entrance (.icon-entrance)
```css
/* Usage: Icon pop-in animation */
animation: iconEntrance 0.2s ease-out;

@keyframes iconEntrance {
  from { opacity: 0; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1); }
}
```

### Live Pulse (.live-pulse)
```css
/* Usage: Live/active indicators */
animation: live-pulse 2s ease-in-out infinite;

@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

### Live Pulse Dot (.live-pulse-dot)
```css
/* Usage: Small status indicators */
animation: pulse-dot 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Number Counter (.number-counter)
```css
/* Usage: Animating number changes */
transition: all 0.5s ease-in-out;
```

### Status Transition (.status-transition)
```css
/* Usage: Status badge color changes */
transition: background-color 0.3s, color 0.3s;
```

### Button Press (.btn-press)
```css
/* Usage: Button press feedback */
active:scale-98;
transition: transform 0.1s;
```

### Stagger In List (.stagger-in-list)
```css
/* Usage: List items appearing in sequence */
/* Apply to container, set animationDelay on children */
animation: fadeIn 0.3s ease-in-out;
/* Delay: 0.05s per item (50ms) */
```

---

## 🔢 Border Radius

```css
/* Small: 4px */
rounded       /* 4px - subtle rounding */

/* Medium: 8px */
rounded-lg    /* 8px - standard cards, buttons */

/* Large: 12px */
rounded-xl    /* 12px - modals, large cards */

/* Full: 9999px */
rounded-full  /* Fully rounded - badges, dots */
```

---

## 🌑 Shadows

```css
/* Small: Subtle elevation */
shadow-sm     /* 0 1px 2px rgba(0,0,0,0.05) */

/* Medium: Card elevation */
shadow-md     /* 0 4px 6px rgba(0,0,0,0.1) */

/* Large: Hover/active state */
shadow-lg     /* 0 10px 15px rgba(0,0,0,0.1) */

/* XL: Modals, overlays */
shadow-xl     /* 0 20px 25px rgba(0,0,0,0.1) */
```

---

## 📱 Responsive Breakpoints

```css
/* Tailwind default breakpoints */
sm: 640px    /* Small tablets */
md: 768px    /* Tablets */
lg: 1024px   /* Small desktops */
xl: 1280px   /* Large desktops */
2xl: 1536px  /* Extra large screens */

/* Usage: md:grid-cols-2 lg:grid-cols-3 */
```

---

## ♿ Accessibility

### Prefers Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  /* All animations disabled */
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Touch Targets
```css
/* Minimum size: 44x44px */
.btn-primary, .btn-secondary, etc. {
  min-height: 44px;  /* Sufficient for touch */
}
```

### Focus States
```css
/* All interactive elements */
focus:outline-none
focus:ring-2 focus:ring-blue-500
focus:ring-offset-2
```

---

## 🎯 Usage Guidelines

### DO:
✅ Use design system classes (.btn-primary, .card-base, etc.)  
✅ Follow 4px/8px grid for spacing  
✅ Use semantic color names (success, warning, error)  
✅ Test in both light and dark mode  
✅ Ensure 44x44px minimum touch targets  
✅ Support prefers-reduced-motion  

### DON'T:
❌ Use inline Tailwind for buttons/cards  
❌ Create custom shadows without tokens  
❌ Use arbitrary spacing values  
❌ Forget dark mode variants  
❌ Skip accessibility considerations  
❌ Create new animation durations  

---

## 📚 Component Examples

### Button
```tsx
<button className="btn-primary">
  Save Changes
</button>
```

### Card
```tsx
<div className="card-hover p-6">
  <h3 className="text-h3 mb-2">Title</h3>
  <p className="text-body">Content</p>
</div>
```

### Badge
```tsx
<span className="badge-success">
  Healthy
</span>
```

### Input
```tsx
<input 
  className="input-base"
  placeholder="Enter value..."
/>
```

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-12 | Initial design tokens documented |

---

**Maintained by:** BMad Master  
**Epic:** 14 - Dashboard UX Polish  
**Status:** 🟢 Active & Complete


