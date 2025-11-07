# Synergy Data Quick Reference

**Based on Current Database Statistics**

## Current State Summary

| Metric | Value | Insight |
|--------|-------|---------|
| **Total Opportunities** | 6,324 | Large pool of automation opportunities |
| **Synergy Types** | 1 (device_pair) | Only device-to-device synergies detected |
| **Average Impact** | 51% | Moderate impact, viable for implementation |
| **Easy to Implement** | 6,324 (100%) | All are low complexity - quick wins |
| **Pattern Validated** | 5,224 (82.6%) | High confidence in viability |

---

## Impact Rating for Automation

### Priority Tiers (Estimated Distribution)

Based on 51% average impact, estimated distribution:

| Tier | Impact Range | Estimated Count | Priority | Action |
|------|--------------|-----------------|----------|--------|
| **Tier 1** | ≥70% | ~500-800 | **Immediate** | Implement first |
| **Tier 2** | 60-70% | ~1,200-1,800 | **High** | High priority queue |
| **Tier 3** | 50-60% | ~2,500-3,000 | **Standard** | Current average |
| **Tier 4** | 40-50% | ~1,000-1,500 | **Low** | Review before implementing |
| **Tier 5** | <40% | ~500-800 | **Review** | May not be worth it |

### Recommended Priority Score Formula

```python
priority_score = (
    impact_score × 0.40 +           # Impact weight: 40%
    confidence × 0.25 +              # Confidence weight: 25%
    pattern_support_score × 0.25 +   # Pattern validation: 25%
    (1 if validated_by_patterns else 0) × 0.10  # Validation bonus: 10%
)
```

**Complexity Bonus:**
- Low complexity: +0.10 bonus
- Medium complexity: No adjustment
- High complexity: -0.10 penalty

---

## Best Use Cases

### 1. **Pattern-Validated Quick Wins** ⭐ TOP PRIORITY

**Target:** 5,224 pattern-validated synergies
- **Impact:** High confidence (validated by historical patterns)
- **Risk:** Low (proven patterns)
- **ROI:** High (quick implementation, proven value)

**Action Plan:**
1. Filter: `validated_by_patterns = true`
2. Sort by: Priority score (descending)
3. Implement: Top 200-500 in first month
4. Track: Success rate and user satisfaction

### 2. **High-Impact Opportunities**

**Target:** Synergies with impact >60%
- **Estimated Count:** ~2,000-2,600 synergies
- **Value:** Maximum ROI per automation
- **Focus:** Areas with highest impact scores

**Action Plan:**
1. Filter: `impact_score >= 0.6`
2. Prioritize: Pattern-validated first
3. Group: By area for batch implementation
4. Measure: Impact before/after implementation

### 3. **Area-Based Campaigns**

**Strategy:** Implement all synergies in one area at a time

**Benefits:**
- Contextual grouping (all bedroom automations together)
- Easier testing and validation
- Immediate visible impact in specific rooms

**Workflow:**
1. Identify top 5 areas by synergy count
2. Implement all synergies in Area #1
3. Measure impact (usage, energy, convenience)
4. Expand to next area

### 4. **Relationship Type Focus**

**Current Types (from code):**
- `motion_to_light`: Motion sensor → Light
- `door_to_light`: Door sensor → Light
- `door_to_lock`: Door sensor → Lock
- `motion_to_climate`: Motion sensor → Climate
- `occupancy_to_light`: Occupancy sensor → Light

**Strategy:** Focus on relationship types with:
- Highest impact scores
- Most occurrences
- Best pattern validation rates

---

## Implementation Roadmap

### Phase 1: Quick Wins (Weeks 1-2)
**Target:** Top 200 synergies
- Impact >60%
- Pattern validated
- Low complexity
- High confidence (>0.8)

**Expected Outcome:**
- ~200 automations implemented
- High user satisfaction
- Validates synergy detection system

### Phase 2: Pattern-Validated Batch (Weeks 3-4)
**Target:** All pattern-validated synergies with impact >50%
- ~4,000-4,500 synergies
- Batch generation of automation templates
- User review and approval workflow

**Expected Outcome:**
- Significant automation coverage
- Measurable convenience improvements
- Energy savings (for climate-related synergies)

### Phase 3: Contextual Expansion (Month 2+)
**Target:** Enable weather/energy/event context synergies
- Currently 0 contextual synergies detected
- Enable contextual detection in daily batch
- Expected: +500-1,000 new opportunities

**Expected Outcome:**
- More sophisticated automations
- Energy optimization opportunities
- Weather-aware automations

---

## Key Insights

### Strengths
✅ **82.6% Pattern Validated** - High confidence in data quality  
✅ **100% Low Complexity** - Easy to implement, quick wins  
✅ **Large Dataset** - 6,324 opportunities provides significant potential  
✅ **Consistent Type** - All device_pair = uniform implementation approach  

### Gaps & Opportunities
⚠️ **Only 1 Synergy Type** - Enable weather/energy/event context (+500-1,000 opportunities)  
⚠️ **51% Average Impact** - Moderate, but viable (need to focus on >60% for best ROI)  
⚠️ **Unknown Distributions** - Need to analyze:
   - Impact score distribution (histogram)
   - Area distribution (which areas have most opportunities)
   - Relationship type distribution (which relationships are most common)

---

## Next Steps

### Immediate (This Week)
1. ✅ Run detailed analysis script: `python scripts/analyze_synergy_data.py`
2. ✅ Query impact distribution to understand score spread
3. ✅ Identify top 10 areas by synergy count
4. ✅ Identify top 5 relationship types

### Short-Term (This Month)
1. Implement priority scoring system in API
2. Create automation template generator
3. Enable contextual synergy detection
4. Build batch implementation workflow

### Long-Term (Next Quarter)
1. Track automation success rates
2. Recalculate impact scores based on real-world results
3. Create "automation packages" (related synergies grouped)
4. Build one-click implementation feature

---

## SQL Queries for Analysis

See `implementation/analysis/SYNERGY_DATA_ANALYSIS.md` for detailed SQL queries to:
- Get impact distribution
- Find top areas
- Analyze relationship types
- Calculate priority scores
- Identify top opportunities

---

**Last Updated:** January 2025  
**Data Source:** Synergy Opportunities Database  
**Analysis Tool:** `scripts/analyze_synergy_data.py`

