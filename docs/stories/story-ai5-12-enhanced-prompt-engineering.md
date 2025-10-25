# Story AI5.12: Enhanced Prompt Engineering with Aggregates

**Epic:** AI-5 (Incremental Pattern Processing)  
**Story Type:** Enhancement (Optional - Phase 2)  
**Priority:** Medium  
**Effort:** 8-10 hours  
**Dependencies:** AI5.1-AI5.11 (complete Epic AI-5 first)

---

## Story Description

As an **AI Automation Service**,  
I want to **leverage daily pattern aggregates in OpenAI prompts**,  
So that **automation suggestions are more accurate and nuanced**.

---

## Problem Statement

**Current State:**
OpenAI prompts contain only summary statistics:
```
- Occurrences: 12 times in last 30 days
- Confidence: 85%
```

**Issues:**
- ❌ Limited context for LLM reasoning
- ❌ No trend information (strengthening/weakening)
- ❌ No day-of-week patterns
- ❌ No consistency metrics
- ❌ Generic suggestions without temporal nuance

**Opportunity:**
With Epic AI-5's daily aggregates, we can provide **30 days of rich temporal data** to OpenAI for better suggestions.

---

## Proposed Solution

### Enhanced Prompt Structure

**Before:**
```python
prompt = f"""
PATTERN DETECTED:
- Device: {device_name}
- Occurrences: {occurrences} times
- Confidence: {confidence:.0%}
"""
```

**After:**
```python
prompt = f"""
PATTERN DETECTED:
- Device: {device_name}

AGGREGATE ANALYSIS (30 Days):
- Total Occurrences: {total_occurrences}
- Active Days: {days_active}/30 ({active_percentage:.0%})
- Consistency Score: {consistency:.0%}
- Trend: {trend} ({trend_change:+.0%})
- Weekday Average: {weekday_avg:.1f}/day
- Weekend Average: {weekend_avg:.1f}/day
- Peak Hours: {peak_hours}

CONFIDENCE BREAKDOWN:
- Statistical: {stat_confidence:.0%}
- Stability: {stability:.0%}
- Recency: {recency:.0%}
- Overall: {recommendation_strength}
"""
```

---

## Technical Design

### 1. Aggregate Statistics Calculator

**File:** `src/llm/aggregate_stats.py` (NEW)

