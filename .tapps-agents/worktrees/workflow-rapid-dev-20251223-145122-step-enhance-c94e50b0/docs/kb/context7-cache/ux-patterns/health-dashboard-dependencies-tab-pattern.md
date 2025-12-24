# Health Dashboard Dependencies Tab - UX/UI Pattern

**Source:** http://localhost:3000/ - Dependencies Tab  
**Component:** `ServiceDependencyGraph.tsx`  
**Created:** 2025-10-12  
**Status:** ✅ Preferred Pattern for System Visualization

## Overview

The Dependencies Tab provides an **interactive, visual representation of service dependencies and data flow** in the HA Ingestor system. This pattern has been identified as a preferred UX/UI approach for future system visualization features.

## Key Design Patterns

### 1. **Interactive Dependency Graph**
- **Visual layered architecture** (top-to-bottom data flow)
- **Click-to-highlight dependencies** - interactive exploration
- **Hover tooltips** with contextual information
- **Selection persistence** - selected node stays highlighted until cleared

### 2. **Visual Status Indicators**
Color-coded service health states:
- 🟢 **Green** - Service running/healthy
- 🟡 **Yellow** - Service degraded
- 🔴 **Red** - Service error/down
- ⚫ **Gray** - Unknown/not reporting

### 3. **Layered Architecture Visualization**
```
Layer 1: Data Source (Home Assistant)
    ↓
Layer 2: Ingestion (WebSocket Ingestion)
    ↓
Layer 3: External Services (6 services in grid)
    ↓
Layer 4: Processing (Enrichment Pipeline)
    ↓
Layer 5: Storage & Services (4 services)
```

### 4. **Icon-Based Service Representation**
Each service has a distinctive emoji icon for quick visual recognition:
- 🏠 Home Assistant
- 📡 WebSocket Ingestion
- ☁️ Weather API
- 🌱 Carbon Intensity
- ⚡ Electricity Pricing
- 💨 Air Quality
- 📅 Calendar
- 📈 Smart Meter
- 🔄 Enrichment Pipeline
- 🗄️ InfluxDB
- 💾 Data Retention
- 🔌 Admin API
- 📊 Health Dashboard

### 5. **Interaction Patterns**

#### Click Interaction
- **Click service node** → Highlights node + all dependencies
- **Ring effect** (4px blue ring) on selected node
- **Scale transform** (scale-110) on selected node
- **Opacity adjustment** on connections (100% for related, 10% for unrelated)
- **Info panel** appears below with "Clear Selection" button

#### Hover Interaction
- **Scale effect** (scale-105) on hover
- **Tooltip appears** with service description
- **Smooth transitions** (transition-all)

### 6. **Legend & Documentation**
- **Status legend** at top with color-coded examples
- **Descriptive header** with usage instructions
- **Selected service info** panel with contextual help

### 7. **Dark Mode Support**
Full dark mode implementation:
- Background: `bg-gray-800` (dark) / `bg-white` (light)
- Text: `text-white` (dark) / `text-gray-900` (light)
- Borders: `border-gray-600` (dark) / `border-gray-300` (light)
- Status colors adapt to theme

### 8. **Responsive Layout**
- **Grid layout** for service groups (2 columns for external services)
- **Flexbox** for main layout structure
- **Overflow handling** (`overflow-x-auto`) for horizontal scrolling
- **Min-width** container to prevent crushing

### 9. **Animation & Transitions**
- **Smooth scale transforms** on hover/select
- **Opacity transitions** for connections
- **Transition-all** duration ~200ms
- **Ring animation** on selection

## Technical Implementation

### Technology Stack
- **React 18.2** with TypeScript
- **Tailwind CSS 3.4** for styling
- **No external graph library** - custom CSS/React implementation
- **Chart.js 4.5** for other dashboard visualizations

### Component Structure
```typescript
interface ServiceNode {
  id: string;
  name: string;
  icon: string;
  type: 'ui' | 'core' | 'external' | 'storage';
  layer: number;
  position: number;
}

interface ServiceDependency {
  from: string;
  to: string;
  type: 'data_flow' | 'api_call' | 'storage';
  description: string;
}
```

### State Management
```typescript
const [selectedNode, setSelectedNode] = useState<string | null>(null);
const [hoveredNode, setHoveredNode] = useState<string | null>(null);
```

### Key Functions
- `getServiceStatus(nodeId)` - Maps nodes to service health data
- `getStatusColor(nodeId)` - Returns Tailwind classes for status
- `isNodeHighlighted(nodeId)` - Determines if node in dependency path
- `getConnectionOpacity(from, to)` - Adjusts connection visibility
- `handleNodeClick(nodeId)` - Toggle selection state

## Why This Pattern Works

### ✅ **Strengths**

