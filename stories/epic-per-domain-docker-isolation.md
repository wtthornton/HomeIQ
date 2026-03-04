---
epic: per-domain-docker-isolation
priority: high
status: complete
estimated_duration: "1 week"
risk_level: low
source: docker-breakout-initiative
type: infrastructure
---

# Epic 21: Per-Domain Docker Desktop Isolation

**Status:** Complete (Mar 4, 2026)
**Priority:** P1 High
**Duration:** 1 week
**Risk Level:** Low (compose `name:` directive is additive; no existing behavior changes when running from root)
**Source:** Docker breakout initiative
**Affects:** All 9 domain `compose.yml` files, `docker-bake.hcl`

## Context

When all services are started via the root `docker-compose.yml` (`name: homeiq`), Docker Desktop groups every container under one "homeiq" project. The goal is for each domain to appear as its own named group (e.g., `homeiq-data-collectors`) so operators can start, stop, and inspect domains independently from Docker Desktop.

The mechanism: add a `name:` directive to each domain `compose.yml`. When run standalone with `docker compose -f domains/{domain}/compose.yml up -d`, Docker uses that name. When run via the root `docker-compose.yml`, the `include:` directive's parent `name: homeiq` takes precedence — so full-stack behavior is unchanged.

**The network bootstrap problem:** All 8 non-core-platform domains declare `homeiq-network` as `external: true`. Standalone startup fails if core-platform hasn't created the network. A lightweight `ensure-network.sh` helper solves this.

**Build context mismatch:** Two frontend services (`health-dashboard`, `ai-automation-ui`) use different build contexts in compose vs `docker-bake.hcl`, causing inconsistent build behavior depending on which tool is used.

---

## Stories

### Story 21.1: Add `name:` Directives to All 9 Domain Compose Files

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** No domain `compose.yml` has a `name:` directive. Docker Desktop groups all containers under "homeiq" when run via root compose. Running standalone produces directory-derived names (e.g., "core-platform") which lack the `homeiq-` prefix.

**Scope:** All 9 `domains/*/compose.yml` files

**Acceptance Criteria:**
- [ ] `domains/core-platform/compose.yml` gains `name: homeiq-core-platform` at top level
- [ ] `domains/data-collectors/compose.yml` gains `name: homeiq-data-collectors`
- [ ] `domains/ml-engine/compose.yml` gains `name: homeiq-ml-engine`
- [ ] `domains/automation-core/compose.yml` gains `name: homeiq-automation-core`
- [ ] `domains/blueprints/compose.yml` gains `name: homeiq-blueprints`
- [ ] `domains/energy-analytics/compose.yml` gains `name: homeiq-energy-analytics`
- [ ] `domains/device-management/compose.yml` gains `name: homeiq-device-management`
- [ ] `domains/pattern-analysis/compose.yml` gains `name: homeiq-pattern-analysis`
- [ ] `domains/frontends/compose.yml` gains `name: homeiq-frontends`
- [ ] `docker compose -f domains/data-collectors/compose.yml config` shows `name: homeiq-data-collectors`
- [ ] `docker compose config` from repo root still shows `name: homeiq`

---

### Story 21.2: Fix Missing `homeiq-` Container Name Prefixes

**Priority:** P1 High | **Estimate:** 1h | **Risk:** Low

**Problem:** Two containers break the `homeiq-` prefix convention:
- `pattern-analysis/compose.yml`: `container_name: ai-pattern-service` (missing prefix)
- `frontends/compose.yml`: `container_name: ai-automation-ui` (missing prefix)

**Acceptance Criteria:**
- [ ] `domains/pattern-analysis/compose.yml`: `container_name` changed to `homeiq-ai-pattern-service`
- [ ] `domains/frontends/compose.yml`: `container_name` changed to `homeiq-ai-automation-ui`
- [ ] Grep confirms no scripts/configs reference old container names

---

### Story 21.3: Create `scripts/ensure-network.sh` Bootstrap Helper

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** Starting any non-core-platform domain standalone fails with "network homeiq-network declared as external, but could not be found". No lightweight way to pre-create the network.

**Acceptance Criteria:**
- [ ] `scripts/ensure-network.sh` created — calls `docker network create homeiq-network --driver bridge` only if network doesn't exist
- [ ] Script is idempotent — running multiple times does not error
- [ ] Script is POSIX-compatible (`#!/bin/sh`)
- [ ] Script is executable (`chmod +x`)
- [ ] PowerShell equivalent `scripts/ensure-network.ps1` created for Windows

---

### Story 21.4: Align `health-dashboard` Build Context Between Compose and Bake

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** `core-platform/compose.yml` uses `context: health-dashboard` (service-relative), while `docker-bake.hcl` uses `context: "."` (repo root). Builds may produce different results.

**Acceptance Criteria:**
- [ ] `domains/core-platform/compose.yml` health-dashboard build updated to `context: ../..` with `dockerfile: domains/core-platform/health-dashboard/Dockerfile`
- [ ] Dockerfile `COPY` instructions audited and updated for repo-root context
- [ ] `docker compose -f domains/core-platform/compose.yml build health-dashboard` succeeds
- [ ] `docker buildx bake health-dashboard` succeeds
- [ ] Both produce functionally identical images

---

### Story 21.5: Align `ai-automation-ui` Build Context Between Compose and Bake

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** Same mismatch as Story 21.4 for `ai-automation-ui`. `frontends/compose.yml` uses `context: ai-automation-ui` while bake uses `context: "."`.

**Acceptance Criteria:**
- [ ] `domains/frontends/compose.yml` ai-automation-ui build updated to `context: ../..` with `dockerfile: domains/frontends/ai-automation-ui/Dockerfile`
- [ ] Dockerfile `COPY` instructions audited and updated for repo-root context
- [ ] `docker compose -f domains/frontends/compose.yml build ai-automation-ui` succeeds
- [ ] `docker buildx bake ai-automation-ui` succeeds

---

## Summary

| Story | Description | Est. | Risk |
|-------|-------------|------|------|
| 21.1 | Add `name:` directives to all 9 domain compose files | 2h | Low |
| 21.2 | Fix 2 missing `homeiq-` container name prefixes | 1h | Low |
| 21.3 | Create `ensure-network.sh` bootstrap helper | 2h | Low |
| 21.4 | Align `health-dashboard` build context (compose vs bake) | 2h | Low |
| 21.5 | Align `ai-automation-ui` build context (compose vs bake) | 2h | Low |
| **Total** | | **~9h** | |

## Dependencies

- Epic 21 has no external dependencies — implement first
- Stories 21.4 and 21.5 depend on 21.1 (add name directives first)
- Epic 24 (deployment tooling) depends on Story 21.3 (ensure-network.sh)
- Epic 22 (volume decoupling) depends on Story 21.1 (name directives needed for predictable volume prefixes)
