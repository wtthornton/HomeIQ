# Patterns Engine Review and Improvement Ideas

**Date:** January 2025  
**Status:** Review Complete  
**Focus:** Engine improvements (not UI/UX)

## Executive Summary

The patterns detection engine is a sophisticated multi-detector system with ML enhancements, incremental processing, and quality filtering. Current state shows **1,094 patterns** across **109 devices** with **91% average confidence** and **3 pattern types** detected. The engine has strong foundations but several areas for optimization.

## Current Architecture Overview

### Pattern Detection Pipeline

```
Events (InfluxDB) 
  ↓
Daily Analysis Scheduler (3 AM daily)
  ↓
10 Pattern Detectors (Parallel/Sequential)
  ├─ TimeOfDayPatternDetector (Legacy)
  ├─ CoOccurrencePatternDetector (Legacy)
  ├─ SequenceDetector (ML-enhanced)
  ├─ ContextualDetector (ML-enhanced)
  ├─ RoomBasedDetector (ML-enhanced)
  ├─ SessionDetector (ML-enhanced)
  ├─ DurationDetector (ML-enhanced)
  ├─ DayTypeDetector (ML-enhanced)
  ├─ SeasonalDetector (ML-enhanced)
  └─ AnomalyDetector (ML-enhanced)
  ↓
Pattern Filtering & Validation
  ├─ Domain filtering (exclude sensors, events)
  ├─ Occurrence threshold (min 10)
  ├─ Confidence threshold (min 0.7)
  └─ Actionability check
  ↓
Pattern Deduplication
  ↓
Cross-Validation
  ↓
Confidence Calibration
  ↓
Database Storage (SQLite)
  └─ History tracking & trend analysis
```

### Key Components

1. **MLPatternDetector Base Class** (`ml_pattern_detector.py`)
   - ML clustering (MiniBatchKMeans)
   - Anomaly detection (LocalOutlierFactor)
   - Incremental learning support
   - Confidence calibration
   - Utility scoring

2. **Pattern Filters** (`pattern_filters.py`)
   - Domain exclusions (sensor, event, image)
   - Prefix exclusions (battery, tracker, status)
   - Actionability validation
   - Minimum thresholds (10 occurrences, 0.7 confidence)

3. **Pattern Storage** (`database/crud.py`)
   - Validation before storage
   - Deduplication (merge by pattern_type + device_id)
   - History snapshots
   - Trend cache updates

4. **Daily Analysis Scheduler** (`daily_analysis.py`)
   - Unified batch job (Epic AI-1 + AI-2 + AI-3)
   - Incremental processing support
   - Parallel pattern processing
   - Quality improvements (deduplication, cross-validation, calibration)

## Current State Analysis

### Pattern Statistics (from UI)
- **Total Patterns:** 1,094
- **Unique Devices:** 109
- **Average Confidence:** 91%
- **Pattern Types:** 3 (co_occurrence, time_of_day, likely sequence)
- **Last Analysis:** Never (suggests manual run or stale data)

### Pattern Distribution
From UI snapshot, patterns are primarily:
- **Co-occurrence patterns** with very high occurrence counts (25,612 occurrences)
- Examples: `media_player.denon_avr_x6500h+media_player.living_room_2` (9,287 occurrences)
- Light co-occurrences: `light.downstairs+light.tv_room` (62,985 occurrences)

### Observations

**Strengths:**
1. ✅ Comprehensive detector suite (10 detectors)
2. ✅ ML enhancements with clustering and anomaly detection
3. ✅ Incremental processing for performance
4. ✅ Quality filtering (domain, occurrence, confidence)
5. ✅ History tracking and trend analysis
6. ✅ Pattern deduplication and cross-validation
7. ✅ Confidence calibration based on acceptance rates

