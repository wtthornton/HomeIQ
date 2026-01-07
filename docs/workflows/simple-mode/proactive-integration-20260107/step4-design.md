# Step 4: Design Specifications - Proactive Agent Service UI Integration

## Design System Alignment

### Existing Patterns to Follow
- **Dark/Light Mode**: Use `darkMode` from `useAppStore()`
- **Card Components**: Follow `ConversationalSuggestionCard` patterns
- **Motion**: Use Framer Motion for animations
- **Toast Notifications**: Use `react-hot-toast`
- **Loading States**: Use `LoadingSpinner` component
- **API Client Pattern**: Follow `api.ts` structure

### Color Palette (Dark Mode Primary)
```css
/* Background colors */
--bg-primary: #0f172a;     /* slate-900 */
--bg-card: #1e293b;        /* slate-800 */
--bg-hover: #334155;       /* slate-700 */

/* Text colors */
--text-primary: #f8fafc;   /* slate-50 */
--text-secondary: #94a3b8; /* slate-400 */
--text-muted: #64748b;     /* slate-500 */

/* Accent colors by context type */
--weather: #38bdf8;        /* sky-400 */
--sports: #f97316;         /* orange-500 */
--energy: #22c55e;         /* green-500 */
--historical: #a855f7;     /* purple-500 */

/* Status colors */
--pending: #fbbf24;        /* amber-400 */
--sent: #3b82f6;           /* blue-500 */
--approved: #22c55e;       /* green-500 */
--rejected: #ef4444;       /* red-500 */
```

---

## TypeScript Types

### `src/types/proactive.ts`

```typescript
/**
 * Proactive Suggestion Types
 * For proactive-agent-service integration
 */

export type ProactiveContextType = 'weather' | 'sports' | 'energy' | 'historical';

export type ProactiveSuggestionStatus = 'pending' | 'sent' | 'approved' | 'rejected';

export interface ProactiveSuggestion {
  id: string;
  prompt: string;
  context_type: ProactiveContextType;
  status: ProactiveSuggestionStatus;
  quality_score: number;
  context_metadata: Record<string, any>;
  prompt_metadata: Record<string, any>;
  agent_response?: Record<string, any> | null;
  created_at: string;
  sent_at?: string | null;
  updated_at: string;
}

export interface ProactiveSuggestionStats {
  total: number;
  by_status: Record<ProactiveSuggestionStatus, number>;
  by_context_type: Record<ProactiveContextType, number>;
}

export interface ProactiveSuggestionFilters {
  status?: ProactiveSuggestionStatus | null;
  context_type?: ProactiveContextType | null;
  limit?: number;
  offset?: number;
}

export interface ProactiveSuggestionListResponse {
  suggestions: ProactiveSuggestion[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProactiveTriggerResponse {
  success: boolean;
  results: Record<string, any>;
}
```

---

## API Client Specification

### `src/services/proactiveApi.ts`

```typescript
/**
 * Proactive Agent Service API Client
 * 
 * Endpoints:
 * - GET  /api/proactive/suggestions          - List suggestions
 * - GET  /api/proactive/suggestions/{id}     - Get by ID
 * - PATCH /api/proactive/suggestions/{id}    - Update status
 * - DELETE /api/proactive/suggestions/{id}   - Delete
 * - GET  /api/proactive/suggestions/stats/summary - Stats
 * - POST /api/proactive/suggestions/trigger  - Manual trigger
 */

const PROACTIVE_API_BASE = '/api/proactive';

class ProactiveAPI {
  // List suggestions with filters
  async getSuggestions(filters?: ProactiveSuggestionFilters): Promise<ProactiveSuggestionListResponse>;
  
  // Get single suggestion
  async getSuggestion(id: string): Promise<ProactiveSuggestion>;
  
  // Update suggestion status
  async updateSuggestionStatus(id: string, status: ProactiveSuggestionStatus): Promise<ProactiveSuggestion>;
  
  // Delete suggestion
  async deleteSuggestion(id: string): Promise<{ success: boolean; message: string }>;
  
  // Get statistics
  async getStats(): Promise<ProactiveSuggestionStats>;
  
  // Trigger manual generation
  async triggerGeneration(): Promise<ProactiveTriggerResponse>;
  
  // Health check
  async healthCheck(): Promise<{ status: string }>;
}

export const proactiveApi = new ProactiveAPI();
```

---

## Component Specifications

### 1. ProactiveSuggestions Page

**File**: `src/pages/ProactiveSuggestions.tsx`

