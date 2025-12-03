# Simulation Framework - Next Steps Plan

**Date:** December 3, 2025  
**Status:** ✅ **COMPLETE**  
**Context:** Post-Epic AI-18 completion, queries distribution fix

## Current State

✅ **Completed:**
- Epic AI-18 marked as COMPLETE
- Training data collection integrated
- Data validation and export working
- Queries distribution fixed (now across all homes)
- Data lineage tracking operational

## Plan Overview

### Phase 1: Comprehensive Data Collection
**Goal:** Collect substantial training data to meet retraining thresholds

**Actions:**
1. Run comprehensive simulation with optimal parameters
2. Verify data collection across all data types
3. Check data quality metrics
4. Validate data sufficiency for retraining

**Success Criteria:**
- All 5 data types collected (pattern, synergy, suggestion, YAML, Ask AI)
- Data quality >90% (per Epic AI-18 success criteria)
- Data volume meets minimum thresholds for at least one model type

### Phase 2: Data Sufficiency Verification
**Goal:** Verify collected data meets retraining requirements

**Actions:**
1. Check data counts per model type
2. Verify quality metrics
3. Run DataSufficiencyChecker for all models
4. Generate sufficiency report

**Success Criteria:**
- Identify which models can be retrained
- Document data gaps if any
- Provide clear recommendations

### Phase 3: Retraining Pipeline Test
**Goal:** Test end-to-end retraining pipeline

**Actions:**
1. Initialize RetrainingManager
2. Check retraining triggers
3. Execute retraining for eligible models (if any)
4. Verify model evaluation
5. Document results

**Success Criteria:**
- Retraining pipeline executes successfully
- Models are evaluated correctly
- No regressions detected

### Phase 4: Results & Recommendations
**Goal:** Document findings and provide next steps

**Actions:**
1. Generate comprehensive results report
2. Analyze data collection effectiveness
3. Provide recommendations for:
   - Simulation parameters optimization
   - Data collection improvements
   - Retraining frequency
   - Production integration

**Success Criteria:**
- Clear documentation of results
- Actionable recommendations
- Next steps identified

## Execution Plan

### Step 1: Run Comprehensive Simulation
```bash
python cli.py --mode standard --homes 50 --queries 20
```

**Expected Output:**
- 50 homes × 20 queries = 1,000 Ask AI queries
- Training data for all 5 types
- Data exported to `simulation/training_data/`

### Step 2: Verify Data Collection
- Check exported files
- Verify lineage database
- Count data per type

### Step 3: Check Data Sufficiency
- Use DataSufficiencyChecker
- Compare against thresholds:
  - GNN Synergy: 100 samples
  - Soft Prompt: 50 samples
  - Pattern Detection: 200 samples
  - YAML Generation: 100 samples

### Step 4: Test Retraining (if sufficient)
- Initialize RetrainingManager
- Check triggers
- Execute retraining (dry-run first)
- Evaluate results

### Step 5: Generate Report
- Document all findings
- Provide recommendations
- Identify next steps

## Risk Mitigation

1. **Insufficient Data:** Run larger simulation if needed
2. **Retraining Failures:** Test with dry-run first
3. **Performance Issues:** Monitor simulation duration
4. **Data Quality:** Review validation logs

## Success Metrics

- ✅ Data collected for all 5 types
- ✅ At least one model type meets sufficiency threshold
- ✅ Retraining pipeline tested successfully
- ✅ Comprehensive report generated

