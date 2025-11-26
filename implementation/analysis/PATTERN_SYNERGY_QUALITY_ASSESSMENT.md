# Pattern and Synergy Quality Assessment Framework

**Date:** November 25, 2025  
**Status:** Planning

---

## Problem Statement

**Current Issue:** How do we know if detected patterns and synergies are actually good?

From test results:
- **Precision: 0.018** (very low - 98% false positives)
- **Recall: 0.600** (moderate - finding 60% of expected patterns)
- **F1 Score: 0.000** (very low)
- **170 patterns detected** vs **5 expected patterns**

This suggests we're detecting many patterns, but most may not be meaningful.

---

## Quality Assessment Dimensions

### 1. **Quantitative Metrics** (Current)

#### Pattern Quality Metrics
- **Precision**: TP / (TP + FP) - Are detected patterns correct?
- **Recall**: TP / (TP + FN) - Are we finding all expected patterns?
- **F1 Score**: Harmonic mean of precision and recall
- **Confidence Score**: Pattern detector's confidence (0.0-1.0)
- **Occurrence Count**: How many times pattern occurred
- **Frequency**: Occurrences per day/week

#### Synergy Quality Metrics
- **Impact Score**: Benefit score (0.0-1.0)
- **Confidence**: Synergy detector's confidence
- **Pattern Support Score**: How well patterns support the synergy
- **Validation Status**: 'valid' | 'warning' | 'invalid'
- **Priority Score**: Weighted combination of all factors

### 2. **Qualitative Assessment** (Needed)

#### Pattern Meaningfulness
- **Device Relationship**: Do devices make sense together?
  - Same area? ✅
  - Logical pairing (motion → light)? ✅
  - Random correlation? ❌
- **Temporal Consistency**: Does pattern occur at consistent times?
- **Frequency Reasonableness**: Is occurrence count realistic?
- **Blueprint Correlation**: Does pattern match known automations?

#### Synergy Benefit Validation
- **Automation Potential**: Can this be automated?
- **User Benefit**: Will this save time/energy/effort?
- **Complexity vs Benefit**: Is complexity worth the benefit?
- **Real-world Applicability**: Does this make sense in practice?

### 3. **Validation Layers** (Needed)

#### Layer 1: Pattern Validation
1. **Format Validation**: Pattern has required fields
2. **Confidence Threshold**: Confidence >= minimum (e.g., 0.7)
3. **Occurrence Threshold**: Occurred at least N times (e.g., 3)
4. **Device Relationship**: Devices are related (same area, logical pairing)
5. **Blueprint Correlation**: Matches known automation patterns

#### Layer 2: Synergy Validation
1. **Pattern Support**: Patterns validate the synergy
2. **Impact Score**: Benefit score >= threshold (e.g., 0.5)
3. **Device Compatibility**: Devices can actually work together
4. **Complexity Assessment**: Automation complexity is reasonable
5. **Existing Automation Check**: Not already automated

#### Layer 3: Real-world Validation
1. **User Acceptance**: Historical acceptance rate
2. **Deployment Success**: Success rate when deployed
3. **Feedback Score**: User feedback on suggestions
4. **Usage Tracking**: How often deployed automations are used

---

## Current Quality Indicators

### ✅ What We Have

1. **Metrics Calculation** (`metrics.py`)
   - Precision, recall, F1
   - Pattern similarity matching
   - Synergy matching

2. **Confidence Scores**
   - Pattern confidence (0.0-1.0)
   - Synergy confidence
   - Pattern support scores

3. **Impact Scores**
   - Benefit scores for synergies
   - Priority scores (weighted combination)

4. **Pattern Validation** (`pattern_synergy_validator.py`)
   - Support score calculation
   - Validation status ('valid' | 'warning' | 'invalid')
   - Confidence adjustments

5. **Blueprint Correlation** (`pattern_blueprint_validator.py`)
   - Pattern-to-blueprint matching
   - Confidence boosting

### ❌ What We Need

1. **Pattern Quality Scoring**
   - Multi-factor quality score
   - Meaningfulness assessment
   - Temporal consistency check

2. **Synergy Quality Scoring**
   - Benefit validation
   - Automation feasibility
   - User value assessment

3. **Quality Reporting**
   - Quality breakdown per pattern/synergy
   - Quality trends over time
   - Quality by home/device type

