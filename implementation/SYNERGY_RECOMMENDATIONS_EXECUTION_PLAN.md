# Synergy Scoring Recommendations Execution Plan

**Date:** January 16, 2026  
**Status:** 🚀 **READY TO EXECUTE**

---

## Executive Summary

Plan to execute recommendations from synergy scoring analysis:
1. Backfill quality scores for 24,755 synergies with NULL quality_score
2. Investigate final_score field usage
3. Review device_chain quality scoring

---

## Recommendation 1: Backfill Quality Scores ✅ READY

### Status
- **Script Available:** `services/ai-pattern-service/scripts/backfill_quality_scores.py`
- **Synergies Needing Scores:** 24,755 (56.1% of total)
- **Action:** Execute backfill script

### Execution Steps

1. **Dry Run (Preview)**
   ```bash
   docker exec ai-pattern-service python /tmp/backfill_quality_scores.py --db-path /app/data/ai_automation.db --dry-run
   ```

2. **Execute Backfill**
   ```bash
   docker exec ai-pattern-service python /tmp/backfill_quality_scores.py --db-path /app/data/ai_automation.db
   ```

3. **Verify Results**
   - Re-run scoring analysis to verify coverage improved
   - Check tier distribution after backfill

### Expected Results

- **Before:** 24,755 NULL quality scores (56.1%)
- **After:** All synergies should have quality scores
- **Estimated Time:** 5-15 minutes (processing 24,755 synergies in batches of 100)

---

## Recommendation 2: Investigate Final Score Usage

### Status
- **Current:** 100% of synergies have NULL final_score
- **Action:** Investigate if field should be populated or documented as unused

### Investigation Steps

1. **Check Code References**
   - Search for final_score usage in codebase
   - Check if field is read anywhere
   - Check documentation

2. **Review N-level Synergy Fields**
   - `embedding_similarity` - Used for similarity calculations
   - `rerank_score` - Used for reranking
   - `final_score` - Combined score (needs investigation)

3. **Document Decision**
   - If unused: Document as deprecated/unused
   - If needed: Create script to populate final_score

---

## Recommendation 3: Review Device Chain Quality Scoring

### Status
- **Issue:** device_chain synergies have lower quality scores (0.393 avg) despite higher impact (0.850 avg)
- **Action:** Review quality calculation for device_chain type

### Investigation Steps

1. **Analyze Quality Calculation**
   - Review quality score formula
   - Check if complexity adjustment affects device_chain
   - Compare device_pair vs device_chain scoring inputs

2. **Review Complexity Settings**
   - Check if device_chain synergies have different complexity values
   - Complexity adjustment: low=+0.15, medium=0.0, high=-0.15

3. **Compare Inputs**
   - device_pair: avg quality=0.764, avg impact=0.716
   - device_chain: avg quality=0.393, avg impact=0.850
   - Why lower quality despite higher impact?

---

## Execution Order

1. ✅ **Backfill Quality Scores** (Immediate - High Impact)
2. ⚠️ **Investigate Final Score** (Analysis - Medium Priority)
3. ⚠️ **Review Device Chain Scoring** (Analysis - Low Priority)

---

## Next Steps

1. Execute quality score backfill
2. Investigate final_score field
3. Review device_chain scoring discrepancy
4. Document findings and decisions

---

**Status:** 🚀 **READY TO EXECUTE**  
**Last Updated:** January 16, 2026