**Issues:**
1. ⚠️ Only 3 pattern types stored despite 10 detectors running
2. ⚠️ Very high occurrence counts (25K+) suggest potential accumulation issues
3. ⚠️ Pattern-to-device ratio (1,094 patterns / 109 devices ≈ 10:1) seems high
4. ⚠️ Some detectors may be failing silently or not finding patterns
5. ⚠️ Co-occurrence patterns dominate (may indicate other detectors need tuning)

## Improvement Ideas

### 1. Pattern Occurrence Accumulation Fix

**Problem:** Patterns showing 25,612 occurrences suggest accumulation without proper reset or time-windowing.

**Solution:**
```python
# In store_patterns() - Add time-windowed occurrence tracking
async def store_patterns(db: AsyncSession, patterns: list[dict], time_window_days: int = 30) -> int:
    """
    Store patterns with time-windowed occurrence tracking.
    
    Instead of accumulating occurrences indefinitely, track occurrences
    within a rolling time window (e.g., last 30 days).
    """
    # Calculate occurrences within time window
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_window_days)
    
    for pattern_data in valid_patterns:
        existing_pattern = await get_existing_pattern(db, pattern_data)
        
        if existing_pattern:
            # Get occurrences from last time window only
            recent_occurrences = await get_occurrences_in_window(
                pattern_id=existing_pattern.id,
                start_date=cutoff_date
            )
            
            # Update with windowed count, not accumulated
            existing_pattern.occurrences = recent_occurrences
            existing_pattern.confidence = calculate_confidence(recent_occurrences, time_window_days)
```

**Benefits:**
- Prevents unbounded accumulation
- More accurate confidence scores
- Better reflects current usage patterns

### 2. Detector Health Monitoring

**Problem:** 7 detectors not producing results - need visibility into why.

**Solution:**
```python
# Add detector health tracking
class DetectorHealthMonitor:
    """Track detector performance and failures"""
    
    def __init__(self):
        self.detector_stats = {}
    
    async def track_detection_run(
        self,
        detector_name: str,
        patterns_found: int,
        processing_time: float,
        error: Exception | None = None
    ):
        """Track detector execution"""
        stats = self.detector_stats.get(detector_name, {
            'runs': 0,
            'successful_runs': 0,
            'total_patterns': 0,
            'avg_processing_time': 0.0,
            'last_error': None
        })
        
        stats['runs'] += 1
        if error:
            stats['last_error'] = str(error)
        else:
            stats['successful_runs'] += 1
            stats['total_patterns'] += patterns_found
            stats['avg_processing_time'] = (
                (stats['avg_processing_time'] * (stats['successful_runs'] - 1) + processing_time) 
                / stats['successful_runs']
            )
        
        self.detector_stats[detector_name] = stats
    
    def get_health_report(self) -> dict:
        """Generate health report for all detectors"""
        return {
            detector: {
                'success_rate': stats['successful_runs'] / max(stats['runs'], 1),
                'avg_patterns_per_run': stats['total_patterns'] / max(stats['successful_runs'], 1),
                'avg_processing_time': stats['avg_processing_time'],
                'last_error': stats['last_error'],
                'status': 'healthy' if stats['successful_runs'] / max(stats['runs'], 1) > 0.8 else 'degraded'
            }
            for detector, stats in self.detector_stats.items()
        }
```

**Benefits:**
- Visibility into detector failures
- Identify detectors needing threshold adjustments
- Performance monitoring

### 3. Adaptive Threshold Tuning

**Problem:** Fixed thresholds may be too strict for some detectors, too lenient for others.