4. **Quality Thresholds**
   - Minimum quality scores for acceptance
   - Quality-based filtering
   - Quality-based ranking

---

## Proposed Solution

### Phase 1: Pattern Quality Scorer

Create `PatternQualityScorer` class that calculates:
- **Base Quality** (0.0-1.0):
  - Confidence score (40%)
  - Occurrence frequency (30%)
  - Temporal consistency (20%)
  - Device relationship strength (10%)

- **Validation Boost**:
  - Blueprint match: +0.2
  - Ground truth match: +0.3
  - Pattern support: +0.1

- **Quality Score** = min(1.0, base_quality + validation_boost)

### Phase 2: Synergy Quality Scorer

Create `SynergyQualityScorer` class that calculates:
- **Base Quality** (0.0-1.0):
  - Impact score (35%)
  - Confidence (25%)
  - Pattern support score (25%)
  - Device compatibility (15%)

- **Validation Boost**:
  - Pattern validation: +0.2
  - Blueprint match: +0.15
  - Low complexity: +0.1

- **Quality Score** = min(1.0, base_quality + validation_boost)

### Phase 3: Quality Reporting

Create quality reports that show:
- Quality distribution (histogram)
- Quality by pattern type
- Quality trends over time
- Top/bottom quality patterns/synergies
- Quality vs acceptance correlation

### Phase 4: Quality-Based Filtering

Filter patterns/synergies by:
- Minimum quality threshold (e.g., 0.6)
- Quality percentile (e.g., top 50%)
- Quality + confidence combination

---

## Implementation Plan

### Step 1: Pattern Quality Scorer
**File**: `services/ai-automation-service/src/testing/pattern_quality_scorer.py`

**Features**:
- Calculate multi-factor quality score
- Assess pattern meaningfulness
- Check temporal consistency
- Validate device relationships

### Step 2: Synergy Quality Scorer
**File**: `services/ai-automation-service/src/testing/synergy_quality_scorer.py`

**Features**:
- Calculate synergy quality score
- Validate automation potential
- Assess user benefit
- Check complexity vs benefit

### Step 3: Quality Metrics Integration
**Update**: `services/ai-automation-service/src/testing/metrics.py`

**Features**:
- Add quality scores to metrics
- Quality-based precision/recall
- Quality distribution statistics

### Step 4: Test Integration
**Update**: `services/ai-automation-service/tests/datasets/test_single_home_patterns.py`

**Features**:
- Calculate quality scores in tests
- Report quality metrics
- Filter by quality threshold

### Step 5: Quality Reporting
**File**: `services/ai-automation-service/src/testing/quality_reporter.py`

**Features**:
- Generate quality reports
- Quality distribution charts
- Quality trends analysis

---

## Success Criteria

### Quantitative
- **Quality Score Range**: 0.0-1.0 (higher is better)
- **Minimum Quality Threshold**: 0.6 for acceptance
- **Quality Distribution**: Most patterns/synergies above 0.5

### Qualitative
- **Pattern Meaningfulness**: Patterns make logical sense
- **Synergy Benefit**: Synergies provide clear value
- **User Acceptance**: High-quality items have higher acceptance

### Validation
- **Ground Truth Match**: High-quality items match ground truth
- **Blueprint Correlation**: High-quality items correlate with blueprints
- **User Feedback**: High-quality items receive positive feedback

---

## Next Steps

1. **Implement Pattern Quality Scorer**
2. **Implement Synergy Quality Scorer**
3. **Integrate into test framework**
4. **Generate quality reports**
5. **Analyze quality vs acceptance correlation**

---

## Example Quality Scores

### High Quality Pattern (0.85)
- Confidence: 0.9
- Occurrences: 15 (consistent)
- Temporal: Same time daily
- Device relationship: Motion sensor → Light (same area)
- Blueprint match: Yes
- **Result**: High quality, should be accepted

### Medium Quality Pattern (0.65)
- Confidence: 0.75
- Occurrences: 5 (moderate)
- Temporal: Variable times
- Device relationship: Two sensors (same area)
- Blueprint match: No
- **Result**: Medium quality, review needed

### Low Quality Pattern (0.35)
- Confidence: 0.5
- Occurrences: 2 (rare)
- Temporal: Random times
- Device relationship: Unrelated devices
- Blueprint match: No
- **Result**: Low quality, likely false positive

---

## Status

**Current**: Planning phase  
**Next**: Implement Pattern Quality Scorer

