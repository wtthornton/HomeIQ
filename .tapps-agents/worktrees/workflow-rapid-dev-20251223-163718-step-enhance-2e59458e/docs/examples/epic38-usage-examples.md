# Epic 38: Advanced Correlation Features - Usage Examples

**Epic:** 38 - Correlation Analysis Advanced Features  
**Status:** Complete  
**Last Updated:** November 25, 2025

---

## Overview

Epic 38 adds advanced correlation analysis features including:
- **Calendar Integration** - Presence-aware correlations based on calendar events
- **Augmented Analytics** - Automated pattern detection and correlation explanations
- **Automated Insights** - Natural language explanations and automation suggestions
- **Presence-Aware Correlations** - Correlations that consider user presence patterns

---

## Calendar Integration

### Basic Usage

```python
from datetime import datetime, timezone
from src.correlation import CalendarCorrelationIntegration

# Initialize calendar integration
calendar_integration = CalendarCorrelationIntegration(
    calendar_service_url="http://calendar-service:8013",
    cache_ttl=timedelta(hours=1),
    max_cache_size=100
)

# Connect to calendar service
await calendar_integration.connect()

try:
    # Get current presence
    timestamp = datetime.now(timezone.utc)
    current_presence = await calendar_integration.get_current_presence(timestamp)
    
    print(f"Currently home: {current_presence['currently_home']}")
    print(f"WFH today: {current_presence['wfh_today']}")
    print(f"Confidence: {current_presence['confidence']}")
    
    # Get predicted presence (next 24 hours)
    predicted_presence = await calendar_integration.get_predicted_presence(
        hours_ahead=24,
        timestamp=timestamp
    )
    
    print(f"Will be home: {predicted_presence['will_be_home']}")
    print(f"Next arrival: {predicted_presence['next_arrival']}")
    
    # Get presence features for correlation analysis
    presence_features = await calendar_integration.get_presence_features(timestamp)
    
    print(f"Current presence: {presence_features['current_presence']}")
    print(f"Predicted presence: {presence_features['predicted_presence']}")
    
finally:
    # Clean up
    await calendar_integration.close()
```

### Integration with Correlation Service

```python
from src.correlation import CorrelationService, CalendarCorrelationIntegration

# Initialize calendar integration
calendar_integration = CalendarCorrelationIntegration()

# Initialize correlation service with calendar integration
correlation_service = CorrelationService(
    calendar_integration=calendar_integration,
    enable_tabpfn=True,
    enable_streaming=True
)

# Compute correlation with presence awareness
entity1 = {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'}
entity2 = {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}
timestamp = datetime.now(timezone.utc)

correlation = await correlation_service.compute_correlation(
    entity1, entity2, timestamp=timestamp
)

# Correlation now includes presence features automatically
if correlation:
    print(f"Correlation: {correlation['correlation']}")
    print(f"Features: {correlation.get('features', {})}")
```

---

## Augmented Analytics

### Pattern Detection

```python
from src.correlation import AugmentedCorrelationAnalytics, CorrelationService

# Initialize correlation service
correlation_service = CorrelationService()

# Initialize augmented analytics
augmented_analytics = AugmentedCorrelationAnalytics(correlation_service)

# Define entities and correlations
entities = [
    {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'},
    {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'},
    {'entity_id': 'light.kitchen', 'domain': 'light', 'area_id': 'kitchen'}
]

correlations = [
    {
        'entity1_id': 'light.living',
        'entity2_id': 'binary_sensor.motion',
        'correlation': 0.85,
        'confidence': 0.9
    },
    {
        'entity1_id': 'light.kitchen',
        'entity2_id': 'binary_sensor.motion',
        'correlation': 0.75,
        'confidence': 0.8
    }
]

# Detect patterns
patterns = await augmented_analytics.detect_patterns(entities, correlations)

for pattern in patterns:
    print(f"Pattern: {pattern['pattern_type']}")
    print(f"Entities: {pattern['entities']}")
    print(f"Confidence: {pattern['confidence']}")
```

### Correlation Explanation

```python
# Explain a correlation
correlation_data = {
    'entity1_id': 'light.living',
    'entity2_id': 'binary_sensor.motion',
    'correlation': 0.85,
    'confidence': 0.9,
    'features': {
        'same_area': True,
        'temporal_proximity': 0.8,
        'same_device_type': False
    }
}

explanation = await augmented_analytics.explain_correlation(correlation_data)
print(explanation)

# Or use entity metadata directly
entity1 = {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'}
entity2 = {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}

explanation = await augmented_analytics.explain_correlation(
    entity1, entity2, correlation=0.85, confidence=0.9
)
print(explanation)
```

---

## Presence-Aware Correlations

### Analyzing Presence Correlations

