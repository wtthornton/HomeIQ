# Step 4: Component Design - Debug Tab Integration

## UI/UX Design

### Tab Navigation Design
- **Location**: Below validation feedback panel, above content area
- **Style**: Horizontal tabs with border-bottom indicator
- **Active State**: Blue border and text (matches existing blue theme)
- **Inactive State**: Gray text with hover effect
- **Spacing**: Consistent padding (px-4 py-2)

### Tab Content Design
- **Preview Tab**: 
  - Existing YAML syntax highlighter
  - Maintains all existing functionality
- **Debug Tab**:
  - Full-height DebugTab component
  - Scrollable content area
  - Maintains DebugTab's internal navigation

## Component Specifications

### AutomationPreview Updates

**New State:**
```typescript
const [activeTab, setActiveTab] = useState<'preview' | 'debug'>('preview');
```

**New Import:**
```typescript
import { DebugTab } from './DebugTab';
```

**Tab Navigation JSX:**
```tsx
<div className={`border-b flex gap-1 px-6 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
  <button onClick={() => setActiveTab('preview')}>Preview</button>
  <button onClick={() => setActiveTab('debug')}>🐛 Debug</button>
</div>
```

**Conditional Content Rendering:**
```tsx
{activeTab === 'preview' ? (
  <YAMLContent />
) : (
  <DebugTab conversationId={conversationId || null} darkMode={darkMode} />
)}
```

## Color Palette

- **Active Tab**: 
  - Dark: `border-blue-500 text-blue-400`
  - Light: `border-blue-600 text-blue-600`
- **Inactive Tab**:
  - Dark: `text-gray-400 hover:text-gray-300`
  - Light: `text-gray-600 hover:text-gray-900`

## Accessibility

- **Keyboard Navigation**: Tab buttons are keyboard accessible
- **ARIA Labels**: Consider adding aria-label for tab buttons
- **Focus States**: Maintain visible focus indicators

## Responsive Design

- **Tab Overflow**: Tabs wrap if needed on small screens
- **Content Area**: Maintains existing overflow handling
- **Modal Size**: No changes to modal dimensions
