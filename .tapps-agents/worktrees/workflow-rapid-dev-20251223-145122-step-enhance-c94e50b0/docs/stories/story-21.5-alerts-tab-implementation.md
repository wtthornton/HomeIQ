# Story 21.5: Alerts Tab Implementation

**Epic:** Epic 21 - Dashboard API Integration Fix  
**Story ID:** 21.5  
**Created:** October 13, 2025  
**Status:** In Progress  
**Priority:** High  
**Estimated Effort:** 4-6 hours  

## Goal

Create a full alerts management interface using data-api alerts endpoints, enabling users to view, filter, and manage system alerts with real-time updates.

## Current State

- AlertsTab exists as a placeholder component with no functionality
- Alert endpoints exist in data-api (`/api/v1/alerts`)
- No alert types/interfaces defined in frontend
- No alert management UI components

## User Story

**As a** system administrator  
**I want to** view and manage system alerts in the dashboard  
**So that** I can quickly respond to critical issues and track alert history

## Requirements

### Functional Requirements

1. **Alert Display**
   - Display active alerts with severity indicators
   - Show alert details (service, message, timestamp)
   - Group alerts by severity (critical, warning, info)
   - Display alert count in summary cards

2. **Alert Filtering**
   - Filter by severity (all, info, warning, error, critical)
   - Filter by service (websocket-ingestion, enrichment-pipeline, etc.)
   - Filter by status (active, acknowledged, resolved)

3. **Alert Actions**
   - Acknowledge alerts
   - Resolve alerts
   - Dismiss alerts
   - View alert details

4. **Real-time Updates**
   - Receive new alerts via WebSocket
   - Update alert status in real-time
   - Show notification badge for new alerts

5. **Alert History**
   - View resolved alerts (past 24 hours)
   - Track alert lifecycle (created → acknowledged → resolved)

### Non-Functional Requirements

1. **Performance**
   - Load alerts in < 1 second
   - Handle 100+ alerts without lag
   - Pagination for large alert lists

2. **Usability**
   - Responsive design (mobile, tablet, desktop)
   - Clear visual hierarchy
   - Intuitive action buttons
   - Loading states and error handling

3. **Accessibility**
   - Keyboard navigation
   - Screen reader support
   - Color contrast compliance
   - ARIA labels

## Design

### Component Structure

```
AlertsTab
├── Alert Summary Cards (Top)
│   ├── Active Alerts (count + icon)
│   ├── Warning Alerts (count + icon)
│   ├── Critical Alerts (count + icon)
│   └── Last Alert Time
├── Filter Bar (Middle)
│   ├── Severity Filter (dropdown)
│   ├── Service Filter (dropdown)
│   └── Status Filter (dropdown)
└── Alerts List (Bottom)
    ├── AlertCard (for each alert)
    │   ├── Severity Badge
    │   ├── Service Name
    │   ├── Alert Message
    │   ├── Timestamp
    │   └── Action Buttons
    │       ├── Acknowledge
    │       ├── Resolve
    │       └── Dismiss
    └── Pagination (if needed)
```

### Data Models

```typescript
// Alert severity levels
type AlertSeverity = 'critical' | 'error' | 'warning' | 'info';

// Alert status
type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'dismissed';

// Alert interface
interface Alert {
  id: string;
  severity: AlertSeverity;
  service: string;
  message: string;
  details?: string;
  timestamp: string;
  status: AlertStatus;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
  resolvedAt?: string;
  resolvedBy?: string;
}

// Alert filters
interface AlertFilters {
  severity?: AlertSeverity;
  service?: string;
  status?: AlertStatus;
}

// Alert summary
interface AlertSummary {
  total: number;
  active: number;
  warning: number;
  critical: number;
  lastAlertTime: string | null;
}
```

### API Endpoints

**GET /api/v1/alerts**
- Query params: severity, service, status, limit, offset
- Returns: List of alerts matching filters

**POST /api/v1/alerts/{id}/acknowledge**
- Marks alert as acknowledged
- Returns: Updated alert

**POST /api/v1/alerts/{id}/resolve**
- Marks alert as resolved
- Returns: Updated alert

**DELETE /api/v1/alerts/{id}**
- Dismisses/deletes alert
- Returns: Success response

## Tasks

