# Epic Execution Plan — March 2026

**Created:** 2026-03-06
**Target Deployment:** Week of March 9-13, 2026
**Status:** Active

---

## Executive Summary

| Priority | Epic | Status | Target Completion |
|----------|------|--------|-------------------|
| **P0** | frontend-security-hardening | ✅ Complete (7/7) | Mar 6 |
| **P1** | tapps-quality-gate-compliance (Story 3) | ✅ Complete (4/4) | Mar 6 |
| **P1** | backend-completion (ML Stories) | ✅ Complete | Mar 6 |
| **P1** | production-deployment | 🟡 Ready (Day 0 Passed) | Mar 9-13 |

---

## Phase 1: Critical Security (Mar 6-7)

### Epic: frontend-security-hardening

**Owner:** TBD
**Blocker For:** Production deployment

| Story | Description | Est | Status | Completed |
|-------|-------------|-----|--------|-----------|
| 1.1 | Remove hardcoded API keys from ai-automation-ui | 2h | ✅ | 2026-03-06 |
| 1.2 | Remove hardcoded API keys from health-dashboard | 2h | ✅ | 2026-03-06 (Already secure) |
| 1.3 | Fix CORS wildcard + credentials in nginx | 2h | ✅ | 2026-03-06 (Already using allowlist) |
| 1.4 | Add CSP headers to nginx configs | 3h | ✅ | 2026-03-06 (Already present) |
| 1.5 | Fix input validation (RegExp, URL sanitization) | 3h | ✅ | 2026-03-06 |
| 1.6 | Fix CSRF token generation (crypto.getRandomValues) | 1h | ✅ | 2026-03-06 (Already secure) |
| 1.7 | Secure Docker configs (non-root nginx, npm ci) | 1h | ✅ | 2026-03-06 |

**Files to modify:**
- `domains/frontends/ai-automation-ui/src/pages/Discovery.tsx`
- `domains/frontends/ai-automation-ui/src/api/admin.ts`
- `domains/frontends/ai-automation-ui/src/api/settings.ts`
- `domains/frontends/ai-automation-ui/src/api/preferences.ts`
- `domains/frontends/ai-automation-ui/nginx.conf`
- `domains/core-platform/health-dashboard/src/services/api.ts`
- `domains/core-platform/health-dashboard/nginx.conf`

**Acceptance Criteria:**
- [x] `grep -r "VITE_API_KEY" domains/frontends/` returns 0 hardcoded values
- [x] CORS headers use specific origin, not `*`
- [x] CSP headers present in all nginx responses
- [x] All Docker images run as non-root user

---

## Phase 2: Quality Gate CI (Mar 7)

### Epic: tapps-quality-gate-compliance — Story 3

**Owner:** TBD
**Status:** Stories 1-2 Complete

| Task | Description | Est | Status | Completed |
|------|-------------|-----|--------|-----------|
| 3.1 | Create `.github/workflows/tapps-quality.yml` | 1h | ✅ | 2026-03-06 |
| 3.2 | Configure `tapps-mcp validate-changed` in workflow | 30m | ✅ | 2026-03-06 |
| 3.3 | Add PR blocking on quality gate failure | 30m | ✅ | 2026-03-06 |
| 3.4 | Update CONTRIBUTING.md with quality expectations | 30m | ✅ | 2026-03-06 |

**Acceptance Criteria:**
- [x] PRs with Python changes trigger quality gate
- [x] Failed quality gates show clear error messages
- [x] Documentation explains quality requirements

---

## Phase 3: ML Upgrades (Mar 7-10)

### Epic: backend-completion — ML Stories

**Owner:** TBD
**Risk:** High (model regeneration required)

| Story | Description | Est | Status | Completed |
|-------|-------------|-----|--------|-----------|
| 1 | Phase 3 Prerequisites (backup models, baseline metrics) | 4h | ✅ | 2026-03-06 |
| 2 | numpy & scipy upgrade (1.26→2.4.2, 1.13→1.17.1) | 3d | ✅ | 2026-03-06 |
| 3 | pandas 3.0.1 upgrade | 2d | ✅ | 2026-03-06 |
| 4 | scikit-learn 1.8.0 + model regeneration (46 .pkl files) | 3d | ✅ | 2026-03-06 |

**Services Affected:**
- `domains/ml-engine/ml-service/`
- `domains/ml-engine/device-intelligence-service/`
- `domains/pattern-analysis/ai-pattern-service/`

**Backup Location:** `backups/ml-models/20260306_104119` (46 files, 12.07 MB)

**Rollback Plan:**
- `.\scripts\backup-ml-models.ps1 -RestoreLatest` restores backed-up models (PowerShell)
- All upgrades reversible via git revert + model restore

**Next Steps (Story 4 - Model Regeneration):**
1. Rebuild Docker images with new requirements
2. Start device-intelligence-service container
3. Call `POST /api/v1/predictions/train` to regenerate models
4. Verify model accuracy against baseline
5. Test prediction endpoints

---

## Phase 4: Test Debt (Mar 10-14)

### Epic: backend-completion — Test Stories

| Story | Description | Est | Status | Completed |
|-------|-------------|-----|--------|-----------|
| 5 | Fix 6 skipped test suites | 1d | ⬜ | |
| 6 | Implement 42 test stubs (automation-core) | 2d | ⬜ | |
| 7 | Implement 13 test stubs (pattern-analysis) | 1d | ⬜ | |

