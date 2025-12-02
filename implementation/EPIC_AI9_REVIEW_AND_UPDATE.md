# Epic AI-9: Dashboard HA 2025 Enhancements - Review and Update

**Date:** December 2, 2025  
**Status:** ✅ **REVIEWED AND UPDATED**  
**Action:** Updated epic to reflect current 2025 UI architecture

---

## Review Summary

Reviewed Epic AI-9 against the current 2025 UI architecture and updated all stories to align with:
- Current component structure
- Design system patterns
- Technology stack (React 18, Vite, Framer Motion, Zustand)
- Existing UI patterns (badges, cards, filters)

---

## Current UI Architecture (2025)

### Technology Stack
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Routing:** React Router v6 (BrowserRouter)
- **Animation:** Framer Motion
- **State Management:** Zustand (`src/store.ts`)
- **Styling:** Tailwind CSS + Custom Design System
- **Icons:** Home Assistant MDI icons + Emoji fallbacks

### Page Structure
```
/ (root)                    → ConversationalDashboard.tsx (Main)
/ask-ai                     → AskAI.tsx (Natural language queries)
/patterns                   → Patterns.tsx
/synergies                  → Synergies.tsx
/deployed                   → Deployed.tsx
/discovery                  → Discovery.tsx
/name-enhancement           → NameEnhancementDashboard.tsx
/settings                   → Settings.tsx
/admin                      → Admin.tsx
```

### Key Components

**Suggestion Display:**
- `ConversationalSuggestionCard.tsx` - Main card (description-first UI)
- `SuggestionCard.tsx` - Legacy card (still used)
- `DeployedBadge.tsx` - Deployment status badge

**Filtering:**
- `FilterPills.tsx` - Pill-based filter UI
- Supports: category, confidence, status
- Multi-select with visual feedback

**Device Display:**
- `discovery/DeviceExplorer.tsx` - Device discovery
- `DeviceMappingModal.tsx` - Device selection

**Shared Components:**
- `shared/DesignSystemButton.tsx` - Reusable button
- `shared/DesignSystemCard.tsx` - Reusable card

### Design System

**Location:** `src/utils/designSystem.ts`, `src/styles/design-system.css`

**Key Patterns:**
- Glass morphism (backdrop-filter: blur(12px))
- Rounded-xl borders (1rem border radius)
- Gradient backgrounds
- Corner accents on cards
- Smooth animations with Framer Motion
- Respect prefers-reduced-motion

**Color Palette:**
- Background: #0a0e27, #1a1f3a, #0f1419
- Accent: #3b82f6 (blue), #06b6d4 (cyan)
- Status: #10b981 (success), #f59e0b (warning), #ef4444 (error)
- Text: #ffffff (primary), #cbd5e1 (secondary), #94a3b8 (tertiary)

---

## Updates Made to Epic AI-9

### 1. Updated Technology Stack Section
**Before:** Basic component list  
**After:** Complete tech stack with:
- React 18, TypeScript, Vite
- Routing (React Router v6)
- Animation (Framer Motion)
- State management (Zustand)
- All pages and key components
- API clients (v1 and v2)
- Hooks (useConversationV2, useOptimisticUpdates)

### 2. Updated Integration Points
**Before:** Simple component list  
**After:** Detailed integration points:
- Suggestion display components
- Filtering system details
- Device display components
- Type definitions
- API integration

### 3. Enhanced Story AI9.1: Automation Tags Display
**Added:**
- Implementation details (follow DeployedBadge.tsx pattern)
- Design system color coding
- Animation approach (Framer Motion with AnimatePresence)
- Responsive design requirements
- New component: `TagBadge.tsx`

**Updated Files:**
- Added `TagBadge.tsx` (NEW component)
- Clarified FilterPills.tsx extension

### 4. Enhanced Story AI9.2: Entity Labels and Options
**Added:**
- Implementation details (DeviceInfo interface updates)
- Badge pattern for labels
- Preferences section for options
- Format examples ("Brightness: 128/255 (50%)")
- Filter integration approach

