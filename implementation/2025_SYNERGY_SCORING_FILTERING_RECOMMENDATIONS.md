# 2025 Synergy Scoring & Filtering Recommendations

**Date:** January 16, 2025  
**Purpose:** Comprehensive recommendations for scoring and filtering synergies that don't make sense to keep  
**Based on:** 2025 pattern validation, device activity analysis, and quality metrics

---

## Executive Summary

This document provides recommendations for implementing a comprehensive scoring and filtering system to remove synergies that don't make sense to keep. Based on 2025 patterns and current system analysis, we recommend a **multi-tier filtering approach** with **quality scoring** and **automatic cleanup**.

**Key Findings:**
- Current system has **6,675 synergies** (mostly `device_pair` type)
- Pattern validation is working (support scores calculated)
- Device activity filtering exists but needs enhancement
- No comprehensive quality scoring system
- Missing filters for: duplicates, low-quality, stale synergies

**Recommendation:** Implement a **Quality Score** system with **automatic filtering** at storage and query time.

---

## Current State Analysis

### Existing Scoring Systems

1. **Priority Score** (used for ranking):
   - 40% impact_score
   - 25% confidence
   - 25% pattern_support_score
   - Missing: validation bonus, complexity adjustment

2. **Impact Score** (base score):
   - Calculated from benefit_score with complexity penalties
   - Low: 0% penalty
   - Medium: 10% penalty
   - High: 30% penalty

3. **Pattern Support Score**:
   - Calculated from pattern validation (co-occurrence, time-of-day patterns)
   - Range: 0.0-1.0
   - Threshold: ≥0.7 = validated_by_patterns

4. **Multi-Modal Context Enhanced Score**:
   - Enhances impact_score with temporal/weather/energy/behavioral context
   - Currently used for display/ranking, not filtering

### Existing Filters

1. **Confidence Threshold**: `min_confidence >= 0.7` (in detector)
2. **Device Activity**: Optional filter via API (`include_inactive=False`)
3. **Pattern Validation**: Scores calculated but not used for filtering
4. **Same Area Required**: Configurable in detector (`same_area_required=True`)

### Gaps Identified

1. ❌ **No Quality Score**: No single metric that combines all factors
2. ❌ **No Automatic Filtering**: Low-quality synergies stored but not filtered
3. ❌ **No Duplicate Detection**: Same device pairs stored multiple times
4. ❌ **No Stale Synergy Cleanup**: Old synergies for removed devices persist
5. ❌ **No Minimum Quality Threshold**: All synergies stored regardless of quality
6. ❌ **Pattern Support Not Enforced**: Low pattern_support_score synergies still stored
7. ❌ **No Complexity-Based Filtering**: High complexity synergies not penalized enough

---

## Recommended Quality Scoring System

### Quality Score Formula

**Primary Quality Score (0.0-1.0):**

```python
quality_score = (
    # Base metrics (60%)
    impact_score * 0.25 +
    confidence * 0.20 +
    pattern_support_score * 0.15 +
    
    # Validation bonuses (25%)
    (0.10 if validated_by_patterns else 0.0) +
    (0.10 if active_devices else 0.0) +  # All devices active
    (0.05 if blueprint_fit_score > 0.7 else 0.0) +
    
    # Complexity penalty (15%)
    complexity_adjustment  # -0.15 (high), 0.0 (medium), +0.15 (low)
)
```

**Complexity Adjustment:**
- Low complexity: +0.15 bonus
- Medium complexity: 0.0 (no change)
- High complexity: -0.15 penalty

**Final Quality Score**: Clamped to [0.0, 1.0]

### Quality Tiers

| Tier | Score Range | Action |
|------|-------------|--------|
| **High Quality** | ≥ 0.70 | Keep, prioritize in recommendations |
| **Medium Quality** | 0.50 - 0.69 | Keep, show with warnings |
| **Low Quality** | 0.30 - 0.49 | Mark for review, deprioritize |
| **Poor Quality** | < 0.30 | **Auto-filter/remove** (recommended) |

---

## Recommended Filtering Rules

### Tier 1: Hard Filters (Always Remove)

These synergies should **never** be stored or returned:

1. **Invalid Device Pairs**:
   - Devices from external data sources (sports, weather, calendar, energy APIs)
   - Incompatible domains (e.g., `sensor.temperature` → `lock.door`)
   - Devices that don't exist in Home Assistant

2. **Duplicate Synergies**:
   - Same device pair (canonical: sorted device IDs)
   - Same relationship type
   - Within same area (if area-based)

