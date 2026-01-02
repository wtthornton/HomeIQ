# Step 3: Architecture Design - Debug Tab Integration

## Component Architecture

```
AutomationPreview
├── State Management
│   ├── activeTab: 'preview' | 'debug'
│   ├── Existing state (isCreating, validationResult, etc.)
│   └── Tab switching logic
├── Tab Navigation
│   ├── Preview Tab Button
│   └── Debug Tab Button
└── Tab Content
    ├── Preview Tab Content
    │   └── YAML SyntaxHighlighter (existing)
    └── Debug Tab Content
        └── DebugTab Component (reused)
```

## Data Flow

1. **Tab Selection**: User clicks tab → `setActiveTab()` updates state
2. **Content Rendering**: Conditional rendering based on `activeTab` state
3. **DebugTab Integration**: 
   - Receives `conversationId` prop
   - Receives `darkMode` prop
   - Manages its own internal state (breakdown, loading, activeSection)

## Component Integration

### Props Flow
```
AutomationPreview Props
├── conversationId (now used, was previously unused)
├── darkMode
└── ... other props

DebugTab Props
├── conversationId: string | null
└── darkMode: boolean
```

### State Management
- **Local State**: `activeTab` managed in AutomationPreview
- **No Global State**: Tab state is local to component instance
- **State Persistence**: Tab state persists while modal is open, resets on close

## Styling Architecture

- **Tab Navigation**: Border-bottom indicator for active tab
- **Tab Content**: Flex layout with overflow handling
- **Dark Mode**: Consistent with existing dark mode patterns
- **Responsive**: Maintains existing responsive behavior

## Performance Considerations

- **Lazy Loading**: DebugTab only loads when Debug tab is selected
- **Memoization**: Existing useMemo hooks preserved
- **Re-renders**: Tab switching triggers minimal re-renders
