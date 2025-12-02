# Scripts Cleanup Analysis

**Date:** December 2025  
**Purpose:** Identify scripts that are no longer relevant and can be deleted  
**Status:** Review Complete

---

## Executive Summary

After reviewing all scripts in the `scripts/` directory, I've identified **47 scripts** that are either obsolete, reference deprecated services, or were for one-time migrations/fixes that are complete. These are organized into categories below.

---

## 🚨 HIGH PRIORITY - Delete Immediately

### Scripts Referencing Deprecated enrichment-pipeline Service (Epic 31)

**Reason:** enrichment-pipeline service was deprecated in Epic 31 (October 2025). The architecture now uses direct InfluxDB writes from websocket-ingestion.

1. **`validate-optimized-images.sh`** - References enrichment-pipeline in services list (line 41) and tests it (lines 87-97)
2. **`validate-optimized-images.ps1`** - PowerShell version with same issues
3. **`execute-influxdb-reset.sh`** - References enrichment-pipeline in stop/start services (lines 154, 160, 292-293, 363-368)
4. **`validate-deployment.ps1`** - Validates enrichment-pipeline health endpoint (line 10)
5. **`deploy.sh`** - References enrichment-pipeline logs directory (line 119) and service name (line 199)
6. **`deploy.ps1`** - PowerShell version with same issues (lines 129, 221)
7. **`deploy-wizard.sh`** - Sets ENRICHMENT_PIPELINE_PORT=8002 (line 706)
8. **`analyze-code-quality.sh`** - Lists enrichment-pipeline as a service (line 225)

**Current Architecture (Epic 31):**
- ❌ OLD: HA → websocket-ingestion → enrichment-pipeline → InfluxDB
- ✅ NEW: HA → websocket-ingestion → InfluxDB (direct)

---

## 📋 MEDIUM PRIORITY - Review & Delete if Complete

### One-Time Migration/Deployment Scripts

9. **`deploy_and_test_phase1.py`** - Phase 1 deployment script (likely complete)
10. **`deploy-phase4-enhancements.ps1`** - Phase 4 deployment script (likely complete)
11. **`verify-epic-ai3-deployment.ps1`** - Epic AI-3 verification (likely complete)
12. **`verify-epic41-dependencies.py`** - Epic 41 dependency verification (one-time migration)
13. **`deploy_home_type_integration.sh`** - Home type integration deployment (one-time)
14. **`deploy_home_type_integration.ps1`** - PowerShell version
15. **`verify_home_type_integration.py`** - Home type verification (one-time check)

**Note:** These may have been for specific epics/phases that are complete. Verify completion status before deleting.

### Pattern/Synergy Testing Scripts (Feature May Be Deprecated)

16. **`clear_pattern_synergy_data.py`** - Clears pattern/synergy data from database
17. **`run_pattern_synergy_tests.py`** - Runs pattern/synergy tests
18. **`query_patterns_synergies.py`** - Queries pattern/synergy data
19. **`verify_synergies_fix.py`** - Verifies synergy fixes
20. **`analyze_synergy_data.py`** - Analyzes synergy data

**Note:** Verify if pattern/synergy features are still active before deleting.

---

## 🔍 LOW PRIORITY - Archive or Update

### Test/Validation Scripts for Specific Features

21. **`test_ask_ai_hue_lights.py`** - Specific test for Hue lights (may still be useful)
22. **`test_device_name_flow.py`** - Device name flow test (may still be useful)
23. **`test_full_flow.py`** - Full flow test (may still be useful)
24. **`test_existing_suggestion.py`** - Suggestion test (may still be useful)
25. **`test_http_discovery.py`** - HTTP discovery test (may still be useful)
26. **`test_real_query.py`** - Real query test (may still be useful)
27. **`test_exact_analysis_query.py`** - Analysis query test (may still be useful)
28. **`evaluate-conversational-system.ps1`** - Conversational system evaluation (may still be useful)

**Recommendation:** Keep these if they're still used in testing. Archive if not.

### Setup/Configuration Scripts (May Be Superseded)

29. **`setup-openvino-models.py`** - OpenVINO model setup (check if still needed)
30. **`setup-downsampling-schedule.py`** - InfluxDB downsampling setup (may be in service now)
31. **`setup-influxdb-ai5-buckets.sh`** - Epic AI5 bucket setup (one-time migration)
32. **`setup-nlevel-windows.ps1`** - N-level setup (check if still needed)
33. **`verify-nlevel-setup.py`** - N-level verification (check if still needed)

**Recommendation:** Review if functionality moved to services or is no longer needed.

### Analysis/Diagnostic Scripts (May Be Obsolete)

34. **`analyze_device_matching_fix.py`** - One-time analysis for device matching fix
35. **`analyze_missing_suggestions.py`** - Analysis for missing suggestions
36. **`analyze_device_type_event_frequency.py`** - Device type event frequency analysis
37. **`analyze_datasets.py`** - Dataset analysis (may still be useful)
38. **`analyze_production_ha_events.py`** - Production HA events analysis (may still be useful)
39. **`fetch_suggestion_debug_data.py`** - Suggestion debug data fetcher (may still be useful)

