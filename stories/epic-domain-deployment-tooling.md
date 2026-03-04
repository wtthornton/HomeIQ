---
epic: domain-deployment-tooling
priority: high
status: complete
estimated_duration: "1 week"
risk_level: low
source: docker-breakout-initiative
type: infrastructure
---

# Epic 24: Domain Deployment Tooling

**Status:** Complete (Mar 4, 2026)
**Priority:** P1 High
**Duration:** 1 week
**Risk Level:** Low (new scripts only — no existing behavior modified except deploy-phase-5.sh enhancement)
**Source:** Docker breakout initiative
**Affects:** `scripts/` directory

## Context

The Docker breakout requires new tooling to replace the root `docker-compose.yml` as the primary way to manage services:

1. **`scripts/deploy.sh` is stale:** References port 8003 for admin-api (correct: 8004), uses "HA Ingestor" branding, and targets the pre-domain-split layout. Confusing for developers.

2. **No per-domain convenience scripts:** Starting just data-collectors requires: `docker compose -f domains/data-collectors/compose.yml up -d`. No shortcut exists.

3. **No ordered multi-domain startup:** Starting all 9 domains as separate Docker Desktop groups in the correct dependency order requires 9 manual commands. `deploy-phase-5.sh` is close but doesn't pre-create the network or validate core-platform health.

---

## Stories

### Story 24.1: Archive Stale `scripts/deploy.sh`

**Priority:** P1 High | **Estimate:** 1h | **Risk:** Low

**Problem:** `scripts/deploy.sh` references outdated ports, wrong branding, and pre-domain-split layout. Keeping it visible is a trap for new contributors.

**Acceptance Criteria:**
- [ ] `scripts/deploy.sh` moved to `scripts/archive/deploy-legacy-pre-domain-split.sh`
- [ ] `scripts/archive/README.md` note added explaining these are deprecated scripts
- [ ] Grep confirms no CI workflows or docs reference `scripts/deploy.sh`

---

### Story 24.2: Create `scripts/domain.sh` — Per-Domain Helper

**Priority:** P1 High | **Estimate:** 4h | **Risk:** Low

**Problem:** No convenient wrapper for per-domain Docker operations.

**Accepted Design:**

```
Usage: ./scripts/domain.sh <command> <domain> [service]

Commands:
  start    Start a domain's services
  stop     Stop a domain's services
  restart  Restart a domain's services
  status   Show running containers
  logs     Tail service logs
  build    Build domain images via docker buildx bake
  list     Print valid domain names
```

**Acceptance Criteria:**
- [ ] `scripts/domain.sh` created with all subcommands
- [ ] Calls `ensure-network.sh` before `start` and `restart`
- [ ] Valid domains: `core-platform`, `data-collectors`, `ml-engine`, `automation-core`, `blueprints`, `energy-analytics`, `device-management`, `pattern-analysis`, `frontends`
- [ ] Invalid domain names print usage with valid options
- [ ] `./scripts/domain.sh start core-platform` creates network and starts core-platform
- [ ] PowerShell equivalent `scripts/domain.ps1` created for Windows
- [ ] `chmod +x scripts/domain.sh`

---

### Story 24.3: Create `scripts/start-stack.sh` — Ordered Multi-Domain Startup

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Low

**Problem:** No script starts all 9 domains as separate Docker Desktop groups in dependency order with health gates between tiers.

**Accepted Design:**

Startup order:
1. `core-platform` — wait for influxdb (8086) + data-api (8006) healthy
2. `data-collectors` — no wait (stateless, retries internally)
3. `ml-engine` — no wait
4. `automation-core` through `frontends` — no wait (all use retry logic)

**Acceptance Criteria:**
- [ ] `scripts/start-stack.sh` created
- [ ] Calls `ensure-network.sh` first
- [ ] Starts each domain using `docker compose -f domains/{name}/compose.yml up -d` in order
- [ ] After core-platform, polls `http://localhost:8086/health` (influxdb) and `http://localhost:8006/health` (data-api) with 60-second timeout
- [ ] Prints `[OK]` / `[WAITING]` / `[TIMEOUT]` status per gate
- [ ] `--skip-wait` flag starts all domains without health polling
- [ ] PowerShell equivalent `scripts/start-stack.ps1` created for Windows
- [ ] `chmod +x scripts/start-stack.sh`

---

### Story 24.4: Update `deploy-phase-5.sh` with Network Pre-Create and Health Gate

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** `scripts/deploy-phase-5.sh` doesn't pre-create `homeiq-network` before starting non-core-platform domains, and doesn't validate core-platform health before proceeding to tier 2.

**File:** `scripts/deploy-phase-5.sh`

**Acceptance Criteria:**
- [ ] Calls `scripts/ensure-network.sh` as first step in `deploy_tier1()` function
- [ ] After core-platform `docker compose up`, waits for influxdb and data-api to be healthy before advancing to tier 2
- [ ] Health gate uses existing `check_service_health()` function pattern
- [ ] `--help` output documents dependency on `ensure-network.sh`

---

### Story 24.5: Create `scripts/README.md` — Scripts Directory Documentation

**Priority:** P2 Medium | **Estimate:** 2h | **Risk:** Low

**Problem:** The `scripts/` directory has 200+ files with no index. New contributors can't find the right scripts.

**Acceptance Criteria:**
- [ ] `scripts/README.md` created with:
  - "Current Scripts" table: Script, Purpose, When to Use
  - "Archived Scripts" note pointing to `scripts/archive/`
  - Quick start examples for common operations
- [ ] `docs/README.md` updated with link to `scripts/README.md`

---

## Summary

| Story | Description | Est. | Risk |
|-------|-------------|------|------|
| 24.1 | Archive stale `scripts/deploy.sh` | 1h | Low |
| 24.2 | Create `scripts/domain.sh` per-domain helper | 4h | Low |
| 24.3 | Create `scripts/start-stack.sh` ordered startup | 3h | Low |
| 24.4 | Update `deploy-phase-5.sh` with network + health gates | 2h | Low |
| 24.5 | Create `scripts/README.md` | 2h | Low |
| **Total** | | **~12h** | |

## Dependencies

- Story 24.2 depends on Epic 21 Stories 21.1 (name directives) + 21.3 (ensure-network.sh)
- Story 24.3 depends on Story 24.2
- Story 24.4 depends on Story 21.3 (ensure-network.sh)
- Story 24.5 depends on 24.1–24.4 (document after scripts exist)