**Solution:**
```python
# Adaptive threshold adjustment based on pattern yield
class AdaptiveThresholdTuner:
    """Automatically adjust detector thresholds based on pattern yield"""
    
    def __init__(self, target_patterns_per_detector: int = 10):
        self.target_patterns = target_patterns_per_detector
        self.threshold_history = {}
    
    def suggest_thresholds(
        self,
        detector_name: str,
        current_thresholds: dict,
        patterns_found: int,
        events_analyzed: int
    ) -> dict:
        """Suggest threshold adjustments"""
        
        if patterns_found == 0:
            # Too strict - lower thresholds
            return {
                'min_occurrences': max(3, current_thresholds.get('min_occurrences', 10) - 2),
                'min_confidence': max(0.5, current_thresholds.get('min_confidence', 0.7) - 0.1)
            }
        elif patterns_found > self.target_patterns * 2:
            # Too lenient - raise thresholds
            return {
                'min_occurrences': current_thresholds.get('min_occurrences', 10) + 2,
                'min_confidence': min(0.95, current_thresholds.get('min_confidence', 0.7) + 0.05)
            }
        else:
            # Good range - keep current
            return current_thresholds
```

**Benefits:**
- Automatic optimization of detector thresholds
- Better pattern yield across all detectors
- Reduces manual tuning

### 4. Pattern Quality Scoring Enhancement

**Problem:** Current utility scoring may not capture all quality dimensions.

**Solution:**
```python
# Enhanced quality scoring
class EnhancedPatternQualityScorer:
    """Multi-dimensional pattern quality scoring"""
    
    def score_pattern(self, pattern: dict, events_df: pd.DataFrame) -> dict:
        """
        Score pattern across multiple dimensions:
        - Actionability (device type)
        - Consistency (temporal variance)
        - Frequency (occurrence rate)
        - Recency (last seen)
        - Automation potential (can it be automated?)
        """
        scores = {
            'actionability': self._score_actionability(pattern),
            'consistency': self._score_consistency(pattern, events_df),
            'frequency': self._score_frequency(pattern, events_df),
            'recency': self._score_recency(pattern),
            'automation_potential': self._score_automation_potential(pattern)
        }
        
        # Weighted total
        total_score = (
            scores['actionability'] * 0.3 +
            scores['consistency'] * 0.2 +
            scores['frequency'] * 0.2 +
            scores['recency'] * 0.1 +
            scores['automation_potential'] * 0.2
        )
        
        scores['total_quality'] = total_score
        return scores
    
    def _score_automation_potential(self, pattern: dict) -> float:
        """Score how easily this pattern can be automated"""
        pattern_type = pattern.get('pattern_type', '')
        
        # Time-of-day patterns are easy to automate
        if pattern_type == 'time_of_day':
            return 1.0
        
        # Co-occurrence patterns need triggers
        elif pattern_type == 'co_occurrence':
            device1 = pattern.get('device1', '')
            device2 = pattern.get('device2', '')
            
            # If one is a trigger (sensor) and one is an action (light), high potential
            if self._is_trigger_device(device1) and self._is_action_device(device2):
                return 0.9
            elif self._is_trigger_device(device2) and self._is_action_device(device1):
                return 0.9
            else:
                return 0.6
        
        # Sequence patterns are moderate
        elif pattern_type == 'sequence':
            return 0.7
        
        # Other patterns vary
        else:
            return 0.5
```

**Benefits:**
- Better pattern prioritization
- Focus on high-value automation opportunities
- Multi-dimensional quality assessment

### 5. Pattern Lifecycle Management

**Problem:** Patterns may become stale or invalid over time.

**Solution:**
```python
# Pattern lifecycle management
class PatternLifecycleManager:
    """Manage pattern lifecycle: creation, validation, deprecation, deletion"""
    
    async def manage_pattern_lifecycle(self, db: AsyncSession):
        """Run lifecycle management tasks"""
        
        # 1. Deprecate stale patterns (not seen in 60 days)
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        stale_patterns = await db.execute(
            select(Pattern).where(Pattern.last_seen < stale_cutoff)
        )
        
        for pattern in stale_patterns.scalars():
            pattern.deprecated = True
            pattern.deprecated_at = datetime.now(timezone.utc)
            logger.info(f"Deprecated stale pattern {pattern.id} (last seen: {pattern.last_seen})")
        
        # 2. Delete very old deprecated patterns (90+ days deprecated)
        old_deprecated_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        await db.execute(
            delete(Pattern).where(
                Pattern.deprecated == True,
                Pattern.deprecated_at < old_deprecated_cutoff
            )
        )
        
        # 3. Validate active patterns (check if still occurring)
        active_patterns = await db.execute(
            select(Pattern).where(Pattern.deprecated == False)
        )
        
        for pattern in active_patterns.scalars():
            recent_occurrences = await self._check_recent_occurrences(pattern)
            if recent_occurrences == 0:
                # Pattern no longer occurring - mark for review
                pattern.needs_review = True
                logger.info(f"Pattern {pattern.id} marked for review (no recent occurrences)")
        
        await db.commit()
```

