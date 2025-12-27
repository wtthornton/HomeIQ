# 7. Implementation Guide (Practical Examples)

### 7.1 Simple Pattern Detection Code Examples

**Keep It Simple Principle:** Use simplest approach that works. No over-engineering.

#### **Example 1: Time-of-Day Clustering (Story 1.4)**

```python
import pandas as pd
from sklearn.cluster import KMeans
from datetime import datetime

def detect_time_of_day_patterns(events: pd.DataFrame) -> list:
    """
    Simple KMeans clustering to find consistent usage times.
    
    Input: events DataFrame with columns [device_id, timestamp, state]
    Output: List of patterns with confidence scores
    """
    
    # 1. Feature engineering (keep simple!)
    events['hour'] = events['timestamp'].dt.hour
    events['minute'] = events['timestamp'].dt.minute
    events['time_decimal'] = events['hour'] + events['minute'] / 60
    
    patterns = []
    
    # 2. Analyze each device separately
    for device_id in events['device_id'].unique():
        device_events = events[events['device_id'] == device_id]
        
        # Need minimum data
        if len(device_events) < 5:
            continue
        
        # 3. Cluster time patterns (simple KMeans)
        times = device_events[['time_decimal']].values
        kmeans = KMeans(n_clusters=min(3, len(times)), random_state=42)
        labels = kmeans.fit_predict(times)
        
        # 4. Find consistent clusters (confidence = size / total)
        for cluster_id in range(kmeans.n_clusters):
            cluster_times = times[labels == cluster_id]
            
            if len(cluster_times) >= 3:  # Minimum 3 occurrences
                avg_time = cluster_times.mean()
                confidence = len(cluster_times) / len(times)
                
                if confidence > 0.7:  # Only high confidence
                    patterns.append({
                        'device_id': device_id,
                        'pattern_type': 'time_of_day',
                        'hour': int(avg_time),
                        'minute': int((avg_time % 1) * 60),
                        'occurrences': len(cluster_times),
                        'confidence': confidence
                    })
    
    return patterns

# That's it! ~40 lines, no complexity.
```

#### **Example 2: Device Co-Occurrence (Story 1.5)**

```python
from itertools import combinations
from collections import defaultdict

def detect_co_occurrence_patterns(events: pd.DataFrame, window_minutes=5) -> list:
    """
    Find devices used together within time window.
    Simple approach: sliding window + counting.
    """
    
    # 1. Sort by time
    events = events.sort_values('timestamp')
    
    # 2. Find co-occurrences
    co_occurrences = defaultdict(int)
    
    for i, event in events.iterrows():
        # Look ahead within window
        window_end = event['timestamp'] + pd.Timedelta(minutes=window_minutes)
        nearby = events[
            (events['timestamp'] > event['timestamp']) &
            (events['timestamp'] <= window_end)
        ]
        
        # Count co-occurrences
        for _, nearby_event in nearby.iterrows():
            if nearby_event['device_id'] != event['device_id']:
                # Create sorted pair (avoid duplicates)
                pair = tuple(sorted([event['device_id'], nearby_event['device_id']]))
                co_occurrences[pair] += 1
    
    # 3. Filter for significant patterns
    patterns = []
    total_events = len(events)
    
    for (device1, device2), count in co_occurrences.items():
        confidence = count / total_events
        
        if count >= 5 and confidence > 0.7:  # Thresholds
            patterns.append({
                'pattern_type': 'co_occurrence',
                'device1': device1,
                'device2': device2,
                'occurrences': count,
                'confidence': confidence
            })
    
    return patterns

# ~35 lines. Simple and effective.
```

#### **Example 3: Anomaly Detection (Story 1.6)**

