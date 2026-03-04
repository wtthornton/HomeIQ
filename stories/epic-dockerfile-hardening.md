---
epic: dockerfile-hardening
priority: high
status: open
estimated_duration: "1 week"
risk_level: low
source: docker-breakout-initiative
type: infrastructure
---

# Epic 23: Dockerfile Security & Consistency Hardening

**Status:** Open
**Priority:** P1 High
**Duration:** 1 week
**Risk Level:** Low (each change is isolated to one Dockerfile; no cross-service impact)
**Source:** Docker breakout initiative — Dockerfile audit findings
**Affects:** 13 Dockerfiles across 6 domains

## Context

The Dockerfile audit found three categories of inconsistency across the 49 service Dockerfiles:

**Security (P1):**
- 2 services run as root (`energy-forecasting`, `rule-recommendation-ml`)
- 4 device-management services have no `HEALTHCHECK` in Dockerfile
- 3 Dockerfiles install `requirements.txt` before shared libs (fragile ordering)

**Consistency (P2):**
- 3 services use UID 1000 instead of the standard 1001
- 3 services use single-stage builds instead of multi-stage
- 2 services use `httpx` for health checks instead of standard `curl`
- 1 service missing `EXPOSE` directive
- 2 entrypoint scripts have CRLF line endings (Windows artifact)

---

## Stories

### Story 23.1: Fix Root-User Dockerfiles — `energy-forecasting` and `rule-recommendation-ml`

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Low

**Problem:** Both services copy packages to `/root/.local` and never set a `USER` directive. They run as root in production, violating container security best practices.

**Files:**
- `domains/energy-analytics/energy-forecasting/Dockerfile`
- `domains/blueprints/rule-recommendation-ml/Dockerfile`

**Acceptance Criteria:**
- [ ] Both Dockerfiles add `RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup` (or slim equivalent)
- [ ] Package paths updated from `/root/.local` to `/home/appuser/.local`
- [ ] `USER appuser` added before `CMD`
- [ ] `ENV PATH=/home/appuser/.local/bin:$PATH` updated
- [ ] `docker run --rm {image} id` shows `uid=1001(appuser)` for both
- [ ] Both services still pass their health check endpoints after rebuild

---

### Story 23.2: Add `HEALTHCHECK` to 4 Device-Management Dockerfiles

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** `device-context-classifier`, `device-health-monitor`, `device-recommender`, `device-setup-assistant` have health checks only in `compose.yml`, not in the Dockerfile itself. Images built for CI/deployment have no health probe.

**Files:**
- `domains/device-management/device-context-classifier/Dockerfile` (port 8020)
- `domains/device-management/device-health-monitor/Dockerfile` (port 8019)
- `domains/device-management/device-recommender/Dockerfile` (port 8023)
- `domains/device-management/device-setup-assistant/Dockerfile` (port 8021)

**Acceptance Criteria:**
- [ ] All 4 Dockerfiles gain `HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{PORT}/health')"` (using urllib since curl is not installed in Alpine)
- [ ] `docker inspect` shows healthcheck defined for each image

---

### Story 23.3: Standardize UID to 1001 — 3 Services

**Priority:** P2 Medium | **Estimate:** 2h | **Risk:** Low

**Problem:** `blueprint-suggestion-service`, `blueprint-index`, and `ha-setup-service` use UID 1000 while all other services use UID 1001.

**Files:**
- `domains/blueprints/blueprint-suggestion-service/Dockerfile`
- `domains/blueprints/blueprint-index/Dockerfile`
- `domains/device-management/ha-setup-service/Dockerfile`

**Acceptance Criteria:**
- [ ] All 3 Dockerfiles updated to UID/GID 1001
- [ ] `chown` calls reference user by name (not numeric UID) — verify no breakage
- [ ] `docker run --rm {image} id` shows `uid=1001(appuser)` for all 3

---

### Story 23.4: Convert 3 Single-Stage Builds to Multi-Stage

**Priority:** P2 Medium | **Estimate:** 4h | **Risk:** Low

**Problem:** `automation-linter`, `blueprint-suggestion-service`, and `blueprint-index` use single-stage builds. Build tools (gcc, build-essential) remain in the final image, bloating size and attack surface.

**Files:**
- `domains/automation-core/automation-linter/Dockerfile`
- `domains/blueprints/blueprint-suggestion-service/Dockerfile`
- `domains/blueprints/blueprint-index/Dockerfile`