### Backend (if needed)
- [x] Verify alert endpoints exist in data-api
- [ ] Test alert endpoints functionality
- [ ] Add missing alert actions if needed

### Frontend
- [ ] Create `types/alerts.ts` with Alert interfaces
- [ ] Create `hooks/useAlerts.ts` for data fetching
- [ ] Create `components/alerts/AlertCard.tsx` component
- [ ] Create `components/alerts/AlertSummaryCards.tsx` component
- [ ] Update `components/tabs/AlertsTab.tsx` with full functionality
- [ ] Add WebSocket listener for real-time alerts
- [ ] Implement alert action handlers
- [ ] Add loading states and error handling
- [ ] Add responsive styling

### Testing
- [ ] Test alert loading from API
- [ ] Test severity filtering
- [ ] Test service filtering
- [ ] Test alert actions (acknowledge, resolve, dismiss)
- [ ] Test real-time updates
- [ ] Test error handling
- [ ] Test responsive design

## Acceptance Criteria

### Must Have
- [ ] Alerts load from `/api/v1/alerts` endpoint
- [ ] Summary cards show correct alert counts
- [ ] Severity filtering works (all severities)
- [ ] Service filtering works (all services)
- [ ] Alert actions call correct API endpoints
- [ ] Loading states display during API calls
- [ ] Error handling with retry functionality
- [ ] Responsive design for mobile/tablet/desktop

### Should Have
- [ ] Real-time alerts via WebSocket
- [ ] Alert history view (resolved alerts)
- [ ] Pagination for large alert lists
- [ ] Notification badge in header
- [ ] Keyboard shortcuts for actions

### Nice to Have
- [ ] Alert sound notifications
- [ ] Export alerts to CSV
- [ ] Alert detail modal
- [ ] Alert configuration view
- [ ] Alert trends/analytics

## Technical Considerations

### State Management
- Use React hooks (useState, useEffect)
- Custom useAlerts hook for data fetching
- Local state for filters and UI state

### WebSocket Integration
- Reuse existing WebSocket connection
- Listen for 'alert' events
- Update alert list in real-time
- Show notification for new critical alerts

### Performance
- Paginate alerts (50 per page)
- Virtualized scrolling for large lists
- Debounce filter changes
- Memoize expensive calculations

### Error Handling
- Display error messages in UI
- Retry failed requests
- Fallback to cached data if available
- Log errors to console

## Dependencies

### Internal
- data-api service (alert endpoints)
- WebSocket connection (real-time updates)
- Existing UI components (SkeletonCard, etc.)

### External
- None (using existing React/TypeScript stack)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Alert endpoint not fully implemented | High | Verify endpoints, implement missing functionality |
| Large number of alerts causes performance issues | Medium | Implement pagination, virtualization |
| WebSocket connection drops | Medium | Implement reconnection logic, fallback to polling |
| Alert actions fail | Medium | Add retry logic, show error messages |

## Timeline

- **Phase 1 (1-2 hours):** Setup types, interfaces, and useAlerts hook
- **Phase 2 (1-2 hours):** Create AlertCard and summary components
- **Phase 3 (1-2 hours):** Update AlertsTab with full functionality
- **Phase 4 (0.5-1 hour):** Add WebSocket integration
- **Phase 5 (0.5-1 hour):** Testing and refinement

**Total:** 4-6 hours

## Success Metrics

- Alert tab loads in < 1 second
- Users can filter and manage alerts efficiently
- Real-time updates work without page refresh
- 0 critical bugs in production
- Positive user feedback on usability

## Related Stories

- **Story 21.0:** Deploy Data API Service (prerequisite)
- **Story 21.1:** Devices Tab Integration
- **Story 21.2:** Sports Tab Implementation
- **Story 21.3:** Events Tab Historical Queries
- **Story 21.4:** Analytics Tab with Real Data
- **Story 21.6:** Enhanced Overview Tab (includes alert integration)

## References

- Epic 21 document: `docs/stories/epic-21-dashboard-api-integration-fix.md`
- Alert endpoints: `services/data-api/src/alert_endpoints.py`
- WebSocket implementation: `services/data-api/src/websocket_endpoints.py`

---

**Created by:** AI Assistant (BMAD Method)  
**Last Updated:** October 13, 2025