3. **Stale Synergies**:
   - All devices inactive for >90 days
   - Devices removed from Home Assistant
   - Created >1 year ago with no activity

4. **Invalid Metadata**:
   - Missing required fields (device_ids, impact_score, confidence)
   - Invalid synergy_type (not in allowed list)
   - Invalid complexity (not 'low', 'medium', 'high')

### Tier 2: Quality Filters (Configurable Thresholds)

These synergies are filtered based on configurable thresholds:

1. **Minimum Quality Score**: `quality_score < 0.30` (default: remove)
2. **Minimum Pattern Support**: `pattern_support_score < 0.30` (default: warn)
3. **Minimum Confidence**: `confidence < 0.50` (default: remove)
4. **Minimum Impact**: `impact_score < 0.30` (default: remove)
5. **Unvalidated High Complexity**: `complexity == 'high' AND NOT validated_by_patterns` (default: remove)

### Tier 3: Context Filters (User-Configurable)

These filters are applied at query time, not storage:

1. **Device Activity**: Filter inactive devices (default: 30 days)
2. **Area Filtering**: Filter by specific areas
3. **Quality Tier**: Show only high/medium quality (user preference)
4. **Pattern Validation**: Show only validated synergies (user preference)

---

## Implementation Recommendations

### 1. Add Quality Score to Database Model

**File:** `services/ai-pattern-service/src/database/models.py`

```python
class SynergyOpportunity(Base):
    # ... existing fields ...
    
    # 2025 Enhancement: Quality score for filtering
    quality_score = Column(Float, nullable=True)  # Calculated quality score (0.0-1.0)
    quality_tier = Column(String(20), nullable=True)  # 'high', 'medium', 'low', 'poor'
    last_validated_at = Column(DateTime, nullable=True)  # Last quality validation timestamp
    filter_reason = Column(String(200), nullable=True)  # Reason if filtered (for audit)
```

### 2. Create Quality Scorer Service

**File:** `services/ai-pattern-service/src/services/synergy_quality_scorer.py`

```python
class SynergyQualityScorer:
    """
    Calculate quality scores for synergies and determine filtering decisions.
    
    2025 Best Practice: Centralized quality scoring with configurable thresholds.
    """
    
    def calculate_quality_score(
        self,
        synergy: dict[str, Any],
        active_devices: set[str] | None = None,
        blueprint_fit_score: float | None = None
    ) -> dict[str, Any]:
        """
        Calculate comprehensive quality score for a synergy.
        
        Returns:
            {
                'quality_score': float (0.0-1.0),
                'quality_tier': str ('high'|'medium'|'low'|'poor'),
                'should_filter': bool,
                'filter_reason': str | None,
                'score_breakdown': dict
            }
        """
        # Implementation of quality score formula
        pass
    
    def should_filter_synergy(
        self,
        synergy: dict[str, Any],
        quality_score: float,
        config: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """
        Determine if synergy should be filtered (hard filters + quality thresholds).
        
        Returns:
            (should_filter: bool, reason: str | None)
        """
        # Implementation of filtering logic
        pass
```

### 3. Update Synergy Storage to Calculate Quality Score

**File:** `services/ai-pattern-service/src/crud/synergies.py`

```python
async def store_synergy_opportunities(
    db: AsyncSession,
    synergies: list[dict],
    calculate_quality: bool = True,  # New parameter
    filter_low_quality: bool = True,  # New parameter
    min_quality_score: float = 0.30  # New parameter
) -> tuple[int, int]:  # Returns (stored_count, filtered_count)
    """
    Store synergies with quality scoring and optional filtering.
    
    Args:
        calculate_quality: Calculate quality_score for each synergy
        filter_low_quality: Filter synergies below min_quality_score
        min_quality_score: Minimum quality score threshold (default: 0.30)
    
    Returns:
        Tuple of (stored_count, filtered_count)
    """
    quality_scorer = SynergyQualityScorer()
    stored_count = 0
    filtered_count = 0
    
    for synergy in synergies:
        # Calculate quality score
        if calculate_quality:
            quality_result = quality_scorer.calculate_quality_score(synergy)
            synergy['quality_score'] = quality_result['quality_score']
            synergy['quality_tier'] = quality_result['quality_tier']
        
        # Check if should filter
        should_filter, filter_reason = quality_scorer.should_filter_synergy(
            synergy,
            synergy.get('quality_score', 0.0)
        )
        
        if should_filter and filter_low_quality:
            filtered_count += 1
            logger.debug(f"Filtered synergy {synergy.get('synergy_id')}: {filter_reason}")
            continue
        
        # Store synergy
        # ... existing storage logic ...
        stored_count += 1
    
    return stored_count, filtered_count
```