```python
class AggregateStatsCalculator:
    """Calculate statistics from daily pattern aggregates."""
    
    def calculate_time_of_day_stats(
        self,
        aggregates: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for time-of-day patterns.
        
        Args:
            aggregates: List of daily aggregates from InfluxDB
            
        Returns:
            Dictionary with:
            - total_occurrences: Total count
            - days_active: Number of days with activity
            - consistency: Consistency score (0-1)
            - trend: "strengthening", "stable", "weakening"
            - trend_percentage: Change percentage
            - weekday_avg: Average weekday occurrences
            - weekend_avg: Average weekend occurrences
            - peak_hours: List of peak activity hours
            - statistical_confidence: Statistical confidence score
            - stability_score: Pattern stability score
            - recency_score: Recent activity score
            - recommendation_strength: "strong", "moderate", "weak"
        """
        # Calculate total occurrences
        total_occurrences = sum(agg['count'] for agg in aggregates)
        
        # Calculate active days
        days_active = len([agg for agg in aggregates if agg['count'] > 0])
        
        # Calculate consistency (inverse of variance)
        counts = [agg['count'] for agg in aggregates]
        consistency = 1.0 - (np.std(counts) / (np.mean(counts) + 1e-6))
        
        # Calculate trend (compare last 7 days to previous 7 days)
        recent = aggregates[-7:]
        previous = aggregates[-14:-7]
        recent_avg = np.mean([agg['count'] for agg in recent])
        previous_avg = np.mean([agg['count'] for agg in previous])
        trend_percentage = ((recent_avg - previous_avg) / (previous_avg + 1e-6)) * 100
        
        if trend_percentage > 10:
            trend = "strengthening"
        elif trend_percentage < -10:
            trend = "weakening"
        else:
            trend = "stable"
        
        # Calculate weekday/weekend split
        weekday_counts = [agg['count'] for agg in aggregates if agg['day_of_week'] < 5]
        weekend_counts = [agg['count'] for agg in aggregates if agg['day_of_week'] >= 5]
        weekday_avg = np.mean(weekday_counts) if weekday_counts else 0
        weekend_avg = np.mean(weekend_counts) if weekend_counts else 0
        
        # Calculate peak hours
        hourly_dist = self._calculate_hourly_distribution(aggregates)
        peak_hours = sorted(hourly_dist, key=hourly_dist.get, reverse=True)[:3]
        
        # Calculate confidence scores
        statistical_confidence = min(1.0, total_occurrences / 10.0)  # 10+ occurrences = 100%
        stability_score = consistency
        recency_score = min(1.0, len([agg for agg in recent if agg['count'] > 0]) / 7.0)
        
        # Overall recommendation strength
        overall_score = (statistical_confidence + stability_score + recency_score) / 3.0
        if overall_score > 0.8:
            recommendation_strength = "strong"
        elif overall_score > 0.6:
            recommendation_strength = "moderate"
        else:
            recommendation_strength = "weak"
        
        return {
            'total_occurrences': total_occurrences,
            'days_active': days_active,
            'active_percentage': days_active / len(aggregates),
            'consistency': consistency,
            'trend': trend,
            'trend_percentage': trend_percentage,
            'weekday_avg': weekday_avg,
            'weekend_avg': weekend_avg,
            'peak_hours': peak_hours,
            'statistical_confidence': statistical_confidence,
            'stability_score': stability_score,
            'recency_score': recency_score,
            'recommendation_strength': recommendation_strength
        }
    
    def calculate_co_occurrence_stats(
        self,
        aggregates: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate statistics for co-occurrence patterns."""
        # Similar structure to time_of_day_stats
        # Add time delta statistics, temporal patterns, etc.
        pass
    
    def _calculate_hourly_distribution(
        self,
        aggregates: List[Dict]
    ) -> Dict[int, int]:
        """Calculate hourly distribution from aggregates."""
        hourly_dist = defaultdict(int)
        for agg in aggregates:
            hour = agg.get('hour', 0)
            hourly_dist[hour] += agg['count']
        return dict(hourly_dist)
```

---

### 2. Enhanced OpenAI Client Methods

**File:** `src/llm/openai_client.py`

**Changes:**

```python
class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # Existing code...
        self.stats_calculator = AggregateStatsCalculator()  # NEW
    
    def _build_time_of_day_prompt(
        self,
        pattern: Dict,
        device_context: Optional[Dict] = None,
        aggregates: Optional[List[Dict]] = None  # NEW parameter
    ) -> str:
        """Build time-of-day prompt with optional aggregate enhancement."""
        
        # Existing basic prompt building...
        basic_section = self._build_basic_pattern_section(pattern, device_context)
        
        # NEW: Add aggregate analysis if available
        if aggregates:
            stats = self.stats_calculator.calculate_time_of_day_stats(aggregates)
            aggregate_section = f"""
AGGREGATE ANALYSIS (30 Days):
- Total Activations: {stats['total_occurrences']}
- Active Days: {stats['days_active']}/30 ({stats['active_percentage']:.0%})
- Consistency Score: {stats['consistency']:.0%}
- Trend: {stats['trend']} ({stats['trend_percentage']:+.0%} change)
- Weekday Pattern: {stats['weekday_avg']:.1f} activations/day
- Weekend Pattern: {stats['weekend_avg']:.1f} activations/day
- Peak Activity Hours: {', '.join(map(str, stats['peak_hours']))}

CONFIDENCE BREAKDOWN:
- Statistical Confidence: {stats['statistical_confidence']:.0%}
- Pattern Stability: {stats['stability_score']:.0%}
- Recency Score: {stats['recency_score']:.0%}
- Overall Recommendation: {stats['recommendation_strength'].upper()}

AUTOMATION GUIDANCE:
- Priority: {"high" if stats['recommendation_strength'] == "strong" else "medium"}
- Conditions: {"Add weekday condition" if abs(stats['weekday_avg'] - stats['weekend_avg']) > 0.5 else "No day-of-week condition needed"}
- Reliability: {"Very reliable pattern" if stats['consistency'] > 0.8 else "Moderate reliability"}
"""
        else:
            aggregate_section = ""
        
        return f"""{basic_section}

{aggregate_section}

INSTRUCTIONS:
1. Create a valid Home Assistant automation in YAML format
2. Use the aggregate analysis to inform your automation design
3. If weekday/weekend patterns differ significantly, add day-of-week conditions
4. Adjust priority based on recommendation strength
5. Mention pattern trend and stability in rationale

OUTPUT FORMAT:
[... existing format ...]
"""
```