**Benefits:**
- Automatic cleanup of stale patterns
- Pattern validation over time
- Database size management

### 6. Pattern Clustering and Deduplication Enhancement

**Problem:** Current deduplication may miss similar patterns with slight variations.

**Solution:**
```python
# Enhanced pattern clustering
class PatternClusterer:
    """Cluster similar patterns to reduce redundancy"""
    
    def cluster_patterns(self, patterns: list[dict]) -> list[dict]:
        """Cluster similar patterns using ML"""
        
        # Extract features for clustering
        features = []
        for pattern in patterns:
            feature_vector = self._extract_features(pattern)
            features.append(feature_vector)
        
        if len(features) < 3:
            return patterns
        
        # Cluster using DBSCAN (density-based, finds clusters of any shape)
        from sklearn.cluster import DBSCAN
        clustering = DBSCAN(eps=0.3, min_samples=2)
        cluster_labels = clustering.fit_predict(features)
        
        # Merge patterns in same cluster
        clustered_patterns = []
        clusters = defaultdict(list)
        
        for i, pattern in enumerate(patterns):
            cluster_id = cluster_labels[i]
            if cluster_id == -1:
                # Noise - keep as-is
                clustered_patterns.append(pattern)
            else:
                clusters[cluster_id].append(pattern)
        
        # Merge clusters
        for cluster_id, cluster_patterns in clusters.items():
            merged = self._merge_cluster(cluster_patterns)
            clustered_patterns.append(merged)
        
        return clustered_patterns
    
    def _merge_cluster(self, patterns: list[dict]) -> dict:
        """Merge patterns in a cluster into single representative pattern"""
        # Use pattern with highest confidence as base
        base_pattern = max(patterns, key=lambda p: p.get('confidence', 0))
        
        # Merge metadata
        merged_occurrences = sum(p.get('occurrences', 0) for p in patterns)
        merged_confidence = max(p.get('confidence', 0) for p in patterns)
        
        base_pattern['occurrences'] = merged_occurrences
        base_pattern['confidence'] = merged_confidence
        base_pattern['metadata']['cluster_size'] = len(patterns)
        base_pattern['metadata']['merged_from'] = [p.get('pattern_id') for p in patterns]
        
        return base_pattern
```

**Benefits:**
- Better pattern deduplication
- Reduces redundancy
- Improves pattern quality

### 7. Incremental Processing Optimization

**Problem:** Incremental processing may not be fully utilized or optimized.

**Solution:**
```python
# Optimized incremental processing
class IncrementalProcessor:
    """Optimize incremental pattern updates"""
    
    async def incremental_update(
        self,
        detector: MLPatternDetector,
        events_df: pd.DataFrame,
        last_update_time: datetime,
        window_days: int = 30
    ) -> list[dict]:
        """
        Optimized incremental update:
        1. Only fetch events since last update
        2. Use cached patterns for context
        3. Update only affected patterns
        """
        
        # Fetch only new events
        new_events = events_df[events_df['timestamp'] > last_update_time]
        
        if new_events.empty:
            return []  # No new data
        
        # Get recent history for context (last window_days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        recent_events = events_df[events_df['timestamp'] > cutoff]
        
        # Run detector on recent events (not just new)
        # This ensures patterns reflect current window
        patterns = detector.detect_patterns(recent_events)
        
        # Filter to only patterns affected by new events
        affected_patterns = self._filter_affected_patterns(patterns, new_events)
        
        return affected_patterns
    
    def _filter_affected_patterns(
        self,
        patterns: list[dict],
        new_events: pd.DataFrame
    ) -> list[dict]:
        """Filter patterns to only those affected by new events"""
        new_device_ids = set(new_events['device_id'].unique())
        
        affected = []
        for pattern in patterns:
            pattern_devices = set(pattern.get('devices', []))
            if pattern_devices & new_device_ids:  # Intersection
                affected.append(pattern)
        
        return affected
```

