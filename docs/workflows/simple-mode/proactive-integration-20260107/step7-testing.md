# Step 7: Testing Plan - Proactive Agent Service UI Integration

## Test Strategy

### Test Types
1. **Unit Tests**: Component logic, API client functions
2. **Integration Tests**: API communication, state management
3. **E2E Tests**: Full user workflows (manual for now)
4. **Manual Testing**: Visual verification, UX validation

---

## Unit Test Plan

### 1. Types (`src/types/proactive.ts`)
```typescript
// No runtime code - TypeScript compile-time checks only
```

### 2. API Client (`src/services/proactiveApi.ts`)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `getSuggestions` - success | Returns suggestions array | High |
| `getSuggestions` - with filters | Applies query params | High |
| `getSuggestions` - error handling | Throws ProactiveAPIError | High |
| `updateSuggestionStatus` - approve | Updates to 'approved' | High |
| `updateSuggestionStatus` - reject | Updates to 'rejected' | High |
| `deleteSuggestion` - success | Returns success message | Medium |
| `getStats` - success | Returns stats object | Medium |
| `triggerGeneration` - success | Returns trigger response | Medium |
| Network error handling | Wraps TypeError | Medium |

### 3. ProactiveSuggestionCard Component

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Renders suggestion prompt | Shows prompt text in quotes | High |
| Shows context type badge | Displays icon and label | High |
| Shows quality score bar | Renders correct percentage | High |
| Shows status badge | Displays correct status color | High |
| Approve button works | Calls onApprove callback | High |
| Reject button works | Calls onReject callback | High |
| Delete button with confirmation | Shows confirm dialog | Medium |
| Loading states during actions | Shows loading indicator | Medium |
| Disables buttons during processing | Prevents double-clicks | Medium |

### 4. ProactiveStats Component

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Renders total count | Shows total number | High |
| Renders context type counts | Shows breakdown by type | High |
| Renders status counts | Shows breakdown by status | Medium |
| Loading skeleton | Shows skeleton when loading | Medium |
| Handles null stats | Returns null | Low |

### 5. ProactiveFilters Component

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Context type dropdown | Changes filter state | High |
| Status dropdown | Changes filter state | High |
| Clear filters button | Resets all filters | Medium |
| Hide clear button when no filters | Conditional render | Low |

### 6. ProactiveSuggestions Page

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Loads suggestions on mount | Calls API on effect | High |
| Loads stats on mount | Calls API on effect | High |
| Filter change reloads | Triggers new API call | High |
| Approve updates local state | Optimistic update | High |
| Reject updates local state | Optimistic update | High |
| Generate button triggers API | Calls triggerGeneration | Medium |
| Refresh button reloads | Calls both load functions | Medium |
| Error state renders | Shows error message | Medium |
| Empty state renders | Shows empty message | Medium |
| Loading state renders | Shows spinner | Medium |

---

## Integration Test Plan

### API Integration

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Nginx proxy routing | `/api/proactive/*` → `:8031` | High |
| CORS headers | Allow frontend origin | High |
| Auth header forwarding | API key passed through | Medium |
| Error response handling | 4xx/5xx codes | Medium |

### Component Integration

| Test Case | Description | Priority |
|-----------|-------------|----------|
| Page + Card integration | Callbacks work correctly | High |
| Page + Filters integration | Filter changes update list | High |
| Page + Stats integration | Stats update on actions | Medium |

---

## E2E Test Plan (Manual)

### Happy Path

1. **View Suggestions**
   - Navigate to `/proactive`
   - Verify suggestions load
   - Verify stats display
   - Verify cards render correctly

2. **Filter Suggestions**
   - Select "Weather" from type dropdown
   - Verify only weather suggestions shown
   - Select "Pending" from status dropdown
   - Verify filters combine correctly
   - Click "Clear Filters"
   - Verify all suggestions shown

3. **Approve Suggestion**
   - Click "Approve" on pending suggestion
   - Verify toast notification
   - Verify status changes to "Approved"
   - Verify stats update

4. **Reject Suggestion**
   - Click "Reject" on pending suggestion
   - Verify toast notification
   - Verify status changes to "Rejected"
   - Verify stats update

5. **Delete Suggestion**
   - Click delete button
   - Confirm in dialog
   - Verify suggestion removed
   - Verify stats update

6. **Manual Trigger**
   - Click "Generate" button
   - Verify loading state
   - Verify toast on success/error
   - Verify list refreshes

### Error Paths

1. **Service Unavailable**
   - Stop proactive-agent-service
   - Navigate to `/proactive`
   - Verify error message displays
   - Click "Try Again"
   - Verify retry works when service up

2. **Network Error**
   - Disconnect network
   - Try to approve suggestion
   - Verify error toast
   - Verify suggestion state unchanged

### Edge Cases

1. **Empty State**
   - Delete all suggestions
   - Verify empty state renders
   - Verify "Generate Sample" button works

2. **Large Dataset**
   - Create 100+ suggestions
   - Verify list renders efficiently
   - Verify scrolling smooth

---

## Test File Locations

```
services/ai-automation-ui/
├── src/
│   ├── services/
│   │   └── __tests__/
│   │       └── proactiveApi.test.ts      [TO CREATE]
│   │
│   ├── components/
│   │   └── proactive/
│   │       └── __tests__/
│   │           ├── ProactiveSuggestionCard.test.tsx  [TO CREATE]
│   │           ├── ProactiveStats.test.tsx           [TO CREATE]
│   │           └── ProactiveFilters.test.tsx         [TO CREATE]
│   │
│   └── pages/
│       └── __tests__/
│           └── ProactiveSuggestions.test.tsx         [TO CREATE]
```

---

## Validation Checklist

### Pre-Deployment
- [ ] TypeScript compiles without errors ✅
- [ ] No ESLint warnings ✅
- [ ] Manual smoke test passes
- [ ] proactive-agent-service running

### Deployment
- [ ] Build UI container
- [ ] Verify nginx routes work
- [ ] Verify API connectivity

### Post-Deployment
- [ ] Navigate to `/proactive`
- [ ] Verify suggestions load (or empty state)
- [ ] Test approve/reject flow
- [ ] Verify stats update

---

## Manual Test Script

```bash
# 1. Ensure proactive-agent-service is running
docker-compose up -d proactive-agent-service

# 2. Verify health endpoint
curl http://localhost:8031/health
# Expected: {"status":"healthy"}

# 3. Rebuild UI with new nginx config
docker-compose build ai-automation-ui
docker-compose up -d ai-automation-ui

# 4. Test nginx proxy
curl http://localhost:3001/api/proactive/suggestions
# Expected: JSON response with suggestions

# 5. Open browser
# Navigate to http://localhost:3001/proactive
# Verify UI loads correctly
```

---

## Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest | To Test |
| Firefox | Latest | To Test |
| Safari | Latest | To Test |
| Edge | Latest | To Test |

---

## Performance Validation

| Metric | Target | Status |
|--------|--------|--------|
| Page Load | < 2s | To Measure |
| API Response | < 500ms | To Measure |
| Animation FPS | 60fps | To Measure |
| Bundle Size Impact | < 10KB | To Measure |

---
*Generated by Simple Mode Build Workflow*
*Timestamp: 2026-01-07*