**Recommendation:** Keep diagnostic scripts if they're still used. Delete one-time fix analysis scripts.

### Database Fix/Migration Scripts (One-Time Fixes)

40. **`fix_duplicate_automations.py`** - Fix for duplicate automations (one-time fix)
41. **`fix_database_quality.py`** - Database quality fixes (may have been one-time)
42. **`fix_influxdb_quality.py`** - InfluxDB quality fixes (may have been one-time)
43. **`fix_influxdb_retention_api.py`** - InfluxDB retention API fixes (may have been one-time)
44. **`fix_influxdb_retention.sh`** - InfluxDB retention fixes (may have been one-time)
45. **`fix-b904-helper.ps1`** - B904 bug fix helper (one-time fix)
46. **`fix-external-data-sources-env.py`** - External data sources env fix (may be one-time)

**Recommendation:** Delete if fixes are complete and applied.

### Deployment Scripts (May Be Superseded)

47. **`deploy-enhanced-fallback.ps1`** - Enhanced fallback deployment (check if still needed)
48. **`deploy-enhanced-fallback.sh`** - Shell version
49. **`deploy-with-fallback.ps1`** - Deployment with fallback (check if still needed)
50. **`deploy-with-fallback.sh`** - Shell version
51. **`deploy-with-validation.ps1`** - Deployment with validation (may be superseded by prepare_for_production.py)
52. **`deploy-with-validation.sh`** - Shell version

**Recommendation:** Review if superseded by `prepare_for_production.py` or newer deployment scripts.

---

## ✅ KEEP - Still Relevant

### Core Production Scripts
- `prepare_for_production.py` - Main production readiness pipeline
- `deploy.sh` / `deploy.ps1` - Core deployment scripts (needs update to remove enrichment-pipeline)
- `simple-unit-tests.py` - Unit test runner
- `validate-services.sh` - Service validation
- `validate-production-deployment.sh` - Production deployment validation

### Database Management
- `backup-all.sh` - Backup scripts
- `sqlite_maintenance.py` - SQLite maintenance
- `check_database_quality.py` - Database quality checks
- `validate-databases.sh` - Database validation

### Testing & Training
- `run_full_test_and_training.py` - Full test and training pipeline
- `train_soft_prompt.py` - Model training
- `test_service_startup.py` - Service startup tests

### Active Development Tools
- `validate_imports.py` - Import validation
- `monitor_query_performance.py` - Query performance monitoring
- `check_openai_rate_limits.py` - Rate limit checking

---

## 📝 Recommended Actions

### Immediate Actions (Delete Now)

1. **Update core deployment scripts** to remove enrichment-pipeline references:
   - `deploy.sh` - Remove enrichment-pipeline from logs and services
   - `deploy.ps1` - Same updates
   - `deploy-wizard.sh` - Remove ENRICHMENT_PIPELINE_PORT

2. **Delete obsolete validation scripts**:
   - `validate-optimized-images.sh` (and .ps1)
   - `validate-deployment.ps1` (or update to remove enrichment-pipeline)
   - `execute-influxdb-reset.sh` (or update to remove enrichment-pipeline)
   - `analyze-code-quality.sh` (update service list)

### Review & Delete (After Verification)

3. **One-time migration scripts** - Verify completion, then delete:
   - Phase 1/4 deployment scripts
   - Epic-specific verification scripts
   - Home type integration scripts (if complete)

4. **Pattern/synergy scripts** - Verify feature status:
   - If feature deprecated, delete all pattern/synergy scripts
   - If still active, keep testing scripts

5. **One-time fix scripts** - Delete after confirming fixes applied:
   - Device matching fix scripts
   - Database quality fix scripts
   - Bug fix helpers (B904, etc.)

### Archive (Move to Archive Directory)

6. **Create `scripts/archive/` directory** and move:
   - Historical deployment scripts
   - Completed migration scripts
   - Obsolete test scripts

---

## Summary Statistics

- **Total Scripts Reviewed:** ~150+
- **Scripts to Delete:** 47
- **Scripts to Update:** 8 (remove enrichment-pipeline references)
- **Scripts to Keep:** ~100+

**Breakdown:**
- High Priority (Delete Now): 8 scripts
- Medium Priority (Review & Delete): 15 scripts
- Low Priority (Archive or Update): 24 scripts

---

## Next Steps

1. **Review this list** with the team
2. **Verify completion status** of one-time migration/fix scripts
3. **Update core scripts** to remove enrichment-pipeline references
4. **Delete confirmed obsolete scripts**
5. **Archive historical scripts** to `scripts/archive/`
6. **Update scripts/README.md** to reflect current scripts

---

**Last Updated:** December 2025  
**Reviewer:** AI Assistant  
**Status:** Ready for Review

