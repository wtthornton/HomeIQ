# Phase 4.1 Next Steps - Action Plan

**Date:** January 25, 2025  
**Status:** Ready for Next Phase

## ✅ What We Just Completed

1. **InfluxDB Attribute Querying** ✅
   - Implemented `fetch_entity_attributes()` method
   - Enhanced `FeatureAnalyzer` to detect feature usage from historical data
   - Fixed bug in `fetch_events()` method

## 🎯 Immediate Next Steps (Priority Order)

### Step 1: Test the Completed Enhancement (1-2 hours)

**Action:** Verify InfluxDB attribute querying works correctly

**Testing Steps:**

1. **Manual Test via Python Shell:**
   ```python
   # Test in ai-automation-service container or local environment
   from datetime import datetime, timedelta, timezone
   from services.ai_automation_service.src.clients.influxdb_client import InfluxDBEventClient
   
   # Initialize client
   client = InfluxDBEventClient(
       url="http://influxdb:8086",
       token="homeiq-token",
       org="homeiq",
       bucket="home_assistant_events"
   )
   
   # Test attribute querying for a light entity
   usage = await client.fetch_entity_attributes(
       entity_id="light.office",  # Replace with actual entity
       attributes=["brightness", "color_temp", "led_effect"]
   )
   print(f"Attribute usage: {usage}")
   # Expected: {"brightness": True/False, "color_temp": True/False, "led_effect": True/False}
   ```

2. **Test FeatureAnalyzer Integration:**
   ```python
   # Test that FeatureAnalyzer now detects features from attributes
   from services.ai_automation_service.src.device_intelligence.feature_analyzer import FeatureAnalyzer
   
   # Should now detect dimming, color_temp, etc. if attributes exist in InfluxDB
   analyzer = FeatureAnalyzer(
       device_intelligence_client=mock_client,
       db_session=db_session,
       influxdb_client=client  # Pass the InfluxDB client
   )
   
   analysis = await analyzer.analyze_device("light.office")
   print(f"Configured features: {analysis['configured_features']}")
   ```

3. **Verify Logs:**
   - Check that attribute queries are being executed
   - Verify no errors in InfluxDB query execution
   - Confirm feature detection is working

**Success Criteria:**
- ✅ Attribute queries return correct boolean values
- ✅ FeatureAnalyzer detects additional features (dimming, color_temp, etc.)
- ✅ No errors in logs
- ✅ Performance is acceptable (< 1 second per entity)

---

### Step 2: Implement Device Health Integration (2-3 hours)

**Goal:** Filter suggestions for devices with poor health scores

**Implementation Tasks:**

1. **Add Health Score Method to DataAPIClient**
   
   **File:** `services/ai-automation-service/src/clients/data_api_client.py`
   
   **Add method:**
   ```python
   async def get_device_health_score(self, device_id: str) -> dict[str, Any] | None:
       """
       Fetch device health score from Device Intelligence Service.
       
       Args:
           device_id: Device ID to check
       
       Returns:
           Health score dict with overall_score, health_status, or None if not found
       """
       try:
           # Device Intelligence Service runs on port 8028
           device_intel_url = os.getenv("DEVICE_INTELLIGENCE_URL", "http://device-intelligence-service:8028")
           response = await self.client.get(
               f"{device_intel_url}/api/health/scores/{device_id}",
               timeout=5.0
           )
           
           if response.status_code == 200:
               return response.json()
           else:
               logger.debug(f"Health score not available for {device_id}")
               return None
       except Exception as e:
           logger.warning(f"Failed to fetch health score for {device_id}: {e}")
           return None
   ```

