---
epic: cross-domain-volume-decoupling
priority: high
status: open
estimated_duration: "1 week"
risk_level: medium
source: docker-breakout-initiative
type: infrastructure
---

# Epic 22: Cross-Domain Shared Resource Decoupling

**Status:** Open
**Priority:** P1 High
**Duration:** 1 week
**Risk Level:** Medium (volume renames require data awareness if volumes already have data)
**Source:** Docker breakout initiative
**Affects:** 6 domain `compose.yml` files

## Context

Three shared Docker volumes are declared (non-external) in multiple domain compose files. When domains run as separate projects (Epic 21), each creates its own project-prefixed copy of the volume instead of sharing one. This causes data isolation between domains that should share state.

**Current volume conflicts:**

| Volume | Declared In | Used By |
|--------|-------------|---------|
| `homeiq_logs` | core-platform, data-collectors, device-management | log-aggregator, websocket-ingestion |
| `ai_automation_data` | ml-engine, automation-core, pattern-analysis | ai-training, ai-automation, ai-pattern |
| `ai_automation_models` | ml-engine, automation-core | ai-training, ai-automation |

**Resolution strategy:** Designate one domain as the owner of each shared volume. Other consumers reference it as `external: true` with an environment-variable-driven name that defaults to the standalone name but can be overridden for full-stack use.

---

## Stories

### Story 22.1: Designate `homeiq_logs` Ownership and Add External References

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Medium

**Problem:** `homeiq_logs` is declared in three domain compose files. When domains run with separate project names, each creates its own namespaced volume instead of sharing one log volume.

**Accepted Design:**
- **Owner:** `core-platform/compose.yml` — keeps `homeiq_logs:` as a local volume declaration
- **Consumers:** `data-collectors/compose.yml` and `device-management/compose.yml` — change to `external: true` with `name: ${HOMEIQ_LOGS_VOLUME:-homeiq-core-platform_homeiq_logs}`
- Root `.env`: add `HOMEIQ_LOGS_VOLUME=homeiq_homeiq_logs` for full-stack usage

**Acceptance Criteria:**
- [ ] `core-platform/compose.yml` volumes: `homeiq_logs:` unchanged (local declaration)
- [ ] `data-collectors/compose.yml` volumes: `homeiq_logs:` becomes external with env-var name
- [ ] `device-management/compose.yml` volumes: same external reference
- [ ] Root `.env`: `HOMEIQ_LOGS_VOLUME=homeiq_homeiq_logs` added
- [ ] `docker compose -f domains/core-platform/compose.yml up -d` creates `homeiq-core-platform_homeiq_logs`
- [ ] `docker compose -f domains/data-collectors/compose.yml up -d` attaches to external volume
- [ ] `docker compose config` from root shows no volume conflicts

---

### Story 22.2: Designate `ai_automation_data` and `ai_automation_models` Ownership

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Medium

**Problem:** `ai_automation_data` is declared in ml-engine, automation-core, and pattern-analysis. `ai_automation_models` is declared in ml-engine and automation-core. These volumes hold AI model data and training artifacts shared between training and inference services.

**Accepted Design:**
- **Owner:** `ml-engine/compose.yml` — keeps both volumes as local declarations
- **Consumers:** `automation-core/compose.yml` and `pattern-analysis/compose.yml` — change to `external: true` with env-var names
- Root `.env`: add `AI_AUTOMATION_DATA_VOLUME` and `AI_AUTOMATION_MODELS_VOLUME`

**Acceptance Criteria:**
- [ ] `ml-engine/compose.yml` volumes: both volumes unchanged (local declarations)
- [ ] `automation-core/compose.yml` volumes: both changed to external with env-var names
- [ ] `pattern-analysis/compose.yml` volumes: `ai_automation_data` changed to external
- [ ] Root `.env`: volume name variables added
- [ ] `docker compose -f domains/ml-engine/compose.yml up -d` creates both volumes
- [ ] `docker compose -f domains/automation-core/compose.yml up -d` attaches to ml-engine's volumes

---

### Story 22.3: Document the Shared-Volume Contract

**Priority:** P2 Medium | **Estimate:** 2h | **Risk:** Low

**Problem:** Volume ownership decisions are architectural constraints that future contributors must understand. No documentation exists explaining the pattern.

**Acceptance Criteria:**
- [ ] `docs/docker-shared-resources.md` created with:
  - Table of all shared volumes: owner domain, consuming domains, env variable, standalone default name, full-stack name
  - The rule: "A volume must have exactly one owner domain. All other consumers declare it external."
  - Instructions for adding a new shared volume
- [ ] `docs/README.md` updated with link to new doc

---

## Summary

| Story | Description | Est. | Risk |
|-------|-------------|------|------|
| 22.1 | Designate `homeiq_logs` ownership + external references | 3h | Medium |
| 22.2 | Designate `ai_automation_data` + `ai_automation_models` ownership | 3h | Medium |
| 22.3 | Document shared-volume contract | 2h | Low |
| **Total** | | **~8h** | |

## Dependencies

- **Epic 21 Story 21.1** must complete first — `name:` directives are required for predictable project-prefixed volume names
- Stories 22.1 and 22.2 can be parallelized
- Story 22.3 depends on 22.1 and 22.2 (document what was decided)

## Risk Mitigation

- **Existing volume data:** If volumes already contain data under the old name, a one-time migration is needed: `docker volume create <new_name> && docker run --rm -v <old>:/from -v <new>:/to alpine cp -a /from/. /to/`. Document this in the shared-volume contract.
- **Full-stack regression:** The `.env` variables ensure that running via root `docker-compose.yml` uses the same volume names as before (no project prefix needed because the root project is `homeiq`).
