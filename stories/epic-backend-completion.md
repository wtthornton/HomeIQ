---
epic: backend-completion
priority: high
status: ml-complete
estimated_duration: 2-3 weeks
risk_level: high
source: rebuild-status.md, phase-3-readiness-report.md, test stub audit
---

# Epic: Backend Completion (ML Upgrades, Test Stubs)

**Status:** ML Stories Complete (Stories 1-4) | Test Stories Pending (Stories 5-7)
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** ~~High~~ Mitigated — ML upgrades complete, models regenerated
**Predecessor:** Epic sqlite-removal (complete)
**Affects:** 4 ML services, 11+ test suites

**Note:** SQLite removal is complete (Epic 0). PostgreSQL is the sole database.

## ML Upgrade Summary (Completed March 6, 2026)

| Component | Previous | Current |
|-----------|----------|---------|
| numpy | 1.26.x | **2.4.2** |
| scipy | 1.13.x | **1.17.1** |
| pandas | 2.x | **3.0.1** |
| scikit-learn | 1.7.2 | **1.8.0** |
| Model Version | 1.0.1 | **1.0.2** |
| Model Accuracy | 99.5% | **100%** |

**Backup:** `backups/ml-models/20260306_104119` (46 files, 12.07 MB)

## Context

Two categories of backend work:
1. ✅ **Phase 3** — ML/AI library upgrades (numpy 2.4.2, pandas 3.0.1, scikit-learn 1.8.0) — **COMPLETE**
2. ⬜ **Test debt** — ~60 unimplemented test stubs and 6 fully-skipped test suites — **PENDING**

## Stories

### Story 1: Phase 3 Prerequisites ✅ COMPLETE

**Priority:** High | **Estimate:** 4h | **Risk:** Low
**Completed:** March 6, 2026

**Tasks:**
- ✅ Run rollback script: `.\scripts\backup-ml-models.ps1` (PowerShell)
- ✅ Baseline metrics collected (99.5% accuracy baseline)
- ✅ Update `device-intelligence-service` requirements.txt

**Acceptance Criteria:**
- [x] Rollback script successfully backs up all 46 `.pkl` model files (12.07 MB)
- [x] Baseline metrics collected (99.5% accuracy)
- [x] Requirements updated to pinned versions
- [x] Backup location: `backups/ml-models/20260306_104119`

---

### Story 2: ML Library Upgrades — numpy & scipy ✅ COMPLETE

**Priority:** High | **Estimate:** 3 days | **Risk:** High
**Completed:** March 6, 2026

**Services:** ml-service, ai-pattern-service, device-intelligence-service

**Upgraded versions:** numpy 1.26.x → **2.4.2**, scipy 1.13.x → **1.17.1**

**Breaking changes audit:** No deprecated APIs found in codebase
- ✅ No `np.string_` usage
- ✅ No `np.bool` alias usage
- ✅ No `DataFrame.append()` usage (pandas 3.0)

**Acceptance Criteria:**
- [x] numpy and scipy upgraded in all 3 ML services
- [x] All numpy deprecation warnings resolved (none found)
- [x] dtype compatibility verified
- [x] Docker images rebuilt successfully
- [x] No version compatibility warnings in runtime

---

### Story 3: ML Library Upgrades — pandas 3.0 ✅ COMPLETE

**Priority:** High | **Estimate:** 2 days | **Risk:** Critical
**Completed:** March 6, 2026

**Services:** ai-pattern-service, device-intelligence-service

**Upgraded version:** pandas 2.x → **3.0.1**

**Breaking changes audit:**
- ✅ No `DataFrame.append()` usage found (all uses are `list.append()`)
- ✅ No `inplace=True` patterns found
- ✅ No deprecated aliases found

**Acceptance Criteria:**
- [x] pandas upgraded to 3.0.1 in both services
- [x] Breaking change audit completed (no issues found)
- [x] Docker images rebuilt successfully
- [x] Service starts without pandas warnings

---

### Story 4: ML Library Upgrades — scikit-learn 1.8 + Model Regeneration ✅ COMPLETE

**Priority:** High | **Estimate:** 3 days | **Risk:** Critical
**Completed:** March 6, 2026

**Services:** ml-service, ai-pattern-service, device-intelligence-service

**Upgraded version:** scikit-learn 1.7.2 → **1.8.0**

**Model regeneration:** All models regenerated with new scikit-learn version
- Model version: 1.0.1 → **1.0.2**
- Training date: 2026-03-06T19:01:22Z
- Accuracy: 99.5% → **100%** (exceeds baseline)

**Bug fix applied:** Fixed parameter mismatch in `predictive_analytics.py`
- `_use_scaled` → `use_scaled` in `_evaluate_models()` and `_validate_models()`

**Acceptance Criteria:**
- [x] scikit-learn upgraded to 1.8.0 in all 3 services
- [x] Models regenerated via `POST /api/predictions/train`
- [x] Model accuracy (100%) exceeds baseline (99.5%)
- [x] Rollback tested: `.\scripts\backup-ml-models.ps1 -RestoreLatest` works
- [x] No version compatibility warnings in container logs

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
