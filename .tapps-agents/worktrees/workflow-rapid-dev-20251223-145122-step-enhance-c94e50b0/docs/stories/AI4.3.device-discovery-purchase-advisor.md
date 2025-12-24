# Story AI4.3: Device Discovery & Purchase Advisor

**Epic:** AI-4 (Community Knowledge Augmentation)  
**Status:** InProgress  
**Created:** October 18, 2025  
**Estimated Effort:** 3-4 days  
**Dependencies:** Story AI4.1 (Community Corpus Foundation) ✅ Complete

---

## Story

**As a** Home Assistant user,  
**I want** to discover what I can do with my existing devices and get data-driven recommendations for new devices,  
**so that** I can maximize my home automation potential and make informed purchase decisions.

---

## Acceptance Criteria

### Functional Requirements

1. **"What Can I Do With This Device?" API**
   - `GET /api/automation-miner/devices/{device_type}/possibilities`
   - Query corpus for automations using specific device type
   - Return list of use cases with examples:
     - **Use case**: "Motion-activated lighting"
     - **Description**: "Turn on lights when motion detected, off after 5 min"
     - **Required devices**: motion_sensor, light
     - **Optional enhancements**: time_condition (night only), lux_sensor
     - **Community examples**: 3 high-quality automations
     - **Difficulty**: low | medium | high
   - Filter by user's existing devices (show what they can do NOW vs with new sensors)

2. **Device Gap Analysis & Recommendations**
   - `GET /api/automation-miner/recommendations/devices`
   - Analyze user's device inventory vs high-value automations in corpus
   - Identify "missing links": Devices that would unlock many new automations
   - Calculate **ROI score** for each recommendation:
     - `ROI = (new_automations_unlocked × avg_quality × use_frequency) / device_cost_estimate`
   - Return top 10 device recommendations:
     - Device type (e.g., "motion_sensor", "temperature_sensor")
     - Automations unlocked count
     - Example use cases (top 3)
     - Estimated cost range
     - ROI score
     - Compatible integrations (Zigbee, Z-Wave, WiFi)

3. **Integration Recommendations**
   - `GET /api/automation-miner/recommendations/integrations`
   - Identify popular integrations user doesn't have
   - Show automations enabled by each integration
   - Example: "MQTT enables 45 automations in corpus, including..."

### UI Requirements

4. **Discovery Tab in AI Automation UI** [[memory:9810709]]
   - New tab: "Discovery" (alongside Suggestions, Patterns, Events)
   - Section 1: **Device Explorer**
     - Dropdown: Select device from user's inventory
     - Display: "What you can automate with [device]"
     - Cards: 5-10 automation ideas with difficulty badges
     - Action: "See full list" → modal with all possibilities
   - Section 2: **Smart Shopping**
     - Cards: Top 5 device recommendations
     - For each: Device name, icon, automation count, cost estimate, "Learn More" button
     - Interactive graph: ROI visualization (automations unlocked vs cost)
   - Section 3: **Integration Opportunities**
     - List: Integrations user doesn't have
     - For each: Automation count, top use cases, "Setup Guide" link

5. **Interactive Visualizations** (using Dependencies Tab pattern) [[memory:9810709]]
   - Device dependency graph: Show which devices work together
   - Automation potential heatmap: Color-code devices by automation count
   - ROI chart: Bar chart of recommended devices sorted by ROI score

### Quality Requirements

6. **Recommendation Accuracy**
   - Only recommend devices available in corpus (≥50 automations)
   - Filter by user's integration preferences (don't recommend Z-Wave if user has only Zigbee)
   - Cost estimates within ±20% of market average
   - ROI calculation validated against manual analysis (±10%)

7. **Performance**
   - API response time: <200ms p95
   - Cache recommendations for 24 hours (corpus changes weekly)
   - UI loads <1s on modern browser

---

## Tasks / Subtasks

