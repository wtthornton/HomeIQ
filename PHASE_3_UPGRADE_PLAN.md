# Phase 3 AI/ML Stack Upgrade Plan

**Status:** In Progress - Option C Testing
**Date:** November 15, 2025
**Phase:** 3 of 4 (Dependency Upgrade Initiative)

---

## Executive Summary

Phase 3 involves upgrading AI/ML dependencies with **HIGH RISK** due to potential embedding incompatibility. We're following a cautious, data-driven approach:

1. **Option C (Current):** Test sentence-transformers compatibility first
2. **Option B (Next):** Upgrade all AI/ML EXCEPT sentence-transformers
3. **Option A (Final):** Add sentence-transformers if tests pass

---

## Option C: Embedding Compatibility Testing (IN PROGRESS)

### Objective
Determine if upgrading `sentence-transformers` from 3.3.1 to 5.1.2 maintains embedding consistency.

### Test Coverage
- **35 test sentences** covering HomeIQ use cases
- **all-MiniLM-L6-v2** model (384-dimensional embeddings)
- **Cosine similarity analysis** between versions
- **Automated testing** with clear pass/fail criteria

### Decision Criteria

| Similarity Range | Decision | Action |
|------------------|----------|--------|
| >= 0.999 | ✅ Excellent | Proceed with full Phase 3A |
| >= 0.99 | ✓ Good | Proceed with Phase 3A + optional re-indexing |
| >= 0.95 | ⚠️ Acceptable | Phase 3B first, then 3A with re-indexing |
| < 0.95 | ❌ Poor | Phase 3B only, pin sentence-transformers |

### Test Artifacts
- `test_embedding_consistency.py` - Main test script
- `run_embedding_test.sh` - Automated runner
- `EMBEDDING_TEST_README.md` - Complete documentation
- `embedding_tests/` - Output directory (created during test)

### Status
🔄 **Running automated test** - ETA 5-10 minutes

Results will determine next steps.

---

## Option B: Safe AI/ML Updates (READY)

### Objective
Update all AI/ML packages EXCEPT sentence-transformers to minimize risk.

### Packages to Update

| Package | Current | Target | Risk | Services |
|---------|---------|--------|------|----------|
| scikit-learn | 1.4.2 | 1.7.2 | 🟡 MEDIUM | 3 |
| spacy | 3.7.2 | 3.8.9 | 🟢 LOW | 1 |
| transformers | 4.46.1 | 4.57.1 | 🟡 MEDIUM | 2 |
| torch | 2.3.1+cpu | 2.9.1+cpu | 🟡 MEDIUM | 2 |
| openvino | 2024.6.0 | 2025.3.0 | 🟡 MEDIUM | 1 |
| optimum-intel | 1.21.0 | 1.26.1 | 🟡 MEDIUM | 1 |

### sentence-transformers Strategy

**Pin to current version:**
```python
sentence-transformers>=3.3.1,<4.0.0  # Pinned - see EMBEDDING_TEST_README.md
```

This prevents accidental upgrades while keeping other improvements.

### Affected Services
- `ai-automation-service` (6 packages)
- `openvino-service` (5 packages)
- `ml-service` (1 package: scikit-learn)
- `device-intelligence-service` (1 package: scikit-learn)

### Testing Requirements
- ML model loading and inference
- NER performance
- Clustering algorithms
- Pattern detection
- Device intelligence features

### Status
⏳ **Waiting for Option C results** - Branch creation ready

---

## Option A: Full AI/ML Upgrade (CONDITIONAL)

### Objective
Complete Phase 3 by adding sentence-transformers 5.1.2 if compatibility tests pass.

### Packages to Add

| Package | Current | Target | Risk | Condition |
|---------|---------|--------|------|-----------|
| sentence-transformers | 3.3.1 | 5.1.2 | 🔴 HIGH | Test passes |

### Triggers

**Proceed if:**
- Option C test shows similarity >= 0.99
- Option B deployed and tested successfully
- Team approves based on test results

**Skip if:**
- Option C test shows similarity < 0.95
- Business risk too high
- Re-indexing effort not acceptable

### Re-indexing Plan (if needed)

If similarity is 0.95-0.99, plan re-indexing:

1. **Stored Embeddings Inventory**
   - Device descriptions
   - Automation patterns
   - User queries
   - Template library

2. **Re-indexing Process**
   - Generate new embeddings with 5.1.2
   - Update database entries
   - Verify functionality
   - Monitor performance

3. **Timeline**
   - Analysis: 1 week
   - Implementation: 2 weeks
   - Testing: 1 week
   - **Total:** 4 weeks