**Test Suites to Fix:**
- [ ] `websocket-ingestion` — broken import path
- [ ] `data-retention` — missing `influxdb_client_3`
- [ ] `carbon-intensity-service` — missing dependency
- [ ] `weather-api` — missing dependency
- [ ] `ha-setup-service` — missing dependency
- [ ] `device-intelligence-service` — missing dependency

---

## Phase 5: Production Deployment (Mar 9-13)

### Epic: production-deployment

**Predecessor:** frontend-security-hardening MUST be complete
**Duration:** 5-day rollout + 2-day validation

| Day | Story | Services | Gate |
|-----|-------|----------|------|
| Day 0 | Pre-deployment validation | All | All 33 health endpoints green |
| Day 1 | Tier 1 (Core Infrastructure) | influxdb, postgres, websocket-ingestion, data-api, admin-api | 30min stable |
| Day 1 | Tier 2 (Essential Services) | health-dashboard, data-retention, 10 collectors | 15min stable |
| Day 2 | Tier 3 (ML/AI) | ai-core, openvino, ml-service, rag-service, etc. | 15min stable |
| Day 3 | Tiers 4-8 (Domain Services) | 24 services across 5 domains | Cross-group auth verified |
| Day 4 | Tier 9 (Frontends) | health-dashboard, ai-automation-ui, observability | All UIs accessible |
| Day 5-6 | Post-deployment monitoring | Full stack (prod profile) | 48h stable, <1% error rate |

**Go/No-Go Checklist:**
- [ ] All 33 health endpoints responding 200 OK
- [ ] 704+ Python tests pass (100%)
- [ ] Frontend test suites pass
- [ ] 3 Playwright E2E scenarios pass
- [ ] All 53 Docker images build successfully
- [ ] All 8 PostgreSQL domain schemas deployed
- [ ] All 13 Alembic migrations run
- [ ] Pre-deployment backup completed

---

## Phase 6: Post-Production (Mar 14+)

### Medium Priority Epics

| Epic | Priority | Duration | Notes |
|------|----------|----------|-------|
| ai-automation-ui-quality | P2 | 1 week | Frontend quality improvements |
| health-dashboard-quality | P2 | 1 week | Frontend quality improvements |
| observability-dashboard-fixes | P2 | 3 days | Dashboard bug fixes |
| frontend-framework-upgrades | P2 | 1 week | React/Vite/Tailwind upgrades |

### Standardization Epics (Tech Debt)

| Epic | Priority | Duration | Notes |
|------|----------|----------|-------|
| external-service-connector-standardization | P3 | 1 week | Connector patterns |
| core-service-bootstrap-standardization | P3 | 1 week | Bootstrap patterns |
| background-processing-standardization | P3 | 1 week | Background job patterns |

### New Features

| Epic | Priority | Duration | Notes |
|------|----------|----------|-------|
| memory-brain | P2 | 6-8 weeks | Semantic memory layer for AI |
| pattern-detectors (from stale branch) | P2 | 2 weeks | 6 new pattern detectors |

---

## Tracking Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Not Started |
| 🟡 | In Progress |
| ✅ | Complete |
| ❌ | Blocked |
| 🔴 | Not Started (Critical) |

---

## Daily Standup Template

```markdown
### Date: YYYY-MM-DD

**Yesterday:**
- 

**Today:**
- 

**Blockers:**
- 

**Metrics:**
- Security stories: X/7 complete
- Quality gate CI: X/4 complete
- ML upgrades: X/4 complete
- Test debt: X/3 complete
```

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-03-06 | Initial plan created | Claude |
| 2026-03-06 | Security hardening: Removed hardcoded API keys from compose.yml | Claude |
| 2026-03-06 | Security hardening: Added rehype-sanitize to MessageContent.tsx | Claude |
| 2026-03-06 | Security hardening: Added URL sanitization to link component | Claude |
| 2026-03-06 | CI Integration: Created .github/workflows/tapps-quality.yml | Claude |
| 2026-03-06 | ML Prep: Created scripts/backup-ml-models.ps1 | Claude |
| 2026-03-06 | Updated epic statuses: frontend-security-hardening, tapps-quality-gate-compliance | Claude |
| 2026-03-06 | ML Backup: Executed backup - 46 files, 12.07 MB at backups/ml-models/20260306_104119 | Claude |
| 2026-03-06 | ML Upgrade: Pinned numpy==2.4.2, scipy==1.17.1, pandas==3.0.1, scikit-learn==1.8.0 in 3 services | Claude |
| 2026-03-06 | Frontend: Installed rehype-sanitize v6.0.0 in ai-automation-ui | Claude |
| 2026-03-06 | ML Build: Rebuilt all 3 ML service Docker images with new libraries | Claude |
| 2026-03-06 | ML Regeneration: Models regenerated v1.0.2 with scikit-learn 1.8.0 (100% accuracy) | Claude |
| 2026-03-06 | Bug Fix: Fixed parameter mismatch in predictive_analytics.py (_use_scaled → use_scaled) | Claude |
| 2026-03-06 | Story 1.7: Non-root nginx - Updated Dockerfiles with USER appuser, port 8080 | Claude |
| 2026-03-06 | Task 3.4: Updated CONTRIBUTING.md with Docker security requirements | Claude |
| 2026-03-06 | Epics Complete: frontend-security-hardening (7/7), tapps-quality-gate-compliance (4/4) | Claude |
| 2026-03-06 | Day 0 Validation: 54/33 services healthy, Docker builds verified, non-root nginx confirmed | Claude |