**Benefits:**
- Faster incremental updates
- More efficient processing
- Better resource utilization

### 8. Pattern Type-Specific Optimizations

**Problem:** Different pattern types may need different processing strategies.

**Solution:**
```python
# Pattern type-specific optimizations
class PatternTypeOptimizer:
    """Optimize processing for specific pattern types"""
    
    OPTIMIZATIONS = {
        'co_occurrence': {
            'window_size': 5,  # minutes
            'max_pairs_per_device': 10,  # Limit pairs per device
            'min_time_between': 60,  # seconds - avoid rapid-fire co-occurrences
        },
        'time_of_day': {
            'time_bins': 15,  # minutes - bin size for time clustering
            'min_days_observed': 7,  # Minimum days to establish pattern
        },
        'sequence': {
            'max_sequence_length': 5,  # Maximum steps in sequence
            'max_gap_seconds': 300,  # Maximum gap between sequence steps
        },
        'session': {
            'session_gap_minutes': 30,
            'min_session_duration_minutes': 5,
        }
    }
    
    def optimize_detector_config(
        self,
        pattern_type: str,
        base_config: dict,
        events_df: pd.DataFrame
    ) -> dict:
        """Optimize detector configuration based on data characteristics"""
        
        if pattern_type not in self.OPTIMIZATIONS:
            return base_config
        
        optimizations = self.OPTIMIZATIONS[pattern_type]
        optimized = base_config.copy()
        
        # Adjust based on data volume
        event_count = len(events_df)
        if event_count > 100000:
            # Large dataset - use more aggressive filtering
            if 'min_occurrences' in optimized:
                optimized['min_occurrences'] = max(
                    optimized['min_occurrences'],
                    optimizations.get('min_occurrences_large', 20)
                )
        
        # Merge type-specific optimizations
        optimized.update(optimizations)
        
        return optimized
```

**Benefits:**
- Better performance for each pattern type
- Adaptive configuration based on data
- Type-specific optimizations

## Implementation Priority

### High Priority (Immediate Impact)
1. **Pattern Occurrence Accumulation Fix** - Prevents unbounded growth
2. **Detector Health Monitoring** - Visibility into failures
3. **Pattern Lifecycle Management** - Automatic cleanup

### Medium Priority (Quality Improvements)
4. **Enhanced Quality Scoring** - Better prioritization
5. **Pattern Clustering Enhancement** - Better deduplication
6. **Incremental Processing Optimization** - Performance

### Low Priority (Nice to Have)
7. **Adaptive Threshold Tuning** - Automatic optimization
8. **Pattern Type-Specific Optimizations** - Fine-tuning

## Expected Outcomes

After implementing improvements:

- **Pattern Quality:** Higher percentage of actionable patterns (80%+)
- **Pattern Count:** More balanced distribution across pattern types
- **Performance:** Faster incremental updates (50%+ reduction)
- **Visibility:** Clear health metrics for all detectors
- **Maintenance:** Automatic cleanup of stale patterns
- **Accuracy:** Time-windowed occurrence tracking reflects current usage

## Next Steps

1. Review and prioritize improvements
2. Implement high-priority items
3. Test with current dataset
4. Monitor detector health
5. Iterate based on results

---

**Note:** This review focuses on engine improvements only. UI/UX improvements are out of scope per requirements.