**Updated Files:**
- Added `DeviceMappingModal.tsx` to file list
- Clarified device info display locations

### 5. Enhanced Story AI9.3: Automation Metadata
**Added:**
- Icons for each mode type:
  - ⚡ single (one-time)
  - 🔄 restart (cancels previous)
  - 📋 queued (sequential)
  - ⚡⚡ parallel (simultaneous)
- Max exceeded display (🔇 silent, ⚠️ warning)
- Initial state indicator ("Auto-enabled" badge)
- Tooltip implementation details
- New component: `AutomationMetadataBadge.tsx`

**Updated Files:**
- Added `AutomationMetadataBadge.tsx` (NEW component)
- Added `max_exceeded` to type definitions

### 6. Enhanced Story AI9.4: Entity Icon Enhancement
**Added:**
- Icon fallback priority: icon → original_icon → domain default
- User-customized indicator (✨ sparkle)
- Tooltip showing icon source
- Home Assistant icon format (mdi:icon-name)
- New utility: `iconHelpers.ts`

**Updated Files:**
- Added `iconHelpers.ts` (NEW utility)
- Added `DeviceMappingModal.tsx` to file list
- Clarified icon resolution logic

### 7. Added Design System Guidelines Section
**New Section:** Complete design system guidelines including:
- Component patterns (badges, cards, animations)
- Color coding standards
- Typography guidelines
- Spacing standards
- Accessibility requirements
- Links to design system files

---

## Story Updates Summary

### Story AI9.1: Automation Tags Display and Filtering
**Status:** Ready to implement  
**Changes:**
- ✅ Aligned with current badge pattern (DeployedBadge.tsx)
- ✅ Added design system color coding
- ✅ Specified animation approach (Framer Motion)
- ✅ Added new component: TagBadge.tsx
- ✅ Clarified FilterPills.tsx extension

### Story AI9.2: Entity Labels and Options Display
**Status:** Ready to implement  
**Changes:**
- ✅ Added DeviceMappingModal.tsx integration
- ✅ Specified badge pattern for labels
- ✅ Added preferences section for options
- ✅ Clarified display locations

### Story AI9.3: Automation Metadata Display
**Status:** Ready to implement  
**Changes:**
- ✅ Added icons for all mode types
- ✅ Added max_exceeded display
- ✅ Added initial_state indicator
- ✅ Added new component: AutomationMetadataBadge.tsx
- ✅ Specified tooltip implementation

### Story AI9.4: Entity Icon Enhancement
**Status:** Ready to implement  
**Changes:**
- ✅ Added icon fallback priority
- ✅ Added user-customized indicator
- ✅ Added new utility: iconHelpers.ts
- ✅ Specified icon resolution logic

---

## Architecture Alignment

### ✅ Component Patterns
- All stories follow existing badge/card patterns
- Consistent with DeployedBadge.tsx, FilterPills.tsx
- Use shared design system utilities

### ✅ Animation Approach
- Framer Motion for all animations
- AnimatePresence for enter/exit
- Respect prefers-reduced-motion
- Consistent with existing components

### ✅ Type Definitions
- All new fields added to existing interfaces
- Backward compatible (optional fields)
- Follows existing type patterns

### ✅ API Integration
- Uses existing API clients (api.ts, api-v2.ts)
- No new API endpoints needed
- Data already available from Epic AI-7 and AI-8

### ✅ Responsive Design
- Mobile-first approach
- Consistent with existing responsive patterns
- Uses Tailwind responsive utilities

---

## New Components to Create

### 1. TagBadge.tsx
**Purpose:** Reusable tag badge component  
**Pattern:** Follow DeployedBadge.tsx  
**Features:**
- Color-coded by tag type
- Hover tooltip
- Smooth animations
- Responsive sizing

### 2. AutomationMetadataBadge.tsx
**Purpose:** Display mode, initial_state, max_exceeded  
**Pattern:** Follow DeployedBadge.tsx  
**Features:**
- Icon for each mode type
- Tooltip explaining behavior
- Compact display
- Expandable details

