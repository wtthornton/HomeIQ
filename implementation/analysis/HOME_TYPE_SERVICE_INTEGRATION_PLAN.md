# Home Type Categorization - Service Integration Plan

**Date:** November 2025  
**Status:** Planning - Ready for Integration  
**Prerequisite:** HOME_TYPE_CATEGORIZATION_IMPLEMENTATION_PLAN.md (Phases 1-7 complete)  
**Epic:** Home Type Categorization & Event Category Mapping  
**Last Updated:** November 2025  
**Review:** See HOME_TYPE_INTEGRATION_PLAN_REVIEW.md for NUC optimization and 2025 best practices validation

---

## Executive Summary

This plan integrates the **Home Type Categorization System** (implemented per HOME_TYPE_CATEGORIZATION_IMPLEMENTATION_PLAN.md) into existing services to leverage home type context for improved automation suggestions, pattern detection, and event categorization.

**Expected Benefits:**
- **+15-20%** suggestion acceptance rate improvement
- **+10-15%** pattern detection quality improvement
- **+20-40%** faster category-based queries
- **+5-10%** validation accuracy improvement

**Assumptions:**
- ✅ Core home type system is complete (model trained, profiling working, classification functional)
- ✅ Home type API endpoints exist (`/api/home-type/profile`, `/api/home-type/classify`)
- ✅ Database schema includes `home_type_profiles` and `home_type_classifications` tables
- ✅ Daily batch job profiles home type at 3 AM

---

## 1. Integration Overview

### 1.1 Services to Integrate

| Service | Priority | Impact | Effort | ROI |
|---------|---------|--------|--------|-----|
| **AI Automation Service** | HIGH | +15-20% acceptance | 2-3 weeks | Very High |
| **Data API Service** | HIGH | +20-40% query speed | 1-2 weeks | High |
| **WebSocket Ingestion** | MEDIUM | Real-time tagging | 1-2 weeks | Medium |
| **Device Intelligence** | MEDIUM | +10-15% accuracy | 1 week | Medium |
| **Energy Correlator** | LOW | +5-10% accuracy | 3-5 days | Low-Medium |
| **Health Dashboard** | LOW | UX improvement | 1 week | Low |

### 1.2 Integration Phases

**Phase 1: Foundation (Week 1-2)**
- Home type client/service integration
- Caching strategy implementation
- Database access patterns

**Phase 2: Core Integrations (Week 3-6)**
- AI Automation Service integration (highest ROI)
- Data API event category endpoints
- WebSocket ingestion tagging

**Phase 3: Enhancements (Week 7-8)**
- Device Intelligence enhancement
- Energy Correlator enhancement
- Dashboard UI updates

---

## 2. Phase 1: Foundation Setup

### 2.1 Home Type Client Service

**Goal:** Create reusable client for accessing home type data across services

**File:** `services/ai-automation-service/src/clients/home_type_client.py`

