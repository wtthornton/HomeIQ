# UX Pattern Quick Reference

**Last Updated:** November 30, 2025  
**Status:** ✅ Active Reference

## 2025 Modern Design Patterns

### Collapsible Statistics & Filters Section

**Pattern**: Space-efficient collapsible section for statistics, filters, and controls

**When to Use**:
- Statistics dashboards
- Filter panels
- Control sections
- Information panels that can be hidden

**Implementation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion';

const [showStats, setShowStats] = useState(true);

<motion.div className="rounded-2xl overflow-hidden transition-all duration-300
  bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20
  border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm">
  
  {/* Header */}
  <motion.div className="p-4 border-b border-blue-500/20">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-xl">📊</span>
        <h2 className="text-lg font-bold">Statistics & Filters</h2>
      </div>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setShowStats(!showStats)}
        className="px-4 py-2 rounded-xl font-medium text-sm
          bg-gradient-to-r from-blue-600 to-purple-600 text-white
          shadow-lg shadow-blue-500/30"
      >
        <motion.span
          animate={{ rotate: showStats ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          {showStats ? '▲' : '▼'}
        </motion.span>
        {showStats ? 'Hide' : 'Show'}
      </motion.button>
    </div>
  </motion.div>

  {/* Collapsible Content */}
  <AnimatePresence>
    {showStats && (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
        className="overflow-hidden"
      >
        <div className="p-6 bg-slate-900/40 backdrop-blur-sm">
          {/* Stats, filters, controls */}
        </div>
      </motion.div>
    )}
  </AnimatePresence>
</motion.div>
```

**Key Features**:
- ✅ Smooth height animation (0.4s)
- ✅ Rotating arrow indicator
- ✅ Gradient button backgrounds
- ✅ Glassmorphism effects
- ✅ Space-efficient when collapsed

**Reference Implementation**: `services/ai-automation-ui/src/pages/Synergies.tsx` (lines 574-986)

---

### Glassmorphism Card Pattern

**Pattern**: Modern frosted glass appearance for cards and overlays

**When to Use**:
- Information cards
- Overlay panels
- Modal backgrounds
- Elevated content sections

**Implementation**:
```tsx
// Dark Mode
<div className="bg-slate-900/40 backdrop-blur-sm border border-blue-500/20
  rounded-xl p-6 shadow-lg">

// Light Mode
<div className="bg-white/60 backdrop-blur-sm border border-blue-200/50
  rounded-xl p-6 shadow-lg">
```

**Variations**:
- `bg-slate-800/60` - More opaque (dark)
- `bg-white/80` - More opaque (light)
- `backdrop-blur-md` - Stronger blur
- `backdrop-blur-sm` - Subtle blur (preferred)

---

### Gradient Background Pattern

**Pattern**: Modern gradient backgrounds for hero sections and cards

**Dark Mode Gradients**:
```tsx
// Card gradient
className="bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20"

// Button gradient
className="bg-gradient-to-r from-blue-600 to-purple-600"

// Text gradient
className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
```

**Light Mode Gradients**:
```tsx
// Card gradient
className="bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50"

// Button gradient
className="bg-gradient-to-r from-blue-500 to-purple-500"
```

---

### Enhanced Button Patterns

**Gradient Primary Button**:
```tsx
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  className="px-4 py-2 rounded-xl font-medium text-sm
    bg-gradient-to-r from-blue-600 to-purple-600 text-white
    shadow-lg shadow-blue-500/30 transition-all duration-300"
>
  Action
</motion.button>
```

**Secondary Button**:
```tsx
<button className="px-4 py-2 rounded-xl font-medium text-sm
  bg-slate-800/60 hover:bg-slate-700/60 text-gray-300 hover:text-white
  border border-slate-700/50 shadow-sm hover:shadow-md">
  Secondary
</button>
```

---

### Smooth Animation Patterns

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
  {isOpen ? '▲' : '▼'}
</motion.span>
```

---

## Pattern Catalog

### Overview Tab Pattern
**File**: `docs/kb/context7-cache/ux-patterns/overview-tab-glanceable-dashboard-pattern.md`  
**Status**: ✅ Complete  
**Use For**: Dashboard overview pages

### Health Dashboard Dependencies Tab Pattern
**File**: `docs/kb/context7-cache/ux-patterns/health-dashboard-dependencies-tab-pattern.md`  
**Status**: ✅ Complete  
**Use For**: Dependency visualization

### Collapsible Statistics Pattern (NEW)
**Status**: ✅ Active  
**Use For**: Statistics, filters, control panels  
**Reference**: Synergies page implementation

---

## Quick Reference

### Spacing
- Section margin: `mb-6` (24px)
- Card padding: `p-6` (24px)
- Gap between items: `gap-4` (16px)

### Colors
- Primary: `blue-600` / `blue-500`
- Accent: `purple-600` / `purple-500`
- Success: `green-500`
- Warning: `yellow-500`
- Error: `red-500`

### Shadows
- Card: `shadow-lg`
- Button: `shadow-lg shadow-blue-500/30`
- Card with glow: `shadow-2xl shadow-blue-900/20`

### Border Radius
- Cards: `rounded-xl` (12px)
- Buttons: `rounded-xl` (12px)
- Small elements: `rounded-lg` (8px)

---

**Maintained by**: BMad Master  
**Last Updated**: November 30, 2025
