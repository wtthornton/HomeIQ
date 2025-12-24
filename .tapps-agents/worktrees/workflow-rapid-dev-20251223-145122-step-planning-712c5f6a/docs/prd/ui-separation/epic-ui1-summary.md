# Epic UI-1: UI Separation and AI Automation Interface Fix

**Epic ID:** Epic-UI-1  
**Epic Goal:** Separate system monitoring from AI automation interface and fix ai-automation-ui service  
**Phase:** Production Stabilization  
**Priority:** High  
**Timeline:** 2-3 days  
**Total Effort:** 12-16 hours

---

## Executive Summary

Currently, the project has two frontend services:
- **health-dashboard (Port 3000)**: System monitoring dashboard with 13 tabs including an "AI Automation" tab
- **ai-automation-ui (Port 3001)**: Dedicated AI automation interface (NOT WORKING)

This Epic will:
1. Remove the AI Automation tab from the health-dashboard (port 3000)
2. Fix the ai-automation-ui service (port 3001) to work correctly
3. Establish clear separation of concerns between system monitoring and user-facing AI features

---

## Problem Statement

### Current Issues

1. **Duplicate Functionality**: AI Automation features exist in both UIs
2. **Service Not Working**: ai-automation-ui (port 3001) is not accessible/functioning
3. **Unclear Separation**: Users don't know which UI to use
4. **Confusing UX**: System monitoring mixed with user features

### Desired State

- **Port 3000 (health-dashboard)**: System monitoring, service health, configuration, logs (admin-focused)
- **Port 3001 (ai-automation-ui)**: AI automation suggestions, patterns, deployed automations (user-focused)

---

## Story List

| Story | Title | Effort | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| **UI1.1** | Remove AI Automation Tab from Health Dashboard | 2-3h | Critical | None |
| **UI1.2** | Fix ai-automation-ui Service Configuration | 4-6h | Critical | None |
| **UI1.3** | Update Documentation and Navigation | 2-3h | High | UI1.1, UI1.2 |
| **UI1.4** | Add Cross-Navigation Between UIs | 2-3h | Medium | UI1.1, UI1.2 |
| **UI1.5** | E2E Testing and Validation | 2-3h | High | UI1.1, UI1.2, UI1.3 |

**Total Stories:** 5  
**Total Effort:** 12-18 hours

---

## Story Details

### UI1.1: Remove AI Automation Tab from Health Dashboard

**Objective:** Remove the AI Automation tab and component from health-dashboard

**Tasks:**
1. Remove AIAutomationTab from Dashboard.tsx tab configuration
2. Remove AIAutomationTab.tsx component file
3. Remove AI Automation export from tabs/index.ts
4. Update tab numbering/ordering
5. Test that remaining 12 tabs work correctly

**Acceptance Criteria:**
- [ ] AI Automation tab no longer visible in health-dashboard
- [ ] All other 12 tabs function correctly
- [ ] No console errors or broken imports
- [ ] Navigation works smoothly between remaining tabs

**Files to Modify:**
- `services/health-dashboard/src/components/Dashboard.tsx`
- `services/health-dashboard/src/components/tabs/AIAutomationTab.tsx` (DELETE)
- `services/health-dashboard/src/components/tabs/index.ts`

---

### UI1.2: Fix ai-automation-ui Service Configuration

**Objective:** Diagnose and fix issues preventing ai-automation-ui from working

**Investigation Required:**
1. Check if service builds correctly
2. Verify environment variables pass through to production build
3. Test API connectivity from container
4. Verify nginx configuration
5. Check health check endpoint

**Potential Issues:**
- Environment variable `VITE_API_URL` not embedded in production build
- Need to add API proxy in nginx.conf for production deployment
- CORS configuration missing container network origins

**Tasks:**
1. Update docker-compose.yml environment variables
2. Add API proxy to nginx.conf
3. Update vite.config.ts for proper API URL handling
4. Add container network CORS origins to ai-automation-service
5. Test build and deployment process
6. Verify all routes work correctly

**Acceptance Criteria:**
- [ ] ai-automation-ui accessible at http://localhost:3001
- [ ] All pages render correctly (Dashboard, Patterns, Deployed, Settings)
- [ ] API calls to port 8018 work successfully
- [ ] No CORS errors in browser console
- [ ] Health check passes
- [ ] Service starts successfully in docker-compose