```python
"""
Home Type Client (Single Home NUC Optimized)

Provides access to home type classification and profiling data.
Optimized for single home deployment with aggressive caching.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HomeTypeError(Exception):
    """Base exception for home type errors."""
    pass


class HomeTypeAPIError(HomeTypeError):
    """API error when fetching home type."""
    pass


class HomeTypeClient:
    """
    Client for accessing home type data (single home optimized).
    
    Features:
    - In-memory caching (24-hour TTL)
    - Connection pooling (httpx)
    - Retry logic with exponential backoff
    - Graceful fallback to default home type
    - Single home optimization (always 'default')
    """
    
    def __init__(self, base_url: str = "http://ai-automation-service:8018"):
        """
        Initialize home type client.
        
        Args:
            base_url: Base URL for home type API
        """
        self.base_url = base_url.rstrip('/')
        
        # Initialize HTTP client with connection pooling (2025 best practice)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
        )
        
        # Single home cache (not dict - just one entry for NUC optimization)
        self._cache: dict[str, Any] | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(hours=24)
        
        logger.info(f"HomeTypeClient initialized (base_url={self.base_url})")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_home_type(
        self,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get current home type classification (single home).
        
        Optimized for single home deployment - always uses 'default' home_id.
        
        Args:
            use_cache: Whether to use cached value
        
        Returns:
            {
                'home_type': str,
                'confidence': float,
                'method': str,
                'features_used': list[str],
                'last_updated': str
            }
        """
        # Check cache
        if use_cache and self._cache and self._cache_time:
            age = datetime.now(timezone.utc) - self._cache_time
            if age < self._cache_ttl:
                logger.debug(
                    f"Using cached home type: {self._cache['home_type']} "
                    f"(age: {age.total_seconds():.0f}s)"
                )
                return self._cache
        
        # Fetch from API (single home, always 'default')
        try:
            url = f"{self.base_url}/api/home-type/classify"
            response = await self.client.get(url, params={'home_id': 'default'})
            
            if response.status_code == 200:
                data = response.json()
                # Cache result
                data['cached_at'] = datetime.now(timezone.utc).isoformat()
                self._cache = data
                self._cache_time = datetime.now(timezone.utc)
                
                logger.info(
                    "Home type fetched",
                    extra={
                        "home_type": data.get("home_type"),
                        "confidence": data.get("confidence"),
                        "cached": False
                    }
                )
                return data
            else:
                logger.warning(
                    f"Failed to get home type: HTTP {response.status_code}",
                    extra={"status_code": response.status_code}
                )
                return self._get_default_home_type()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching home type: {e}")
            raise HomeTypeAPIError(f"Failed to fetch home type: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching home type: {e}", exc_info=True)
            return self._get_default_home_type()
    
    async def startup(self):
        """
        Pre-fetch home type on service startup.
        
        This ensures home type is available immediately when needed.
        """
        try:
            await self.get_home_type(use_cache=False)
            logger.info("Home type pre-fetched at startup")
        except Exception as e:
            logger.warning(
                f"Failed to pre-fetch home type: {e}, will use default",
                exc_info=True
            )
    
    def _get_default_home_type(self) -> dict[str, Any]:
        """Return default home type when API unavailable."""
        return {
            'home_type': 'standard_home',
            'confidence': 0.5,
            'method': 'default_fallback',
            'features_used': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
    
    def clear_cache(self):
        """Clear cache (for testing or manual refresh)."""
        self._cache = None
        self._cache_time = None
        logger.debug("Home type cache cleared")
    
    async def close(self):
        """Close HTTP client (call on service shutdown)."""
        await self.client.aclose()
        logger.debug("HomeTypeClient closed")
```

**Integration Points:**
- Initialize in service startup
- Call `startup()` method to pre-fetch home type
- Use in suggestion ranking, pattern detection, etc.
- Call `close()` on service shutdown
- Cache invalidation on home type update (via `clear_cache()`)

**2025 Best Practices Applied:**
- ✅ Uses `httpx` (not `aiohttp`) - matches codebase pattern
- ✅ Connection pooling for performance
- ✅ Retry logic with exponential backoff (tenacity)
- ✅ Structured error handling
- ✅ Single home optimization (simplified cache)
- ✅ Startup pre-fetch for immediate availability

---

### 2.2 Home Type Helper Functions

**File:** `services/ai-automation-service/src/home_type/integration_helpers.py`