---

### 3. Aggregate Query Methods

**File:** `src/pattern_detection/time_of_day.py`

**Changes:**

```python
class TimeOfDayPatternDetector:
    async def get_pattern_aggregates(
        self,
        pattern_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Query daily aggregates for a specific pattern.
        
        Args:
            pattern_id: Pattern identifier
            days: Number of days to retrieve
            
        Returns:
            List of daily aggregate dictionaries
        """
        from ..data.pattern_aggregate_client import PatternAggregateClient
        
        client = PatternAggregateClient(
            influxdb_url=settings.influxdb_url,
            influxdb_token=settings.influxdb_token,
            influxdb_org=settings.influxdb_org,
            influxdb_bucket=settings.influxdb_bucket
        )
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        aggregates = await client.read_daily_aggregates(
            detector_type="time_of_day",
            start_time=start_time,
            end_time=end_time,
            pattern_id=pattern_id
        )
        
        return aggregates
```

---

### 4. Integration with Suggestion Generation

**File:** `src/scheduler/daily_analysis.py`

**Changes:**

```python
async def run_daily_analysis(self):
    """Run daily analysis with enhanced prompt generation."""
    
    # ... existing pattern detection code ...
    
    # Phase 4: Generate Suggestions (ENHANCED)
    logger.info("🤖 Phase 4/6: Generating AI suggestions...")
    
    for pattern in all_patterns:
        # NEW: Fetch aggregates for this pattern
        aggregates = await pattern_detector.get_pattern_aggregates(
            pattern_id=pattern['pattern_id'],
            days=30
        )
        
        # Generate suggestion with aggregates
        suggestion = await openai_client.generate_automation_suggestion(
            pattern=pattern,
            device_context=device_context,
            aggregates=aggregates  # NEW parameter
        )
        
        # Store suggestion...
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] `AggregateStatsCalculator` class implemented
- [ ] Time-of-day statistics calculation working
- [ ] Co-occurrence statistics calculation working
- [ ] OpenAI prompts enhanced with aggregate data
- [ ] Backward compatible (works without aggregates)
- [ ] Aggregate query methods added to detectors

### Quality Requirements
- [ ] Unit tests for statistics calculator (>90% coverage)
- [ ] Integration tests with OpenAI client
- [ ] Test fallback when aggregates unavailable
- [ ] Validate enhanced prompt structure
- [ ] Test with real OpenAI API

### Performance Requirements
- [ ] Aggregate query < 100ms
- [ ] Statistics calculation < 50ms
- [ ] Total prompt generation < 200ms
- [ ] No increase in OpenAI response time

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_aggregate_stats.py`

