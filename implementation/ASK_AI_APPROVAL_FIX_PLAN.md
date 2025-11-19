# Ask AI Approval & Deployment Fix Plan

**Issue**: User clicks "APPROVE & CREATE" but no automation is created in Home Assistant
**Date**: November 19, 2025
**Status**: Analysis Complete - Ready for Implementation

## Problem Analysis

### 1. Log Analysis
From `docker compose logs ai-automation-service`:
- ✅ Clarification flow completed successfully
- ✅ 2 suggestions generated with 93% confidence
- ✅ Query record created: `clarify-9d171c32`
- ✅ Validated entities: `light.wled` (Office)
- ❌ **NO logs from approval endpoint `/query/{query_id}/suggestions/{suggestion_id}/approve`**
- ❌ **NO YAML generation logs**
- ❌ **NO deployment logs**

### 2. Root Causes Identified

#### A. Missing Approval Endpoint Call
**Evidence**: No log entry `"✅ Approving suggestion {suggestion_id} from query {query_id}"` (line 7129)

**Possible Causes**:
1. UI not calling the approval endpoint
2. Endpoint failing silently before first log
3. Wrong endpoint URL being called
4. Authentication/authorization failure

#### B. Inconsistent YAML Format Documentation
**Evidence**: Multiple conflicting formats in codebase:

```yaml
# Format 1 (CORRECT - 2025 Standard - ask_ai_router.py line 2064-2068)
trigger:      # SINGULAR
  - platform: state
action:       # SINGULAR
  - service: light.turn_on

# Format 2 (INCORRECT - Pre-2025 - nl_automation_generator.py line 326)
triggers:     # PLURAL
  - platform: state
actions:      # PLURAL
  - action: light.turn_on

# Format 3 (MIXED - action_parser.py line 23-24)
actions:      # PLURAL at top
  - action:   # with "action:" field inside
```

## Fix Plan

### Phase 1: Add Comprehensive Logging ✅

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. Add entry logging at line 7129 (BEFORE any processing)
2. Add logging after YAML generation (line 7194)
3. Add logging before HA deployment (line 7453)
4. Add logging after HA deployment success/failure
5. Add exception logging in try/except blocks

**Implementation**:
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(...):
    # Line 7129 - Add detailed entry logging
    logger.info(f"🚀 [APPROVAL START] query_id={query_id}, suggestion_id={suggestion_id}")
    logger.info(f"📝 [APPROVAL] Request body: {request}")
    
    try:
        # Line 7133 - Add query fetch logging
        logger.info(f"🔍 [APPROVAL] Fetching query record: {query_id}")
        query = await db.get(AskAIQueryModel, query_id)
        if not query:
            logger.error(f"❌ [APPROVAL] Query {query_id} not found in database")
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        logger.info(f"✅ [APPROVAL] Found query with {len(query.suggestions)} suggestions")
        
        # Line 7139 - Add suggestion search logging
        logger.info(f"🔍 [APPROVAL] Searching for suggestion_id={suggestion_id}")
        suggestion = None
        for s in query.suggestions:
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            logger.error(f"❌ [APPROVAL] Suggestion {suggestion_id} not found in query suggestions")
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")
        logger.info(f"✅ [APPROVAL] Found suggestion: {suggestion.get('title', 'Untitled')[:50]}")
        
        # Line 7194 - Add YAML generation logging
        logger.info(f"🔧 [YAML_GEN] Starting YAML generation for suggestion {suggestion_id}")
        logger.info(f"📋 [YAML_GEN] Validated entities: {final_suggestion.get('validated_entities')}")
        
        automation_yaml = await generate_automation_yaml(
            final_suggestion, 
            query.original_query, 
            [], 
            db_session=db, 
            ha_client=ha_client
        )
        
        logger.info(f"✅ [YAML_GEN] YAML generated successfully ({len(automation_yaml)} chars)")
        logger.info(f"📄 [YAML_GEN] First 200 chars: {automation_yaml[:200]}")
        
        # Line 7453 - Add deployment logging
        logger.info(f"🚀 [DEPLOY] Starting deployment to Home Assistant")
        creation_result = await ha_client.create_automation(automation_yaml)
        
        if creation_result.get('success'):
            automation_id = creation_result.get('automation_id')
            logger.info(f"✅ [DEPLOY] Successfully created automation: {automation_id}")
        else:
            error_msg = creation_result.get('error', 'Unknown error')
            logger.error(f"❌ [DEPLOY] Failed to create automation: {error_msg}")
            
    except Exception as e:
        logger.error(f"❌ [APPROVAL] Exception: {type(e).__name__}: {str(e)}")
        logger.error(f"❌ [APPROVAL] Stack trace:", exc_info=True)
        raise
```

### Phase 2: Standardize 2025 YAML Format ✅

**Files to Update**:
1. `services/ai-automation-service/src/api/ask_ai_router.py` (already correct)
2. `services/ai-automation-service/src/nl_automation_generator.py` (needs update)
3. `services/ai-automation-service/src/services/automation/action_parser.py` (needs clarification)

**2025 Standard Format** (Reference: Home Assistant 2025.x):
```yaml
id: 'unique_id_12345'
alias: "Descriptive Name"
description: "What it does"
mode: single