**Acceptance Criteria:**
- [ ] All 3 converted to `python:3.12-slim AS builder` + `python:3.12-slim AS production` pattern
- [ ] Shared libs installed before `requirements.txt` in builder stage (correct order)
- [ ] Final images are smaller than single-stage equivalents
- [ ] All services pass health checks after rebuild

---

### Story 23.5: Fix Reversed Install Order in 3 Dockerfiles

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** `automation-linter`, `device-database-client`, and `ai-code-executor` install `requirements.txt` BEFORE shared libs. Since requirements may depend on shared libs, this ordering is fragile and may break when lib versions diverge.

**Files:**
- `domains/automation-core/automation-linter/Dockerfile`
- `domains/device-management/device-database-client/Dockerfile`
- `domains/automation-core/ai-code-executor/Dockerfile`

**Acceptance Criteria:**
- [ ] Install order in each Dockerfile is: `COPY libs/` → `pip install libs` → `COPY requirements.txt` → `pip install -r requirements.txt`
- [ ] `docker build` succeeds for all 3 after reorder
- [ ] Coordinate with Story 23.4 for `automation-linter` (apply to multi-stage builder)

---

### Story 23.6: Replace `httpx` Health Checks with `curl`

**Priority:** P2 Medium | **Estimate:** 1h | **Risk:** Low

**Problem:** `automation-linter` and `ai-code-executor` use `python -c "import httpx; ..."` for `HEALTHCHECK`. This depends on `httpx` being installed and the `python -c` exit code behavior is unreliable.

**Files:**
- `domains/automation-core/automation-linter/Dockerfile` (slim, has curl)
- `domains/automation-core/ai-code-executor/Dockerfile` (Alpine, has curl via `apk add`)

**Acceptance Criteria:**
- [ ] Both Dockerfiles: `HEALTHCHECK CMD` changed to `CMD curl -f http://localhost:{PORT}/health || exit 1`
- [ ] Verify `curl` is installed in the runtime stage of each Dockerfile
- [ ] Both services pass health probes after restart

---

### Story 23.7: Add `EXPOSE 8017` to `energy-correlator` Dockerfile

**Priority:** P2 Medium | **Estimate:** 30min | **Risk:** Low

**Problem:** `energy-correlator/Dockerfile` has a `HEALTHCHECK` and `CMD` on port 8017 but no `EXPOSE` directive.

**File:** `domains/energy-analytics/energy-correlator/Dockerfile`

**Acceptance Criteria:**
- [ ] `EXPOSE 8017` added before `CMD`
- [ ] `docker inspect` shows port 8017 in `ExposedPorts`

---

### Story 23.8: Fix CRLF Entrypoint Scripts + Add `.gitattributes` Rule

**Priority:** P2 Medium | **Estimate:** 1h | **Risk:** Low

**Problem:** `ha-ai-agent-service/docker-entrypoint.sh` and `automation-miner/docker-entrypoint.sh` have CRLF line endings. Both Dockerfiles already work around this with `sed -i 's/\r$//'`, but the source files should be clean.

**Files:**
- `domains/automation-core/ha-ai-agent-service/docker-entrypoint.sh`
- `domains/blueprints/automation-miner/docker-entrypoint.sh`
- `.gitattributes` (root)

**Acceptance Criteria:**
- [ ] Both `.sh` files converted to LF line endings
- [ ] `.gitattributes` at repo root includes `*.sh text eol=lf` to prevent future CRLF commits
- [ ] `file` command reports "ASCII text" (not "with CRLF line terminators") for both

---

## Summary

| Story | Description | Est. | Risk |
|-------|-------------|------|------|
| 23.1 | Fix root-user Dockerfiles (energy-forecasting, rule-recommendation-ml) | 3h | Low |
| 23.2 | Add `HEALTHCHECK` to 4 device-management Dockerfiles | 2h | Low |
| 23.3 | Standardize UID to 1001 (3 services) | 2h | Low |
| 23.4 | Convert 3 single-stage builds to multi-stage | 4h | Low |
| 23.5 | Fix reversed install order in 3 Dockerfiles | 2h | Low |
| 23.6 | Replace `httpx` health checks with `curl` | 1h | Low |
| 23.7 | Add `EXPOSE 8017` to `energy-correlator` | 30min | Low |
| 23.8 | Fix CRLF entrypoint scripts + `.gitattributes` | 1h | Low |
| **Total** | | **~15.5h** | |

## Dependencies

- Stories are largely independent and can be parallelized
- 23.4 and 23.5 should be coordinated for `automation-linter` (multi-stage + install order in same PR)
- 23.3 should complete before or alongside 23.4 (UID standardization before multi-stage conversion)
- No external epic dependencies — can run in parallel with Epics 21 and 22
