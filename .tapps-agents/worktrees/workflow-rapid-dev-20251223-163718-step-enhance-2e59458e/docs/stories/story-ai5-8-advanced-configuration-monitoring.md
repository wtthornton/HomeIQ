# Story AI5.8: Advanced Configuration and Monitoring

**Story ID**: AI5.8  
**Title**: Advanced Configuration and Monitoring  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: Medium  
**Estimated Points**: 4  
**Dependencies**: AI5.3  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **system administrator**, I want to configure and monitor the unified contextual intelligence service so that I can optimize performance and troubleshoot issues.

## Acceptance Criteria

- [ ] Configuration system supports enabling/disabling individual contextual features
- [ ] Configuration supports different settings for user queries vs batch processing
- [ ] Monitoring includes contextual suggestion metrics and performance data
- [ ] Health checks include contextual service status
- [ ] Logging includes contextual decision-making information
- [ ] Configuration can be updated without service restart

## Technical Requirements

- **Configuration**: YAML-based configuration with environment variable overrides
- **Monitoring**: Metrics for contextual suggestion counts, performance, and errors
- **Health Checks**: Include contextual service health in existing health endpoints
- **Logging**: Structured logging for contextual decision-making
- **Hot Reload**: Configuration updates without service restart

## Implementation Details

### Files to Create/Modify
- `services/ai-automation-service/src/intelligence/config.py`
- `services/ai-automation-service/src/api/health_router.py`
- `services/ai-automation-service/infrastructure/env.ai-automation`
- `services/ai-automation-service/src/intelligence/monitoring.py`

### Configuration System

```python
# src/intelligence/config.py
from pydantic import BaseSettings, Field
from typing import Dict, Any

class ContextualConfig(BaseSettings):
    # Feature toggles
    enable_weather_context: bool = Field(default=True, description="Enable weather context")
    enable_energy_context: bool = Field(default=True, description="Enable energy context")
    enable_event_context: bool = Field(default=True, description="Enable event context")
    
    # Performance settings
    weather_lookback_days: int = Field(default=7, description="Days of weather data to analyze")
    energy_lookback_days: int = Field(default=7, description="Days of energy data to analyze")
    event_lookback_days: int = Field(default=7, description="Days of event data to analyze")
    
    # Confidence thresholds
    weather_confidence_threshold: float = Field(default=0.6, description="Minimum confidence for weather suggestions")
    energy_confidence_threshold: float = Field(default=0.6, description="Minimum confidence for energy suggestions")
    event_confidence_threshold: float = Field(default=0.6, description="Minimum confidence for event suggestions")
    
    # Performance limits
    max_contextual_suggestions: int = Field(default=10, description="Maximum contextual suggestions per query")
    contextual_timeout_seconds: int = Field(default=30, description="Timeout for contextual analysis")
    
    # Mode-specific settings
    user_query_mode: Dict[str, Any] = Field(default={
        "weather_lookback_days": 1,
        "max_suggestions": 5,
        "timeout_seconds": 10
    })
    
    batch_processing_mode: Dict[str, Any] = Field(default={
        "weather_lookback_days": 7,
        "max_suggestions": 20,
        "timeout_seconds": 60
    })
    
    class Config:
        env_file = "infrastructure/env.ai-automation"
        env_prefix = "CONTEXTUAL_"
```

### Monitoring System

```python
# src/intelligence/monitoring.py
from dataclasses import dataclass
from typing import Dict, Any
import time

@dataclass
class ContextualMetrics:
    weather_suggestions_generated: int = 0
    energy_suggestions_generated: int = 0
    event_suggestions_generated: int = 0
    total_contextual_suggestions: int = 0
    contextual_errors: int = 0
    average_response_time_ms: float = 0.0
    last_updated: float = 0.0

class ContextualMonitor:
    def __init__(self):
        self.metrics = ContextualMetrics()
        self.response_times = []
    
    def record_suggestion(self, context_type: str, response_time_ms: float):
        """Record a contextual suggestion generation"""
        if context_type == 'weather_aware':
            self.metrics.weather_suggestions_generated += 1
        elif context_type == 'energy_aware':
            self.metrics.energy_suggestions_generated += 1
        elif context_type == 'event_aware':
            self.metrics.event_suggestions_generated += 1
        
        self.metrics.total_contextual_suggestions += 1
        self.response_times.append(response_time_ms)
        self.metrics.average_response_time_ms = sum(self.response_times) / len(self.response_times)
        self.metrics.last_updated = time.time()
    
    def record_error(self):
        """Record a contextual processing error"""
        self.metrics.contextual_errors += 1
        self.metrics.last_updated = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "weather_suggestions": self.metrics.weather_suggestions_generated,
            "energy_suggestions": self.metrics.energy_suggestions_generated,
            "event_suggestions": self.metrics.event_suggestions_generated,
            "total_suggestions": self.metrics.total_contextual_suggestions,
            "errors": self.metrics.contextual_errors,
            "avg_response_time_ms": self.metrics.average_response_time_ms,
            "last_updated": self.metrics.last_updated
        }
```

## Definition of Done

- [ ] Configuration system implemented
- [ ] Monitoring metrics implemented
- [ ] Health checks updated
- [ ] Logging enhanced
- [ ] Hot reload functionality working
- [ ] Documentation updated
- [ ] Testing completed

## Testing

### Unit Tests
- Test configuration loading
- Test monitoring metrics
- Test health check integration
- Test logging functionality

### Integration Tests
- Test configuration hot reload
- Test monitoring in real scenarios
- Test health endpoint updates

## Risks

- **Configuration Complexity**: May be too complex for users
- **Performance Impact**: Monitoring may add overhead
- **Hot Reload Issues**: May cause instability

## Mitigation

- **Configuration**: Use sensible defaults and clear documentation
- **Performance**: Use efficient monitoring and caching
- **Hot Reload**: Thorough testing and graceful fallbacks