### 4. Update Query Functions to Filter by Quality

**File:** `services/ai-pattern-service/src/crud/synergies.py`

```python
async def get_synergy_opportunities(
    db: AsyncSession,
    synergy_type: str | None = None,
    min_confidence: float = 0.0,
    synergy_depth: int | None = None,
    limit: int = 100,
    order_by_priority: bool = False,
    min_quality_score: float | None = None,  # New parameter
    quality_tier: str | None = None,  # New parameter: 'high', 'medium', 'low'
    exclude_filtered: bool = True  # New parameter
) -> list[Any]:
    """
    Retrieve synergy opportunities with quality filtering.
    
    Args:
        min_quality_score: Minimum quality score (None = no filter)
        quality_tier: Filter by quality tier ('high', 'medium', 'low')
        exclude_filtered: Exclude synergies with filter_reason set
    """
    conditions = [SynergyOpportunity.confidence >= min_confidence]
    
    # Quality filters
    if min_quality_score is not None:
        conditions.append(SynergyOpportunity.quality_score >= min_quality_score)
    
    if quality_tier:
        conditions.append(SynergyOpportunity.quality_tier == quality_tier)
    
    if exclude_filtered:
        conditions.append(SynergyOpportunity.filter_reason.is_(None))
    
    # ... rest of query logic ...
```

### 5. Add Duplicate Detection

**File:** `services/ai-pattern-service/src/services/synergy_deduplicator.py`

```python
class SynergyDeduplicator:
    """
    Detect and remove duplicate synergies.
    
    2025 Best Practice: Prevent duplicate storage and improve quality.
    """
    
    def find_duplicates(
        self,
        synergies: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Find duplicate synergies based on canonical device pairs.
        
        Returns:
            {
                'canonical_pair_1': [synergy1, synergy2, ...],
                'canonical_pair_2': [synergy3, ...],
                ...
            }
        """
        # Group by canonical device pair (sorted device IDs)
        # Keep highest quality score from duplicates
        pass
    
    def deduplicate(
        self,
        synergies: list[dict[str, Any]],
        keep_highest_quality: bool = True
    ) -> list[dict[str, Any]]:
        """
        Remove duplicates, keeping highest quality synergy from each group.
        """
        duplicates = self.find_duplicates(synergies)
        deduplicated = []
        
        for canonical_pair, group in duplicates.items():
            if keep_highest_quality:
                # Keep synergy with highest quality_score
                best = max(group, key=lambda s: s.get('quality_score', 0.0))
                deduplicated.append(best)
            else:
                # Keep first occurrence
                deduplicated.append(group[0])
        
        return deduplicated
```

### 6. Create Cleanup Script for Stale Synergies

**File:** `scripts/cleanup_stale_synergies.py`

```python
async def cleanup_stale_synergies(
    db_path: str,
    inactive_days: int = 90,
    min_quality_score: float = 0.30,
    dry_run: bool = True
) -> dict[str, Any]:
    """
    Clean up stale synergies (inactive devices, low quality, old).
    
    Args:
        inactive_days: Devices inactive for this many days are considered stale
        min_quality_score: Remove synergies below this quality score
        dry_run: If True, only report what would be removed
    
    Returns:
        {
            'total_synergies': int,
            'removed_count': int,
            'removed_reasons': dict,
            'remaining_count': int
        }
    """
    # Implementation:
    # 1. Fetch all synergies
    # 2. Check device activity (via DataAPI)
    # 3. Check quality scores
    # 4. Check creation date (old synergies)
    # 5. Mark for removal or delete (based on dry_run)
    pass
```

---

## Filtering Thresholds (Recommended Defaults)

### Storage-Time Filters (Hard Requirements)

| Filter | Threshold | Action |
|--------|-----------|--------|
| Minimum Confidence | `confidence < 0.50` | **Remove** |
| Minimum Impact Score | `impact_score < 0.30` | **Remove** |
| Minimum Quality Score | `quality_score < 0.30` | **Remove** |
| Duplicate Synergies | Same device pair + relationship | **Remove** (keep highest quality) |
| Invalid Devices | External data sources | **Remove** |
| Missing Required Fields | Missing device_ids, scores | **Remove** |

### Query-Time Filters (Configurable)