trigger:                    # ✅ SINGULAR at top level
  - platform: time_pattern  # ✅ "platform:" field REQUIRED
    minutes: "/15"          # ✅ Recurring every 15 minutes
    
conditions: []              # ✅ PLURAL (empty list if none)

action:                     # ✅ SINGULAR at top level  
  - service: light.turn_on  # ✅ "service:" field (NOT "action:")
    target:
      entity_id: light.wled
    data:
      brightness_pct: 100
  - delay: '00:15:00'       # ✅ Delay format
  - service: scene.turn_on  # ✅ Restore previous state
    target:
      entity_id: scene.office_previous
```

**Key Rules**:
- Top level: `trigger:` and `action:` (SINGULAR)
- Inside trigger items: `platform:` field (state, time, time_pattern, etc.)
- Inside action items: `service:` field (NOT `action:`)
- Time patterns: Use `time_pattern` with `minutes: "/15"` for recurring
- Conditions: Always plural `conditions:` even if empty

### Phase 3: Fix WLED-Specific Logic ⚠️

**Issue**: WLED requires special handling for:
1. Saving current state before changing
2. Random effect selection from WLED presets
3. Restoring state after 15 minutes

**WLED Integration Requirements**:
```yaml
# 1. Save current state (use scene.create)
- service: scene.create
  data:
    scene_id: office_wled_restore
    snapshot_entities:
      - light.wled

# 2. Apply random effect (WLED has 100+ effects)
- service: light.turn_on
  target:
    entity_id: light.wled
  data:
    brightness_pct: 100
    effect: >
      {{ state_attr('light.wled', 'effect_list') | random }}

# 3. Wait 15 minutes
- delay: '00:15:00'

# 4. Restore previous state
- service: scene.turn_on
  target:
    entity_id: scene.office_wled_restore
```

### Phase 4: Test & Verify ⏸️

**Test Steps**:
1. Restart service with new logging
2. Click "APPROVE & CREATE"
3. Check logs for `[APPROVAL START]` entry
4. Verify YAML generation logs appear
5. Check Home Assistant for created automation
6. Test automation trigger (wait for 15-minute interval)
7. Verify WLED state restoration

**Expected Log Sequence**:
```
INFO: 🚀 [APPROVAL START] query_id=clarify-9d171c32, suggestion_id=2
INFO: 📝 [APPROVAL] Request body: None
INFO: 🔍 [APPROVAL] Fetching query record: clarify-9d171c32
INFO: ✅ [APPROVAL] Found query with 2 suggestions
INFO: 🔍 [APPROVAL] Searching for suggestion_id=2
INFO: ✅ [APPROVAL] Found suggestion: TIME PATTERN TRIGGER EVERY...
INFO: 🔧 [YAML_GEN] Starting YAML generation for suggestion 2
INFO: 📋 [YAML_GEN] Validated entities: {'Office': 'light.wled'}
INFO: ✅ [YAML_GEN] YAML generated successfully (1234 chars)
INFO: 📄 [YAML_GEN] First 200 chars: id: 'office_wled_random_...'
INFO: 🚀 [DEPLOY] Starting deployment to Home Assistant
INFO: ✅ [DEPLOY] Successfully created automation: automation.office_wled_random_effect_15min
```

## Implementation Priority

1. **HIGH**: Phase 1 - Add comprehensive logging (30 min)
2. **HIGH**: Phase 2 - Fix YAML format to 2025 standard (45 min)
3. **MEDIUM**: Phase 3 - WLED-specific logic (1 hour)
4. **HIGH**: Phase 4 - Test end-to-end (30 min)

## Success Criteria

- [ ] Approval endpoint logs appear in docker logs
- [ ] YAML generation completes without errors
- [ ] YAML uses 2025 format (trigger:/action: singular)
- [ ] Automation created in Home Assistant
- [ ] Automation visible in HA UI (Settings → Automations)
- [ ] WLED effect changes every 15 minutes during time window (6 AM - 4:30 PM PST)
- [ ] WLED state restored after each 15-minute cycle

## Files to Modify

1. `services/ai-automation-service/src/api/ask_ai_router.py` (lines 7117-7500)
2. `services/ai-automation-service/src/nl_automation_generator.py` (lines 326-382)
3. `services/ai-automation-service/src/services/automation/action_parser.py` (lines 23-24)

## Deployment Steps

1. Stop service: `docker compose stop ai-automation-service`
2. Apply code changes
3. Rebuild: `docker compose build ai-automation-service`
4. Start: `docker compose up -d ai-automation-service`
5. Monitor logs: `docker compose logs -f ai-automation-service`
6. Test approval flow
7. Verify in Home Assistant

## Rollback Plan

If issues occur:
1. Revert code changes: `git checkout HEAD -- services/ai-automation-service/`
2. Rebuild: `docker compose build ai-automation-service`
3. Restart: `docker compose up -d ai-automation-service`