**Files to Modify:**
- `services/ai-automation-ui/nginx.conf`
- `services/ai-automation-ui/vite.config.ts`
- `services/ai-automation-service/src/main.py` (CORS)
- `docker-compose.yml` (environment variables)

---

### UI1.3: Update Documentation and Navigation

**Objective:** Update all documentation to reflect UI separation

**Tasks:**
1. Update README.md with clear UI descriptions
2. Update DEPLOYMENT_GUIDE.md
3. Update architecture documentation
4. Add UI decision documentation
5. Update user manual with two UI sections

**Acceptance Criteria:**
- [ ] README clearly explains both UIs
- [ ] Documentation distinguishes between admin and user UIs
- [ ] Architecture docs updated
- [ ] Quick start guide includes both UIs

**Files to Create/Modify:**
- `README.md`
- `docs/USER_MANUAL.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/architecture/frontend-architecture.md`
- `implementation/UI_SEPARATION_COMPLETE.md` (completion report)

---

### UI1.4: Add Cross-Navigation Between UIs

**Objective:** Add helpful links between the two UIs

**Tasks:**
1. Add link to AI Automation UI from health-dashboard header
2. Add link to Admin Dashboard from ai-automation-ui footer
3. Add informational tooltips explaining each UI's purpose
4. Consider adding a "launcher" page or documentation

**Acceptance Criteria:**
- [ ] Easy navigation between UIs
- [ ] Users understand which UI to use for what
- [ ] Links open in new tabs
- [ ] Visual indicators show current UI

**Files to Modify:**
- `services/health-dashboard/src/components/Dashboard.tsx`
- `services/ai-automation-ui/src/App.tsx` (footer already has link)
- `services/ai-automation-ui/src/components/Navigation.tsx`

---

### UI1.5: E2E Testing and Validation

**Objective:** Comprehensive testing of both UIs

**Tasks:**
1. Test all tabs in health-dashboard (12 tabs)
2. Test all pages in ai-automation-ui (4 pages)
3. Test API connectivity from both UIs
4. Test cross-navigation links
5. Performance testing (load times)
6. Browser console error check
7. Mobile responsiveness check

**Acceptance Criteria:**
- [ ] All health-dashboard tabs work
- [ ] All ai-automation-ui pages work
- [ ] No console errors
- [ ] API calls successful
- [ ] Page load times < 2 seconds
- [ ] Mobile responsive
- [ ] Cross-navigation works

**Test Checklist:**
**Health Dashboard (Port 3000):**
- [ ] Overview tab
- [ ] Services tab
- [ ] Dependencies tab
- [ ] Devices tab
- [ ] Events tab
- [ ] Logs tab
- [ ] Sports tab
- [ ] Data Sources tab
- [ ] Energy tab
- [ ] Analytics tab
- [ ] Alerts tab
- [ ] Configuration tab

**AI Automation UI (Port 3001):**
- [ ] Dashboard page
- [ ] Patterns page
- [ ] Deployed page
- [ ] Settings page
- [ ] API connectivity
- [ ] Suggestion approval workflow
- [ ] Pattern detection display

---

## Technical Architecture

### Health Dashboard (Port 3000)
**Purpose:** System administration and monitoring  
**Target Users:** Administrators, DevOps  
**Port:** 3000 (external) → 80 (internal)  
**Backend API:** admin-api (port 8003)  
**Features:**
- System health monitoring
- Service management
- Docker container control
- Event streaming
- Log aggregation
- Configuration management
- Integration status
- Performance analytics

### AI Automation UI (Port 3001)
**Purpose:** AI automation suggestion management  
**Target Users:** End users, home automation enthusiasts  
**Port:** 3001 (external) → 80 (internal)  
**Backend API:** ai-automation-service (port 8018)  
**Features:**
- View AI suggestions
- Approve/reject automations
- View detected patterns
- Manage deployed automations
- Configure AI settings
- View cost/usage stats
- Natural language automation requests

---

## Technical Issues & Solutions

### Issue 1: ai-automation-ui Cannot Reach API

**Problem:** Environment variable `VITE_API_URL=http://localhost:8018/api` not accessible from container