```python
"""
Home Type Integration Helpers

Utility functions for home type-aware processing.
"""

from typing import Any


def get_home_type_preferred_categories(home_type: str) -> list[str]:
    """
    Get preferred suggestion categories for home type.
    
    Args:
        home_type: Home type classification
    
    Returns:
        List of preferred categories (ordered by preference)
    """
    preferences = {
        'security_focused': ['security', 'monitoring', 'lighting'],
        'climate_controlled': ['climate', 'energy', 'monitoring'],
        'high_activity': ['lighting', 'appliance', 'convenience'],
        'smart_home': ['automation', 'integration', 'convenience'],
        'standard_home': ['lighting', 'climate', 'security'],
        'apartment': ['lighting', 'climate', 'space_optimization'],
    }
    return preferences.get(home_type, ['general', 'lighting', 'climate'])


def calculate_home_type_boost(
    suggestion_category: str,
    home_type: str,
    base_boost: float = 0.10
) -> float:
    """
    Calculate home type boost for suggestion ranking.
    
    Args:
        suggestion_category: Suggestion category
        home_type: Home type classification
        base_boost: Base boost value (default: 0.10 = 10%)
    
    Returns:
        Boost value (0.0 to base_boost)
    """
    preferred = get_home_type_preferred_categories(home_type)
    
    if suggestion_category in preferred:
        # Higher boost for more preferred categories
        index = preferred.index(suggestion_category)
        multiplier = 1.0 - (index * 0.2)  # 1.0, 0.8, 0.6, ...
        return base_boost * multiplier
    
    return 0.0


def adjust_pattern_thresholds(
    home_type: str,
    base_min_confidence: float = 0.7,
    base_min_occurrences: int = 10
) -> tuple[float, int]:
    """
    Adjust pattern detection thresholds based on home type.
    
    Args:
        home_type: Home type classification
        base_min_confidence: Base minimum confidence
        base_min_occurrences: Base minimum occurrences
    
    Returns:
        Tuple of (adjusted_confidence, adjusted_occurrences)
    """
    adjustments = {
        'security_focused': {
            'confidence_multiplier': 0.93,  # Lower threshold for security patterns
            'occurrences_multiplier': 0.9
        },
        'climate_controlled': {
            'confidence_multiplier': 0.95,
            'occurrences_multiplier': 0.85
        },
        'high_activity': {
            'confidence_multiplier': 0.90,  # More lenient for active homes
            'occurrences_multiplier': 0.8
        },
        'apartment': {
            'confidence_multiplier': 0.95,
            'occurrences_multiplier': 1.0  # No adjustment
        },
    }
    
    adjustment = adjustments.get(home_type, {})
    conf_mult = adjustment.get('confidence_multiplier', 1.0)
    occ_mult = adjustment.get('occurrences_multiplier', 1.0)
    
    return (
        base_min_confidence * conf_mult,
        int(base_min_occurrences * occ_mult)
    )
```

---

## 3. Phase 2: AI Automation Service Integration

### 3.1 Suggestion Ranking Enhancement

**Goal:** Add home type boost to multi-factor ranking formula

**File:** `services/ai-automation-service/src/database/crud.py`

**Current Code (lines 628-667):**
```python
# Enhanced multi-factor ranking (2025 - from ai_automation_suggester)
# Template match (30%) + Success rate (25%) + Preferences (15%) + 
# Energy (10%) + Utilization (15%) + Time (5%)
```

**Enhancement:**
```python
# Enhanced multi-factor ranking (2025 - with home type boost)
# Template match (30%) + Success rate (25%) + Preferences (15%) + 
# Energy (10%) + Utilization (15%) + Time (5%) + Home Type (10%)

# ... existing code ...

# 7. Home type boost (10% weight) - NEW
# Note: This is calculated in Python layer after query
# We'll add it to weighted_score in post-processing
```

**New Function:**
```python
async def get_suggestions_with_home_type(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 50,
    home_type: str | None = None
) -> list[Suggestion]:
    """
    Get suggestions with home type boost applied.
    
    This function extends get_suggestions() with home type awareness.
    """
    # Get base suggestions
    suggestions = await get_suggestions(db, status=status, limit=limit * 2)
    
    # Apply home type boost if available
    if home_type:
        from ..home_type.integration_helpers import calculate_home_type_boost
        
        for suggestion in suggestions:
            category = suggestion.category or 'general'
            home_type_boost = calculate_home_type_boost(
                category,
                home_type,
                base_boost=0.10
            )
            # Add to weighted score
            suggestion.weighted_score = (
                (suggestion.weighted_score or suggestion.confidence) + 
                home_type_boost
            )
        
        # Re-sort by new weighted score
        suggestions.sort(key=lambda s: s.weighted_score or 0.0, reverse=True)
    
    # Return top N
    return suggestions[:limit]
```

