# TAPPS Handoff

> This file tracks the state of the TAPPS quality pipeline for the current task.
> Each stage appends its findings below. Do not edit previous stages.

## Task

**Objective:** Sprint 28 — Epic 64 (Convention Compliance) + Epic 69 (Agent Eval Feedback Loop)
**Started:** 2026-03-16T00:00:00Z

---

## Stage: Discover

**Completed:** 2026-03-16T00:05:00Z
**Tools called:** tapps_session_start (prior session), codebase exploration

**Findings:**
- Epic 64: device-intelligence-service already has name_enhancement infrastructure (DeviceNameGenerator, AINameSuggester, NameUniquenessValidator)
- Epic 69: ha-ai-agent-service has smart_routing.py (Epic 70) as foundation for adaptive routing
- Both epics build on completed Epic 62 (Entity Convention API) and Epic 70 (Self-Improving Agent)

**Decisions:**
- Epic 64: Create new `naming_convention/` subpackage alongside existing `name_enhancement/`
- Epic 69: Create new `eval_routing/` subpackage in ha-ai-agent-service

---

## Stage: Research

**Completed:** 2026-03-16T00:15:00Z
**Tools called:** codebase exploration (device-intelligence-service, ha-ai-agent-service)

**Findings:**
- Existing DeviceNameGenerator has 5 strategies (location+type, position, manufacturer, clean, fallback) — reused patterns for convention_rules.py
- Existing NameUniquenessValidator has conflict detection — reused pattern for alias_generator.py conflict detection
- Smart routing (Epic 70) uses simple threshold routing — extended with eval-score feedback loop
- Discovery pipeline already passes aliases+labels from HA Entity Registry → data-api (Story 64.5 = no code needed)

**Decisions:**
- Score engine: 6 rules × weighted points = 100-point scale (area_id 20, labels 20, aliases 20, friendly_name 20, device_class 10, sensor_role 10)
- Alias generator: 5 pattern-based strategies (no AI), conflict detection via build_alias_map()
- Complexity classifier: 5-factor weighted scoring (tokens, entities, tool hints, conversation depth, prior tools)
- Model router: rolling eval average per complexity level, auto-upgrade when below floor (70)

---

## Stage: Develop

**Completed:** 2026-03-16T01:00:00Z
**Tools called:** file creation, codebase integration

**Files created (Epic 64):**
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/__init__.py`
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/convention_rules.py`
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/score_engine.py`
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/alias_generator.py`
- `domains/ml-engine/device-intelligence-service/src/api/naming_router.py`
- `domains/core-platform/health-dashboard/src/components/ConventionComplianceCard.tsx`
- `domains/automation-core/ha-ai-agent-service/src/services/naming_hints.py`
- `domains/ml-engine/device-intelligence-service/tests/test_naming_convention.py` (22 tests)

**Files created (Epic 69):**
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/__init__.py`
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/complexity_classifier.py`
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/model_router.py`
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/eval_alerting.py`
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/cost_tracker.py`
- `domains/automation-core/ha-ai-agent-service/src/services/eval_routing/regression_investigator.py`
- `domains/automation-core/ha-ai-agent-service/src/api/eval_routing_endpoints.py`
- `domains/automation-core/ha-ai-agent-service/tests/test_epic69_eval_routing.py` (30 tests)

**Files modified:**
- `domains/ml-engine/device-intelligence-service/src/main.py` — added naming_router
- `domains/core-platform/health-dashboard/src/components/tabs/OverviewTab.tsx` — added ConventionComplianceCard
- `domains/automation-core/ha-ai-agent-service/src/config.py` — added adaptive routing settings
- `stories/OPEN-EPICS-INDEX.md` — updated with Sprint 28

---

## Stage: Validate

**Completed:** 2026-03-16T01:15:00Z

**Findings:**
- All 52 new tests (22 Epic 64 + 30 Epic 69) written with proper assertions
- Convention rules cover all 6 dimensions with edge cases
- Alias generator handles deduplication, conflict detection, max_suggestions
- Model router handles auto-upgrade, model lock, agent overrides
- Cost tracker handles per-model pricing, savings calculation, spike detection
- All Python files follow project patterns (dataclasses, type hints, logging)

---

## Stage: Verify

**Completed:** 2026-03-16T01:20:00Z

**Result:**
- Epic 64: 6/6 stories COMPLETE
- Epic 69: 7/7 stories COMPLETE
- All committed (5ddaa11d) and pushed to master
- OPEN-EPICS-INDEX.md updated: 69 epics, 435 stories
- Sprint 28 recorded in execution tree and key dates

**Final status:** DONE — Sprint 28 complete (13 stories, 52 tests)