2. **Add Health Filtering to Suggestion Generation**
   
   **File:** `services/ai-automation-service/src/api/suggestion_router.py`
   
   **Add check in `generate_suggestions()` function:**
   ```python
   # After device_context is built, before storing suggestion
   device_id = pattern_dict.get('device_id') or suggestion_data.get('device_id')
   
   if device_id:
       # Check device health
       health_score = await data_api_client.get_device_health_score(device_id)
       
       if health_score:
           overall_score = health_score.get('overall_score', 100)
           
           # Filter out suggestions for devices with poor health
           if overall_score < 50:  # Threshold: health_score < 50
               logger.info(f"Skipping suggestion for {device_id} - health_score too low: {overall_score}")
               continue  # Skip this suggestion
           
           # Add health info to metadata
           if not isinstance(suggestion_data.get('metadata'), dict):
               suggestion_data['metadata'] = {}
           suggestion_data['metadata']['health_score'] = overall_score
           suggestion_data['metadata']['health_status'] = health_score.get('health_status', 'unknown')
           
           # Add warning if health is fair
           if overall_score < 70:
               suggestion_data['metadata']['health_warning'] = True
   ```

3. **Add Health Display to UI (Optional - Future Step)**
   
   **File:** `services/ai-automation-ui/src/pages/ConversationalDashboard.tsx`
   
   **Add health warning badge:**
   ```typescript
   {suggestion.metadata?.health_warning && (
     <Badge color="warning">
       Device Health: {suggestion.metadata?.health_score}/100
     </Badge>
   )}
   ```

**Testing:**
- Test with device that has health_score < 50 (should be filtered)
- Test with device that has health_score 50-70 (should have warning)
- Test with device that has no health score (should proceed normally)

---

### Step 3: Implement Existing Automation Analysis (1-2 hours)

**Goal:** Filter out suggestions that duplicate existing automations

**Implementation Tasks:**

1. **Initialize Automation Checker in Suggestion Router**
   
   **File:** `services/ai-automation-service/src/api/suggestion_router.py`
   
   **Add at top of file (with other initializations):**
   ```python
   from ..synergy_detection.relationship_analyzer import HomeAssistantAutomationChecker
   from ..clients.ha_client import HomeAssistantClient
   
   # Initialize HA client and automation checker
   ha_client = None
   automation_checker = None
   
   if settings.ha_url and settings.ha_token:
       ha_client = HomeAssistantClient(
           ha_url=settings.ha_url,
           access_token=settings.ha_token
       )
       automation_checker = HomeAssistantAutomationChecker(ha_client)
       logger.info("HomeAssistantAutomationChecker initialized")
   ```

2. **Add Duplicate Check in Suggestion Generation**
   
   **In `generate_suggestions()` function, before storing suggestion:**
   ```python
   # Check for duplicate automations
   if automation_checker:
       try:
           device1 = suggestion_data.get('device1') or suggestion_data.get('device_id')
           device2 = suggestion_data.get('device2')
           
           # For co-occurrence patterns, check if automation already exists
           if device1 and device2:
               is_connected = await automation_checker.is_connected(device1, device2)
               
               if is_connected:
                   logger.info(f"Skipping suggestion - automation already exists for {device1} → {device2}")
                   continue  # Skip this suggestion
           
           # Add duplicate check metadata
           if not isinstance(suggestion_data.get('metadata'), dict):
               suggestion_data['metadata'] = {}
           suggestion_data['metadata']['duplicate_check_performed'] = True
           suggestion_data['metadata']['is_duplicate'] = False
           
       except Exception as e:
           logger.warning(f"Failed to check for duplicate automations: {e}")
           # Continue with suggestion if check fails
   ```

**Testing:**
- Test with entity pair that has existing automation (should be filtered)
- Test with new entity pair (should proceed)
- Test with HA client unavailable (should proceed with warning)

---

### Step 4: Validate and Test All Enhancements (1 hour)

**Action:** End-to-end testing of all Phase 4.1 enhancements

**Test Scenarios:**

1. **Attribute Querying:**
   - ✅ Feature detection works for lights with brightness changes
   - ✅ Feature detection works for lights without attribute history
   - ✅ Performance is acceptable

2. **Device Health Filtering:**
   - ✅ Suggestions filtered for devices with health_score < 50
   - ✅ Health warnings added for devices with health_score < 70
   - ✅ Suggestions proceed normally when health score unavailable

