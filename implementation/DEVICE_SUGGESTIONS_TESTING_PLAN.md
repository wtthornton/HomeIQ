# Device-Based Automation Suggestions - Testing Plan

**Date:** January 14, 2026  
**Feature:** Device-Based Automation Suggestions  
**Status:** Ready for Testing

## Testing Overview

This document outlines the testing plan for the Device-Based Automation Suggestions feature, covering Phase 1 (Device Selection), Phase 2 (Suggestion Generation), and Phase 3 (Enhancement Flow).

## Prerequisites

### Service Dependencies
- ✅ `data-api` (port 8006) - Device/entity data
- ✅ `ha-ai-agent-service` (port 8030) - Suggestion generation endpoint
- ✅ `ai-automation-ui` (port 3000) - Frontend UI
- ⏭️ `ai-pattern-service` - Synergies (optional, not yet integrated)
- ⏭️ `blueprint-suggestion-service` - Blueprints (optional, not yet integrated)
- ⏭️ `sports-api` - Sports data (optional, not yet integrated)
- ⏭️ `weather-api` - Weather data (optional, not yet integrated)

### Test Data Requirements
- At least one device in the system (e.g., "Office Light Switch" - VZM31-SN by Inovelli)
- Device should have associated entities in Home Assistant
- Device should be linked to an area/location

## Phase 1 Testing: Device Selection

### Test 1.1: Device Picker UI
**Objective:** Verify device picker displays and functions correctly

**Steps:**
1. Navigate to HA Agent Chat page (`http://localhost:3000/agent`)
2. Click "Select Device" button in header
3. Verify device picker panel opens (sidebar on desktop, overlay on mobile)
4. Verify device list loads
5. Test search functionality:
   - Type device name in search box
   - Verify results filter in real-time
6. Test filters:
   - Select device type filter
   - Select area filter
   - Select manufacturer filter
   - Verify results update
7. Select a device from the list
8. Verify device picker closes
9. Verify selected device is displayed in context

**Expected Results:**
- ✅ Device picker opens/closes correctly
- ✅ Device list loads and displays devices
- ✅ Search filters results in real-time
- ✅ Filters work correctly
- ✅ Device selection updates UI

### Test 1.2: Device Context Display
**Objective:** Verify device context displays correctly after selection

**Steps:**
1. Select a device using device picker
2. Verify device context display appears above messages
3. Verify device information displays:
   - Device name
   - Manufacturer
   - Model
   - Area/location
   - Device type
   - Status indicator
4. Verify capabilities load (if available)
5. Verify related entities list displays
6. Click "Clear Selection" button
7. Verify device context disappears

**Expected Results:**
- ✅ Device context displays after selection
- ✅ All device metadata displays correctly
- ✅ Capabilities load (or gracefully handle missing data)
- ✅ Related entities display
- ✅ Clear selection works

### Test 1.3: Device API Service
**Objective:** Verify device API service functions correctly

**Steps:**
1. Open browser DevTools (Network tab)
2. Select a device using device picker
3. Verify API calls are made:
   - `GET /api/data/devices/{device_id}`
   - `GET /api/data/devices/{device_id}/capabilities` (if available)
   - `GET /api/data/entities?device_id={device_id}`
4. Verify API responses are successful (200 status)
5. Verify error handling (if API fails)

**Expected Results:**
- ✅ API calls are made correctly
- ✅ Responses are parsed correctly
- ✅ Error handling works (network errors, 404, etc.)
- ✅ Loading states display correctly

## Phase 2 Testing: Suggestion Generation

### Test 2.1: Suggestion Generation Backend
**Objective:** Verify backend endpoint generates suggestions

**Steps:**
1. Start all services (docker-compose up)
2. Test endpoint directly using curl or Postman:
   ```bash
   curl -X POST http://localhost:8030/api/v1/chat/device-suggestions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${API_KEY}" \
     -d '{
       "device_id": "device_id_here",
       "context": {
         "include_synergies": true,
         "include_blueprints": true,
         "include_sports": true,
         "include_weather": true
       }
     }'
   ```