### Status
⏳ **Waiting for Option C and Option B** - Branch creation ready

---

## Rollout Timeline

### Week 1 (Current)
- ✅ Phase 1 Complete - Security updates
- ✅ Phase 2 Complete - Framework updates
- 🔄 Option C - Embedding tests running
- 📅 Option C - Analyze results

### Week 2
- 📅 Option B - Create branch and implement
- 📅 Option B - Test AI/ML functionality
- 📅 Option B - Create PR and merge
- 📅 Decision point: Proceed with Option A?

### Week 3 (if Option A approved)
- 📅 Option A - Update sentence-transformers
- 📅 Option A - Comprehensive testing
- 📅 Option A - Create PR

### Week 4 (if Option A approved)
- 📅 Option A - Merge and deploy
- 📅 Monitor production performance
- 📅 Complete Phase 3

---

## Risk Mitigation

### Option C Risks
- ✅ Mitigated: Automated testing with clear criteria
- ✅ Mitigated: Test uses HomeIQ-specific sentences
- ✅ Mitigated: Multiple similarity metrics

### Option B Risks
- ⚠️ scikit-learn: Pickled models may break
  - **Mitigation:** Re-train/re-save models
- ⚠️ torch: CPU wheel compatibility
  - **Mitigation:** Use `+cpu` index explicitly
- ⚠️ transformers: Tokenizer changes
  - **Mitigation:** Test NER and embeddings

### Option A Risks
- 🔴 Embedding incompatibility
  - **Mitigation:** Option C testing
- 🔴 Semantic search breaks
  - **Mitigation:** Comprehensive testing
- 🔴 Re-indexing required
  - **Mitigation:** Plan and resource allocation

---

## Success Criteria

### Option C Success
- ✅ Test completes without errors
- ✅ Clear similarity metrics generated
- ✅ Actionable recommendation provided

### Option B Success
- ✅ All services start successfully
- ✅ ML model loading works
- ✅ Pattern detection functional
- ✅ Device intelligence operational
- ✅ No errors in logs

### Option A Success
- ✅ Embeddings compatible (>= 0.99 similarity)
- ✅ Semantic search works correctly
- ✅ Pattern detection maintains accuracy
- ✅ No user-facing issues
- ✅ Performance maintained or improved

---

## Rollback Plan

### If Option B Fails
1. Revert to master branch
2. Investigate specific failure
3. Fix or defer problematic package
4. Retry with subset

### If Option A Fails
1. Keep Option B changes (safe)
2. Revert sentence-transformers to 3.3.1
3. Pin version to prevent auto-upgrade
4. Plan re-indexing effort or freeze indefinitely

---

## Decision Points

### After Option C
- **If Excellent (>= 0.999):** Proceed with Option B → Option A
- **If Good (>= 0.99):** Proceed with Option B → Option A (plan re-indexing)
- **If Acceptable (>= 0.95):** Proceed with Option B only, defer Option A
- **If Poor (< 0.95):** Proceed with Option B only, pin sentence-transformers

### After Option B
- **If Success:** Consider Option A (if tests passed)
- **If Partial Success:** Fix issues, retry
- **If Failure:** Rollback, analyze, defer Phase 3

### After Option A
- **If Success:** Complete Phase 3, move to Phase 4
- **If Failure:** Rollback to Option B state, pin sentence-transformers

---

## Communication Plan

### Stakeholders
- Development team
- DevOps
- ML team
- Product owner

### Updates
- Option C results → Email with recommendation
- Option B PR → Code review required
- Option A decision → Team meeting
- Phase 3 complete → Release notes

---

## Next Phase: Phase 4 Preview

After Phase 3 completes, Phase 4 addresses **breaking changes**:

- LangChain: 0.2.14 → 1.0.7 (MAJOR)
- OpenAI SDK: 1.40.2 → 2.8.0 (MAJOR)
- paho-mqtt: 1.6.1 → 2.1.0 (MAJOR)
- tenacity: 8.2.3 → 9.1.2 (MAJOR)
- docker: 6.1.3 → 7.1.0 (MAJOR)

**Timeline:** 4-6 weeks
**Risk:** HIGH - Breaking API changes

---

## References

- `DEPENDENCY_UPGRADE_REPORT.md` - Full analysis
- `EMBEDDING_TEST_README.md` - Test documentation
- `test_embedding_consistency.py` - Test script
- `embedding_tests/` - Test results (after running)

---

**Status:** ⏳ Awaiting Option C test results
**Next Action:** Analyze embedding test output and decide path forward
**Last Updated:** November 15, 2025
