# SendButton Component Documentation

## Overview

The `SendButton` component is a modern, accessible send button optimized for 2025 best practices. It provides enhanced visual states, micro-interactions, and comprehensive accessibility support.

## Features

### ✅ Phase 1 Implementations (Complete)

1. **Send Icon Integration**
   - SVG send icon (paper plane) in default state
   - Icon animates on hover (subtle forward movement)
   - Icon-only mode for compact layouts

2. **Enhanced Visual States**
   - Hover: Scale 1.02x, color transition, icon animation
   - Active: Scale 0.98x, immediate feedback
   - Disabled: Reduced opacity, gray color scheme
   - Loading: Smooth spinner animation
   - Error: Red accent with retry option

3. **Accessibility Improvements**
   - Comprehensive ARIA labels (`aria-label`, `aria-busy`, `aria-disabled`, `aria-live`)
   - Keyboard navigation support (Enter, Space)
   - Focus indicators (2px ring, high contrast)
   - Screen reader announcements
   - Reduced motion support (`prefers-reduced-motion`)

4. **Better Loading Indicator**
   - Smooth rotating spinner
   - Customizable loading text
   - Maintains button structure during loading

### 🎨 Visual Design

**Default State:**
- Background: Blue-600 (dark) / Blue-500 (light)
- Text: White
- Icon: Send/Arrow icon (16-20px)
- Size: 44px minimum height (WCAG compliant)
- Border radius: 8px (lg)
- Smooth transitions (200ms)

**Hover State:**
- Background: Blue-700 (dark) / Blue-600 (light)
- Scale: 1.02x
- Icon: Forward movement (2px)
- Shadow: Increased elevation

**Active State:**
- Scale: 0.98x
- Background: Slightly darker
- Immediate feedback (< 100ms)

**Disabled State:**
- Background: Gray-700 (dark) / Gray-200 (light)
- Text: Gray-500 (dark) / Gray-400 (light)
- Opacity: 60%
- Cursor: not-allowed
- Tooltip: "Type a message to send"

**Loading State:**
- Background: Maintains primary color
- Spinner: White, smooth rotation
- Text: "Sending..." with ellipsis
- Disabled interaction

**Error State:**
- Background: Red-600 (dark) / Red-500 (light)
- Icon: Retry icon
- Text: "Retry"
- Optional retry handler

## Usage

### Basic Usage

```tsx
import { SendButton } from '../components/ha-agent/SendButton';

<SendButton
  onClick={handleSend}
  disabled={!inputValue.trim()}
  isLoading={isLoading}
  darkMode={darkMode}
/>
```

### With Custom Labels

```tsx
<SendButton
  onClick={handleSend}
  disabled={!inputValue.trim()}
  isLoading={isLoading}
  darkMode={darkMode}
  label="Send Message"
  loadingText="Sending message..."
/>
```

### Icon Only Mode

```tsx
<SendButton
  onClick={handleSend}
  disabled={!inputValue.trim()}
  isLoading={isLoading}
  darkMode={darkMode}
  iconOnly={true}
/>
```

### With Error Handling

```tsx
<SendButton
  onClick={handleSend}
  disabled={!inputValue.trim()}
  isLoading={isLoading}
  hasError={sendError !== null}
  darkMode={darkMode}
  onRetry={handleRetry}
/>
```

### Size Variants

```tsx
// Small
<SendButton size="sm" {...props} />

// Medium (default)
<SendButton size="md" {...props} />

// Large
<SendButton size="lg" {...props} />
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isLoading` | `boolean` | `false` | Whether the button is in loading state |
| `disabled` | `boolean` | `false` | Whether the button is disabled |
| `hasError` | `boolean` | `false` | Whether there's an error state |
| `onClick` | `() => void` | **required** | Click handler |
| `darkMode` | `boolean` | `false` | Dark mode support |
| `label` | `string` | `'Send'` | Button label text |
| `loadingText` | `string` | `'Sending...'` | Loading state text |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Size variant |
| `iconOnly` | `boolean` | `false` | Show icon only (compact) |
| `onRetry` | `() => void` | `undefined` | Retry handler for error state |

## Accessibility

### ARIA Attributes

- `aria-label`: Descriptive label for screen readers
- `aria-busy`: Indicates loading state
- `aria-disabled`: Indicates disabled state
- `aria-live="polite"`: Announces state changes

### Keyboard Support

- **Enter**: Triggers button action
- **Space**: Triggers button action
- **Tab**: Focus navigation
- **Focus indicator**: 2px ring with high contrast

### Screen Reader Support

- Descriptive labels for all states
- Status announcements: "Sending message...", "Message sent"
- Contextual information: "Send button, disabled" when appropriate

### Reduced Motion

The component automatically respects `prefers-reduced-motion` media query:
- Disables scale animations
- Disables icon movement animations
- Maintains functionality without motion

## Animation Specifications

### Timing Functions
- Hover: `ease-out` 200ms
- Active: `ease-in` 100ms
- State transitions: `ease-in-out` 300ms

### Keyframes
- Icon animation: 0px → 2px translation on hover
- Loading spinner: Continuous 360° rotation (0.8s)
- Button scale: 1.0 → 1.02 (hover), 1.0 → 0.98 (active)

### Performance
- Uses CSS transforms (GPU-accelerated)
- Avoids layout-triggering properties
- Optimized for 60fps animations

## Design System Integration

The component follows the existing design system patterns:
- Uses Framer Motion (already in codebase)
- Consistent with DesignSystemButton patterns
- Matches color tokens and spacing
- Theme-aware (dark/light mode)

## Testing Checklist

### Visual Testing
- [x] Dark/light mode rendering
- [x] Different screen sizes (mobile, tablet, desktop)
- [x] High contrast mode
- [x] Reduced motion preferences

### Interaction Testing
- [x] Click/tap responsiveness
- [x] Keyboard navigation
- [x] Screen reader compatibility
- [x] Touch target accuracy (44x44px minimum)

### State Testing
- [x] Default state
- [x] Disabled state
- [x] Loading state
- [x] Error state
- [x] Hover state
- [x] Active state
- [x] Focus state

### Performance Testing
- [x] Animation frame rate (60fps)
- [x] Layout shift (CLS)
- [x] Time to interactive
- [x] Bundle size impact

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile browsers: ✅ Full support

## Future Enhancements (Phase 2+)

- [ ] Success state animation (checkmark)
- [ ] Progress indicator for long operations
- [ ] Mobile FAB (Floating Action Button) pattern
- [ ] Offline/network status indicator
- [ ] Rate limiting visual feedback
- [ ] Haptic feedback on supported devices

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design 3](https://m3.material.io/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Framer Motion Documentation](https://www.framer.com/motion/)

