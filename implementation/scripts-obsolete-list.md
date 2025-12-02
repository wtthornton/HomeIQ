# Obsolete Scripts - Delete List

**Date:** December 2025  
**Quick Reference:** List of scripts that can be safely deleted

---

## 🚨 DELETE IMMEDIATELY (8 scripts)

These scripts reference the deprecated enrichment-pipeline service (Epic 31):

1. ✅ `validate-optimized-images.sh` - Tests enrichment-pipeline
2. ✅ `validate-optimized-images.ps1` - PowerShell version
3. ✅ `execute-influxdb-reset.sh` - Starts/stops enrichment-pipeline
4. ✅ `validate-deployment.ps1` - Validates enrichment-pipeline health
5. ✅ `deploy.sh` - References enrichment-pipeline (needs update, not delete)
6. ✅ `deploy.ps1` - PowerShell version (needs update, not delete)
7. ✅ `deploy-wizard.sh` - Sets enrichment-pipeline port (needs update, not delete)
8. ✅ `analyze-code-quality.sh` - Lists enrichment-pipeline service

**Note:** Scripts 5-7 need updates (remove references) rather than deletion.

---

## 📋 DELETE AFTER VERIFICATION (24 scripts)

### One-Time Deployment Scripts
9. `deploy_and_test_phase1.py`
10. `deploy-phase4-enhancements.ps1`
11. `verify-epic-ai3-deployment.ps1`
12. `verify-epic41-dependencies.py`
13. `deploy_home_type_integration.sh`
14. `deploy_home_type_integration.ps1`
15. `verify_home_type_integration.py`

### Pattern/Synergy Scripts (Verify if feature still active)
16. `clear_pattern_synergy_data.py`
17. `run_pattern_synergy_tests.py`
18. `query_patterns_synergies.py`
19. `verify_synergies_fix.py`
20. `analyze_synergy_data.py`

### One-Time Fix Scripts (Verify fixes applied)
21. `fix_duplicate_automations.py`
22. `fix_database_quality.py`
23. `fix_influxdb_quality.py`
24. `fix_influxdb_retention_api.py`
25. `fix_influxdb_retention.sh`
26. `fix-b904-helper.ps1`
27. `analyze_device_matching_fix.py`

### Superseded Deployment Scripts
28. `deploy-enhanced-fallback.ps1`
29. `deploy-enhanced-fallback.sh`
30. `deploy-with-fallback.ps1`
31. `deploy-with-fallback.sh`
32. `deploy-with-validation.ps1` (may be superseded by prepare_for_production.py)
33. `deploy-with-validation.sh`

---

## 🔍 ARCHIVE OR UPDATE (15 scripts)

These may still have value but should be reviewed:

- `setup-influxdb-ai5-buckets.sh` - One-time Epic AI5 setup
- `setup-openvino-models.py` - Check if still needed
- `setup-downsampling-schedule.py` - May be in service now
- `setup-nlevel-windows.ps1` - Check if still needed
- `verify-nlevel-setup.py` - Check if still needed
- `test_ask_ai_hue_lights.py` - Specific test (may be useful)
- `test_device_name_flow.py` - Flow test (may be useful)
- `test_full_flow.py` - Integration test (may be useful)
- `test_existing_suggestion.py` - Suggestion test (may be useful)
- `test_http_discovery.py` - Discovery test (may be useful)
- `test_real_query.py` - Query test (may be useful)
- `test_exact_analysis_query.py` - Analysis test (may be useful)
- `evaluate-conversational-system.ps1` - Evaluation script (may be useful)
- `analyze_datasets.py` - Dataset analysis (may be useful)
- `analyze_production_ha_events.py` - Production analysis (may be useful)

---

## 📊 Summary

- **Delete Immediately:** 8 scripts (enrichment-pipeline references)
- **Delete After Verification:** 24 scripts (one-time migrations/fixes)
- **Archive or Review:** 15 scripts (may still be useful)
- **Total Candidate for Removal:** 47 scripts

---

## ✅ Action Items

1. **Update (don't delete)** these scripts to remove enrichment-pipeline:
   - `deploy.sh` - Remove lines 119, 199
   - `deploy.ps1` - Remove lines 129, 221
   - `deploy-wizard.sh` - Remove line 706

2. **Delete immediately:** Scripts 1-4, 8 (enrichment-pipeline validation)

3. **Verify & delete:** One-time migration/fix scripts (9-33)

4. **Archive:** Scripts that may have historical value but aren't actively used

---

**See detailed analysis:** `implementation/scripts-cleanup-analysis.md`

