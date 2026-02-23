---
epic: validation-and-cleanup
priority: high
status: pending
estimated_duration: 3-5 days
risk_level: low
source: PRD – Domain Architecture Restructuring (Epic 5 of 5)
---

# Epic: Validation and Cleanup

**Status:** Pending
**Priority:** High
**Duration:** 3--5 days
**Risk Level:** Low
**PRD Reference:** `docs/planning/service-decomposition-plan.md`

## Overview

Final epic in the Domain Architecture Restructuring initiative. Epics 1--4 performed the structural migration: moving services into 9 domain groups, splitting shared libraries, rewriting Docker Compose and bake files, and updating Dockerfiles, imports, CI, and documentation. This epic validates that everything works end-to-end, cleans up migration artifacts, and ensures documentation accurately reflects the new structure.

**Predecessor Epics:**
1. **Epic 1** -- Moved all services into `domains/` (9 groups)
2. **Epic 2** -- Split `shared/` into `libs/` (5 packages)
3. **Epic 3** -- Rewrote all Docker Compose files + added `docker-bake.hcl`
4. **Epic 4** -- Updated all Dockerfiles, imports, CI pipelines, and docs

## Objectives

1. Verify zero regressions from the restructuring across builds, runtime, and tests
2. Clean up all migration artifacts (old directories, symlinks, temp files)
3. Ensure documentation accurately reflects the new 9-domain structure
4. Confirm TAPPS quality gates pass on all modified code

## Success Criteria

- [ ] All 50+ Docker images build successfully via `docker buildx bake full`
- [ ] All services start and pass health checks via `docker compose up -d`
- [ ] All 152+ shared pattern tests pass; all per-service unit tests pass
- [ ] End-to-end flows work (HA -> websocket-ingestion -> InfluxDB -> data-api -> health-dashboard)
- [ ] No references to old `services/` flat layout remain in code or docs
- [ ] Architecture documentation is complete and accurate
- [ ] TAPPS quality gates pass on all modified Python files

---

## User Stories

### Story 1: Run Full Docker Build

**As a** platform engineer
**I want** all 50+ service images to build successfully via `docker buildx bake full`
**So that** I can confirm the restructured Dockerfiles, build contexts, and dependency paths are correct

**Acceptance Criteria:**
- [ ] `docker buildx bake full` completes without errors
- [ ] All 50+ service images are present in `docker image ls`
- [ ] Image sizes are within expected ranges (no bloated layers from broken COPY paths)
- [ ] Multi-stage builds complete correctly (builder and runtime stages)
- [ ] Any build failures are diagnosed, fixed, and re-verified

**Story Points:** 5
**Dependencies:** Epics 1--4 (all structural changes complete)
**Affected Services:** All 50+ services

---

### Story 2: Run Full Docker Stack

**As a** platform engineer
**I want** the full Docker stack to start and all services to report healthy
**So that** I can confirm inter-service communication, port mappings, volume mounts, and environment variables are correct after restructuring

**Acceptance Criteria:**
- [ ] `docker compose up -d` starts all services without exit codes
- [ ] All services pass their `/health` endpoint checks within 60 seconds
- [ ] Inter-service communication works (e.g., websocket-ingestion writes to InfluxDB, data-api reads from InfluxDB)
- [ ] Volume mounts resolve correctly under the new directory structure
- [ ] Environment variables and secrets are injected correctly
- [ ] No services are in restart loops or CrashLoopBackOff

**Story Points:** 5
**Dependencies:** Story 1 (images must build first)
**Affected Services:** All 50+ services

---

### Story 3: Run All Test Suites

**As a** developer
**I want** all unit and integration test suites to pass
**So that** I can confirm the import rewrites, shared library splits, and path changes introduced no regressions

**Acceptance Criteria:**
- [ ] 152+ shared pattern tests pass (`libs/homeiq-patterns/tests/`)
- [ ] Per-service unit tests pass for all services with test suites
- [ ] Integration tests pass where applicable
- [ ] No import errors (`ModuleNotFoundError`, `ImportError`) in any test
- [ ] Any test failures are diagnosed, fixed, and re-verified
- [ ] Test runner output is saved as an artifact for audit