### Task 1: Implement Device Possibilities API (AC: 1)
- [ ] Create `services/automation-miner/src/api/device_routes.py`
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from typing import List
  from pydantic import BaseModel
  
  class AutomationPossibility(BaseModel):
      use_case: str
      description: str
      required_devices: List[str]
      optional_enhancements: List[str]
      examples: List[Dict[str, Any]]  # Top 3 community automations
      difficulty: Literal['low', 'medium', 'high']
      avg_quality: float
  
  router = APIRouter(prefix="/api/automation-miner/devices")
  
  @router.get("/{device_type}/possibilities")
  async def get_device_possibilities(
      device_type: str,
      user_devices: str = Query(None),  # Comma-separated list
      db: AsyncSession = Depends(get_db_session)
  ) -> List[AutomationPossibility]:
      """
      Get automation possibilities for a device type
      
      Example: /api/automation-miner/devices/motion_sensor/possibilities?user_devices=light,switch
      """
      
      repo = CorpusRepository(db)
      
      # Query corpus for automations using this device
      automations = await repo.search({
          'device': device_type,
          'min_quality': 0.7,
          'limit': 100
      })
      
      # Group by use case
      grouped = {}
      for auto in automations:
          use_case = auto['use_case']
          if use_case not in grouped:
              grouped[use_case] = []
          grouped[use_case].append(auto)
      
      # Build possibilities
      possibilities = []
      user_device_list = user_devices.split(',') if user_devices else []
      
      for use_case, autos in grouped.items():
          # Calculate what user CAN do vs COULD do
          required = set()
          optional = set()
          
          for auto in autos:
              for device in auto['devices']:
                  if device != device_type:
                      if device in user_device_list:
                          required.add(device)
                      else:
                          optional.add(device)
          
          possibilities.append(AutomationPossibility(
              use_case=use_case,
              description=self._generate_description(autos),
              required_devices=list(required),
              optional_enhancements=list(optional),
              examples=autos[:3],  # Top 3 by quality
              difficulty=self._calculate_difficulty(autos),
              avg_quality=sum(a['quality_score'] for a in autos) / len(autos)
          ))
      
      # Sort by feasibility (fewer required devices = higher)
      possibilities.sort(key=lambda p: (len(p.required_devices), -p.avg_quality))
      
      return possibilities
  ```
- [ ] Implement `_generate_description()` - Extract common pattern from examples
- [ ] Implement `_calculate_difficulty()` - Based on complexity, condition count
- [ ] Add caching (24 hour TTL)
- [ ] Add unit tests

### Task 2: Implement Device Recommendations API (AC: 2, 6)
- [ ] Create recommendation engine in `services/automation-miner/src/recommendations/device_recommender.py`
  ```python
  from pydantic import BaseModel
  from typing import List, Dict, Any
  
  class DeviceRecommendation(BaseModel):
      device_type: str
      automations_unlocked: int
      example_use_cases: List[str]  # Top 3
      cost_estimate_usd: tuple[int, int]  # (min, max)
      roi_score: float
      compatible_integrations: List[str]
      example_products: List[Dict[str, str]]  # [{name, vendor, url}]
  
  class DeviceRecommender:
      def __init__(self, corpus_repo: CorpusRepository):
          self.repo = corpus_repo
          self.device_costs = self._load_device_costs()  # From static JSON
      
      async def recommend_devices(
          self,
          user_devices: List[str],
          user_integrations: List[str],
          limit: int = 10
      ) -> List[DeviceRecommendation]:
          """
          Analyze gaps and recommend devices
          """
          
          # Get all automations from corpus
          all_automations = await self.repo.get_all(min_quality=0.7)
          
          # Count automations blocked by missing devices
          device_unlock_map = {}  # {device_type: [automations]}
          
          for auto in all_automations:
              # Check if user can already do this
              user_has_all = all(d in user_devices for d in auto['devices'])
              if user_has_all:
                  continue  # Skip automations user can already do
              
              # Find missing devices
              missing = [d for d in auto['devices'] if d not in user_devices]
              
              for missing_device in missing:
                  if missing_device not in device_unlock_map:
                      device_unlock_map[missing_device] = []
                  device_unlock_map[missing_device].append(auto)
          
          # Calculate ROI for each device
          recommendations = []
          
          for device_type, unlocked_autos in device_unlock_map.items():
              if len(unlocked_autos) < 10:  # Minimum threshold
                  continue
              
              # Average quality of unlocked automations
              avg_quality = sum(a['quality_score'] for a in unlocked_autos) / len(unlocked_autos)
              
              # Estimate usage frequency (simplistic: high quality = more useful)
              use_frequency = avg_quality * 0.8  # 0.0-0.8 scale
              
              # Get cost estimate
              cost_range = self.device_costs.get(device_type, (20, 50))  # Default $20-50
              avg_cost = (cost_range[0] + cost_range[1]) / 2
              
              # ROI calculation
              roi = (len(unlocked_autos) * avg_quality * use_frequency) / avg_cost
              
              # Extract use cases
              use_cases = list(set(a['use_case'] for a in unlocked_autos))
              
              # Compatible integrations
              integrations = list(set(
                  i for auto in unlocked_autos
                  for i in auto.get('integrations', [])
              ))
              
              recommendations.append(DeviceRecommendation(
                  device_type=device_type,
                  automations_unlocked=len(unlocked_autos),
                  example_use_cases=use_cases[:3],
                  cost_estimate_usd=cost_range,
                  roi_score=round(roi, 2),
                  compatible_integrations=integrations,
                  example_products=self._get_product_examples(device_type)
              ))
          
          # Sort by ROI descending
          recommendations.sort(key=lambda r: r.roi_score, reverse=True)
          
          return recommendations[:limit]
  ```
- [ ] Create `device_costs.json` with market price ranges
  ```json
  {
    "motion_sensor": [15, 35],
    "temperature_sensor": [20, 40],
    "door_sensor": [15, 30],
    "smart_plug": [15, 40],
    "light_bulb": [10, 60],
    "dimmer_switch": [25, 60],
    "occupancy_sensor": [40, 80],
    "water_leak_sensor": [20, 45]
  }
  ```
- [ ] Implement API endpoint:
  ```python
  @router.get("/recommendations/devices")
  async def recommend_devices(
      user_devices: str = Query(...),  # Required
      user_integrations: str = Query(""),
      limit: int = 10,
      db: AsyncSession = Depends(get_db_session)
  ):
      recommender = DeviceRecommender(CorpusRepository(db))
      recommendations = await recommender.recommend_devices(
          user_devices=user_devices.split(','),
          user_integrations=user_integrations.split(',') if user_integrations else [],
          limit=limit
      )
      return {"recommendations": recommendations, "count": len(recommendations)}
  ```
- [ ] Add integration tests

### Task 3: Implement Discovery Tab UI (AC: 4, 5, 7) [[memory:9810709]]
- [ ] Create `services/ai-automation-ui/src/pages/Discovery.tsx`
  ```typescript
  import React, { useState, useEffect } from 'react';
  import { DeviceExplorer } from '../components/DeviceExplorer';
  import { SmartShopping } from '../components/SmartShopping';
  import { IntegrationOpportunities } from '../components/IntegrationOpportunities';
  
  export const DiscoveryPage: React.FC = () => {
    const [userDevices, setUserDevices] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
      // Fetch user's devices from ai-automation-service
      fetch('/api/ai-automation/devices')
        .then(res => res.json())
        .then(data => {
          setUserDevices(data.devices.map(d => d.device_type));
          setLoading(false);
        });
    }, []);
    
    if (loading) return <div>Loading...</div>;
    
    return (
      <div className="discovery-page">
        <h1>Automation Discovery</h1>
        
        <section className="device-explorer">
          <h2>Device Explorer</h2>
          <p>See what you can automate with your existing devices</p>
          <DeviceExplorer devices={userDevices} />
        </section>
        
        <section className="smart-shopping">
          <h2>Smart Shopping Recommendations</h2>
          <p>Data-driven device suggestions to unlock new automations</p>
          <SmartShopping userDevices={userDevices} />
        </section>
        
        <section className="integrations">
          <h2>Integration Opportunities</h2>
          <p>Expand your automation possibilities</p>
          <IntegrationOpportunities />
        </section>
      </div>
    );
  };
  ```
- [ ] Create `DeviceExplorer.tsx` component
  - [ ] Dropdown to select device from user's inventory
  - [ ] Fetch possibilities: `GET /api/automation-miner/devices/{device}/possibilities?user_devices=...`
  - [ ] Display cards with automation ideas
  - [ ] Color-code by difficulty (green=low, yellow=medium, red=high)
  - [ ] "Can do now" badge if user has required devices
- [ ] Create `SmartShopping.tsx` component (use Dependencies Tab pattern) [[memory:9810709]]
  - [ ] Fetch: `GET /api/automation-miner/recommendations/devices?user_devices=...`
  - [ ] Display top 5 as interactive cards:
    ```tsx
    <div className="device-recommendation-card">
      <div className="device-icon">{getDeviceIcon(device.device_type)}</div>
      <h3>{formatDeviceName(device.device_type)}</h3>
      <div className="stats">
        <span className="automations-count">
          {device.automations_unlocked} automations
        </span>
        <span className="roi-score">ROI: {device.roi_score}</span>
      </div>
      <div className="cost-estimate">
        ${device.cost_estimate_usd[0]} - ${device.cost_estimate_usd[1]}
      </div>
      <button onClick={() => showDetails(device)}>Learn More</button>
    </div>
    ```
  - [ ] ROI bar chart using Chart.js or D3 (simple bars, not full graph lib)
  - [ ] Modal: "Learn More" shows example automations + product links
- [ ] Create `IntegrationOpportunities.tsx` component
  - [ ] Fetch integration recommendations
  - [ ] Display as list with setup guide links
- [ ] Add routing in main App.tsx: `/discovery`
- [ ] Update navigation to include "Discovery" tab

### Task 4: Device Costs Database (AC: 6)
- [ ] Research market prices for common devices (Amazon, Home Depot, specialized stores)
- [ ] Create `services/automation-miner/data/device_costs.json` with 30+ device types
- [ ] Add validation: Cost ranges must be (min, max) where min < max
- [ ] Add update script: `scripts/update-device-costs.py` (manual update quarterly)
- [ ] Document sources in comments

### Task 5: Testing & Documentation (AC: All)
- [ ] Unit tests:
  - [ ] `DeviceRecommender.recommend_devices()` with various user inventories
  - [ ] ROI calculation edge cases (zero cost, zero automations)
  - [ ] Device gap analysis accuracy
- [ ] Integration tests:
  - [ ] Full API flow: User devices → Recommendations → UI display
  - [ ] Test with empty user device list (recommend most popular)
  - [ ] Test with comprehensive list (recommend nichè devices)
- [ ] UI tests:
  - [ ] Discovery page loads and renders all sections
  - [ ] Device selection triggers API call
  - [ ] Shopping cards display correctly
- [ ] Performance tests:
  - [ ] API response time <200ms for recommendations
  - [ ] UI loads <1s (Lighthouse test)
- [ ] Documentation:
  - [ ] API endpoints in OpenAPI/Swagger
  - [ ] User guide: "How to use Discovery tab"
  - [ ] Update architecture docs with new endpoints

---

## Dev Notes

### ROI Calculation Details

**Formula:**
```
ROI = (automations_unlocked × avg_quality × use_frequency) / avg_cost