3. Verify response structure:
   - `suggestions` array (3-5 suggestions)
   - `device_context` object
   - Each suggestion has required fields
4. Verify suggestion scores (confidence_score, quality_score)
5. Verify Home Assistant compatibility flags

**Expected Results:**
- ✅ Endpoint responds with 200 status
- ✅ Response structure matches API models
- ✅ Suggestions are generated (even if basic)
- ✅ Scores are between 0.0 and 1.0
- ✅ Device context is included

### Test 2.2: Suggestion Display UI
**Objective:** Verify suggestions display correctly in UI

**Steps:**
1. Navigate to HA Agent Chat page
2. Select a device
3. Verify suggestions appear below device context
4. Verify loading state displays while fetching
5. Verify suggestion cards display:
   - Title
   - Description
   - Automation preview (trigger → action)
   - Confidence/quality scores
   - Data source indicators
   - "Enhance" button
6. Verify multiple suggestions display (if available)
7. Verify empty state (if no suggestions)

**Expected Results:**
- ✅ Suggestions load after device selection
- ✅ Loading state displays correctly
- ✅ Suggestion cards display all metadata
- ✅ Scores display as percentages
- ✅ Data source indicators show correctly
- ✅ Empty state displays if no suggestions

### Test 2.3: Suggestion API Integration
**Objective:** Verify frontend API service integrates with backend

**Steps:**
1. Open browser DevTools (Network tab)
2. Select a device
3. Verify API call is made:
   - `POST /api/v1/chat/device-suggestions`
   - Request includes device_id and context
   - Request includes authentication headers
4. Verify response is parsed correctly
5. Verify error handling (if API fails):
   - Network error
   - 400 Bad Request
   - 500 Internal Server Error

**Expected Results:**
- ✅ API call is made with correct parameters
- ✅ Authentication headers are included
- ✅ Response is parsed correctly
- ✅ Error handling works (toast notifications)
- ✅ UI handles errors gracefully

## Phase 3 Testing: Enhancement Flow

### Test 3.1: Enhancement Button
**Objective:** Verify "Enhance" button starts conversation

**Steps:**
1. Select a device
2. Wait for suggestions to load
3. Click "Enhance" button on a suggestion
4. Verify chat input is pre-populated with suggestion context
5. Verify input field is focused
6. Edit the input message (optional)
7. Send the message
8. Verify conversation starts
9. Verify AI agent responds with enhancement suggestions

**Expected Results:**
- ✅ "Enhance" button pre-populates input
- ✅ Input field is focused
- ✅ User can edit the message
- ✅ Conversation starts successfully
- ✅ AI agent responds appropriately

### Test 3.2: Enhancement Conversation Flow
**Objective:** Verify enhancement conversation works end-to-end

**Steps:**
1. Click "Enhance" on a suggestion
2. Send the pre-populated message (or edit it)
3. Verify AI agent responds
4. Continue conversation to refine the suggestion
5. Verify AI agent validates device capabilities
6. Verify AI agent suggests alternatives if needed
7. Verify automation is created (if user approves)

**Expected Results:**
- ✅ Conversation flows naturally
- ✅ AI agent understands suggestion context
- ✅ Device capabilities are validated
- ✅ Alternatives are suggested when needed
- ✅ Automation can be created from enhanced suggestion

## Integration Testing

### Test I.1: End-to-End Flow
**Objective:** Verify complete workflow from device selection to automation creation

**Steps:**
1. Navigate to HA Agent Chat page
2. Click "Select Device"
3. Select a device (e.g., Office Light Switch)
4. Verify device context displays
5. Verify suggestions load
6. Click "Enhance" on a suggestion
7. Send message to enhance
8. Continue conversation to refine
9. Approve automation creation
10. Verify automation is created in Home Assistant