```python
from sklearn.ensemble import IsolationForest

def detect_automation_opportunities(events: pd.DataFrame) -> list:
    """
    Find repeated manual interventions = automation opportunities.
    Use Isolation Forest to find "too regular" patterns.
    """
    
    # 1. Feature engineering
    events['hour'] = events['timestamp'].dt.hour
    events['day_of_week'] = events['timestamp'].dt.dayofweek
    
    patterns = []
    
    # 2. Analyze each device
    for device_id in events['device_id'].unique():
        device_events = events[events['device_id'] == device_id]
        
        if len(device_events) < 10:
            continue
        
        # 3. Create features
        features = device_events[['hour', 'day_of_week']].values
        
        # 4. Isolation Forest (inverted - find regular patterns, not anomalies)
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        scores = iso_forest.fit_predict(features)
        
        # 5. Regular patterns (NOT anomalies) = automation candidates
        regular = device_events[scores == 1]  # Inliers
        
        # Group by hour
        for hour in regular['hour'].unique():
            hour_events = regular[regular['hour'] == hour]
            
            if len(hour_events) >= 3:
                patterns.append({
                    'device_id': device_id,
                    'pattern_type': 'anomaly_opportunity',
                    'hour': hour,
                    'occurrences': len(hour_events),
                    'confidence': len(hour_events) / len(device_events)
                })
    
    return patterns

# ~40 lines. Isolation Forest = pattern detector.
```

---

### 7.2 Simple LLM Prompt Template (Story 1.7)

**Keep Prompts Simple - Don't Over-Engineer:**

```python
SIMPLE_AUTOMATION_PROMPT = """
You are a home automation expert. Create a Home Assistant automation based on this pattern.

PATTERN DETECTED:
- Device: {device_id}
- Pattern: Turns on at {hour}:{minute:02d} consistently
- Occurrences: {occurrences} times in last 30 days
- Confidence: {confidence:.0%}

OUTPUT (valid Home Assistant YAML):
alias: "AI Suggested: [descriptive name]"
trigger:
  - platform: time
    at: "{hour:02d}:{minute:02d}:00"
action:
  - service: [appropriate service]
    target:
      entity_id: {device_id}

Explain why this automation makes sense in 1-2 sentences.
"""

# That's it! No complex prompt engineering needed for MVP.
```

---

### 7.3 Data Schemas (Simple SQLite)

**Database Schema - Keep It Minimal:**

```sql
-- patterns table
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,          -- 'time_of_day', 'co_occurrence', 'anomaly'
    device_id TEXT,
    metadata JSON,              -- Pattern-specific data
    confidence REAL,
    occurrences INTEGER,
    created_at TIMESTAMP,
    
    INDEX idx_device (device_id),
    INDEX idx_type (pattern_type)
);

-- suggestions table
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY,
    pattern_id INTEGER,
    title TEXT,
    description TEXT,
    automation_yaml TEXT,       -- HA automation YAML
    status TEXT,                -- 'pending', 'approved', 'deployed', 'rejected'
    confidence REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deployed_at TIMESTAMP,
    ha_automation_id TEXT,      -- HA's ID after deployment
    
    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
);

-- user_feedback table
CREATE TABLE user_feedback (
    id INTEGER PRIMARY KEY,
    suggestion_id INTEGER,
    action TEXT,                -- 'approved', 'rejected', 'modified'
    feedback_text TEXT,         -- User's comments (optional)
    created_at TIMESTAMP,
    
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id)
);

-- No complex joins needed. Keep it simple.
```

---

### 7.4 API Endpoint Specifications (Story 1.10-1.11)

**Simple REST API - No Over-Engineering:**

```python
# GET /api/suggestions
# Query params: status, min_confidence, limit, offset
Response: {
    "suggestions": [
        {
            "id": 1,
            "title": "Morning Bedroom Lights",
            "description": "Turn on bedroom lights at 7 AM on weekdays",
            "confidence": 0.85,
            "status": "pending",
            "created_at": "2025-10-15T03:05:00Z"
        }
    ],
    "total": 8,
    "page": 1
}

# GET /api/suggestions/{id}
Response: {
    "id": 1,
    "title": "Morning Bedroom Lights",
    "pattern": {
        "type": "time_of_day",
        "hour": 7,
        "minute": 0,
        "occurrences": 42,
        "confidence": 0.93
    },
    "automation_yaml": "alias: ...\ntrigger: ...",
    "status": "pending"
}

# PATCH /api/suggestions/{id}
Body: {"status": "approved"}
Response: {"success": true, "deployed_automation_id": "automation.ai_morning_lights"}

# POST /api/deploy/{suggestion_id}
# Deploys to Home Assistant
Response: {"success": true, "ha_automation_id": "automation.1234"}
```