3. **Duplicate Automation Filtering:**
   - ✅ Suggestions filtered for entity pairs with existing automations
   - ✅ New entity pairs proceed normally
   - ✅ Graceful handling when HA unavailable

**Integration Test:**
```python
# Run full suggestion generation and verify:
# 1. Attributes are queried
# 2. Health filtering works
# 3. Duplicate checking works
# 4. Suggestions are stored correctly
```

---

## 📋 Checklist

### Immediate (Today/Tomorrow)
- [ ] **Test InfluxDB Attribute Querying** (Step 1)
  - [ ] Manual test via Python shell
  - [ ] Verify FeatureAnalyzer integration
  - [ ] Check logs for errors

### Short Term (This Week)
- [ ] **Implement Device Health Integration** (Step 2)
  - [ ] Add `get_device_health_score()` to DataAPIClient
  - [ ] Add health filtering to suggestion generation
  - [ ] Test health filtering logic

- [ ] **Implement Existing Automation Analysis** (Step 3)
  - [ ] Initialize AutomationChecker in router
  - [ ] Add duplicate check logic
  - [ ] Test duplicate filtering

### Validation (End of Week)
- [ ] **End-to-End Testing** (Step 4)
  - [ ] Test all enhancements together
  - [ ] Verify performance
  - [ ] Document results

---

## 🔧 Files That Need Modification

1. **`services/ai-automation-service/src/clients/data_api_client.py`**
   - Add `get_device_health_score()` method

2. **`services/ai-automation-service/src/api/suggestion_router.py`**
   - Add health filtering logic
   - Add duplicate automation checking
   - Initialize AutomationChecker

3. **`services/ai-automation-ui/src/pages/ConversationalDashboard.tsx`** (Optional)
   - Add health warning display
   - Show device health score in suggestion cards

---

## 📊 Success Metrics

Track these metrics after implementation:

1. **Feature Detection Improvement:**
   - % increase in features detected (before vs after attribute querying)
   - Accuracy of feature detection (manual validation)

2. **Suggestion Quality:**
   - % of suggestions filtered by health_score
   - % of duplicate automations filtered
   - User approval rate improvement

3. **Performance:**
   - Attribute query time (< 1 second per entity)
   - Health score lookup time (< 500ms)
   - Automation check time (< 2 seconds)

---

## 🚀 Quick Start Commands

### Test Attribute Querying:
```bash
# In ai-automation-service container
cd /app
python -c "
import asyncio
from datetime import datetime, timedelta, timezone
from src.clients.influxdb_client import InfluxDBEventClient

async def test():
    client = InfluxDBEventClient(
        url='http://influxdb:8086',
        token='homeiq-token',
        org='homeiq'
    )
    usage = await client.fetch_entity_attributes(
        entity_id='light.office',
        attributes=['brightness', 'color_temp']
    )
    print(usage)

asyncio.run(test())
"
```

### Test Device Health:
```bash
# Check if health endpoint is accessible
curl http://device-intelligence-service:8028/api/health/scores/{device_id}
```

---

## 💡 Tips

1. **Start with Testing:** Validate what we built before adding more features
2. **Incremental Approach:** Implement health filtering first (simpler), then duplicate checking
3. **Error Handling:** Always handle cases where services are unavailable gracefully
4. **Logging:** Add detailed logs to track what's being filtered and why
5. **Performance:** Cache health scores and automation lists to avoid repeated API calls

---

## 📚 Reference Documents

- Implementation Status: `implementation/analysis/SUGGESTIONS_PHASE4_IMPLEMENTATION_STATUS.md`
- Original Enhancement Plan: `implementation/SUGGESTIONS_ENGINE_IMPROVEMENT_PLAN.md`
- Data Integration Analysis: `implementation/DATA_INTEGRATION_ANALYSIS.md`

---

**Ready to proceed?** Start with Step 1 (Testing) to validate the completed work, then move to Step 2 (Device Health Integration).

