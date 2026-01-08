# HomeIQ Health Dashboard - UI Component Library

**Last Updated:** January 7, 2026  
**Version:** 2.3

## Overview

The Health Dashboard uses a comprehensive UI component library based on **shadcn/ui** patterns with HomeIQ-specific customizations. All UI components follow consistent design patterns and use centralized design tokens.

## Component Library

### Available Components (26 total)

#### Core Interactive Components (8)
- **Button** (`@/components/ui/button`) - Multiple variants (primary, secondary, success, warning, destructive, ghost, link, status)
- **Card** (`@/components/ui/card`) - With status variants (healthy, warning, critical, offline) and glow effects
- **Badge** (`@/components/ui/badge`) - Status badges (healthy, warning, critical, offline) + service categories
- **Dialog** (`@/components/ui/dialog`) - Modal dialogs with overlay
- **Dropdown Menu** (`@/components/ui/dropdown-menu`) - Context menus with keyboard navigation
- **Tooltip** (`@/components/ui/tooltip`) - Hover tooltips + SimpleTooltip convenience component
- **Popover** (`@/components/ui/popover`) - Floating content containers
- **Tabs** (`@/components/ui/tabs`) - Tab navigation with vertical variant support

#### Form Components (7)
- **Input** (`@/components/ui/input`) - Text inputs with error/success states and icon support
- **Textarea** (`@/components/ui/textarea`) - Multi-line text inputs
- **Select** (`@/components/ui/select`) - Dropdown selects with keyboard navigation
- **Checkbox** (`@/components/ui/checkbox`) - Checkboxes with indeterminate state
- **Switch** (`@/components/ui/switch`) - Toggle switches with status color variants
- **Slider** (`@/components/ui/slider`) - Range sliders
- **Label** (`@/components/ui/label`) - Form labels

#### Feedback Components (5)
- **Skeleton** (`@/components/ui/skeleton`) - Loading skeletons (default, shimmer, pulse) + SkeletonText, SkeletonCard, SkeletonAvatar
- **Progress** (`@/components/ui/progress`) - Progress bars with status colors + CircularProgress component
- **Toast** (`@/components/ui/toast`) - Toast notifications with status variants
- **Toaster** (`@/components/ui/toaster`) - Toast provider with useToast hook
- **Alert Dialog** (`@/components/ui/alert-dialog`) - Alert modals with actions

#### Layout Components (5)
- **Separator** (`@/components/ui/separator`) - Horizontal/vertical dividers
- **Scroll Area** (`@/components/ui/scroll-area`) - Custom scrollbars
- **Avatar** (`@/components/ui/avatar`) - User avatars with status indicators (online, offline, busy, away)
- **Accordion** (`@/components/ui/accordion`) - Collapsible content sections
- **Glow Bg** (`@/components/ui/glow-bg`) - Atmospheric glow effects + GradientBg, AmbientGlow

## Usage Examples

### Basic Card with Status

```typescript
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui';

export const ServiceStatusCard = ({ status, title }) => {
  return (
    <Card variant="healthy" hover>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Badge variant="success" dot>Running</Badge>
      </CardContent>
    </Card>
  );
};
```

### Button with Loading State

```typescript
import { Button } from '@/components/ui';

export const ActionButton = () => {
  const [loading, setLoading] = useState(false);
  
  return (
    <Button 
      variant="primary" 
      size="lg"
      loading={loading}
      onClick={() => setLoading(true)}
    >
      Submit
    </Button>
  );
};
```

### Form with Validation

```typescript
import { Input, Label, Button } from '@/components/ui';

export const ConfigForm = () => {
  const [error, setError] = useState(false);
  
  return (
    <form>
      <Label htmlFor="api-key">API Key</Label>
      <Input 
        id="api-key"
        variant={error ? "error" : "default"}
        error={error}
      />
      <Button type="submit" variant="primary">Save</Button>
    </form>
  );
};
```

### Status Indicators

```typescript
import { Badge, Progress, Avatar } from '@/components/ui';

// Status badge
<Badge variant="healthy" dot>Healthy</Badge>
<Badge variant="warning">Degraded</Badge>
<Badge variant="critical">Critical</Badge>

// Progress with status color
<Progress value={75} variant="success" showValue />
<Progress value={50} variant="warning" animated />

// Avatar with status
<Avatar status="online" size="lg">
  <AvatarImage src="/user.jpg" />
  <AvatarFallback>JD</AvatarFallback>
</Avatar>
```

## Design System

### Colors

Colors are centralized in `src/config/colors.ts`:

- **Primary:** HomeIQ blue (50-950 scale)
- **Status:** healthy, warning, critical, offline
- **Accents:** weather, sports, automation, energy
- **Surfaces:** Light, dark, ambient theme variants

**Usage:**
```typescript
import { colors } from '@/config/colors';

// Access color tokens programmatically
const primaryColor = colors.primary[500];
const statusColor = colors.status.healthy.main;
```

**CSS Variables:**
All colors are available as CSS variables for use in Tailwind:
- `hsl(var(--primary))`
- `hsl(var(--status-healthy))`
- `hsl(var(--accent-weather))`

### Typography

**Font Families:**
- **Sans (Body):** Inter Variable
- **Display (Headings):** Outfit Variable  
- **Mono (Code/Metrics):** JetBrains Mono Variable

**Usage:**
```css
/* In CSS */
.font-display { font-family: var(--font-display); }
.font-mono { font-family: var(--font-mono); }
```

```typescript
// In React (via Tailwind)
<h1 className="font-display text-4xl font-bold">Title</h1>
<code className="font-mono">code</code>
```

### Themes