**Integration Point:**
- Update `suggestion_router.py` to use new function
- Fetch home type at request time (cached)
- Apply boost before returning suggestions

---

### 3.2 Pattern Detection Enhancement

**Goal:** Adjust pattern detection thresholds based on home type

**File:** `services/ai-automation-service/src/scheduler/daily_analysis.py`

**Current Code (around line 456-492):**
```python
contextual_detector = ContextualDetector(
    weather_weight=0.3,
    presence_weight=0.4,
    time_weight=0.3,
    min_context_occurrences=5,
    min_confidence=0.6,
    enable_incremental=self.enable_incremental,
    aggregate_client=aggregate_client
)
```

**Enhancement:**
```python
# Get home type for threshold adjustment
from ..clients.home_type_client import HomeTypeClient
home_type_client = HomeTypeClient()
home_type_data = await home_type_client.get_home_type('default')
home_type = home_type_data.get('home_type', 'standard_home')

# Adjust thresholds based on home type
from ..home_type.integration_helpers import adjust_pattern_thresholds
min_confidence, min_occurrences = adjust_pattern_thresholds(
    home_type,
    base_min_confidence=0.6,
    base_min_occurrences=5
)

contextual_detector = ContextualDetector(
    weather_weight=0.3,
    presence_weight=0.4,
    time_weight=0.3,
    min_context_occurrences=min_occurrences,  # Adjusted
    min_confidence=min_confidence,  # Adjusted
    enable_incremental=self.enable_incremental,
    aggregate_client=aggregate_client
)
```

**Apply to All Detectors:**
- ContextualDetector
- RoomBasedDetector
- MLPatternDetector
- SeasonalDetector
- FusionDetector

---

### 3.3 Spatial Validation Enhancement

**Goal:** Use home type to inform spatial validation rules

**File:** `services/ai-automation-service/src/synergy_detection/spatial_validator.py`

**Enhancement:**
```python
class SpatialProximityValidator:
    """Validates device pairs based on semantic proximity."""
    
    def __init__(self, db_session=None, home_id: str = 'default', home_type: str | None = None):
        # ... existing init ...
        self.home_type = home_type
        self._spatial_tolerance = self._get_spatial_tolerance()
    
    def _get_spatial_tolerance(self) -> float:
        """
        Get spatial tolerance based on home type.
        
        Returns:
            Tolerance multiplier (0.8 = stricter, 1.2 = more lenient)
        """
        tolerances = {
            'apartment': 0.8,  # Stricter (smaller spaces)
            'multi-story': 1.2,  # More lenient (cross-floor OK)
            'standard_home': 1.0,  # Default
            'security_focused': 0.9,  # Slightly stricter
        }
        return tolerances.get(self.home_type, 1.0)
    
    async def are_semantically_proximate(
        self, 
        device1: dict, 
        device2: dict
    ) -> Tuple[bool, str]:
        """
        Check if two devices are semantically proximate.
        
        Enhanced with home type awareness.
        """
        # ... existing validation logic ...
        
        # Apply home type tolerance to distance calculations
        if self.home_type == 'multi-story':
            # Allow cross-floor relationships
            if self._is_cross_floor(device1, device2):
                return (True, "cross_floor_allowed")
        
        # ... rest of validation ...
```

---

### 3.4 Quality Framework Integration

**Goal:** Weight quality scores by home type relevance

**File:** `services/ai-automation-service/src/testing/pattern_quality_scorer.py`

