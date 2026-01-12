# Synergy Scoring Analysis Summary

**Date:** January 16, 2026  
**Total Synergies Analyzed:** 44,145

---

## Executive Summary

Analysis of synergy scoring reveals that **56.1% of synergies have NULL quality scores**, indicating quality scoring has not been calculated for all synergies. Among synergies with quality scores, **41.9% are in the "high" tier** (≥0.70).

---

## Quality Score Distribution

### Quality Score Ranges

| Score Range | Count | Percentage | Notes |
|-------------|-------|------------|-------|
| **NULL** | 24,755 | 56.1% | ⚠️ Quality score not calculated |
| **0.7-0.8** | 14,852 | 33.6% | High quality (tier: high) |
| **0.8-0.9** | 3,662 | 8.3% | Very high quality (tier: high) |
| **0.6-0.7** | 255 | 0.6% | Medium-high quality (tier: medium) |
| **0.3-0.4** | 600 | 1.4% | Low quality (tier: low) |
| **0.4-0.5** | 15 | 0.0% | Low-medium quality (tier: low) |
| **0.5-0.6** | 6 | 0.0% | Medium quality (tier: medium) |
| **0.0-0.3** | 0 | 0.0% | Poor quality (tier: poor) |
| **0.9-1.0** | 0 | 0.0% | Maximum quality |

### Quality Tier Distribution

| Tier | Count | Percentage | Score Threshold |
|------|-------|------------|-----------------|
| **high** | 18,514 | 41.9% | ≥ 0.70 |
| **low** | 615 | 1.4% | 0.30 - 0.49 |
| **medium** | 261 | 0.6% | 0.50 - 0.69 |
| **poor** | 0 | 0.0% | < 0.30 |
| **NULL** | 24,755 | 56.1% | Quality score not calculated |

**Quality Tier Thresholds:**
- **high:** ≥ 0.70
- **medium:** 0.50 - 0.69
- **low:** 0.30 - 0.49
- **poor:** < 0.30

---

## Impact Score Distribution

### Impact Score Statistics

- **Min:** 0.500
- **Max:** 1.000
- **Avg:** 0.720
- **Range:** All synergies have impact scores (no NULL values)

### Impact Score Ranges

| Score Range | Count | Percentage |
|-------------|-------|------------|
| **0.6-0.7** | 32,976 | 74.7% |
| **0.9-1.0** | 7,183 | 16.3% |
| **0.8-0.9** | 3,249 | 7.4% |
| **0.5-0.6** | 517 | 1.2% |
| **0.7-0.8** | 220 | 0.5% |
| **0.0-0.5** | 0 | 0.0% |

**Key Finding:** 98.4% of synergies have impact scores ≥ 0.6, with 74.7% in the 0.6-0.7 range.

---

## Confidence Distribution

### Confidence Statistics

- **Min:** 0.500
- **Max:** 1.000
- **Avg:** 0.908
- **Range:** All synergies have confidence scores (no NULL values)

### Confidence Ranges

| Score Range | Count | Percentage |
|-------------|-------|------------|
| **0.8-0.9** | 35,765 | 81.0% |
| **0.9-1.0** | 7,183 | 16.3% |
| **0.5-0.6** | 517 | 1.2% |
| **0.6-0.7** | 411 | 0.9% |
| **0.7-0.8** | 269 | 0.6% |
| **0.0-0.5** | 0 | 0.0% |

**Key Finding:** 97.3% of synergies have confidence ≥ 0.8, with 81.0% in the 0.8-0.9 range.

---

## Final Score Distribution

⚠️ **All synergies have NULL final_score (100%)** - This field is not currently being calculated or used.

---

## Scoring by Synergy Type

### device_pair (42,696 synergies - 96.7%)

- **Avg Quality Score:** 0.764
- **Avg Impact Score:** 0.716
- **Avg Confidence:** 0.908

### device_chain (1,400 synergies - 3.2%)

- **Avg Quality Score:** 0.393 (lower than device_pair)
- **Avg Impact Score:** 0.850 (higher than device_pair)
- **Avg Confidence:** 0.900