```python
from src.correlation import (
    CorrelationService,
    CalendarCorrelationIntegration,
    PresenceAwareCorrelationAnalyzer
)

# Initialize components
calendar_integration = CalendarCorrelationIntegration()
correlation_service = CorrelationService(calendar_integration=calendar_integration)
presence_analyzer = PresenceAwareCorrelationAnalyzer(
    correlation_service,
    calendar_integration
)

# Analyze presence correlation for an entity
entity_id = 'light.living'
timestamp = datetime.now(timezone.utc)

analysis = await presence_analyzer.analyze_presence_correlations(
    entity_id,
    hours_back=168,  # 7 days
    timestamp=timestamp
)

print(f"Entity: {analysis['entity_id']}")
print(f"Presence correlation: {analysis['presence_correlation']}")
print(f"Home usage frequency: {analysis['home_usage_frequency']}")
print(f"Away usage frequency: {analysis['away_usage_frequency']}")
print(f"WFH usage frequency: {analysis['wfh_usage_frequency']}")
print(f"Presence-driven: {analysis['presence_driven']}")
print(f"Insights: {analysis['insights']}")
```

### Presence-Aware Automation Suggestions

```python
# Analyze presence correlation
analysis = await presence_analyzer.analyze_presence_correlations(
    'light.living',
    hours_back=168
)

# If presence-driven, generate automation suggestion
if analysis['presence_driven']:
    suggestion = await presence_analyzer.generate_presence_automation_suggestion(
        'light.living',
        analysis
    )
    
    print(f"Trigger: {suggestion['trigger']}")
    print(f"Action: {suggestion['action']}")
    print(f"Confidence: {suggestion['confidence']}")
```

---

## Automated Insights

### Generating Comprehensive Insights

```python
from src.correlation import (
    CorrelationService,
    AugmentedCorrelationAnalytics,
    PresenceAwareCorrelationAnalyzer,
    AutomatedCorrelationInsights
)

# Initialize components
calendar_integration = CalendarCorrelationIntegration()
correlation_service = CorrelationService(calendar_integration=calendar_integration)
augmented_analytics = AugmentedCorrelationAnalytics(correlation_service)
presence_analyzer = PresenceAwareCorrelationAnalyzer(
    correlation_service,
    calendar_integration
)

# Initialize automated insights
automated_insights = AutomatedCorrelationInsights(
    correlation_service,
    augmented_analytics=augmented_analytics,
    presence_analyzer=presence_analyzer
)

# Generate comprehensive insights
entity1_id = 'light.living'
entity2_id = 'binary_sensor.motion'
entity1_metadata = {'domain': 'light', 'area_id': 'living_room'}
entity2_metadata = {'domain': 'binary_sensor', 'area_id': 'living_room'}

insights = automated_insights.generate_correlation_insights(
    entity1_id,
    entity2_id,
    entity1_metadata,
    entity2_metadata
)

print(f"Summary: {insights['summary']}")
print(f"Correlation explanation: {insights['correlation_explanation']}")
print(f"Pattern detection: {insights['pattern_detection']}")
print(f"Presence insights: {insights.get('presence_insights')}")
print(f"Automation opportunity: {insights['automation_opportunity']}")
print(f"Recommendations: {insights['recommendations']}")
```

### Automation Suggestions

```python
# Generate automation suggestion from correlation
entity1_id = 'light.living'
entity2_id = 'binary_sensor.motion'
correlation_score = 0.85

suggestion = automated_insights.generate_automation_suggestion(
    entity1_id,
    entity2_id,
    correlation_score
)

print(f"Trigger: {suggestion['trigger']}")
print(f"Action: {suggestion['action']}")
print(f"Condition: {suggestion.get('condition')}")
print(f"Confidence: {suggestion['confidence']}")
print(f"Explanation: {suggestion['explanation']}")
```

### Natural Language Explanations

```python
# Generate natural language explanation
correlation_data = {
    'entity1_id': 'light.living',
    'entity2_id': 'binary_sensor.motion',
    'correlation': 0.85,
    'confidence': 0.9,
    'features': {
        'same_area': True,
        'temporal_proximity': 0.8
    }
}

explanation = automated_insights.generate_natural_language_explanation(
    correlation_data
)

print(explanation)
```

---

## End-to-End Workflow

### Complete Correlation Analysis Pipeline