**Story Points:** 5
**Dependencies:** Epics 1--4 (all structural changes complete)
**Affected Services:** All services with test suites, `libs/homeiq-patterns/`

---

### Story 4: Run All E2E Tests

**As a** platform engineer
**I want** end-to-end data flows to work correctly
**So that** I can confirm the restructuring did not break the critical path from Home Assistant to the health dashboard

**Acceptance Criteria:**
- [ ] HA -> websocket-ingestion -> InfluxDB write path works
- [ ] InfluxDB -> data-api query path returns correct data
- [ ] data-api -> health-dashboard rendering path works
- [ ] Admin API CRUD operations function correctly
- [ ] Any existing E2E test scripts pass
- [ ] Manual smoke test of 3+ representative automations succeeds

**Story Points:** 5
**Dependencies:** Story 2 (full stack must be running)
**Affected Services:** websocket-ingestion (8001), data-api (8006), InfluxDB (8086), health-dashboard (3000), admin-api (8003)

---

### Story 5: Verify Git History Tracking

**As a** developer
**I want** `git log --follow` to correctly track file renames from the restructuring
**So that** I can trace the history of any file back to its pre-migration location

**Acceptance Criteria:**
- [ ] `git log --follow` on 5 representative moved files shows history before and after the move
- [ ] Files tested include: 1 Tier 1 service, 1 shared lib module, 1 Dockerfile, 1 test file, 1 compose file
- [ ] Rename detection threshold is documented (Git default 50% similarity)
- [ ] Any files that lost history are documented with workaround instructions

**Story Points:** 1
**Dependencies:** Epic 1 (services moved into `domains/`)
**Affected Services:** None (git metadata only)

---

### Story 6: Clean Up Deprecated Artifacts

**As a** developer
**I want** all migration artifacts removed from the repository
**So that** the codebase is clean and there is no confusion between old and new paths

**Acceptance Criteria:**
- [ ] Old `services/` flat directory is removed (if not already handled by Epic 1)
- [ ] Old `compose/` directory is removed (if not already handled by Epic 3)
- [ ] Any temporary migration scripts or files are deleted
- [ ] Old symlinks pointing to pre-migration paths are removed
- [ ] `.gitignore` is updated if any new patterns are needed
- [ ] `grep -r "services/" docs/` returns zero hits for old flat paths (only `domains/` paths remain)

**Story Points:** 2
**Dependencies:** Stories 1--4 (must confirm everything works before deleting old artifacts)
**Affected Services:** None (repository cleanup)

---

### Story 7: Update service-decomposition-plan.md

**As a** project manager
**I want** the service decomposition plan updated to reflect the completed migration
**So that** the PRD accurately records what was done, serves as a historical reference, and links to the new structure

**Acceptance Criteria:**
- [ ] All completed phases are marked as done with completion dates
- [ ] The 9-domain group structure is documented with service counts per group
- [ ] Links to all 5 epic files are included (Epics 1--5)
- [ ] Any deviations from the original plan are documented with rationale
- [ ] "Lessons Learned" section is added
- [ ] Document serves as a complete historical record of the migration

**Story Points:** 3
**Dependencies:** Stories 1--4 (validation results needed for accurate status)
**Affected Services:** None (documentation only)

---

### Story 8: Create New Architecture Documentation

**As a** developer onboarding to HomeIQ
**I want** a canonical `docs/architecture/domain-structure.md` reference
**So that** I can quickly understand the 9-domain structure, find any service, and know how the system is organized

**Acceptance Criteria:**
- [ ] Document created at `docs/architecture/domain-structure.md`
- [ ] All 9 domains described with purpose and scope
- [ ] Every service listed under its domain with port number and brief description
- [ ] Dependency graph showing inter-domain communication patterns
- [ ] Compose file locations mapped to domains
- [ ] CI pipeline mapping: which pipelines build which domains
- [ ] Directory tree showing the top-level structure
- [ ] Cross-referenced from README.md and architecture docs