1. **Intuitive Understanding** - Visual representation matches mental model
2. **Progressive Disclosure** - Information revealed on interaction
3. **Clear Status Communication** - Color coding + icons work together
4. **Exploratory Interface** - Users can investigate relationships
5. **Performance** - Pure CSS/React, no heavy graph libraries
6. **Accessibility** - Click and keyboard navigable
7. **Beautiful** - Modern, clean, professional appearance
8. **Responsive** - Works on different screen sizes
9. **Stateful** - Selection persists, allowing detailed inspection
10. **Self-Documenting** - Legend and tooltips provide context

### 🎯 **Use Cases for This Pattern**

Apply this pattern when building:
- **Service topology visualizations**
- **Data flow diagrams**
- **System architecture views**
- **Microservice dependency graphs**
- **Pipeline visualizations**
- **Infrastructure maps**
- **Integration status boards**

## Reusable Pattern Components

### 1. Node Card Pattern
```typescript
<div
  onClick={handleClick}
  onMouseEnter={handleHover}
  onMouseLeave={handleLeave}
  className={`
    relative px-6 py-4 rounded-lg border-2 
    cursor-pointer transition-all
    ${statusColor}
    ${isHighlighted ? 'ring-4 ring-blue-500 scale-110' : 'hover:scale-105'}
  `}
>
  <div className="flex flex-col items-center">
    <div className="text-3xl mb-2">{icon}</div>
    <div className="text-sm font-medium text-center">
      {name}
    </div>
  </div>
  {showTooltip && <Tooltip>{description}</Tooltip>}
</div>
```

### 2. Connection Indicator Pattern
```typescript
<div className={`text-4xl ${connectionOpacity}`}>
  {direction === 'down' ? '↓' : '→'}
</div>
```

### 3. Status Color Mapping Pattern
```typescript
const statusColors = {
  running: darkMode 
    ? 'bg-green-900 border-green-700' 
    : 'bg-green-100 border-green-500',
  error: darkMode 
    ? 'bg-red-900 border-red-700' 
    : 'bg-red-100 border-red-500',
  degraded: darkMode 
    ? 'bg-yellow-900 border-yellow-700' 
    : 'bg-yellow-100 border-yellow-500',
  unknown: darkMode 
    ? 'bg-gray-700 border-gray-600' 
    : 'bg-gray-100 border-gray-300'
};
```

### 4. Selection Info Panel Pattern
```typescript
{selectedNode && (
  <div className="mt-8 p-4 rounded-lg bg-gray-50 dark:bg-gray-700">
    <div className="flex items-center justify-between">
      <div>
        <h4 className="font-semibold mb-1">
          Selected: {nodeName}
        </h4>
        <p className="text-sm text-gray-600">
          Dependencies highlighted in blue
        </p>
      </div>
      <button onClick={clearSelection}>
        Clear Selection
      </button>
    </div>
  </div>
)}
```

## Design Principles

1. **Visual Hierarchy** - Most important info (health status) is most prominent
2. **Progressive Enhancement** - Works without interaction, better with it
3. **Feedback Loop** - Every interaction provides visual feedback
4. **Consistency** - Same patterns throughout (colors, spacing, transitions)
5. **Clarity** - No ambiguity in what each element represents
6. **Performance** - Lightweight, no unnecessary re-renders
7. **Accessibility** - Keyboard nav, ARIA labels, high contrast

## Performance Considerations

- **No heavy graph libraries** (D3, Vis.js, etc.) - pure React/CSS
- **Memoized status lookups** to avoid recalculation
- **CSS transitions** instead of JavaScript animations
- **Minimal re-renders** with proper state management
- **Lazy evaluation** of highlighted nodes

## Future Enhancements

Consider adding:
- [ ] **Zoom/Pan** for large graphs
- [ ] **Filtering** by service type or status
- [ ] **Export** as PNG/SVG
- [ ] **Animation** of data flow
- [ ] **Historical view** (service status over time)
- [ ] **Search/Find** specific services
- [ ] **Metrics overlay** (throughput, latency)
- [ ] **Auto-layout** for dynamic service additions

## Related Patterns

- **Tab Navigation Pattern** - From same dashboard
- **Status Card Pattern** - Used in Overview tab
- **Dark Mode Pattern** - Consistent across dashboard
- **Tooltip Pattern** - Reusable across components

## References

- Component: `services/health-dashboard/src/components/ServiceDependencyGraph.tsx`
- Parent: `services/health-dashboard/src/components/Dashboard.tsx`
- Types: `services/health-dashboard/src/types/index.ts`
- Styles: Tailwind CSS 3.4 utility classes

---

**Pattern Status:** ✅ Production-tested, User-approved  
**Complexity:** Medium  
**Reusability:** High  
**Maintenance:** Low  
**Last Updated:** 2025-10-12