```python
def test_calculate_time_of_day_stats():
    """Test time-of-day statistics calculation."""
    calculator = AggregateStatsCalculator()
    
    # Mock aggregates (30 days)
    aggregates = [
        {'date': '2025-01-01', 'count': 2, 'hour': 19, 'day_of_week': 0},
        {'date': '2025-01-02', 'count': 1, 'hour': 19, 'day_of_week': 1},
        # ... 28 more days
    ]
    
    stats = calculator.calculate_time_of_day_stats(aggregates)
    
    assert stats['total_occurrences'] > 0
    assert 0 <= stats['consistency'] <= 1
    assert stats['trend'] in ['strengthening', 'stable', 'weakening']
    assert stats['recommendation_strength'] in ['strong', 'moderate', 'weak']

def test_enhanced_prompt_generation():
    """Test enhanced prompt with aggregates."""
    client = OpenAIClient(api_key="test")
    
    pattern = {'pattern_type': 'time_of_day', 'hour': 19, 'minute': 0}
    aggregates = [...]  # Mock data
    
    prompt = client._build_time_of_day_prompt(pattern, None, aggregates)
    
    assert "AGGREGATE ANALYSIS" in prompt
    assert "Consistency Score" in prompt
    assert "Trend:" in prompt
    assert "CONFIDENCE BREAKDOWN" in prompt

def test_backward_compatibility():
    """Test prompts work without aggregates."""
    client = OpenAIClient(api_key="test")
    
    pattern = {'pattern_type': 'time_of_day', 'hour': 19, 'minute': 0}
    
    # Should work without aggregates parameter
    prompt = client._build_time_of_day_prompt(pattern, None)
    
    assert prompt  # Non-empty
    assert "AGGREGATE ANALYSIS" not in prompt  # No aggregate section
```

---

## Implementation Checklist

### Step 1: Create Statistics Calculator (3h)
- [ ] Create `src/llm/aggregate_stats.py`
- [ ] Implement `calculate_time_of_day_stats()`
- [ ] Implement `calculate_co_occurrence_stats()`
- [ ] Add helper methods for trend/consistency
- [ ] Write unit tests

### Step 2: Enhance OpenAI Client (2h)
- [ ] Add `aggregates` parameter to prompt methods
- [ ] Update `_build_time_of_day_prompt()`
- [ ] Update `_build_co_occurrence_prompt()`
- [ ] Maintain backward compatibility
- [ ] Write unit tests

### Step 3: Add Aggregate Queries (2h)
- [ ] Add `get_pattern_aggregates()` to detectors
- [ ] Implement query logic using `PatternAggregateClient`
- [ ] Add caching for repeated queries
- [ ] Write integration tests

### Step 4: Integration (1h)
- [ ] Update `daily_analysis.py` to fetch aggregates
- [ ] Pass aggregates to suggestion generation
- [ ] Add error handling for missing aggregates
- [ ] Test end-to-end flow

### Step 5: Testing & Validation (1-2h)
- [ ] Run all unit tests
- [ ] Run integration tests
- [ ] Test with real OpenAI API
- [ ] Validate suggestion quality improvement
- [ ] Performance testing

---

## Deployment Notes

### Configuration
No new configuration needed - uses existing InfluxDB settings.

### Migration
- ✅ No database migration needed
- ✅ Backward compatible with existing code
- ✅ Works with or without aggregates

### Rollback
If issues occur:
1. Remove `aggregates` parameter from calls
2. Prompts revert to basic format
3. No data loss or breaking changes

---

## Success Metrics

### Before (Current)
- Generic automation suggestions
- Single confidence number
- No temporal context
- Basic time triggers

### After (Enhanced)
- Nuanced automation suggestions
- Confidence breakdown
- Rich temporal context
- Day-aware conditions

### Measurable Improvements
- **Prompt richness**: +200% more context
- **User satisfaction**: Target +20% approval rate
- **Suggestion accuracy**: Target +15% user acceptance
- **Cost increase**: ~30% (still < $1/year)

---

## Related Documents
- [Epic AI-5: Incremental Pattern Processing](epic-ai5-incremental-pattern-processing.md)
- [Story AI5.2: InfluxDB Daily Aggregates](story-ai5-2-influxdb-daily-aggregates.md)
- [ML Models Impact Analysis](story-ai5-ml-models-impact-analysis.md)

---

**Story Status:** Draft  
**Created:** 2025-01-15  
**Last Updated:** 2025-01-15