### scene_based (14 synergies - 0.0%)

- **Avg Quality Score:** 0.502
- **Avg Impact Score:** 0.850
- **Avg Confidence:** 0.700

### weather_context (35 synergies - 0.1%)

- **Avg Quality Score:** 0.453
- **Avg Impact Score:** 0.650
- **Avg Confidence:** 0.700

---

## Key Findings

### ✅ Strengths

1. **High Impact Scores:** 98.4% of synergies have impact ≥ 0.6
2. **High Confidence:** 97.3% of synergies have confidence ≥ 0.8
3. **Quality Distribution:** When calculated, 41.9% are "high" tier (≥0.70)
4. **Strong Averages:** Overall avg impact = 0.720, avg confidence = 0.908

### ⚠️ Areas for Improvement

1. **Quality Score Coverage:** 56.1% of synergies have NULL quality_score
   - **Recommendation:** Run quality score backfill script for all synergies
   - **Script:** `services/ai-pattern-service/scripts/backfill_quality_scores.py`

2. **Final Score:** 100% NULL - Field not being used
   - **Recommendation:** Either populate final_score or document why it's not used

3. **Device Chain Quality:** Lower average quality score (0.393) compared to device_pair (0.764)
   - **Investigation:** Review quality calculation for device_chain synergies

---

## Recommendations

### Immediate Actions

1. **Backfill Quality Scores**
   - Run quality score calculation for all synergies with NULL quality_score
   - Estimated: 24,755 synergies need quality scores calculated
   - Script: `scripts/backfill_quality_scores.py` or equivalent

2. **Investigate Final Score Usage**
   - Determine if final_score field should be populated
   - If not needed, consider deprecating or documenting as unused

### Analysis Actions

1. **Review Device Chain Scoring**
   - Why do device_chain synergies have lower quality scores (0.393) despite higher impact (0.850)?
   - Review quality calculation formula for device_chain type

2. **Quality Score Coverage Analysis**
   - Identify why 56.1% of synergies lack quality scores
   - Check if quality calculation is enabled for all synergy creation paths

---

## Score Group Summary

### By Quality Score (when calculated)

| Group | Count | Percentage |
|-------|-------|------------|
| **High (≥0.70)** | 18,514 | 41.9% |
| **Medium (0.50-0.69)** | 276 | 0.6% |
| **Low (0.30-0.49)** | 615 | 1.4% |
| **Poor (<0.30)** | 0 | 0.0% |
| **NULL (not calculated)** | 24,755 | 56.1% |

### By Quality Tier (when set)

| Tier | Count | Percentage |
|------|-------|------------|
| **high** | 18,514 | 41.9% |
| **medium** | 261 | 0.6% |
| **low** | 615 | 1.4% |
| **poor** | 0 | 0.0% |
| **NULL** | 24,755 | 56.1% |

---

## Quality Score Calculation Details

**Formula (from `synergy_quality_scorer.py`):**

- **Base metrics (60%):**
  - Impact score × 0.25
  - Confidence × 0.20
  - Pattern support score × 0.15

- **Validation bonuses (25%):**
  - Pattern validation: +0.10
  - Active devices: +0.10
  - Blueprint fit: +0.05

- **Complexity adjustment (15%):**
  - Low complexity: +0.15
  - Medium complexity: 0.0
  - High complexity: -0.15

**Tier Thresholds:**
- High: ≥ 0.70
- Medium: 0.50 - 0.69
- Low: 0.30 - 0.49
- Poor: < 0.30

---

## Data Files

- **Analysis Script:** `scripts/analyze_synergy_scoring.py`
- **Results JSON:** `implementation/synergy_scoring_analysis.json`
- **This Summary:** `implementation/SYNERGY_SCORING_ANALYSIS_SUMMARY.md`

---

**Analysis Date:** January 16, 2026  
**Database:** `/app/data/ai_automation.db` (via Docker)  
**Total Synergies:** 44,145
