# Recommendations Execution Plan

**Date:** December 3, 2025  
**Status:** In Progress  
**Priority:** High

## Plan Overview

Execute recommendations from simulation results report, focusing on immediate and short-term improvements.

## Execution Phases

### Phase 1: Fix YAML Data Collection (High Priority)
**Goal:** Enable YAML generation data collection for model retraining

**Actions:**
1. Review YAML collection logic in `cli.py`
2. Verify `ask_ai_simulator.py` returns YAML data correctly
3. Fix any collection issues
4. Test YAML data collection

**Expected Outcome:** YAML data collected and exported

### Phase 2: Retrain Soft Prompt Model (High Priority)
**Goal:** Retrain model with 1,180 collected samples

**Actions:**
1. Verify training script exists and is accessible
2. Prepare training data in correct format
3. Execute retraining
4. Verify model output

**Expected Outcome:** Retrained Soft Prompt model

### Phase 3: Collect Additional Data (Medium Priority)
**Goal:** Collect data for GNN Synergy and Pattern Detection models

**Actions:**
1. Run simulation for GNN Synergy (20-30 homes)
2. Run simulation for Pattern Detection (50-100 homes)
3. Verify data sufficiency after collection

**Expected Outcome:** All models eligible for retraining

## Success Criteria

- ✅ YAML data collection working
- ✅ Soft Prompt model retrained
- ✅ GNN Synergy data sufficient
- ✅ Pattern Detection data sufficient

