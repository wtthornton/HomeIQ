# Trigger Device Discovery - Manual Testing Guide

**Date:** November 4, 2025  
**Purpose:** Manual testing procedures for Phase 2 validation

---

## Prerequisites

### Services Required
- ✅ AI Automation Service (port 8018)
- ✅ AI Automation UI (port 3001)
- ✅ Device Intelligence Service (port 8021)
- ✅ Home Assistant (with presence sensors configured)

### Test Data Requirements
- Presence sensor in "office" area (e.g., `binary_sensor.ps_fp2_desk`)
- Motion sensor in "kitchen" area
- Door sensor (optional)
- Lights in various areas

---

## Test Scenarios

### Test 1: Presence Sensor Detection (Primary Use Case)

**Query:**  
```
When I sit at my desk. I wan the wled sprit to show fireworks for 15 sec and slowly run the 4 celling lights to energize.
```

**Expected Results:**
1. ✅ **Entity Extraction:**
   - Action devices: "wled sprit", "ceiling lights"
   - Area: "office"

2. ✅ **Trigger Condition Detection:**
   - Trigger type: "presence"
   - Location: "office"
   - Device class: "occupancy"

3. ✅ **Trigger Device Discovery:**
   - Found: Presence sensor (e.g., `binary_sensor.ps_fp2_desk`)
   - Sensor name: "PS FP2 Desk" or similar

4. ✅ **UI Display:**
   - Message shows: "I detected these devices: wled sprit, ceiling lights, PS FP2 Desk"
   - All three devices appear in the device list

5. ✅ **Automation Generation:**
   - YAML uses `binary_sensor.ps_fp2_desk` as trigger entity
   - NOT conceptual trigger like "SITTING AT THE DESK"

