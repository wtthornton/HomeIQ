# 2025 Modern Design Patterns - Quick Reference

**Date:** November 30, 2025  
**Status:** ✅ Active Design Standard  
**Version:** 1.0.0

## Overview

This document provides a quick reference for the modern 2025 design patterns implemented across the HomeIQ UI. These patterns create a polished, space-efficient, and visually appealing user experience.

---

## 🎨 Core Patterns

### 1. Collapsible Sections

**Purpose**: Save screen space while keeping important controls accessible

**Key Features**:
- Smooth height animation (0.4s cubic-bezier)
- Rotating arrow indicator (▲/▼)
- Gradient toggle button
- Glassmorphism content area

**Implementation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion';

const [isOpen, setIsOpen] = useState(true);

<motion.div className="rounded-2xl overflow-hidden
  bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20
  border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm">
  
  {/* Header */}
  <div className="p-4 border-b border-blue-500/20">
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-bold">Section Title</h2>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600
          text-white shadow-lg shadow-blue-500/30"
      >
        <motion.span animate={{ rotate: isOpen ? 180 : 0 }}>
          {isOpen ? '▲' : '▼'}
        </motion.span>
        {isOpen ? 'Hide' : 'Show'}
      </motion.button>
    </div>
  </div>

  {/* Content */}
  <AnimatePresence>
    {isOpen && (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      >
        <div className="p-6 bg-slate-900/40 backdrop-blur-sm">
          {/* Content */}
        </div>
      </motion.div>
    )}
  </AnimatePresence>
</motion.div>
```

**Reference**: `services/ai-automation-ui/src/pages/Synergies.tsx` (lines 574-986)

---

### 2. Glassmorphism Effects

**Purpose**: Modern frosted glass appearance for depth and visual interest

**Dark Mode**:
```tsx
className="bg-slate-900/40 backdrop-blur-sm border border-blue-500/20"
```

**Light Mode**:
```tsx
className="bg-white/60 backdrop-blur-sm border border-blue-200/50"
```

**Variations**:
- `bg-slate-800/60` - More opaque (dark)
- `bg-white/80` - More opaque (light)
- `backdrop-blur-md` - Stronger blur effect

---

### 3. Gradient Backgrounds

**Card Gradients**:

**Dark Mode**:
```tsx
className="bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20
  border border-blue-500/20 shadow-2xl shadow-blue-900/20"
```

**Light Mode**:
```tsx
className="bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50
  border border-blue-200/50 shadow-xl shadow-blue-100/50"
```

**Button Gradients**:
```tsx
// Primary button
className="bg-gradient-to-r from-blue-600 to-purple-600 text-white
  shadow-lg shadow-blue-500/30"

// Light mode
className="bg-gradient-to-r from-blue-500 to-purple-500 text-white
  shadow-lg shadow-blue-400/30"
```

**Text Gradients**:
```tsx
className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
```

---

### 4. Enhanced Shadows

**Pattern**: Color-tinted shadows for depth and visual interest

**Card Shadows**:
```tsx
// Dark mode
className="shadow-2xl shadow-blue-900/20"

// Light mode
className="shadow-xl shadow-blue-100/50"
```

**Button Shadows**:
```tsx
className="shadow-lg shadow-blue-500/30"
```

---

### 5. Smooth Animations

**Standard Transition**:
```tsx
transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
```

**Hover Effects**:
```tsx
<motion.div
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>
```

**Rotating Icons**:
```tsx
<motion.span
  animate={{ rotate: isOpen ? 180 : 0 }}
  transition={{ duration: 0.3, ease: "easeInOut" }}
>
```

---

## 🎯 Usage Guidelines

### When to Use Each Pattern

**Collapsible Sections**:
- ✅ Statistics dashboards
- ✅ Filter panels
- ✅ Control sections
- ✅ Information panels
- ❌ Critical information (always visible)
- ❌ Primary actions

**Glassmorphism**:
- ✅ Overlay panels
- ✅ Modal backgrounds
- ✅ Elevated content
- ✅ Information cards
- ❌ Primary backgrounds
- ❌ High-contrast needs

**Gradients**:
- ✅ Hero sections
- ✅ Primary buttons
- ✅ Card backgrounds
- ✅ Text highlights
- ❌ Body text
- ❌ Small elements

---

## 📐 Design Tokens

### Spacing
- Section padding: `p-6` (24px)
- Card padding: `p-4` (16px) or `p-6` (24px)
- Gap between items: `gap-4` (16px)
- Border radius: `rounded-xl` (12px) or `rounded-2xl` (16px)

### Colors
- Primary: `blue-600` / `blue-500`
- Accent: `purple-600` / `purple-500`
- Background dark: `slate-900/95`
- Background light: `white` or `white/60` (glassmorphism)

### Shadows
- Card: `shadow-2xl shadow-blue-900/20` (dark) or `shadow-xl shadow-blue-100/50` (light)
- Button: `shadow-lg shadow-blue-500/30`
- Hover: Enhanced shadow on hover

### Animations
- Duration: `0.4s` (standard), `0.3s` (quick)
- Easing: `cubic-bezier(0.4, 0, 0.2, 1)` (smooth)
- Hover scale: `1.05`
- Tap scale: `0.95`

---

## 🔗 Related Documentation

- **[Frontend Specification](../architecture/frontend-specification.md)** - Complete design system
- **[Modern Design System](./MODERN_MANLY_DESIGN_SYSTEM.md)** - Full design tokens
- **[UX Pattern Quick Reference](../kb/ux-pattern-quick-reference.md)** - Pattern catalog
- **[UI Design Goals](../prd/user-interface-design-goals.md)** - Design philosophy

---

## 📝 Examples

### Complete Collapsible Section Example

See `services/ai-automation-ui/src/pages/Synergies.tsx` for a complete implementation of:
- Collapsible statistics section
- Glassmorphism effects
- Gradient backgrounds
- Smooth animations
- Modern button styles

---

## ✅ Checklist for New Components

When implementing new UI components, ensure:

- [ ] Uses collapsible pattern for non-critical sections
- [ ] Implements glassmorphism where appropriate
- [ ] Uses gradient backgrounds for hero/primary elements
- [ ] Includes smooth animations (0.4s transitions)
- [ ] Supports both dark and light modes
- [ ] Uses enhanced shadows for depth
- [ ] Follows spacing guidelines (p-4, p-6, gap-4)
- [ ] Implements hover/tap feedback
- [ ] Respects `prefers-reduced-motion`

---

**Maintained by**: BMad Master  
**Last Updated**: November 30, 2025  
**Status**: ✅ Active & Production-Ready

