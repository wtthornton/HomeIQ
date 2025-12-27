# Dependency Graph Visualization - Knowledge Base

**Component:** Health Dashboard - Dependencies Tab  
**Technology:** React + SVG + TypeScript  
**Last Updated:** October 17, 2025

## Overview

The Health Dashboard includes an interactive dependency graph that provides real-time visualization of the Home Assistant Ingestor system architecture. The visualization uses animated SVG elements to show data flow between services with live metrics and interactive features.

## Architecture

### Component Structure

```
AnimatedDependencyGraph.tsx
├── ServiceNode[] - Node definitions with positioning
├── DataFlowPath[] - Connection definitions with animations
├── SVG Canvas - 1000x650px interactive diagram
├── Node Rendering - Clickable service nodes with status indicators
├── Flow Rendering - Animated data flow paths with particles
└── Interactive Features - Click highlighting, hover tooltips
```

### Layout Design

**Horizontal Multi-Layer Architecture:**

1. **External Sources Layer** (y=60)
   - External APIs, ESPN API, Home Assistant, OpenWeather
   - Spread horizontally across top

2. **Ingestion Layer** (y=180)
   - External Services, Sports Data, WebSocket Ingestion
   - Second row with proper spacing

3. **Processing Layer** (y=180)
   - Enrichment Pipeline, AI Automation
   - Center processing with clear separation

4. **AI Models Layer** (y=300-420)
   - OpenAI GPT-4o-mini, OpenVINO Models
   - Right side with vertical spacing

5. **Storage Layer** (y=380)
   - InfluxDB, SQLite
   - Bottom storage with horizontal spread

6. **API Gateway Layer** (y=480)
   - Data API, Admin API
   - Second from bottom

7. **UI Layer** (y=580)
   - Health Dashboard
   - Bottom center

## Key Features

### Interactive Elements

- **Clickable Nodes**: Click any service to highlight its dependencies
- **Hover Tooltips**: Detailed service information on hover
- **Status Indicators**: Real-time health status with color coding
- **Live Metrics**: Throughput and connection status display

### Visual Design

- **Animated Flows**: Moving particles along data flow paths
- **Color Coding**: Different colors for different flow types
- **Status Colors**: Green (running), Red (error), Yellow (degraded), Gray (unknown)
- **Glow Effects**: Visual emphasis for active flows and selected nodes

### Data Flow Types

- **Blue**: WebSocket/Query connections
- **Green**: Primary data paths
- **Orange**: Enhancement paths
- **Purple**: AI pattern analysis
- **Red**: OpenAI GPT-4o-mini connections
- **Cyan**: Weather inline enrichment
- **Gray**: External API connections

## Technical Implementation

### Node Positioning

```typescript
const nodes: ServiceNode[] = [
  // Layer 1: External Sources (Horizontal spread)
  { id: 'external-apis', position: { x: 80, y: 60 } },
  { id: 'espn-api', position: { x: 200, y: 60 } },
  { id: 'home-assistant', position: { x: 320, y: 60 } },
  { id: 'openweather', position: { x: 440, y: 60 } },
  
  // Layer 2: Ingestion (Second row)
  { id: 'external-services', position: { x: 80, y: 180 } },
  { id: 'sports-data', position: { x: 200, y: 180 } },
  { id: 'websocket-ingestion', position: { x: 320, y: 180 } },
  
  // Layer 3: Processing (Center)
  { id: 'enrichment-pipeline', position: { x: 500, y: 180 } },
  { id: 'ai-automation-service', position: { x: 650, y: 180 } },
  
  // Layer 4: AI Models (Right side, vertical)
  { id: 'openai-gpt4', position: { x: 650, y: 300 } },
  { id: 'openvino-models', position: { x: 650, y: 420 } },
  
  // Layer 5: Storage (Bottom, horizontal)
  { id: 'influxdb', position: { x: 200, y: 380 } },
  { id: 'sqlite', position: { x: 400, y: 380 } },
  
  // Layer 6: API Gateway (Second from bottom)
  { id: 'data-api', position: { x: 200, y: 480 } },
  { id: 'admin-api', position: { x: 400, y: 480 } },
  
  // Layer 7: UI (Bottom center)
  { id: 'health-dashboard', position: { x: 300, y: 580 } },
];
```

### Animation System

```typescript
// Animated flow paths with particles
<path
  d={path}
  fill="none"
  stroke={flow.color}
  strokeWidth="3"
  strokeLinecap="round"
  opacity="0.6"
  filter={`url(#glow-${flow.type})`}
>
  <animate
    attributeName="stroke-dasharray"
    values="10,5;20,15"
    dur="1s"
    repeatCount="indefinite"
  />
  <animate
    attributeName="stroke-dashoffset"
    from="0"
    to="30"
    dur="1.5s"
    repeatCount="indefinite"
  />
</path>

// Moving particles
<circle r="4" fill={flow.color} filter={`url(#glow-${flow.type})`}>
  <animateMotion
    dur={`${2 + Math.random() * 2}s`}
    repeatCount="indefinite"
    path={path}
  />
</circle>
```

## Layout Optimization History

### Problem Resolution

**Issue 1: Vertical Stacking**
- **Problem**: External services cramped in 2-column vertical grid
- **Solution**: Horizontal spread across top row
- **Result**: Clear visual flow from left to right

**Issue 2: Overlapping Nodes**
- **Problem**: WebSocket Ingestion and Enrichment Pipeline overlapping
- **Solution**: Increased horizontal spacing (x=320 to x=500)
- **Result**: Clear separation between ingestion and processing

**Issue 3: AI Models Stacking**
- **Problem**: AI automation nodes too close vertically
- **Solution**: Increased vertical spacing (y=280 to y=300, y=360 to y=420)
- **Result**: Clear vertical hierarchy for AI components

### Canvas Optimization

**Before**: 800px width with cramped layout
**After**: 1000px width with proper spacing
**Benefit**: Accommodates horizontal layout without crowding

## Usage Guidelines

### For Developers

1. **Adding New Services**: Update node array with proper positioning
2. **Modifying Flows**: Update dataFlows array with connection definitions
3. **Layout Changes**: Maintain horizontal spacing to prevent overlaps
4. **Animation Updates**: Modify SVG animation attributes for different effects

### For Users

1. **Navigation**: Click any service node to highlight its dependencies
2. **Information**: Hover over nodes for detailed service information
3. **Status Monitoring**: Green nodes indicate healthy services
4. **Flow Understanding**: Follow colored paths to understand data flow

## Performance Considerations

- **SVG Rendering**: Optimized for smooth animations
- **Memory Usage**: Efficient particle system with cleanup
- **Responsiveness**: Maintains 60fps animations
- **Scalability**: Canvas size scales with content

## Future Enhancements

1. **Responsive Design**: Mobile-friendly layout
2. **Zoom Controls**: Pan and zoom functionality
3. **Export Feature**: Save diagram as image
4. **Customization**: User-configurable layouts
5. **Real-time Updates**: Live node status updates

## Related Documentation

- [Health Dashboard Story 5.2](../stories/5.2.health-dashboard-interface.md)
- [Architecture Documentation](../architecture.md)
- [Implementation Summary](../../implementation/DEPENDENCY_GRAPH_LAYOUT_IMPROVEMENTS.md)

---

**Maintenance**: Update positioning when adding new services  
**Testing**: Verify no overlapping nodes after layout changes  
**Performance**: Monitor animation performance with large datasets