**Steps:**
1. Navigate to AI Automation UI (http://localhost:3001/ask-ai)
2. Enter the query above
3. Click "Ask AI"
4. Wait for response
5. Check the device detection message
6. Review the generated automation YAML (if available)
7. Verify trigger entity is actual sensor, not conceptual

---

### Test 2: Motion Sensor Detection

**Query:**  
```
When motion is detected in the kitchen, turn on the kitchen lights
```

**Expected Results:**
1. ✅ Trigger type: "motion"
2. ✅ Location: "kitchen"
3. ✅ Device class: "motion"
4. ✅ Motion sensor discovered (e.g., `binary_sensor.motion_kitchen`)
5. ✅ UI shows motion sensor in detected devices
6. ✅ Automation uses motion sensor entity as trigger

**Steps:**
1. Enter query
2. Submit
3. Verify motion sensor appears in detected devices
4. Check automation trigger uses motion sensor entity

---

### Test 3: Door Sensor Detection

**Query:**  
```
If the front door opens, turn on the hallway lights
```

**Expected Results:**
1. ✅ Trigger type: "door"
2. ✅ Location: "front" or detected area
3. ✅ Device class: "door"
4. ✅ Door sensor discovered
5. ✅ UI shows door sensor in detected devices

**Steps:**
1. Enter query
2. Submit
3. Verify door sensor appears in detected devices
4. Check automation trigger uses door sensor entity

---

### Test 4: Multiple Triggers

**Query:**  
```
When motion is detected or the door opens, turn on the lights
```

**Expected Results:**
1. ✅ Multiple trigger conditions detected
2. ✅ Multiple trigger devices discovered
3. ✅ UI shows all discovered trigger devices
4. ✅ Automation uses multiple trigger entities

**Steps:**
1. Enter query
2. Submit
3. Verify multiple trigger devices appear
4. Check automation uses multiple triggers

---

### Test 5: No Trigger Conditions (Control Test)

**Query:**  
```
Turn on the lights at 7am
```

**Expected Results:**
1. ✅ No trigger devices discovered (time-based, not sensor-based)
2. ✅ Only action devices appear
3. ✅ No error messages

**Steps:**
1. Enter query
2. Submit
3. Verify no trigger devices appear
4. Verify no errors

---

### Test 6: Edge Case - Ambiguous Location

**Query:**  
```
When I sit at my desk, turn on lights
```

**Expected Results:**
1. ✅ Presence trigger detected
2. ✅ Location may be "desk" or inferred from context
3. ✅ Presence sensor discovered (may search broader if desk area not found)
4. ✅ Sensor appears in detected devices

**Steps:**
1. Enter query
2. Submit
3. Verify presence sensor is discovered
4. Check if location matching works correctly

---

### Test 7: Error Handling - No Matching Sensors

**Query:**  
```
When I sit at my desk in the basement, turn on the lights
```

**Expected Results:**
1. ✅ Trigger condition detected (presence)
2. ✅ No sensors found (if basement has no presence sensors)
3. ✅ System degrades gracefully
4. ✅ Action devices still detected
5. ✅ No error messages shown to user
6. ✅ Automation may use conceptual trigger as fallback

**Steps:**
1. Enter query with location that has no sensors
2. Submit
3. Verify graceful degradation
4. Verify no errors shown

---

## Verification Checklist

### Entity Detection
- [ ] Action devices are detected
- [ ] Trigger devices are detected
- [ ] Areas are detected
- [ ] All devices appear in UI message

### Trigger Condition Analysis
- [ ] Trigger type correctly identified
- [ ] Location correctly extracted
- [ ] Device class correctly mapped
- [ ] Confidence scores present

### Trigger Device Discovery
- [ ] Sensors found matching conditions
- [ ] Entity IDs are correct
- [ ] Device metadata present (name, area, device_class)
- [ ] Duplicates filtered

### UI Display
- [ ] All devices listed in detection message
- [ ] Device names are readable
- [ ] No error messages for valid queries
- [ ] Loading indicators work

### Automation Generation
- [ ] Trigger entities use actual sensor entity IDs
- [ ] NOT using conceptual triggers
- [ ] YAML is valid
- [ ] Automation structure is correct

### Performance
- [ ] Response time < 3 seconds
- [ ] No timeouts
- [ ] UI remains responsive

---

## Logging and Debugging

### Check Logs

**AI Automation Service:**
```bash
docker logs ai-automation-service | grep -i trigger
```

**Look for:**
- "Discovered {N} trigger devices"
- "Found trigger condition: {type}"
- "No trigger devices discovered"
- Error messages (should not appear for valid queries)

### API Testing

**Direct API Call:**
```bash
curl -X POST http://localhost:8018/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "When I sit at my desk, turn on the lights",
    "user_id": "test_user"
  }'
```

**Check Response:**
- Look for `extracted_entities` array
- Verify trigger devices have `extraction_method: "trigger_discovery"`
- Verify trigger devices have `trigger_type` field

---

## Success Criteria

### Detection Rate
- ✅ >80% of presence trigger queries detect presence sensors
- ✅ >80% of motion trigger queries detect motion sensors
- ✅ >80% of door trigger queries detect door sensors

### Accuracy
- ✅ >90% of detected trigger devices are correct
- ✅ <10% false positives

### User Experience
- ✅ All detected devices appear in UI
- ✅ Trigger devices distinguished from action devices (future enhancement)
- ✅ No error messages for valid queries

### Automation Quality
- ✅ >90% of automations use actual trigger entities
- ✅ NOT using conceptual triggers when sensors exist

---

## Known Issues / Limitations

1. **Location Matching:** May not always match exact location names
2. **Multiple Sensors:** All matching sensors returned (no ranking yet)
3. **Confidence Scores:** Fixed values (not dynamic based on match quality)
4. **UI Distinction:** Trigger devices not visually distinguished from action devices (future enhancement)

---

## Reporting Issues

When reporting issues, include:

1. **Query Text:** Exact query used
2. **Expected Result:** What should have happened
3. **Actual Result:** What actually happened
4. **Logs:** Relevant log entries
5. **Sensors Available:** What sensors exist in the system
6. **Area Configuration:** How areas are configured in HA

**Example Issue Report:**
```
Query: "When I sit at my desk, turn on lights"
Expected: Presence sensor "PS FP2 Desk" detected
Actual: No trigger devices detected
Sensors Available: binary_sensor.ps_fp2_desk (occupancy, office area)
Logs: [paste relevant log entries]
```

---

## Next Steps After Manual Testing

1. **Fix Issues:** Address any bugs found during testing
2. **Update Patterns:** Add more trigger patterns if edge cases found
3. **Enhance UI:** Add visual distinction for trigger vs action devices
4. **Performance Tuning:** Optimize if response times are too high
5. **Documentation:** Update docs with findings