```typescript
interface ProactiveSuggestionsState {
  suggestions: ProactiveSuggestion[];
  loading: boolean;
  error: string | null;
  filters: ProactiveSuggestionFilters;
  stats: ProactiveSuggestionStats | null;
  triggerLoading: boolean;
}
```

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  💡 Proactive Suggestions                    [Generate] [Refresh]│
│  Context-aware automation ideas from weather, sports & energy   │
├─────────────────────────────────────────────────────────────────┤
│  Stats: ○ Total: 24  ○ Weather: 8  ○ Energy: 10  ○ Sports: 6   │
├─────────────────────────────────────────────────────────────────┤
│  Filters: [All Types ▼] [All Status ▼]         [Clear Filters] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ☁️ WEATHER                          Quality: ████░ 85%      ││
│  │ "It's going to be 95°F today. Should I pre-cool your       ││
│  │  home before you arrive?"                                   ││
│  │                                                              ││
│  │ ○ Pending  · Created: 2 hours ago                          ││
│  │                               [Approve ✓] [Reject ✗]       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ⚡ ENERGY                           Quality: ████░ 78%      ││
│  │ "Electricity prices drop to $0.08/kWh at 2 AM. Should I   ││
│  │  schedule the dishwasher to run overnight?"                 ││
│  │                                                              ││
│  │ ○ Pending  · Created: 5 hours ago                          ││
│  │                               [Approve ✓] [Reject ✗]       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. ProactiveSuggestionCard Component

**File**: `src/components/proactive/ProactiveSuggestionCard.tsx`

**Props**:
```typescript
interface ProactiveSuggestionCardProps {
  suggestion: ProactiveSuggestion;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onViewDetails?: (id: string) => void;
  darkMode: boolean;
}
```

**Visual Design**:
- Card with rounded corners, subtle shadow
- Context type icon and label in top-left
- Quality score bar in top-right
- Prompt text as main content
- Status badge with timestamp
- Action buttons at bottom

**Context Type Icons**:
```typescript
const CONTEXT_ICONS: Record<ProactiveContextType, { icon: string; color: string }> = {
  weather: { icon: '☁️', color: 'text-sky-400' },
  sports: { icon: '🏈', color: 'text-orange-500' },
  energy: { icon: '⚡', color: 'text-green-500' },
  historical: { icon: '📊', color: 'text-purple-500' },
};
```

### 3. ProactiveFilters Component

**File**: `src/components/proactive/ProactiveFilters.tsx`

**Props**:
```typescript
interface ProactiveFiltersProps {
  filters: ProactiveSuggestionFilters;
  onFilterChange: (filters: ProactiveSuggestionFilters) => void;
  darkMode: boolean;
}
```

**Elements**:
- Context type dropdown (All / Weather / Sports / Energy / Historical)
- Status dropdown (All / Pending / Sent / Approved / Rejected)
- Clear filters button

### 4. ProactiveStats Component

**File**: `src/components/proactive/ProactiveStats.tsx`

**Props**:
```typescript
interface ProactiveStatsProps {
  stats: ProactiveSuggestionStats | null;
  loading: boolean;
  darkMode: boolean;
}
```

**Display**:
```
○ Total: 24  ○ Weather: 8  ○ Energy: 10  ○ Sports: 4  ○ Historical: 2
```

---

## Navigation Integration

### `src/components/Navigation.tsx` Changes

Add new navigation item:
```typescript
{
  name: 'Proactive',
  path: '/proactive',
  icon: LightBulbIcon, // or BrainIcon
  tooltip: 'Context-aware suggestions from weather, sports & energy'
}
```

Position: After "Suggestions", before "Patterns"

---

## Empty State Design

When no suggestions exist:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│                          🤖                                      │
│                                                                  │
│               No Proactive Suggestions Yet                       │
│                                                                  │
│    The AI analyzes weather, sports, and energy data at 3 AM     │
│    daily to suggest context-aware automations.                  │
│                                                                  │
│              [Generate Sample Suggestion]                        │
│                                                                  │
│    💡 How it works: The AI looks at tomorrow's weather,         │
│       upcoming sports games, and energy prices to suggest       │
│       automations that save energy or enhance comfort.          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Loading State Design

Use skeleton cards matching the card layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  ████████                                    ████████████       │
│  ████████████████████████████████████████████████████████       │
│  ████████████████████████████████████████████                   │
│                                                                  │
│  ████████  · ████████████████                                   │
│                               [████████] [████████]             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error State Design

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│                          ⚠️                                      │
│                                                                  │
│            Unable to Load Proactive Suggestions                  │
│                                                                  │
│    {error.message}                                              │
│                                                                  │
│                        [Try Again]                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Animation Specifications

### Card Entry Animation
```typescript
const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.3 }
  },
  exit: { opacity: 0, x: -20 }
};
```

### Status Change Animation
- Flash green on approve
- Flash red on reject
- Fade out after 500ms

### Staggered List Animation
```typescript
const listVariants = {
  visible: {
    transition: {
      staggerChildren: 0.1
    }
  }
};
```

---

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| < 640px (sm) | Single column, stacked filters |
| 640-1024px (md) | Single column, inline filters |
| > 1024px (lg) | Single column, full stats row |

---
*Generated by Simple Mode Build Workflow*
*Timestamp: 2026-01-07*
