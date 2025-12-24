# Epic 20: Devices Dashboard

## Epic Overview
**Epic ID**: 20  
**Epic Title**: Devices & Entities Dashboard UI  
**Epic Goal**: Create interactive dashboard tab to explore Home Assistant devices, entities, and integrations  
**Epic Status**: Approved  
**Epic Priority**: P2 - MEDIUM  
**Epic Effort**: Small (2-3 weeks)  
**Epic Risk**: Low (reuses existing patterns)

## Epic Description
**As a** system operator,  
**I want** an interactive dashboard to browse and visualize devices, entities, and integrations,  
**so that** I can explore my Home Assistant setup and understand system topology.

## Business Justification
Epic 19 provides complete device/entity inventory via REST API. Epic 20 adds user-friendly visualization using the proven Dependencies Tab pattern that users love. Enables easy exploration, troubleshooting, and system understanding.

**Foundation**: Epic 19 REST API endpoints (completed)  
**UX Pattern**: Reuse Dependencies Tab interactive graph pattern (proven, loved by users)

## Epic Acceptance Criteria
1. **AC1: Devices Tab** - Dashboard has "Devices" tab showing all discovered devices
2. **AC2: Interactive Visualization** - Device browser with search, filter, and click-to-view
3. **AC3: Entity Browser** - View entities associated with each device
4. **AC4: Integration Status** - Display all integrations with health status
5. **AC5: Responsive Design** - Works on desktop and tablet, follows existing dark mode theme

## Epic Stories

### Story 20.1: Devices Tab - Device Browser
**Goal**: Create Devices tab with interactive device list and visualization  
**Priority**: P1 - HIGH | **Effort**: 1 week

**Acceptance Criteria**:
- Add "Devices" tab to dashboard navigation
- Display all devices in grid/list view
- Show device details (manufacturer, model, firmware, area)
- Search devices by name
- Filter by manufacturer, model, area
- Click device to view details
- Responsive layout with dark mode support
- Loading states and error handling

### Story 20.2: Entity Browser & Device Details
**Goal**: Show entities associated with each device  
**Priority**: P1 - HIGH | **Effort**: 1 week

**Acceptance Criteria**:
- Click device opens entity browser
- Show all entities for selected device
- Display entity details (ID, domain, platform, state)
- Group entities by domain (lights, sensors, switches)
- Visual indicators for disabled entities
- Link to entity in Home Assistant
- Smooth animations and transitions

### Story 20.3: Device Topology Visualization
**Goal**: Visual graph showing device relationships (OPTIONAL - reuse Dependencies Tab pattern)  
**Priority**: P3 - LOW | **Effort**: 3-5 days

**Acceptance Criteria**:
- Interactive graph similar to Dependencies Tab
- Nodes represent devices (with icons)
- Edges show device relationships
- Click to highlight connected entities
- Hover for tooltips with device info
- Color-coded by device type
- Zoom and pan controls

## Technical Requirements

### Frontend Stack (Reuse Existing)
- React 18.2 + TypeScript 5.2
- TailwindCSS 3.4 (styling)
- Heroicons (icons)
- Existing API service layer

### UX Pattern to Reuse
**Dependencies Tab Pattern** (from `ServiceDependencyGraph.tsx`):
- Interactive click-to-highlight
- Hover tooltips
- Color-coded status indicators
- Icon-based representation
- Smooth animations
- Dark mode support
- Pure React/CSS (no heavy libraries)

**Reference**: `docs/kb/context7-cache/ux-patterns/health-dashboard-dependencies-tab-pattern.md`

### API Integration
- Uses Epic 19 REST endpoints (already available)
- GET /api/devices
- GET /api/entities
- GET /api/integrations

### Components to Create
- `DevicesTab.tsx` - Main devices tab container
- `DeviceGrid.tsx` - Grid view of devices
- `DeviceCard.tsx` - Individual device card
- `EntityBrowser.tsx` - Entity list/browser
- `DeviceTopology.tsx` (optional) - Graph visualization
- `useDevices.ts` - Hook for API calls
- `useEntities.ts` - Hook for entity data

## Dependencies
- **Required**: Epic 19 complete (REST API endpoints) ✅
- **Existing**: Health Dashboard infrastructure ✅
- **Existing**: API service layer ✅
- **Existing**: Dependencies Tab pattern ✅

## Out of Scope
- Device control (turn on/off) - just viewing
- Entity state updates - just showing current config
- Device configuration - read-only
- Historical device tracking - defer to future

## Success Criteria
- Devices tab accessible and responsive
- All devices displayed with correct data
- Entity browser shows accurate entity list
- Search and filters working
- No performance degradation
- < 100ms API response time
- Follows existing design patterns

## Implementation Notes

### Keep It Simple
- Reuse existing components where possible
- Copy Dependencies Tab pattern (proven UX)
- Minimal new CSS (use TailwindCSS utilities)
- Standard React patterns (hooks, context)
- No complex state management (just API calls)

### Design Principles
- Match existing dashboard aesthetic
- Reuse color palette and typography
- Follow existing navigation pattern
- Maintain consistency with other tabs

## Timeline
**Week 1**: Story 20.1 (Devices tab and browser)  
**Week 2**: Story 20.2 (Entity browser and details)  
**Week 3** (Optional): Story 20.3 (Topology visualization)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| API performance | Low | Pagination, caching if needed |
| UX complexity | Low | Reuse proven Dependencies Tab pattern |
| Large device count (1000+) | Low | Pagination, virtualization if needed |
| Browser compatibility | Low | Modern React, tested browsers |

**Overall Risk**: **LOW** - Reusing proven patterns, simple UI

## Related Documentation
- **Epic 19**: `docs/prd/epic-19-device-entity-discovery.md` (API foundation)
- **Dependencies Tab**: `services/health-dashboard/src/components/ServiceDependencyGraph.tsx`
- **UX Pattern**: `docs/kb/context7-cache/ux-patterns/health-dashboard-dependencies-tab-pattern.md`
- **Dashboard**: `services/health-dashboard/src/components/Dashboard.tsx`

---

**Created**: October 12, 2025  
**Status**: Ready for Story Creation  
**Dependencies**: Epic 19 ✅ Complete  
**Next Step**: Create Story 20.1 - Devices Tab & Browser