---

### 7.5 MQTT Message Examples (Story 1.12)

**Simple MQTT Messages - No Complex Schemas:**

```json
// Topic: ha-ai/events/suggestion/generated
{
  "event_type": "suggestions_ready",
  "count": 8,
  "timestamp": "2025-10-15T03:10:00Z"
}

// Topic: ha-ai/commands/automation/test
{
  "automation_id": "test_123",
  "device_id": "light.bedroom",
  "action": "turn_on"
}

// Topic: ha-ai/responses/automation/executed
{
  "automation_id": "morning_lights",
  "status": "success",
  "execution_time_ms": 234,
  "timestamp": "2025-10-15T07:00:01Z"
}
```

---

### 7.6 Key Implementation Principles (From Context7 KB)

**MVP-First Principles:**

1. ✅ **Start Simple** - Use simplest algorithm that works (KMeans before DBSCAN)
2. ✅ **Iterate Based on Data** - Don't optimize prematurely
3. ✅ **Measure Everything** - Log pattern counts, confidence scores, execution times
4. ✅ **Fail Fast** - Quick validation, discard low-confidence patterns early
5. ✅ **User Feedback Loop** - Track approval/rejection rates to improve

**Anti-Patterns to Avoid:**

1. ❌ **Over-Engineering** - Don't build complex hierarchies in Phase 1
2. ❌ **Premature Optimization** - Don't optimize before measuring
3. ❌ **Feature Creep** - Resist adding "just one more pattern type"
4. ❌ **Complex Prompt Engineering** - Simple prompts work for MVP
5. ❌ **Heavy Dependencies** - Avoid Prophet, deep learning in Phase 1

**Testing Strategy:**

```python
# Simple validation approach
def validate_pattern(pattern):
    """3 checks, that's it."""
    return (
        pattern['occurrences'] >= 3 and
        pattern['confidence'] > 0.7 and
        pattern['device_id'] in known_devices
    )

# Don't overthink it.
```

---

### 7.7 Reference Architecture Diagram

**Simple Data Flow (No Complex Orchestration):**

```
┌──────────────┐
│  Data API    │  (existing)
│  Port 8006   │
└──────┬───────┘
       │ HTTP GET /api/events?start=-30d
       │
┌──────▼───────────────────────────────────┐
│  Daily Batch Job (3 AM)                  │
│  ┌──────────────────────────────────┐    │
│  │ 1. Fetch data (pandas DataFrame) │    │
│  │ 2. Run 3 pattern detectors       │    │
│  │ 3. Store patterns (SQLite)       │    │
│  │ 4. Call OpenAI (top 5-10)        │    │
│  │ 5. Store suggestions (SQLite)    │    │
│  │ 6. Publish MQTT (done!)          │    │
│  └──────────────────────────────────┘    │
│  Time: 5-10 minutes                      │
└──────────────────────────────────────────┘
       │
       │ MQTT: ha-ai/status/analysis_complete
       │
┌──────▼───────┐
│  Frontend    │  User browses suggestions
│  Port 3002   │  Clicks "Approve"
└──────┬───────┘
       │
       │ POST /api/deploy/{id}
       │
┌──────▼──────────┐
│  AI Service     │  Converts to HA YAML
│  Port 8011      │  POST to HA API
└──────┬──────────┘
       │
       │ POST http://ha:8123/api/config/automation/config
       │
┌──────▼──────────┐
│  Home Assistant │  Automation now runs!
│  Port 8123      │
└─────────────────┘
```

**Total Complexity:** LOW  
**Moving Parts:** 5 services  
**Dependencies:** Minimal