**Enhancement:**
```python
class PatternQualityScorer:
    """Calculate quality scores for detected patterns"""
    
    def __init__(self, blueprint_validator=None, ground_truth_patterns=None, home_type: str | None = None):
        # ... existing init ...
        self.home_type = home_type
    
    def calculate_quality_score(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate comprehensive quality score for a pattern.
        
        Enhanced with home type relevance weighting.
        """
        # ... existing quality calculation ...
        
        # Apply home type relevance boost
        if self.home_type:
            home_type_relevance = self._calculate_home_type_relevance(pattern)
            # Boost quality score by up to 10%
            quality_score = min(1.0, base_quality * (1.0 + home_type_relevance * 0.1))
        else:
            quality_score = base_quality
        
        return {
            'quality_score': quality_score,
            'base_quality': base_quality,
            'home_type_relevance': home_type_relevance if self.home_type else None,
            # ... rest of return ...
        }
    
    def _calculate_home_type_relevance(self, pattern: dict[str, Any]) -> float:
        """
        Calculate how relevant pattern is to home type.
        
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not self.home_type:
            return 0.0
        
        # Check if pattern matches home type preferences
        pattern_type = pattern.get('pattern_type', '')
        device_domain = pattern.get('device_domain', '')
        
        # Security-focused homes prefer security patterns
        if self.home_type == 'security_focused':
            if pattern_type in ['motion', 'door', 'lock'] or device_domain == 'binary_sensor':
                return 0.8
        
        # Climate-controlled homes prefer climate patterns
        elif self.home_type == 'climate_controlled':
            if pattern_type in ['temperature', 'humidity'] or device_domain == 'climate':
                return 0.8
        
        # Default relevance
        return 0.3
```

---

## 4. Phase 2: Data API Service Integration

### 4.1 Event Category Tagging

**Goal:** Add event_category tag to InfluxDB schema and queries

**File:** `services/data-api/src/events_endpoints.py`

**Enhancement:**
```python
class EventFilter(BaseModel):
    """Event filtering parameters"""
    # ... existing fields ...
    event_category: str | None = None  # NEW: Filter by category
    home_type: str | None = None  # NEW: Use home type for category mapping

async def get_events(
    filter_params: EventFilter,
    # ... other params ...
):
    """
    Get events with optional category filtering.
    
    Enhanced with home type-aware categorization.
    """
    # Get home type if provided
    home_type = filter_params.home_type
    if home_type:
        # Use home type to determine category mappings
        from ..services.event_categorizer import EventCategorizer
        categorizer = EventCategorizer(home_type=home_type)
    else:
        categorizer = None
    
    # Build InfluxDB query with category filter
    query = f'''
        from(bucket: "{bucket}")
            |> range(start: {start_time}, stop: {stop_time})
            |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
    '''
    
    # Add category filter if specified
    if filter_params.event_category:
        query += f'|> filter(fn: (r) => r["event_category"] == "{filter_params.event_category}")'
    
    # ... rest of query ...
```

**New Endpoint:**
```python
@router.get("/api/events/categories")
async def get_event_categories(
    home_type: str | None = Query(None, description="Home type for category mapping"),
    hours: int = Query(24, description="Hours of history")
) -> dict[str, Any]:
    """
    Get event categories with counts.
    
    Uses home type to determine category mappings.
    """
    # ... implementation ...
```

---

### 4.2 Home Type API Endpoints

**Goal:** Expose home type data via Data API

**File:** `services/data-api/src/home_type_endpoints.py` (new file)

```python
"""
Home Type API Endpoints

Expose home type classification and profiling data.
"""

from fastapi import APIRouter, Query
from typing import Any

router = APIRouter(prefix="/api/home-type", tags=["Home Type"])


@router.get("/profile")
async def get_home_type_profile(
    home_id: str = Query('default', description="Home identifier")
) -> dict[str, Any]:
    """
    Get current home type profile.
    
    Returns comprehensive home profile including:
    - Device composition
    - Event patterns
    - Spatial layout
    - Behavior patterns
    """
    # Forward to ai-automation-service
    # ... implementation ...


@router.get("/classify")
async def classify_home_type(
    home_id: str = Query('default', description="Home identifier")
) -> dict[str, Any]:
    """
    Get current home type classification.
    
    Returns:
        {
            'home_type': str,
            'confidence': float,
            'method': str,
            'features_used': list[str]
        }
    """
    # Forward to ai-automation-service
    # ... implementation ...
```

---