**Story Points:** 5
**Dependencies:** Stories 1--4 (final structure must be validated)
**Affected Services:** None (documentation only)

---

### Story 9: Update Developer Onboarding Docs

**As a** new developer joining the HomeIQ project
**I want** README.md and getting-started guides to reference the new folder structure
**So that** I can set up my development environment and navigate the codebase without confusion

**Acceptance Criteria:**
- [ ] `README.md` updated with new directory structure and quick-start commands
- [ ] `CONTRIBUTING.md` updated (if it exists) with new file placement guidelines
- [ ] Any getting-started guides reference `domains/` instead of `services/`
- [ ] Docker Compose commands reference new file locations
- [ ] Development workflow section updated (how to build, test, deploy a single domain)
- [ ] All path examples in docs use the new structure

**Story Points:** 3
**Dependencies:** Story 8 (architecture docs provide the canonical reference)
**Affected Services:** None (documentation only)

---

### Story 10: Create Migration Verification Checklist

**As a** developer verifying the restructuring
**I want** a runnable markdown checklist that validates every aspect of the migration
**So that** anyone can independently confirm the restructuring is complete and correct

**Acceptance Criteria:**
- [ ] Checklist created at `docs/architecture/migration-verification-checklist.md`
- [ ] Service count assertions: expected count per domain vs actual
- [ ] Docker build checks: all images build, correct tags
- [ ] Import resolution checks: no `ModuleNotFoundError` across codebase
- [ ] CI trigger checks: correct paths in CI config for each domain
- [ ] Path reference checks: no stale `services/` references in code or docs
- [ ] Health check verification: all `/health` endpoints respond
- [ ] Checklist is self-contained and can be run by any team member

**Story Points:** 2
**Dependencies:** Stories 1--4 (must know what to verify)
**Affected Services:** None (documentation only)

---

### Story 11: Update MEMORY.md and CLAUDE.md

**As a** AI assistant (Claude) working on the HomeIQ codebase
**I want** MEMORY.md and CLAUDE.md updated with correct paths and structure notes
**So that** future AI-assisted sessions have accurate context about the codebase layout

**Acceptance Criteria:**
- [ ] All path references in MEMORY.md updated from `services/X` to `domains/group/X`
- [ ] All path references in CLAUDE.md updated to new structure
- [ ] Notes about the 9-domain structure added to MEMORY.md project overview
- [ ] References to old flat `services/` layout removed
- [ ] `libs/` package paths documented (replacing old `shared/` references)
- [ ] Key architecture insights section updated with domain groupings

**Story Points:** 2
**Dependencies:** Story 8 (architecture docs provide canonical reference for paths)
**Affected Services:** None (AI context files only)

---

### Story 12: Final TAPPS Validation

**As a** quality engineer
**I want** all modified Python files to pass TAPPS quality gates
**So that** the restructuring meets the project's code quality standards and no regressions were introduced

**Acceptance Criteria:**
- [ ] `tapps_validate_changed()` run on all modified Python files
- [ ] All files pass the "standard" quality gate preset (70+)
- [ ] No security scan findings (bandit + secret detection)
- [ ] `tapps_checklist(task_type="refactor")` confirms all pipeline steps were followed
- [ ] Any quality gate failures are fixed and re-validated
- [ ] Final TAPPS report saved as a migration artifact

**Story Points:** 3
**Dependencies:** All other stories (this is the absolute final validation)
**Affected Services:** All services with modified Python files

---

## Dependencies

