# Step 2: User Stories - Proactive Agent Service UI Integration

## Epic Overview
**Epic**: Proactive Suggestions UI Integration
**Goal**: Enable users to view and manage context-aware automation suggestions from proactive-agent-service

---

## User Stories

### Story 1: Nginx Route Configuration
**As a** frontend developer  
**I want** an nginx proxy route to proactive-agent-service  
**So that** the UI can communicate with the proactive suggestions API

**Story Points**: 1  
**Priority**: Critical (Blocking)

**Acceptance Criteria**:
- [ ] Nginx route `/api/proactive/*` proxies to `proactive-agent-service:8031`
- [ ] Authentication headers are forwarded
- [ ] CORS headers are properly configured
- [ ] Health check endpoint is accessible

**Tasks**:
1. Add location block to nginx.conf for `/api/proactive/*`
2. Configure proxy_pass to proactive-agent-service:8031
3. Add authentication header forwarding
4. Test route with curl/Postman

---

### Story 2: Proactive API Client
**As a** frontend developer  
**I want** a TypeScript API client for proactive-agent-service  
**So that** React components can fetch and manage proactive suggestions

**Story Points**: 2  
**Priority**: Critical

**Acceptance Criteria**:
- [ ] API client implements all proactive-agent-service endpoints
- [ ] TypeScript interfaces match backend models
- [ ] Error handling follows existing patterns
- [ ] Authentication headers are included

**Tasks**:
1. Create `src/services/proactiveApi.ts`
2. Define TypeScript interfaces for ProactiveSuggestion
3. Implement CRUD methods (list, get, update, delete)
4. Implement stats and trigger methods
5. Add error handling with APIError class

---

### Story 3: Proactive Suggestions Page
**As a** homeowner  
**I want** to see context-aware automation suggestions  
**So that** I can discover useful automations based on weather, sports, and energy

**Story Points**: 5  
**Priority**: Critical

**Acceptance Criteria**:
- [ ] New page at `/proactive` route
- [ ] Display suggestions in card format
- [ ] Show context type icon (weather, sports, energy, historical)
- [ ] Show quality score and status
- [ ] Loading and error states handled
- [ ] Empty state with helpful message

**Tasks**:
1. Create `src/pages/ProactiveSuggestions.tsx`
2. Implement suggestion card component
3. Add loading skeleton
4. Add empty state component
5. Integrate with API client

---

### Story 4: Suggestion Filtering
**As a** homeowner  
**I want** to filter proactive suggestions by type and status  
**So that** I can focus on relevant suggestions

**Story Points**: 2  
**Priority**: High

**Acceptance Criteria**:
- [ ] Filter by context type (weather, sports, energy, historical)
- [ ] Filter by status (pending, sent, approved, rejected)
- [ ] Filters update URL params for shareability
- [ ] Clear filters button

**Tasks**:
1. Add filter dropdowns to page header
2. Implement filter state management
3. Connect filters to API query params
4. Add URL sync for filters

---

### Story 5: Suggestion Actions
**As a** homeowner  
**I want** to approve or reject proactive suggestions  
**So that** I can control which automations get created

**Story Points**: 3  
**Priority**: Critical

**Acceptance Criteria**:
- [ ] Approve button changes status to "approved"
- [ ] Reject button changes status to "rejected"
- [ ] Confirmation dialog for destructive actions
- [ ] Optimistic UI updates
- [ ] Toast notifications for success/error

**Tasks**:
1. Add action buttons to suggestion cards
2. Implement status update API calls
3. Add confirmation dialogs
4. Add toast notifications
5. Implement optimistic updates

---

### Story 6: Navigation Integration
**As a** user  
**I want** to access proactive suggestions from the navigation  
**So that** I can easily find the new feature

**Story Points**: 1  
**Priority**: High

**Acceptance Criteria**:
- [ ] "Proactive" tab added to main navigation
- [ ] Icon matches context-aware theme (lightbulb, brain, etc.)
- [ ] Active state styling
- [ ] Mobile responsive

**Tasks**:
1. Add route to App.tsx
2. Add navigation item to Navigation.tsx
3. Choose appropriate icon
4. Test mobile responsiveness

---

### Story 7: Statistics Dashboard
**As a** homeowner  
**I want** to see statistics about proactive suggestions  
**So that** I can understand the AI's activity

**Story Points**: 2  
**Priority**: Medium

**Acceptance Criteria**:
- [ ] Total suggestions count
- [ ] Breakdown by status (pending, approved, rejected)
- [ ] Breakdown by context type
- [ ] Visual representation (badges, charts)

**Tasks**:
1. Add stats section to page header
2. Fetch stats from API
3. Display in badge/pill format
4. Add loading state for stats

---

### Story 8: Manual Trigger
**As a** power user  
**I want** to manually trigger suggestion generation  
**So that** I don't have to wait for the 3 AM job

**Story Points**: 1  
**Priority**: Medium

**Acceptance Criteria**:
- [ ] "Generate Suggestions" button in page header
- [ ] Loading state during generation
- [ ] Success/error feedback
- [ ] Rate limiting indication

**Tasks**:
1. Add trigger button to page
2. Implement trigger API call
3. Add loading state
4. Show results/errors

---

## Implementation Order

```
Story 1 (Nginx) ─────┐
                     ├──► Story 3 (Page) ─────► Story 4 (Filters)
Story 2 (API) ───────┘           │
                                 ├──► Story 5 (Actions)
                                 │
Story 6 (Nav) ───────────────────┘
                                 │
                                 ├──► Story 7 (Stats)
                                 └──► Story 8 (Trigger)
```

## Estimated Timeline
- **Total Story Points**: 17
- **Estimated Duration**: 1-2 sprints (assuming 8-10 points per sprint)
- **Dependencies**: Stories 1 & 2 must complete before Stories 3-8

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| proactive-agent-service not running | Medium | High | Add health check, graceful degradation |
| API schema changes | Low | Medium | Use TypeScript strict mode, add tests |
| Port conflicts | Low | High | Verify docker-compose port mappings |
| Styling inconsistencies | Medium | Low | Use existing component patterns |

---
*Generated by Simple Mode Build Workflow*
*Timestamp: 2026-01-07*