```python
from datetime import datetime, timedelta, timezone
from src.correlation import (
    CorrelationService,
    CalendarCorrelationIntegration,
    AugmentedCorrelationAnalytics,
    PresenceAwareCorrelationAnalyzer,
    AutomatedCorrelationInsights
)

async def analyze_correlation_with_advanced_features():
    """Complete workflow for advanced correlation analysis"""
    
    # 1. Initialize all components
    calendar_integration = CalendarCorrelationIntegration()
    await calendar_integration.connect()
    
    correlation_service = CorrelationService(
        calendar_integration=calendar_integration,
        enable_tabpfn=True,
        enable_streaming=True
    )
    
    augmented_analytics = AugmentedCorrelationAnalytics(correlation_service)
    presence_analyzer = PresenceAwareCorrelationAnalyzer(
        correlation_service,
        calendar_integration
    )
    automated_insights = AutomatedCorrelationInsights(
        correlation_service,
        augmented_analytics=augmented_analytics,
        presence_analyzer=presence_analyzer
    )
    
    # 2. Define entities to analyze
    entity1 = {
        'entity_id': 'light.living',
        'domain': 'light',
        'area_id': 'living_room'
    }
    entity2 = {
        'entity_id': 'binary_sensor.motion',
        'domain': 'binary_sensor',
        'area_id': 'living_room'
    }
    timestamp = datetime.now(timezone.utc)
    
    try:
        # 3. Get presence features
        presence_features = await calendar_integration.get_presence_features(timestamp)
        print(f"Current presence: {presence_features['current_presence']}")
        
        # 4. Compute correlation
        correlation = await correlation_service.compute_correlation(
            entity1, entity2, timestamp=timestamp
        )
        
        if correlation:
            print(f"Correlation: {correlation['correlation']}")
            print(f"Confidence: {correlation['confidence']}")
            
            # 5. Generate explanation
            explanation = await augmented_analytics.explain_correlation(correlation)
            print(f"Explanation: {explanation}")
            
            # 6. Analyze presence correlation
            presence_analysis = await presence_analyzer.analyze_presence_correlations(
                entity1['entity_id'],
                hours_back=168,
                timestamp=timestamp
            )
            print(f"Presence correlation: {presence_analysis['presence_correlation']}")
            
            # 7. Generate comprehensive insights
            insights = automated_insights.generate_correlation_insights(
                entity1['entity_id'],
                entity2['entity_id'],
                entity1,
                entity2
            )
            print(f"Summary: {insights['summary']}")
            print(f"Recommendations: {insights['recommendations']}")
            
            # 8. Generate automation suggestion
            suggestion = automated_insights.generate_automation_suggestion(
                entity1['entity_id'],
                entity2['entity_id'],
                correlation['correlation']
            )
            print(f"Automation suggestion: {suggestion}")
    
    finally:
        # 9. Clean up
        await calendar_integration.close()

# Run the workflow
import asyncio
asyncio.run(analyze_correlation_with_advanced_features())
```

---

## Error Handling

### Graceful Fallback

```python
# Calendar integration gracefully falls back if service unavailable
calendar_integration = CalendarCorrelationIntegration(
    calendar_service_url="http://calendar-service:8013"
)

try:
    presence = await calendar_integration.get_current_presence()
    if presence['confidence'] < 0.5:
        # Low confidence - use fallback
        print("Using fallback presence data")
except Exception as e:
    # Service unavailable - uses conservative defaults
    print(f"Calendar service unavailable: {e}")
    # Integration returns default values automatically
```

### Handling Missing Data

```python
# Correlation service handles missing data gracefully
correlation = await correlation_service.compute_correlation(
    entity1, entity2, timestamp=timestamp
)

if correlation is None:
    print("Not enough data for correlation analysis")
    # Service returns None instead of raising exception
else:
    print(f"Correlation: {correlation['correlation']}")
```

---

## Performance Optimization

### Caching

```python
# Calendar integration uses caching automatically
calendar_integration = CalendarCorrelationIntegration(
    cache_ttl=timedelta(hours=1),  # Cache for 1 hour
    max_cache_size=100  # Maximum 100 cached entries
)

# First query (uncached)
start = time.time()
presence1 = await calendar_integration.get_current_presence(timestamp)
uncached_time = (time.time() - start) * 1000

# Second query (cached)
start = time.time()
presence2 = await calendar_integration.get_current_presence(timestamp)
cached_time = (time.time() - start) * 1000

print(f"Uncached: {uncached_time:.2f}ms")
print(f"Cached: {cached_time:.2f}ms")  # Should be <10ms
```

### Batch Processing

```python
# Process multiple entities efficiently
entities = [
    {'entity_id': f'light.room_{i}', 'domain': 'light'}
    for i in range(10)
]

# Compute correlations in batch
correlations = []
for i in range(len(entities) - 1):
    correlation = await correlation_service.compute_correlation(
        entities[i], entities[i+1]
    )
    if correlation:
        correlations.append(correlation)

# Generate insights in batch
insights = []
for corr in correlations:
    insight = automated_insights.generate_correlation_insights(
        corr['entity1_id'],
        corr['entity2_id']
    )
    insights.append(insight)
```

---

## Best Practices

1. **Always close connections**: Use `try/finally` to ensure calendar integration is closed
2. **Check for None**: Correlation methods may return None if insufficient data
3. **Use caching**: Calendar integration caches automatically - reuse instances
4. **Handle errors gracefully**: All components have fallback mechanisms
5. **Batch operations**: Process multiple entities together for efficiency
6. **Monitor performance**: Use performance tests to validate targets

---

**Created:** November 25, 2025  
**Last Updated:** November 25, 2025

