# Ask AI Debug Panel Enhancement - Design Options

## Overview
Enhance the Debug Panel to show a complete sequence/flow from the initial user prompt all the way through to the Home Assistant API call and response, making it very user-friendly.

## Current State
The Debug Panel currently shows:
- Device Selection (reasoning)
- OpenAI Prompts (system, user, filtered)
- Technical Prompt (JSON)
- YAML Response

## Proposed Flow Sequence

1. **User Prompt** - Initial natural language query
2. **Entity Extraction** - Home Assistant Conversation API call
3. **Device Selection** - AI reasoning for device selection
4. **OpenAI Prompt Generation** - System + user prompts created
5. **OpenAI API Call** - Suggestion generation request
6. **OpenAI Response** - Generated suggestion with confidence
7. **Technical Prompt Creation** - Structured automation format
8. **YAML Generation** (on approve) - Automation YAML created
9. **HA API Call** (on approve) - POST to create automation
10. **HA Response** (on approve) - Automation ID, status, warnings

---

## Option 1: Timeline/Sequence View

### Design Concept
A vertical timeline showing each step in sequence with:
- Step number and name
- Status indicator (pending, in-progress, completed, error)
- Expandable sections for details
- Visual connectors between steps
- Time stamps for each step
- Request/Response previews

### Visual Layout
```
┌─────────────────────────────────────────┐
│ 🔍 Debug Panel - Execution Flow        │
├─────────────────────────────────────────┤
│                                         │
│ 1️⃣  User Prompt                        │
│     ✓ Completed                         │
│     └─ "Turn on office lights at 9am"  │
│                                         │
│ 2️⃣  Entity Extraction                  │
│     ✓ Completed                         │
│     └─ API: POST /conversation/process  │
│        Response: 4 entities found       │
│        [Expand to see details]          │
│                                         │
│ 3️⃣  Device Selection                   │
│     ✓ Completed                         │
│     └─ 4 devices selected               │
│        [Expand to see reasoning]        │
│                                         │
│ 4️⃣  OpenAI Prompt Generation           │
│     ✓ Completed                         │
│     └─ System prompt: 2,450 tokens     │
│        User prompt: 1,230 tokens        │
│        [Expand to see prompts]          │
│                                         │
│ 5️⃣  OpenAI API Call                    │
│     ✓ Completed                         │
│     └─ Model: gpt-4o-mini              │
│        Duration: 1.2s                   │
│        [Expand to see request/response] │
│                                         │
│ 6️⃣  Technical Prompt                   │
│     ✓ Completed                         │
│     └─ JSON structure created           │
│        [Expand to see JSON]             │
│                                         │
│ 7️⃣  YAML Generation                    │
│     ⏳ Pending (click Approve to run)   │
│                                         │
│ 8️⃣  HA API Call                        │
│     ⏳ Pending (click Approve to run)   │
│                                         │
│ 9️⃣  HA Response                        │
│     ⏳ Pending (click Approve to run)   │
│                                         │
└─────────────────────────────────────────┘
```

### Features
- **Collapsible Steps**: Each step can be expanded to show full details
- **Status Colors**: Green (✓), Yellow (⏳), Red (✗), Blue (⟳)
- **Progress Indicators**: Show which steps are complete
- **Request/Response Viewers**: Formatted JSON/YAML with syntax highlighting
- **Copy to Clipboard**: Easy copying of any step's data
- **Timing Information**: Show duration for each API call
- **Error Display**: Clear error messages if any step fails

### User Experience
- Scrollable timeline
- Smooth animations when steps complete
- Auto-expand on errors
- Search/filter capability
- Export flow as JSON

---

## Option 2: Flow Diagram View

### Design Concept
A visual flow diagram with connected nodes showing:
- Each step as a card/node
- Arrows showing data flow
- Expandable details in each node
- Color-coded status
- Interactive hover states
- Side-by-side request/response panels

### Visual Layout
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Debug Panel - Execution Flow                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                                            │
│  │ 1. User     │                                            │
│  │    Prompt   │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 2. Entity   │                                            │
│  │ Extraction  │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 3. Device   │                                            │
│  │ Selection   │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 4. OpenAI   │                                            │
│  │ Prompt Gen  │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 5. OpenAI   │                                            │
│  │ API Call    │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 6. Technical│                                            │
│  │ Prompt      │                                            │
│  │    ✓        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 7. YAML Gen │                                            │
│  │    ⏳        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 8. HA API   │                                            │
│  │ Call        │                                            │
│  │    ⏳        │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │ 9. HA       │                                            │
│  │ Response    │                                            │
│  │    ⏳        │                                            │
│  └─────────────┘                                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Selected Node Details                               │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Request:                                            │   │
│  │ { ... }                                             │   │
│  │                                                      │   │
│  │ Response:                                           │   │
│  │ { ... }                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Features
- **Interactive Nodes**: Click to select and view details
- **Visual Flow**: Clear arrows showing data direction
- **Side Panel**: Shows request/response for selected node
- **Status Badges**: Color-coded status on each node
- **Zoom Controls**: Zoom in/out for better viewing
- **Minimap**: Overview of entire flow
- **Node Expansion**: Click to expand node inline
- **Connection Labels**: Optional labels on arrows showing data passed

### User Experience
- Horizontal/vertical layout toggle
- Smooth transitions when nodes update
- Keyboard navigation (arrow keys)
- Print/export as image
- Responsive design for mobile

---

## Comparison

| Feature | Option 1: Timeline | Option 2: Flow Diagram |
|---------|-------------------|------------------------|
| **Readability** | ⭐⭐⭐⭐⭐ Excellent for sequential flow | ⭐⭐⭐⭐ Good, more visual |
| **Space Efficiency** | ⭐⭐⭐⭐ Good, vertical scroll | ⭐⭐⭐ Takes more space |
| **User-Friendly** | ⭐⭐⭐⭐⭐ Very intuitive | ⭐⭐⭐⭐ Good, slightly more complex |
| **Mobile Friendly** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Limited |
| **Implementation** | ⭐⭐⭐⭐ Moderate | ⭐⭐⭐ More complex |
| **Details View** | ⭐⭐⭐⭐⭐ Expandable inline | ⭐⭐⭐⭐ Side panel |
| **Status Visibility** | ⭐⭐⭐⭐⭐ Clear at a glance | ⭐⭐⭐⭐ Clear with colors |

---

## Recommendation

**Option 1 (Timeline View)** is recommended because:
1. More user-friendly for non-technical users
2. Better mobile/responsive experience
3. Easier to implement and maintain
4. Clear sequential flow matches the actual process
5. Better for showing detailed information inline
6. Familiar pattern (like git history, transaction logs)

**Option 2 (Flow Diagram)** could be added as an alternative view toggle for users who prefer visual diagrams.

---

## Implementation Notes

### Data Requirements
Need to capture and store:
- Timestamps for each step
- Request/response data for API calls
- Error messages if any step fails
- Duration/timing information
- Entity extraction results
- Device selection reasoning
- OpenAI token usage
- HA API response details

### Backend Changes
- Add timing information to responses
- Include request/response data in debug object
- Track entity extraction API calls
- Store HA API call details in approve response

### Frontend Changes
- New "Flow" tab in Debug Panel
- Timeline component with expandable steps
- Request/response viewer components
- Status indicator components
- Copy to clipboard functionality