**Expected Results:**
- ✅ Complete workflow works end-to-end
- ✅ No errors or crashes
- ✅ All UI states transition correctly
- ✅ Automation is created successfully

### Test I.2: Error Scenarios
**Objective:** Verify error handling works correctly

**Scenarios:**
1. **Network Error:**
   - Disconnect network
   - Select device
   - Verify error message displays
   - Verify UI doesn't crash

2. **API Error (500):**
   - Simulate backend error
   - Verify error handling
   - Verify user-friendly error message

3. **No Devices:**
   - Test with empty device list
   - Verify empty state displays

4. **Device Not Found:**
   - Use invalid device_id
   - Verify error handling

**Expected Results:**
- ✅ All error scenarios handled gracefully
- ✅ User-friendly error messages
- ✅ UI doesn't crash
- ✅ User can recover from errors

## Performance Testing

### Test P.1: Load Time
**Objective:** Verify suggestions load within acceptable time

**Steps:**
1. Select a device
2. Measure time from selection to suggestion display
3. Verify load time < 5 seconds (target: 3-5 seconds)

**Expected Results:**
- ✅ Suggestions load within 5 seconds
- ✅ Loading state displays during fetch
- ✅ User experience is smooth

### Test P.2: UI Responsiveness
**Objective:** Verify UI remains responsive during operations

**Steps:**
1. Select device
2. While suggestions load, interact with UI
3. Verify UI remains responsive
4. Verify no UI freezing or blocking

**Expected Results:**
- ✅ UI remains responsive during API calls
- ✅ No UI freezing
- ✅ Smooth animations

## Browser Compatibility

### Test B.1: Browser Support
**Objective:** Verify feature works in supported browsers

**Browsers to Test:**
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest, if available)

**Steps:**
1. Test in each browser
2. Verify all functionality works
3. Verify UI displays correctly
4. Verify no console errors

**Expected Results:**
- ✅ Feature works in all supported browsers
- ✅ UI displays correctly
- ✅ No browser-specific issues

## Accessibility Testing

### Test A.1: Keyboard Navigation
**Objective:** Verify keyboard accessibility

**Steps:**
1. Use keyboard only (no mouse)
2. Navigate to device picker
3. Select device using keyboard
4. Navigate suggestions using keyboard
5. Use "Enhance" button with keyboard
6. Verify all interactions work

**Expected Results:**
- ✅ All features accessible via keyboard
- ✅ Focus indicators visible
- ✅ Tab order is logical

### Test A.2: Screen Reader
**Objective:** Verify screen reader compatibility

**Steps:**
1. Enable screen reader (NVDA, JAWS, or VoiceOver)
2. Navigate through device picker
3. Verify device information is announced
4. Verify suggestions are announced
5. Verify button labels are clear

**Expected Results:**
- ✅ Screen reader announces all elements
- ✅ Labels are descriptive
- ✅ Navigation is logical

## Test Results Template

```
Test Case: [Test ID]
Date: [Date]
Tester: [Name]
Browser: [Browser/Version]
Environment: [Dev/Staging/Prod]

Steps:
1. [Step 1]
2. [Step 2]
...

Expected: [Expected result]
Actual: [Actual result]
Status: [Pass/Fail/Skip]
Notes: [Any additional notes]
```

## Known Limitations

1. **Data Aggregation:**
   - Synergies API integration not yet implemented
   - Blueprints API integration not yet implemented
   - Sports data integration not yet implemented
   - Weather data integration not yet implemented

2. **Suggestion Generation:**
   - Currently uses basic suggestion generation
   - Can be enhanced with LLM or rule-based logic

3. **Device Capability Validation:**
   - Basic validation in place
   - Can be enhanced with more detailed validation

## Next Steps

1. Execute test plan
2. Document test results
3. Fix any issues found
4. Enhance suggestion generation
5. Integrate additional data sources
6. Improve device capability validation