**Solution:** Add nginx proxy configuration
```nginx
location /api {
    proxy_pass http://ai-automation-service:8018/api;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Issue 2: CORS Errors from Container Network

**Problem:** Container-to-container calls use different hostname

**Solution:** Add container network origins to CORS:
```python
allow_origins=[
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://ai-automation-ui",  # Container network
    "http://ai-automation-ui:80"
]
```

### Issue 3: Build-Time Environment Variables

**Problem:** Vite embeds environment variables at build time

**Solution:** Use build args in Dockerfile:
```dockerfile
ARG VITE_API_URL=http://localhost:8018/api
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build
```

---

## Success Metrics

### Functional Success:
- ✅ Health dashboard has 12 tabs (AI Automation removed)
- ✅ AI automation UI accessible at port 3001
- ✅ All API calls work from both UIs
- ✅ No CORS errors
- ✅ Health checks pass

### Performance Success:
- ✅ Both UIs load in < 2 seconds
- ✅ API response times < 500ms
- ✅ No console errors
- ✅ Mobile responsive

### User Experience Success:
- ✅ Clear separation of concerns
- ✅ Users understand which UI to use
- ✅ Easy navigation between UIs
- ✅ Consistent UI/UX patterns

---

## Risk Mitigation

| Risk | Mitigation | Story |
|------|-----------|-------|
| Breaking health dashboard | Careful testing of all tabs | UI1.1, UI1.5 |
| ai-automation-ui still doesn't work | Systematic debugging checklist | UI1.2 |
| API connectivity issues | Multiple networking solutions | UI1.2 |
| User confusion | Clear documentation | UI1.3 |
| Missing features in ai-automation-ui | Feature parity check | UI1.2 |

---

## Rollback Plan

If issues arise:
1. Keep AIAutomationTab.tsx in git history
2. Can re-add tab to health-dashboard if needed
3. Document any discovered limitations
4. Consider merge back to single UI if separation doesn't work

---

## Definition of Done (Epic Level)

### All Stories Complete:
- [ ] All 5 stories marked as "Done"
- [ ] All acceptance criteria met
- [ ] All tests passing

### System Functional:
- [ ] Health dashboard (port 3000) has 12 tabs
- [ ] AI automation UI (port 3001) fully functional
- [ ] Both UIs accessible and working
- [ ] Cross-navigation works

### Quality Gates:
- [ ] No console errors
- [ ] All health checks pass
- [ ] API calls successful from both UIs
- [ ] Documentation updated
- [ ] Mobile responsive

### Documentation:
- [ ] README updated
- [ ] User manual updated
- [ ] Architecture docs updated
- [ ] Completion report created

---

## Implementation Order

### Phase 1: Quick Win (Day 1 - 4 hours)
1. **UI1.1**: Remove AI Automation tab (2-3h)
   - Immediate cleanup of health-dashboard
   - Removes confusion

### Phase 2: Core Fix (Day 1-2 - 6 hours)
2. **UI1.2**: Fix ai-automation-ui (4-6h)
   - Critical path item
   - Enables full Epic completion

### Phase 3: Polish (Day 2 - 3 hours)
3. **UI1.3**: Update documentation (2-3h)
4. **UI1.4**: Add cross-navigation (2-3h)

### Phase 4: Validation (Day 2-3 - 3 hours)
5. **UI1.5**: E2E testing (2-3h)

**Total Timeline:** 2-3 days with careful testing

---

## Related Epics

- **Epic AI-1**: AI Automation Suggestion System (provides ai-automation-ui features)
- **Epic 13**: API Layer Separation (separated admin-api and data-api)
- **Epic 17**: Enhanced Monitoring (health-dashboard features)

---

## References

- **PRD**: `docs/prd/ai-automation/epic-ai1-summary.md`
- **Architecture**: `docs/architecture/source-tree.md`
- **Docker Compose**: `docker-compose.yml`
- **Health Dashboard**: `services/health-dashboard/`
- **AI Automation UI**: `services/ai-automation-ui/`
- **AI Automation Service**: `services/ai-automation-service/`

---

**Epic Status:** Ready for Implementation  
**Created:** 2025-10-16  
**Priority:** High (Production Stabilization)  
**Estimated Completion:** 2-3 days

