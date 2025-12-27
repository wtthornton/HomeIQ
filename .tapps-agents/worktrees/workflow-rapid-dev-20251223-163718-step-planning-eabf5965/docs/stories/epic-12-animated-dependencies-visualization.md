# Epic 12: Animated Real-Time Dependencies Visualization - Brownfield Enhancement

## Epic Goal

Transform the static Dependencies tab into an engaging real-time data flow visualization with animated particles, interactive highlights, and live metrics that show users exactly how data moves through their system.

## Epic Description

### Existing System Context

- **Current functionality:** ServiceDependencyGraph shows static boxes and arrows with click-to-highlight
- **Technology stack:** React 18.2 + TypeScript, SVG rendering, Tailwind CSS
- **Integration points:** Dashboard component, Admin API for service status, real-time metrics

### Enhancement Details

**What's being added:**
- AnimatedDependencyGraph component with SVG animations
- Real-time data flow particles using `<animateMotion>`
- Live metrics display (events/sec, active APIs)
- Interactive node highlighting on click
- Color-coded flows by type (WebSocket, API, Storage, Sports)
- Pulsing effects for active nodes
- Throughput visualization on connections
- Team-specific flow filtering (integrates with Epic 11)

**How it integrates:**
- Replaces existing ServiceDependencyGraph component
- Uses existing service status API
- Adds new `/api/v1/metrics/realtime` endpoint
- Follows existing dark mode and responsive patterns
- Integrates sports data flows from Epic 11

**Success criteria:**
- 60fps smooth animations
- <2s real-time metric updates
- Interactive highlights respond <100ms
- Mobile-responsive (scales to phone screens)
- No performance degradation to dashboard
- Sports flows visible when teams selected

## Stories

### Story 12.1: Animated SVG Data Flow Component
Create AnimatedDependencyGraph component with SVG animations, particles, and interactive features.

**Key Tasks:**
- AnimatedDependencyGraph component structure
- SVG path calculations and rendering
- `<animateMotion>` particle animations
- `<animate>` for pulsing effects
- SVG filter effects (glow, blur)
- Interactive node click handlers
- Color-coded flow paths
- Responsive SVG viewport

### Story 12.2: Real-Time Metrics API & Polling
Implement real-time metrics endpoint and dashboard polling for live system statistics.

**Key Tasks:**
- `/api/v1/metrics/realtime` endpoint in admin-api
- Events per second calculator
- Active API sources tracker
- Frontend polling hook (2s intervals)
- Metrics display UI
- Error handling for polling
- Metrics caching strategy

### Story 12.3: Sports Data Flow Integration
Integrate sports data flows into animated visualization showing NFL/NHL API activity.

**Key Tasks:**
- Add NFL/NHL nodes to graph
- Sports-specific flow paths
- Team selection filtering
- Flow activation based on live games
- Throughput labels for sports flows
- Live game indicators
- Color coding for sports data

## Compatibility Requirements

- [x] Existing ServiceDependencyGraph API unchanged (new component, drop-in replacement)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (Tailwind, React, SVG)
- [x] Performance impact is minimal (GPU-accelerated SVG, efficient polling)

## Risk Mitigation

**Primary Risk:** Animation performance issues on low-end devices

**Mitigation:**
- Use GPU-accelerated SVG animations
- Request animation frame for updates
- Conditional rendering based on visibility
- Debounced metric updates (2s minimum)
- Performance monitoring

**Rollback Plan:**
- Revert to ServiceDependencyGraph component
- Single line change in Dashboard.tsx
- No API changes to rollback
- Feature flag for gradual rollout

## Definition of Done

- [x] All 3 stories completed with acceptance criteria met
- [x] 60fps animations verified on target devices
- [x] Real-time updates working reliably
- [x] Sports integration functional
- [x] Existing dependencies tab functionality preserved
- [x] E2E tests for animations and interactions
- [x] Performance tested (CPU, memory, render time)
- [x] Mobile responsive verified
- [x] Dark mode working correctly
- [x] Documentation updated with animation details

## Dependencies

- Epic 11 (for sports data integration)
- React Flow patterns (from Context7 KB research)
- Framer Motion patterns (from Context7 KB research)
- No new npm packages required (uses native SVG)

## Estimated Effort

- Story 12.1: 3 days (animated component)
- Story 12.2: 2 days (real-time metrics)
- Story 12.3: 2 days (sports integration)

**Total:** ~7 days (1.5 weeks)

---

**Status:** Draft  
**Created:** October 12, 2025  
**Epic Owner:** Product Team  
**Development Lead:** TBD  
**Depends On:** Epic 11 (for sports flows)

