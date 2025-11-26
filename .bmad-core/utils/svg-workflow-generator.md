# SVG Workflow Diagram Generator Guide

This guide explains how to create SVG workflow diagrams for BMAD workflows.

## Overview

SVG workflow diagrams provide beautiful visual representations of workflows, showing:
- Complete methodology flow
- Agent handoffs
- Decision points
- Phase transitions
- Optional steps

## Workflow Structure

Each workflow YAML file can include an `svg_diagram` field:

```yaml
workflow:
  id: workflow-id
  name: Workflow Name
  # ... other fields ...
  
  svg_diagram: |
    <!-- SVG content here -->
    <svg>...</svg>
  
  # Or reference external file
  svg_diagram_file: "workflows/diagrams/workflow-id.svg"
```

## SVG Diagram Elements

### Basic Structure

```svg
<svg width="1200" height="800" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="800" fill="#f5f5f5"/>
  
  <!-- Workflow elements -->
  <!-- ... -->
</svg>
```

### Node Types

1. **Start/End Nodes** (rounded rectangles)
2. **Process Nodes** (rectangles)
3. **Decision Nodes** (diamonds)
4. **Agent Nodes** (special styling)
5. **Optional Steps** (dashed borders)

### Color Scheme

```css
/* Phase colors */
Planning: #FFE4B5 (light orange)
Development: #ADD8E6 (light blue)
Review: #F0E68C (light yellow)
Complete: #90EE90 (light green)

/* Agent colors */
Analyst: #FFE4B5
PM: #FFE4B5
UX: #E1F5FE
Architect: #F3E5F5
Dev: #E3F2FD
QA: #FFD54F
PO: #F9AB00
SM: #E8F5E9

/* Status colors */
Optional: #E6E6FA (dashed)
Required: solid colors
```

## Generation Methods

### Method 1: Convert from Mermaid

Existing workflows have Mermaid diagrams. Convert to SVG:

1. **Use Mermaid CLI:**
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   mmdc -i workflow.mmd -o workflow.svg
   ```

2. **Use online converter:**
   - https://mermaid.live/
   - Export as SVG

3. **Use Mermaid library:**
   ```javascript
   import mermaid from 'mermaid';
   mermaid.initialize({ startOnLoad: true });
   // Render to SVG
   ```

### Method 2: Create Custom SVG

For more control, create custom SVG:

```svg
<svg width="1200" height="800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Gradients, patterns, etc. -->
  </defs>
  
  <!-- Title -->
  <text x="600" y="30" text-anchor="middle" font-size="24" font-weight="bold">
    Workflow Name
  </text>
  
  <!-- Nodes -->
  <rect x="100" y="100" width="150" height="60" rx="5" fill="#ADD8E6" stroke="#000"/>
  <text x="175" y="135" text-anchor="middle">Start</text>
  
  <!-- Arrows -->
  <path d="M 250 130 L 300 130" stroke="#000" stroke-width="2" marker-end="url(#arrowhead)"/>
  
  <!-- Decision diamond -->
  <polygon points="400,100 450,130 400,160 350,130" fill="#E3F2FD" stroke="#000"/>
  
  <!-- More elements... -->
</svg>
```

### Method 3: Use Diagram Tools

Tools that export SVG:
- **Draw.io / diagrams.net**: Export as SVG
- **Lucidchart**: Export as SVG
- **Figma**: Export as SVG
- **Inkscape**: Native SVG editor

## Workflow Diagram Template

```svg
<svg width="1200" height="800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#000"/>
    </marker>
  </defs>
  
  <!-- Title -->
  <text x="600" y="30" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">
    Workflow Name
  </text>
  
  <!-- Phase 1: Planning -->
  <rect x="50" y="80" width="1100" height="200" fill="#FFF" stroke="#CCC" stroke-dasharray="5,5" opacity="0.3"/>
  <text x="60" y="100" font-size="16" font-weight="bold" fill="#666">Planning Phase</text>
  
  <!-- Planning nodes -->
  <!-- ... -->
  
  <!-- Phase 2: Development -->
  <rect x="50" y="300" width="1100" height="300" fill="#FFF" stroke="#CCC" stroke-dasharray="5,5" opacity="0.3"/>
  <text x="60" y="320" font-size="16" font-weight="bold" fill="#666">Development Phase</text>
  
  <!-- Development nodes -->
  <!-- ... -->
  
  <!-- Phase 3: Review -->
  <rect x="50" y="620" width="1100" height="150" fill="#FFF" stroke="#CCC" stroke-dasharray="5,5" opacity="0.3"/>
  <text x="60" y="640" font-size="16" font-weight="bold" fill="#666">Review Phase</text>
  
  <!-- Review nodes -->
  <!-- ... -->
</svg>
```

## Integration with Workflows

### Option 1: Inline SVG

```yaml
workflow:
  id: quick-fix
  svg_diagram: |
    <svg>...</svg>
```

### Option 2: External File Reference

```yaml
workflow:
  id: quick-fix
  svg_diagram_file: "workflows/diagrams/quick-fix.svg"
```

### Option 3: Generated on Demand

```yaml
workflow:
  id: quick-fix
  svg_diagram_source: "mermaid"  # or "custom"
  mermaid_diagram: |
    graph TD
      A[Start] --> B[Process]
```

## Best Practices

1. **Consistent Styling**: Use same colors/symbols across workflows
2. **Clear Labels**: Use descriptive text in nodes
3. **Proper Spacing**: Allow room for readability
4. **Responsive**: Consider different screen sizes
5. **Accessible**: Include alt text and proper contrast

## Tools and Resources

- **Mermaid**: https://mermaid.js.org/
- **Draw.io**: https://app.diagrams.net/
- **SVG Optimizer**: https://jakearchibald.github.io/svgomg/
- **SVG Validator**: https://validator.w3.org/

## Example: Quick Fix Workflow SVG

See `.bmad-core/workflows/quick-fix.yaml` for Mermaid diagram that can be converted to SVG.

## Notes

- SVG diagrams are optional but recommended
- Mermaid diagrams can coexist (for text-based viewing)
- SVG provides better visual presentation
- Consider generating SVGs from Mermaid automatically