```
Epics 1-4 (prerequisite for all stories)
        |
        v
Story 1 (Docker Build)
        |
        v
Story 2 (Docker Stack)
        |
        v
Story 4 (E2E Tests)
        |
        +---> Stories 6-11 (parallelizable after validation)
        |
        v
Story 12 (Final TAPPS Validation)

Story 3 (Test Suites)     -- independent of Stories 1-2, depends on Epics 1-4
Story 5 (Git History)     -- independent, depends on Epic 1 only

Dependency detail:
  Story 1 ──> Story 2 ──> Story 4 ──┐
  Story 3 (parallel with 1-2) ──────┤
  Story 5 (parallel with 1-4) ──────┤
                                     ├──> Story 6  (Cleanup)
                                     ├──> Story 7  (Update PRD)
                                     ├──> Story 8  (Architecture Docs)
                                     ├──> Story 10 (Verification Checklist)
                                     │
                                     └──> Story 8 ──> Story 9  (Onboarding Docs)
                                                  ──> Story 11 (MEMORY.md / CLAUDE.md)

  All Stories ──> Story 12 (Final TAPPS Validation)
```

## Suggested Execution Order

**Phase 1 -- Build and Runtime Validation (sequential):**
1. **Story 1** -- Full Docker build (`docker buildx bake full`)
2. **Story 2** -- Full Docker stack (`docker compose up -d` + health checks)

**Phase 2 -- Test Validation (parallel with Phase 1 where possible):**
3. **Story 3** -- All test suites (can start as soon as Epics 1--4 are done)
4. **Story 4** -- E2E tests (requires Story 2 stack running)
5. **Story 5** -- Git history verification (independent, can run anytime)

**Phase 3 -- Cleanup and Documentation (parallelizable):**
6. **Story 6** -- Clean up deprecated artifacts
7. **Story 7** -- Update service-decomposition-plan.md
8. **Story 8** -- Create domain-structure.md architecture reference
9. **Story 10** -- Create migration verification checklist

**Phase 4 -- Dependent Documentation:**
10. **Story 9** -- Update developer onboarding docs (after Story 8)
11. **Story 11** -- Update MEMORY.md and CLAUDE.md (after Story 8)

**Phase 5 -- Final Gate:**
12. **Story 12** -- Final TAPPS validation (absolute last step)

## Agent Team Strategy

**Recommended team structure for parallel execution:**

| Agent | Role | Stories | Notes |
|-------|------|---------|-------|
| **Agent 1 (Build Lead)** | Docker build + stack validation | Stories 1, 2, 4 | Sequential -- must complete in order |
| **Agent 2 (Test Lead)** | Test suite execution + git verification | Stories 3, 5 | Can run in parallel with Agent 1 |
| **Agent 3 (Docs Lead)** | Documentation and cleanup | Stories 6, 7, 8, 9, 10, 11 | Starts after Phase 2 completes |
| **Agent 4 (Quality Watchdog)** | TAPPS validation | Story 12 | Runs last; monitors all other agents' output |

**Coordination rules:**
- Agents 1 and 2 start immediately (parallel)
- Agent 3 starts after Agents 1 and 2 confirm all builds and tests pass
- Agent 4 runs `tapps_validate_changed()` only after all other agents complete
- Any agent finding a regression files a blocking issue and notifies the Build Lead

## Implementation Artifacts

| Artifact | Path | Story |
|----------|------|-------|
| Docker build log | (stdout artifact) | 1 |
| Docker stack health report | (stdout artifact) | 2 |
| Test suite results | (stdout artifact) | 3 |
| E2E test results | (stdout artifact) | 4 |
| Git history verification | (stdout artifact) | 5 |
| Architecture reference | `docs/architecture/domain-structure.md` | 8 |
| Migration verification checklist | `docs/architecture/migration-verification-checklist.md` | 10 |
| Updated PRD | `docs/planning/service-decomposition-plan.md` | 7 |
| Updated README | `README.md` | 9 |
| Updated MEMORY.md | MEMORY.md (user private) | 11 |
| Updated CLAUDE.md | `CLAUDE.md` | 11 |
| TAPPS validation report | (stdout artifact) | 12 |

---

## References

- [PRD: Service Decomposition Plan](../docs/planning/service-decomposition-plan.md)
- [Services Ranked by Importance](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md)
- [Architecture Quick Reference](../docs/architecture/README_ARCHITECTURE_QUICK_REF.md)
- [Event Flow Architecture](../docs/architecture/event-flow-architecture.md)
- [Shared Patterns README](../libs/homeiq-patterns/README.md)