Three theme modes are supported:

1. **Light** (default) - Standard light theme
2. **Dark** (`.dark` class) - Dark theme for low-light environments
3. **Ambient** (`.ambient` class) - Ultra-low-light theme for dashboard viewing

**Usage:**
```typescript
// Toggle dark mode
document.documentElement.classList.toggle('dark');

// Enable ambient mode
document.documentElement.classList.add('ambient');
```

### Animations

Enhanced animation library with speed variants:

**Fade:**
- `animate-fade-in-faster` (0.15s)
- `animate-fade-in-fast` (0.2s)
- `animate-fade-in` (0.4s)
- `animate-fade-in-slow` (0.8s)

**Slide:**
- `animate-slide-up-fast` (0.15s)
- `animate-slide-up` (0.3s)
- `animate-slide-up-slow` (0.5s)

**Effects:**
- `animate-shimmer` - Shimmer loading effect
- `animate-pulse-ring` - Pulsing ring effect
- `animate-float` - Floating animation
- `animate-glow` - Glowing effect

**Usage:**
```typescript
<Card className="animate-fade-in">
  <div className="animate-shimmer">Loading...</div>
</Card>
```

### Breakpoints

Height-aware breakpoints for dashboard optimization:

```typescript
// Width-based (standard Tailwind)
sm: '640px'
md: '768px'
lg: '1024px'

// Height-based (NEW)
tall-sm: 'min-height: 640px'
tall-md: 'min-height: 768px'
tall-lg: 'min-height: 1024px'

// Combined queries
dashboard: 'min-width: 1024px and min-height: 768px'
dashboard-wide: 'min-width: 1280px and min-height: 800px'

// Orientation
portrait: 'orientation: portrait'
landscape: 'orientation: landscape'
```

**Usage:**
```typescript
<div className="tall-md:grid-cols-3 dashboard:grid-cols-4">
  {/* Adapts to viewport height and width */}
</div>
```

## Migration Guide

### From Custom CSS Classes to UI Primitives

**Before:**
```typescript
<div className="card-base card-hover">
  <button className="btn-primary">Action</button>
  <span className="badge-success">Status</span>
</div>
```

**After:**
```typescript
import { Card, CardContent, Button, Badge } from '@/components/ui';

<Card hover>
  <CardContent>
    <Button variant="primary">Action</Button>
    <Badge variant="success">Status</Badge>
  </CardContent>
</Card>
```

### Component Status Variants

**Status Mapping:**
- `healthy` → `variant="healthy"` (green)
- `warning` → `variant="warning"` (yellow/amber)
- `critical` → `variant="critical"` (red)
- `offline` → `variant="offline"` (gray)

**Card Status Borders:**
```typescript
<Card variant="healthy">  {/* Left border + status styling */}
<Card variant="warning">
<Card variant="critical">
<Card variant="offline">
```

## Best Practices

### ✅ DO

- Use UI primitives from `@/components/ui` for all new components
- Use `cn()` utility for conditional class merging
- Leverage status variants for semantic styling
- Use design system color tokens (CSS variables)
- Follow component composition patterns
- Use TypeScript interfaces for component props
- Add loading states with built-in loading prop
- Use status indicators (Badge, Progress, Avatar status)

### ❌ DON'T

- Don't create custom CSS classes that duplicate UI primitive functionality
- Don't use inline styles (use Tailwind classes or design tokens)
- Don't hardcode colors (use CSS variables or design tokens)
- Don't mix old CSS classes (`.card-base`, `.btn-primary`) with new components
- Don't bypass the design system for "quick fixes"

## Component Development

### Creating a New Component

```typescript
// src/components/MyComponent.tsx
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface MyComponentProps {
  title: string;
  variant?: 'default' | 'healthy' | 'warning' | 'critical';
  className?: string;
}

export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  variant = 'default',
  className,
}) => {
  return (
    <Card variant={variant} className={cn("animate-fade-in", className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="primary">Action</Button>
      </CardContent>
    </Card>
  );
};
```

### Adding Component Variants

```typescript
// Use class-variance-authority for variants
import { cva, type VariantProps } from 'class-variance-authority';

const myComponentVariants = cva(
  "base-classes",
  {
    variants: {
      variant: {
        default: "default-classes",
        custom: "custom-classes",
      },
      size: {
        sm: "small-classes",
        lg: "large-classes",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "sm",
    },
  }
);

export interface MyComponentProps
  extends VariantProps<typeof myComponentVariants> {
  // ... other props
}
```

## Accessibility

All components follow accessibility best practices:

- **Keyboard Navigation:** All interactive components support keyboard navigation
- **ARIA Labels:** Proper ARIA attributes for screen readers
- **Focus Management:** Visible focus indicators
- **Color Contrast:** WCAG AA compliant color combinations
- **Reduced Motion:** Animations respect `prefers-reduced-motion`

## Performance

- **Tree Shaking:** Only used components are bundled
- **Code Splitting:** Components can be lazy-loaded
- **CSS Variables:** Efficient theme switching without re-renders
- **Variable Fonts:** Smaller font file sizes with full weight range

## Resources

- **Component Source:** `src/components/ui/`
- **Color Config:** `src/config/colors.ts`
- **Font Config:** `src/styles/fonts.css`
- **Tailwind Config:** `tailwind.config.js`
- **shadcn/ui Docs:** https://ui.shadcn.com/
- **Radix UI Docs:** https://www.radix-ui.com/

---

**See Also:**
- [README.md](./README.md) - Main dashboard documentation
- [Tailwind Config](./tailwind.config.js) - Tailwind configuration
- [Color Config](./src/config/colors.ts) - Color system