| Filter | Default Threshold | Configurable |
|--------|------------------|--------------|
| Device Activity | 30 days inactive | ✅ Yes (activity_window_days) |
| Quality Tier | Show all | ✅ Yes (quality_tier parameter) |
| Pattern Validation | Show all | ✅ Yes (validated_by_patterns parameter) |
| Minimum Quality | No filter | ✅ Yes (min_quality_score parameter) |

### Quality Tier Thresholds

| Tier | Quality Score Range | Default Action |
|------|---------------------|----------------|
| High | ≥ 0.70 | Keep, prioritize |
| Medium | 0.50 - 0.69 | Keep, show normally |
| Low | 0.30 - 0.49 | Keep, deprioritize (warn) |
| Poor | < 0.30 | **Remove/Filter** |

---

## Scoring Enhancements

### 1. Enhanced Priority Score (For Ranking)

Update the priority score calculation to include quality factors:

```python
# Current (in crud/synergies.py):
priority_score = (
    impact_score * 0.40 +
    confidence * 0.25 +
    pattern_support_score * 0.25
)

# Recommended Enhancement:
priority_score = (
    impact_score * 0.30 +
    confidence * 0.20 +
    pattern_support_score * 0.20 +
    quality_score * 0.20 +  # NEW: Quality score component
    (0.10 if validated_by_patterns else 0.0)  # NEW: Validation bonus
)

# Complexity adjustment (applied after):
if complexity == 'low':
    priority_score += 0.05
elif complexity == 'high':
    priority_score -= 0.05

priority_score = max(0.0, min(1.0, priority_score))  # Clamp
```

### 2. Pattern Support Weight Adjustment

**Current Issue:** Pattern support score has equal weight (0.25) but should be weighted higher for validated synergies.

**Recommendation:** Use tiered weighting:

```python
# High pattern support (≥0.7): Higher weight
if pattern_support_score >= 0.7:
    pattern_weight = 0.30  # Increased from 0.25
elif pattern_support_score >= 0.5:
    pattern_weight = 0.25  # Standard
else:
    pattern_weight = 0.15  # Reduced for low support
```

---

## Implementation Priority

### Phase 1: Foundation (High Priority)

1. ✅ **Add Quality Score Calculation** (1-2 days)
   - Create `SynergyQualityScorer` service
   - Add quality_score/quality_tier to database model
   - Calculate quality scores during storage

2. ✅ **Implement Hard Filters** (1-2 days)
   - Duplicate detection
   - Invalid device filtering
   - Minimum threshold enforcement

3. ✅ **Update Storage Logic** (1 day)
   - Calculate quality scores before storage
   - Filter low-quality synergies (configurable)
   - Log filtered synergies for audit

### Phase 2: Enhancement (Medium Priority)

4. ✅ **Query-Time Filtering** (1 day)
   - Add quality filters to query functions
   - Update API endpoints with quality parameters
   - Default to exclude poor-quality synergies

5. ✅ **Cleanup Script** (1 day)
   - Create stale synergy cleanup script
   - Schedule periodic cleanup (monthly)
   - Generate cleanup reports

### Phase 3: Optimization (Low Priority)

6. ✅ **Enhanced Priority Score** (1 day)
   - Update priority score calculation
   - Add complexity adjustments
   - Update ranking logic

7. ✅ **Pattern Support Weighting** (1 day)
   - Implement tiered pattern support weighting
   - Update scoring formulas
   - Validate improvements

---

## Testing Recommendations

### Unit Tests

1. **Quality Score Calculation**:
   - Test quality_score formula with various inputs
   - Verify quality_tier assignment
   - Test edge cases (missing fields, extreme values)

2. **Filtering Logic**:
   - Test hard filters (duplicates, invalid devices)
   - Test quality thresholds
   - Test filter_reason assignment

3. **Deduplication**:
   - Test duplicate detection (same device pairs)
   - Test highest-quality selection
   - Test area-based duplicate handling

### Integration Tests

1. **Storage with Filtering**:
   - Store synergies with quality scoring enabled
   - Verify low-quality synergies are filtered
   - Verify quality_score stored in database

2. **Query with Quality Filters**:
   - Query with min_quality_score parameter
   - Query with quality_tier parameter
   - Verify filtered synergies excluded

3. **Cleanup Script**:
   - Test stale synergy detection
   - Test dry-run mode
   - Test actual cleanup execution

### Validation Tests

1. **Quality Score Distribution**:
   - Analyze quality_score distribution after implementation
   - Verify quality tiers are balanced
   - Check filter rates (should filter ~20-30% of synergies)