---

### 7.8 Practical Development Tips

#### **For Backend Developers (Stories 1.2-1.12):**

**Start Here:**
1. Copy `services/data-api/` structure (proven pattern)
2. Use `shared/logging_config.py` (already exists)
3. Follow FastAPI patterns from `admin-api/src/main.py`
4. SQLite example in `services/sports-data/` (webhooks.db)

**Don't Reinvent:**
- ✅ Copy existing Docker patterns
- ✅ Reuse existing error handling
- ✅ Use existing health check format
- ✅ Follow existing logging patterns

#### **For Frontend Developers (Stories 1.13-1.17):**

**Start Here:**
1. Copy `services/health-dashboard/` structure
2. Copy `tailwind.config.js` exactly
3. Copy tab navigation from `Dashboard.tsx`
4. Copy modal pattern from `ServiceDetailsModal.tsx`
5. Copy hooks pattern from `useHealth.ts`

**Don't Reinvent:**
- ✅ Reuse SkeletonCard, ErrorBoundary, AlertBanner
- ✅ Copy status color helpers
- ✅ Use same dark mode pattern
- ✅ Follow same responsive breakpoints

---

### 7.9 Quick Reference: Key Files to Copy/Reference

| What You're Building | Reference This File | Why |
|---------------------|-------------------|-----|
| **FastAPI Service** | `services/admin-api/src/main.py` | Proven FastAPI setup |
| **SQLite Models** | `services/data-api/src/models/device.py` | SQLAlchemy patterns |
| **Docker Setup** | `services/data-api/Dockerfile` | Multi-stage build |
| **Tab Component** | `health-dashboard/src/components/tabs/OverviewTab.tsx` | Tab structure |
| **Modal Pattern** | `health-dashboard/src/components/ServiceDetailsModal.tsx` | Modal UX |
| **Custom Hook** | `health-dashboard/src/hooks/useHealth.ts` | Data fetching |
| **Card Component** | `health-dashboard/src/components/CoreSystemCard.tsx` | Card UI |

**Time Saved:** 20-30 hours by copying proven patterns

---

### 7.10 Common Pitfalls to Avoid

**Backend:**
1. ❌ Don't query InfluxDB directly (use Data API)
2. ❌ Don't block the main thread (use async/background jobs)
3. ❌ Don't store patterns in InfluxDB (use SQLite)
4. ❌ Don't over-complicate pattern detection (simple is better)
5. ❌ Don't send raw data to LLM (anonymize first)

**Frontend:**
1. ❌ Don't create new design system (copy health-dashboard)
2. ❌ Don't use different UI patterns (consistency matters)
3. ❌ Don't skip loading states (use skeletons)
4. ❌ Don't forget error boundaries (graceful failures)
5. ❌ Don't ignore mobile (44px touch targets)

**ML/AI:**
1. ❌ Don't use Prophet in Phase 1 (too heavy)
2. ❌ Don't implement complex hierarchies (Phase 1 = simple)
3. ❌ Don't tune hyperparameters excessively (defaults work)
4. ❌ Don't train models (use pre-built scikit-learn algorithms)
5. ❌ Don't cache LLM responses forever (7 day TTL max)

---

### 7.11 Success Metrics (Measure These)

**Phase 1 MVP Success:**

```python
# Track in SQLite and log these metrics
metrics = {
    'patterns_detected_per_run': 20-50,      # Target range
    'suggestions_generated_per_run': 5-10,   # Quality over quantity
    'user_approval_rate': '>60%',            # High acceptance
    'analysis_duration_minutes': '<10',      # Performance target
    'api_cost_monthly': '<$10',              # Budget constraint
    'memory_peak_mb': '<1000',               # Resource constraint
    'false_positive_rate': '<30%',           # Pattern quality
}
```

**How to Measure:**
1. Log all metrics during batch job
2. Store in SQLite for trending
3. Display in Insights Dashboard (Story 1.17)
4. Review weekly, adjust thresholds

---