## 5. Phase 2: WebSocket Ingestion Integration

### 5.1 Event Category Tag at Ingestion

**Goal:** Tag events with category at ingestion time

**File:** `services/websocket-ingestion/src/influxdb_schema.py`

**Enhancement:**
```python
class InfluxDBSchema:
    """InfluxDB schema design and data models"""
    
    def __init__(self):
        # ... existing tags ...
        self.TAG_EVENT_CATEGORY = "event_category"  # NEW
    
    def build_point(self, event: dict, home_type: str | None = None) -> Point:
        """
        Build InfluxDB point from event.
        
        Enhanced with event category tagging.
        """
        point = Point(self.MEASUREMENT_EVENTS)
        # ... existing tag/field assignments ...
        
        # Add event category tag
        if home_type:
            from ..event_categorizer import categorize_event
            category = categorize_event(event, home_type)
            point.tag(self.TAG_EVENT_CATEGORY, category)
        
        return point
```

**Caching Strategy:**
- Cache home type in memory (24-hour TTL)
- Refresh on daily batch job completion
- Fallback to default if unavailable

---

## 6. Phase 3: Enhancement Integrations

### 6.1 Device Intelligence Enhancement

**File:** `services/device-intelligence-service/src/core/device_parser.py`

**Enhancement:**
```python
class DeviceParser:
    """Parser for normalizing device data from multiple sources."""
    
    def __init__(self, home_type: str | None = None):
        # ... existing init ...
        self.home_type = home_type
    
    def _extract_device_class(self, entities: list[dict]) -> str | None:
        """
        Extract device class with home type context.
        
        Enhanced to prioritize device types relevant to home type.
        """
        # ... existing extraction logic ...
        
        # Apply home type boost
        if self.home_type == 'security_focused':
            # Boost security device classes
            if 'motion' in device_classes or 'door' in device_classes:
                return 'security'
        
        # ... rest of logic ...
```

---

### 6.2 Energy Correlator Enhancement

**File:** `services/energy-correlator/src/correlator.py`