2. **Filter Effectiveness**:
   - Compare filtered vs. unfiltered synergy quality
   - Verify filtered synergies are truly low-quality
   - Check for false positives (good synergies filtered)

---

## Metrics & Monitoring

### Key Metrics to Track

1. **Quality Distribution**:
   - Count by quality_tier (high, medium, low, poor)
   - Average quality_score over time
   - Quality score improvements after filtering

2. **Filter Rates**:
   - Percentage filtered at storage time
   - Filter reasons breakdown
   - Duplicate detection rate

3. **Synergy Counts**:
   - Total synergies before/after filtering
   - Active synergies (not filtered)
   - Stale synergies removed

4. **User Impact**:
   - Average quality_score of returned synergies
   - User approval rate (if tracked)
   - Suggestion acceptance rate

### Monitoring Recommendations

1. **Log Filter Events**:
   - Log every filtered synergy with reason
   - Track filter_reason distribution
   - Alert on high filter rates (>50%)

2. **Quality Score Tracking**:
   - Track quality_score distribution weekly
   - Alert on quality degradation
   - Monitor quality improvements

3. **Cleanup Reports**:
   - Generate monthly cleanup reports
   - Track cleanup statistics
   - Review cleanup decisions

---

## Configuration

### Recommended Configuration File

**File:** `services/ai-pattern-service/src/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Synergy Quality Scoring (2025 Enhancement)
    synergy_quality_enabled: bool = True
    synergy_min_quality_score: float = 0.30  # Filter synergies below this
    synergy_filter_low_quality: bool = True  # Auto-filter at storage
    synergy_quality_tiers: dict[str, float] = {
        'high': 0.70,
        'medium': 0.50,
        'low': 0.30,
        'poor': 0.0
    }
    
    # Filtering Thresholds
    synergy_min_confidence: float = 0.50  # Hard filter
    synergy_min_impact: float = 0.30  # Hard filter
    synergy_min_pattern_support: float = 0.30  # Warning threshold
    
    # Duplicate Detection
    synergy_deduplicate_enabled: bool = True
    synergy_duplicate_keep_highest: bool = True
    
    # Stale Synergy Cleanup
    synergy_stale_inactive_days: int = 90
    synergy_stale_max_age_days: int = 365
```

---

## Migration Strategy

### For Existing Synergies

1. **Calculate Quality Scores**:
   - Run script to calculate quality_score for all existing synergies
   - Update quality_tier for all synergies
   - Mark synergies with filter_reason if they would be filtered

2. **Gradual Filtering**:
   - Phase 1: Calculate scores, don't filter (dry-run)
   - Phase 2: Filter new synergies only (storage-time)
   - Phase 3: Apply filters to queries (exclude filtered)
   - Phase 4: Cleanup stale/low-quality synergies (optional)

3. **Backward Compatibility**:
   - Keep existing API parameters working
   - Add new quality parameters as optional
   - Default to current behavior if quality scoring disabled

---

## Summary

### Key Recommendations

1. ✅ **Implement Quality Score System**: Single metric combining all quality factors
2. ✅ **Add Hard Filters**: Remove duplicates, invalid devices, missing fields
3. ✅ **Implement Quality Thresholds**: Filter synergies below 0.30 quality score
4. ✅ **Add Query-Time Filtering**: Allow users to filter by quality tier
5. ✅ **Create Cleanup Script**: Remove stale synergies periodically
6. ✅ **Enhance Priority Score**: Include quality_score and validation bonus
7. ✅ **Track Metrics**: Monitor quality distribution and filter rates

### Expected Impact

- **Quality Improvement**: 20-30% of synergies filtered (low-quality removed)
- **User Experience**: Higher quality recommendations, fewer false positives
- **Database Size**: Reduced storage (filtered synergies not stored)
- **Performance**: Faster queries (fewer synergies to process)

### Implementation Timeline

- **Phase 1 (Foundation)**: 3-5 days
- **Phase 2 (Enhancement)**: 2-3 days
- **Phase 3 (Optimization)**: 2-3 days
- **Total**: 7-11 days

---

## References

- Current Priority Score: `services/ai-pattern-service/src/crud/synergies.py:360-367`
- Pattern Validation: `services/ai-pattern-service/src/synergy_detection/synergy_detector.py:377-413`
- Device Activity Filtering: `services/ai-pattern-service/src/api/synergy_router.py:201-227`
- Database Model: `services/ai-pattern-service/src/database/models.py:22-66`
- Existing Recommendations: `implementation/FINAL_RECOMMENDATIONS_PATTERN_SYNERGY_VALIDATION.md`