Where:
- automations_unlocked: Count of corpus automations requiring this device
- avg_quality: Average quality_score of those automations (0.0-1.0)
- use_frequency: Estimated usage rate = avg_quality × 0.8 (simplistic)
- avg_cost: Average of (min_cost + max_cost) / 2 in USD
```

**Example:**
```
motion_sensor unlocks 120 automations
avg_quality = 0.85
use_frequency = 0.85 × 0.8 = 0.68
avg_cost = ($15 + $35) / 2 = $25

ROI = (120 × 0.85 × 0.68) / 25 = 2.77
```

**Interpretation:**
- ROI > 3.0: Excellent purchase (many high-quality automations, low cost)
- ROI 1.5-3.0: Good purchase (decent automation potential)
- ROI < 1.5: Niche use case (consider if specific need)

### Device Dependency Graph (Optional Enhancement)

Using Dependencies Tab pattern [[memory:9810709]], show which devices work together:

```
┌─────────────┐
│ motion_sensor│ ──────┐
└─────────────┘       │
                      ├──> ┌─────────┐
┌─────────────┐       │    │  light  │
│ lux_sensor  │ ──────┘    └─────────┘
└─────────────┘

Click "light" → highlights connected devices (motion_sensor, lux_sensor)
```

Implementation:
- Extract device co-occurrence from corpus
- Build graph: nodes = devices, edges = co-occurrence count
- Use D3 force-directed layout (lightweight, no heavy graph library)
- Same interactive pattern as Dependencies Tab

### Integration with Existing UI

**Current UI Structure:**
```
health-dashboard (Port 3000)
ai-automation-ui (Port 3001)
├─ Suggestions tab
├─ Patterns tab
└─ Events tab
```

**New Structure:**
```
ai-automation-ui (Port 3001)
├─ Suggestions tab  (existing)
├─ Patterns tab     (existing)
├─ Events tab       (existing)
└─ Discovery tab    (NEW - Story AI4.3)
   ├─ Device Explorer
   ├─ Smart Shopping
   └─ Integration Opportunities