**Enhancement:**
```python
class EnergyEventCorrelator:
    """Correlates Home Assistant events with power consumption changes"""
    
    def __init__(self, ..., home_type: str | None = None):
        # ... existing init ...
        self.home_type = home_type
        self._correlation_window = self._get_correlation_window()
    
    def _get_correlation_window(self) -> int:
        """
        Get correlation window based on home type.
        
        Different home types may have different power patterns.
        """
        windows = {
            'security_focused': 15,  # Longer window for security devices
            'climate_controlled': 5,  # Shorter window (predictable)
            'high_activity': 10,  # Medium window
        }
        return windows.get(self.home_type, 10)  # Default: 10 seconds
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Files to Test:**
- `test_home_type_client.py` - Client caching and API calls
- `test_integration_helpers.py` - Helper functions
- `test_suggestion_ranking.py` - Ranking with home type boost
- `test_pattern_detection.py` - Threshold adjustments
- `test_spatial_validation.py` - Home type-aware validation

**Test Coverage Target:** >90%

### 7.2 Integration Tests

**Test Scenarios:**
1. Suggestion ranking with home type boost
2. Pattern detection with adjusted thresholds
3. Event categorization at ingestion
4. API endpoint functionality
5. Cache invalidation on home type update

### 7.3 Performance Tests

**Metrics to Validate:**
- Home type API response time: <100ms
- Cache hit rate: >80%
- Suggestion ranking overhead: <10ms
- Pattern detection overhead: <50ms

---

## 8. Success Criteria

### 8.1 Functional Criteria

- [ ] Home type client caches data correctly (24-hour TTL)
- [ ] Suggestion ranking includes home type boost
- [ ] Pattern detection thresholds adjust based on home type
- [ ] Event categories tagged at ingestion
- [ ] API endpoints return home type data
- [ ] All services can access home type data

### 8.2 Performance Criteria

- [ ] Home type API: <100ms response time
- [ ] Cache hit rate: >80%
- [ ] Suggestion ranking overhead: <10ms
- [ ] Pattern detection overhead: <50ms
- [ ] No degradation in existing functionality

### 8.3 Quality Criteria

- [ ] Suggestion acceptance rate: +15-20% improvement
- [ ] Pattern quality: +10-15% improvement
- [ ] Query performance: +20-40% for category queries
- [ ] Test coverage: >90%
- [ ] No regressions in existing tests

---

## 9. Implementation Timeline

### Week 1-2: Foundation Setup
- [ ] Create HomeTypeClient
- [ ] Create integration helpers
- [ ] Implement caching strategy
- [ ] Unit tests for foundation

### Week 3-4: AI Automation Integration
- [ ] Suggestion ranking enhancement
- [ ] Pattern detection enhancement
- [ ] Spatial validation enhancement
- [ ] Quality framework integration
- [ ] Integration tests

### Week 5-6: Data API & Ingestion
- [ ] Event category endpoints
- [ ] Home type API endpoints
- [ ] Ingestion tagging
- [ ] Performance optimization
- [ ] Integration tests

### Week 7-8: Enhancements
- [ ] Device Intelligence enhancement
- [ ] Energy Correlator enhancement
- [ ] Dashboard UI updates
- [ ] End-to-end tests
- [ ] Documentation

---

## 10. Risks & Mitigations

### Risk 1: Home Type API Unavailable
**Mitigation:**
- Fallback to default home type
- Cache with 24-hour TTL
- Graceful degradation in all integrations

### Risk 2: Performance Impact
**Mitigation:**
- Aggressive caching
- Async API calls
- Batch processing where possible
- Performance monitoring

### Risk 3: Integration Complexity
**Mitigation:**
- Phased integration approach
- Comprehensive testing
- Rollback procedures
- Feature flags for gradual rollout

### Risk 4: Model Accuracy Issues
**Mitigation:**
- Monitor classification confidence
- Alert on low confidence (<0.7)
- Manual override capability
- Continuous model improvement

---

## 11. Dependencies

### Internal Dependencies
- ✅ Home Type Categorization System (HOME_TYPE_CATEGORIZATION_IMPLEMENTATION_PLAN.md)
- ✅ Home type API endpoints
- ✅ Database schema (home_type_profiles, home_type_classifications)
- ✅ Daily batch job (home type profiling)

### External Dependencies
- httpx (for async HTTP client - already in requirements.txt)
- tenacity (for retry logic - already in requirements.txt)
- Existing service infrastructure
- InfluxDB schema updates

---

## 12. Monitoring & Observability

### Metrics to Track
- Home type API response time
- Cache hit/miss rates
- Suggestion acceptance rate (before/after)
- Pattern detection quality scores
- Event categorization accuracy
- Error rates

### Alerts
- Home type API unavailable >5 minutes
- Cache hit rate <70%
- Suggestion acceptance rate drops
- Classification confidence <0.7

---

## 13. Documentation Updates

### Documents to Update
- `services/ai-automation-service/README.md` - Home type integration
- `docs/architecture/home-type-categorization.md` - Integration details
- `docs/api/home-type-api.md` - API documentation
- `docs/user/home-type-profiles.md` - User guide

---

## 14. Next Steps

### Immediate Actions
1. **Review & Approve Plan**
   - Review integration approach
   - Confirm resource allocation
   - Get approval for timeline

2. **Set Up Development Environment**
   - Create feature branch
   - Set up test infrastructure
   - Prepare integration test data

3. **Start Phase 1: Foundation**
   - Create HomeTypeClient
   - Implement caching
   - Write unit tests

### Preparation
1. **Verify Prerequisites**
   - Home type system is complete
   - API endpoints are functional
   - Database schema is deployed

2. **Set Up Monitoring**
   - Add metrics collection
   - Set up alerts
   - Create dashboards

---

## Status

**Current:** Planning Complete - Ready for Integration  
**Next:** Phase 1 - Foundation Setup  
**Owner:** AI Automation Service Team  
**Last Updated:** November 2025