### 3. iconHelpers.ts (Utility)
**Purpose:** Icon resolution and fallback logic  
**Functions:**
- `resolveEntityIcon(icon, original_icon, domain)` - Get best icon
- `isUserCustomized(icon, original_icon)` - Check if customized
- `getIconTooltip(icon, original_icon)` - Generate tooltip text
- `getDomainDefaultIcon(domain)` - Get domain fallback icon

---

## Files to Modify

### Type Definitions (src/types/index.ts)
**Add to `Suggestion` interface:**
```typescript
tags?: string[];  // Automation tags (ai-generated, energy, security, etc.)
mode?: string;  // Automation mode (single, restart, queued, parallel)
initial_state?: boolean;  // Initial state (enabled by default)
max_exceeded?: string;  // Max exceeded behavior (silent, warning)
```

**Add to `SuggestionDeviceInfo` interface:**
```typescript
labels?: string[];  // Entity labels (outdoor, security, etc.)
options?: Record<string, any>;  // Entity options (default brightness, etc.)
icon?: string;  // Current icon (user-customized)
original_icon?: string;  // Original icon from integration
aliases?: string[];  // Entity aliases
```

### Component Updates

**ConversationalSuggestionCard.tsx:**
- Add tags display section (below description)
- Add metadata display section (mode, initial_state, max_exceeded)
- Update device_info display (show labels, options, icon)
- Use new TagBadge and AutomationMetadataBadge components

**FilterPills.tsx:**
- Add 'tags' type support (similar to 'category')
- Color-code tag pills
- Multi-select functionality

**DeviceMappingModal.tsx:**
- Display entity labels
- Display entity options as preferences
- Show icon with customization indicator

**DeviceExplorer.tsx:**
- Add label filtering
- Display labels on device cards
- Show options in device details

---

## Implementation Order

### Phase 1: Tags and Badges (Week 1)
1. Create `TagBadge.tsx` component
2. Update `Suggestion` interface with tags
3. Display tags in `ConversationalSuggestionCard.tsx`
4. Extend `FilterPills.tsx` for tag filtering

### Phase 2: Metadata and Icons (Week 2)
5. Create `AutomationMetadataBadge.tsx` component
6. Update `Suggestion` interface with mode, initial_state, max_exceeded
7. Display metadata in `ConversationalSuggestionCard.tsx`
8. Create `iconHelpers.ts` utility
9. Update icon display in all components

### Phase 3: Entity Attributes (Week 2-3)
10. Update `SuggestionDeviceInfo` interface
11. Display labels/options in `DeviceMappingModal.tsx`
12. Add label filtering to `DeviceExplorer.tsx`
13. Show preferences in device info sections

---

## Testing Strategy

### Component Tests
- Unit tests for new components (TagBadge, AutomationMetadataBadge)
- Unit tests for iconHelpers utility
- Snapshot tests for UI components

### Integration Tests
- Test tag filtering end-to-end
- Test label filtering in device explorer
- Test metadata display with various modes
- Test icon fallback logic

### Visual Tests
- Screenshot tests for new badges
- Responsive design tests (mobile, tablet, desktop)
- Dark mode tests
- Animation tests (with/without reduced motion)

---

## Related Documentation

- [HA Best Practices & API 2025 Update Plan](../../implementation/HA_BEST_PRACTICES_AND_API_2025_UPDATE_PLAN.md)
- [Epic AI-7: Home Assistant Best Practices Implementation](./epic-ai7-home-assistant-best-practices-implementation.md)
- [Epic AI-8: Home Assistant 2025 API Integration](./epic-ai8-home-assistant-2025-api-integration.md)
- [Design System](../../services/ai-automation-ui/src/utils/designSystem.ts)
- [Design System CSS](../../services/ai-automation-ui/src/styles/design-system.css)

---

**Epic AI-9 Review Complete** ✅  
**All stories updated to reflect 2025 UI architecture**  
**Ready for implementation**

