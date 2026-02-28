---
epic: backend-completion
priority: high
status: open
estimated_duration: 2-3 weeks
risk_level: high
source: rebuild-status.md, phase-3-readiness-report.md, test stub audit
---

# Epic: Backend Completion (ML Upgrades, Test Stubs)

**Status:** Open
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** High — ML library upgrades require model regeneration
**Predecessor:** Epic sqlite-removal (complete)
**Affects:** 4 ML services, 11+ test suites

**Note:** SQLite removal is complete (Epic 0). PostgreSQL is the sole database.

## Context

Two categories of backend work remain:
1. **Phase 3** — ML/AI library upgrades (numpy 2.4, pandas 3, scikit-learn 1.8)
2. **Test debt** — ~60 unimplemented test stubs and 6 fully-skipped test suites

## Stories

### Story 1: Phase 3 Prerequisites (Pre-Mar 11)

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Problem:** 3 of 8 Phase 3 prerequisites are not yet met.

**Tasks:**
- Run rollback script dry-run: `./scripts/rollback-ml-upgrade.sh backup`
- Set up isolated testing venv with current library versions + baseline metrics
- Update `device-intelligence-service` pandas pin from `<3.0.0` to `<4.0.0`

**Acceptance Criteria:**
- [ ] Rollback script successfully backs up all 36 `.pkl` model files
- [ ] Baseline metrics collected (inference latency, accuracy for each ML service)
- [ ] pandas pin updated in `domains/device-management/device-intelligence-service/requirements.txt`
- [ ] All 8 prerequisites documented as MET in `docs/planning/phase-3-readiness-report.md`

---

### Story 2: ML Library Upgrades — numpy & scipy

**Priority:** High | **Estimate:** 3 days | **Risk:** High

**Services:** ml-service, ai-pattern-service, device-intelligence-service

**Target versions:** numpy 1.26.x → 2.4.2, scipy 1.13.x → 1.17.0

**Key breaking changes (numpy 2.x):**
- `np.string_` removed → use `np.bytes_`
- `np.bool` alias removed → use `np.bool_` or builtin `bool`
- Default integer dtype may differ on some platforms
- C API changes affect compiled extensions

**Acceptance Criteria:**
- [ ] numpy and scipy upgraded in all 3 ML services
- [ ] All numpy deprecation warnings resolved
- [ ] dtype compatibility verified for all data pipelines
- [ ] Unit tests pass in all 3 services
- [ ] Baseline inference latency within 10% of pre-upgrade

---

### Story 3: ML Library Upgrades — pandas 3.0

**Priority:** High | **Estimate:** 2 days | **Risk:** Critical

**Services:** ai-pattern-service, device-intelligence-service

**Key breaking changes (pandas 3.0):**
- Default string dtype changes (backed by PyArrow)
- `DataFrame.append()` removed
- `inplace` parameter removed from many methods
- Copy-on-write becomes default
- Many deprecated aliases removed

**Acceptance Criteria:**
- [ ] pandas upgraded to 3.0.x in both services
- [ ] All `DataFrame.append()` calls replaced with `pd.concat()`
- [ ] String dtype handling verified (explicit `dtype="string"` where needed)
- [ ] All `inplace=True` patterns replaced with assignment
- [ ] Data pipeline outputs verified identical pre/post upgrade

---

### Story 4: ML Library Upgrades — scikit-learn 1.8 + Model Regeneration

**Priority:** High | **Estimate:** 3 days | **Risk:** Critical

**Services:** ml-service, ai-pattern-service, device-intelligence-service

**Critical:** All 36 `.pkl` model files in `device-intelligence-service` must be
regenerated after scikit-learn upgrade. joblib serialization is NOT cross-version compatible.

**Acceptance Criteria:**
- [ ] scikit-learn upgraded to 1.8.x in all 3 services
- [ ] All 36 `.pkl` model files regenerated with new scikit-learn
- [ ] Model accuracy compared to baseline (must be within 2%)
- [ ] Rollback script tested: `./scripts/rollback-ml-upgrade.sh restore` works
- [ ] tiktoken upgraded to 0.12.0 in ha-ai-agent-service

---

### Story 5: Fix Skipped Test Suites (6 services)

**Priority:** Medium | **Estimate:** 1 day | **Risk:** Low

**Problem:** 6 services have entire test suites skipped via `pytest.skip(allow_module_level=True)`
due to missing dependencies in CI:
- `websocket-ingestion` — broken import path for InfluxDB client test (300 lines of tests dead)
- `data-retention` — `influxdb_client_3` not installed
- `carbon-intensity-service` — missing optional dependency
- `weather-api` — missing optional dependency
- `ha-setup-service` — missing optional dependency
- `device-intelligence-service` — missing optional dependency

**Acceptance Criteria:**
- [ ] Dependencies added to CI requirements or conftest skips narrowed to specific tests
- [ ] `websocket-ingestion` test import path fixed to current module
- [ ] All 6 test suites actually execute in CI (not silently skipped)
- [ ] Test count increase documented (expect 50-100+ newly-running tests)

---

### Story 6: Implement Test Stubs — Automation Core (42 stubs)

**Priority:** Medium | **Estimate:** 2 days | **Risk:** Low

**Problem:** 42+ `# TODO: Implement test` stubs with `pass` bodies across automation-core services.

**Files and stubs:**
- `ai-automation-service-new/tests/clients/test_openai_client.py` — 6 stubs
- `ai-automation-service-new/tests/services/test_yaml_generation_service.py` — 9 stubs
- `ai-automation-service-new/tests/tests/test_test_suggestion_router.py` — 1 stub
- `ai-automation-service-new/tests/test_performance.py` — 1 skipped test
- `ha-ai-agent-service/tests/services/validation/test_ai_automation_validation_strategy.py` — 1 duplicate (shadows real test)
- `ha-ai-agent-service/tests/services/validation/test_yaml_validation_strategy.py` — 1 duplicate
- `yaml-validation-service/tests/test_normalizer_choose_fix.py` — 8 stubs (+ broken import path)
- `ai-query-service/tests/test_performance.py` — 3 skipped tests
- `ai-query-service/tests/test_query_router.py` — 1 skipped test

**Acceptance Criteria:**
- [ ] All stubs replaced with real assertions (or deleted if test is a duplicate/meta-wrapper)
- [ ] Duplicate `test_name` methods in ha-ai-agent-service fixed (delete shadowing duplicates)
- [ ] Broken import path in yaml-validation-service fixed
- [ ] Performance test skips converted to proper `@pytest.mark.slow` markers
- [ ] All new tests pass in CI

---

### Story 7: Implement Test Stubs — Pattern Analysis (13 stubs)

**Priority:** Medium | **Estimate:** 1 day | **Risk:** Low

**Files:**
- `ai-pattern-service/tests/pattern_analyzer/test_filters.py` — 8 stubs (pure functions, easily testable)
- `ai-pattern-service/tests/api/test_synergy_router.py` — 1 stub
- `ai-pattern-service/tests/tests/test_test_e2e_patterns_synergies.py` — 4 meta-test stubs (likely delete)

**Acceptance Criteria:**
- [ ] Filter function tests implemented with real assertions
- [ ] Synergy router test implemented
- [ ] Meta-test wrapper file deleted (autogenerated scaffolding, not useful)
- [ ] All tests pass in CI