```

### Example Product Database (Sample)

```json
{
  "motion_sensor": [
    {
      "name": "Philips Hue Motion Sensor",
      "vendor": "Philips",
      "integration": "hue",
      "url": "https://www.philips-hue.com/...",
      "price_usd": 40
    },
    {
      "name": "Aqara Motion Sensor",
      "vendor": "Aqara",
      "integration": "zigbee2mqtt",
      "url": "https://www.aqara.com/...",
      "price_usd": 20
    }
  ],
  "temperature_sensor": [...]
}
```

### Caching Strategy

**Device Possibilities:**
- Key: `{device_type}:{user_devices_hash}`
- TTL: 24 hours
- Invalidate: After weekly corpus refresh

**Device Recommendations:**
- Key: `{user_devices_hash}:{user_integrations_hash}`
- TTL: 24 hours
- Invalidate: After weekly corpus refresh OR user adds new device

**Implementation:**
```python
from functools import lru_cache
import hashlib

def cache_key(devices: List[str]) -> str:
    return hashlib.md5(','.join(sorted(devices)).encode()).hexdigest()

@lru_cache(maxsize=1000)
def get_recommendations_cached(devices_hash: str):
    # ... implementation ...
    pass
```

### Performance Optimizations

**Database Queries:**
- Pre-compute device co-occurrence matrix (weekly job)
- Index on `devices` JSON field (GIN index in PostgreSQL, or full-text in SQLite)
- Materialize recommendations for common device sets (cache)

**UI Optimizations:**
- Lazy load Discovery tab (code splitting)
- Prefetch recommendations on app load (background)
- Debounce device selection (300ms delay before API call)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Story created with Discovery UI and ROI logic | BMad Master |

---

## Dev Agent Record

### Agent Model Used
*Populated during implementation*

### Debug Log References
*Populated during implementation*

### Completion Notes List
*Populated during implementation*

### File List
*Populated during implementation*

---

## QA Results
*QA Agent review pending*

