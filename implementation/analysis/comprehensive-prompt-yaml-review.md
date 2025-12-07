# Comprehensive Prompt, YAML, and Code Review

**Date:** December 5, 2025  
**Purpose:** Review system prompt, injected context, and code against actual Home Assistant devices

---

## Actual Office Devices (from Home Assistant)

Based on the Home Assistant Devices dashboard, the Office area contains these **light devices**:

| Device Name | Integration | Manufacturer | Model | Expected Entity ID Pattern |
|-------------|-------------|--------------|-------|----------------------------|
| **Office Go** | Philips Hue | Signify Netherlands B.V. | Hue go | `light.office_go` or `light.hue_go_1` |
| **Office** (Room) | Philips Hue | Signify Netherlands B.V. | Room | `light.office` (group/room entity) |
| **Office** (WLED) | WLED | WLED | FOSS | `light.office` or `light.wled_office` or `light.office_wled` |
| **Office Back Right** | Philips Hue | Signify Netherlands B.V. | Hue color downlight | `light.office_back_right` |
| **Office Back Left** | Philips Hue | Signify Netherlands B.V. | Hue color downlight | `light.office_back_left` |
| **Office Front Right** | Philips Hue | Signify Netherlands B.V. | Hue color downlight | `light.office_front_right` |
| **Office Front Left** | Philips Hue | Signify Netherlands B.V. | Hue color downlight | `light.office_front_left` |

**Total Office Lights: 7** (matches context count)

**Non-Light Devices (not relevant to light automations):**
- HP Tango (printer)
- Samsung 7 Series (TV)
- Presence-Sensor-FP2-8B8A (sensor)

---

## System Prompt Review

### ✅ **Correct Elements**

1. **Area Filtering FIRST (Line 70):**
   - ✅ Correctly states: "If user mentions area (e.g., 'office', 'kitchen'), ONLY consider entities in that area"
   - ✅ Clear instruction: "Matching wrong area is WRONG - try again"
   - ✅ Uses `area_id` from context

2. **Prefer Area-Based Targeting (Line 52):**
   - ✅ States: "Prefer `target.area_id` or `target.device_id` over multiple `entity_id` entries"
   - ✅ This is the correct approach for most automations

3. **Entity Resolution Guidelines (Lines 68-92):**
   - ✅ Area filtering first
   - ✅ Positional keyword matching
   - ✅ Device type matching
   - ✅ Validation requirements
   - ✅ Context usage guidelines
   - ✅ Device type guidelines (Epic AI-24)

4. **YAML Examples (Lines 96-221):**
   - ✅ Shows correct `target.area_id: office` pattern
   - ✅ Shows state restoration pattern
   - ✅ Shows time pattern triggers
   - ✅ Shows color/blink patterns

### ⚠️ **Potential Issues**

1. **Example in System Prompt (Line 266):**
   - Shows: "**🎯 What's affected:** • Office Lights (light.office_*) • Office area"
   - ⚠️ Uses generic pattern `light.office_*` which doesn't match actual entities
   - **Recommendation:** Update to show actual entity names or emphasize area-based targeting

2. **Scene Snapshot Example (Lines 139-141):**
   - Shows: `light.office_light_1`, `light.office_light_2`
   - ⚠️ These are placeholder entity IDs that don't match actual Office devices
   - **Recommendation:** Add note that these are examples and actual entity IDs should come from context

3. **Context Usage (Line 78):**
   - States: "Context shows ALL lights (up to 20) - search all options"
   - ⚠️ This is outdated - we removed examples, so context now shows counts only
   - **Recommendation:** Update to: "Context shows entity counts by area. Use `target.area_id` for actions. For `scene.create` snapshot_entities, query context or use area-based approach."

---

## Injected Context Review

### Current State (After Fix)

**What Context Now Shows:**
```
Light: 52 entities (Backyard: 3, Bar: 4, ..., Office: 7, Kitchen: 3, ...)
```

**What's Missing:**
- ❌ No actual Office entity IDs listed
- ❌ No Office entity friendly names
- ❌ No Office entity attributes (effects, colors, etc.)

**Impact:**
- ✅ Good: No misleading generic examples from other areas
- ⚠️ Issue: Assistant can't see actual Office entities for `scene.create` snapshot_entities
- ✅ Good: Assistant will use `target.area_id: office` for actions (correct approach)

### What Context Should Show (Future Enhancement)

**When user mentions "Office", context should show:**
```
Light: 52 entities (Backyard: 3, Bar: 4, ..., Office: 7, Kitchen: 3, ...)

Office Lights (7):
- Office Go (light.office_go) - Hue go, effects: [off, candle, fire, ...], colors: color_temp, xy
- Office (light.office) - Hue Room, controls 4 lights
- Office Back Right (light.office_back_right) - Hue color downlight, colors: color_temp, xy
- Office Back Left (light.office_back_left) - Hue color downlight, colors: color_temp, xy
- Office Front Right (light.office_front_right) - Hue color downlight, colors: color_temp, xy
- Office Front Left (light.office_front_left) - Hue color downlight, colors: color_temp, xy
- Office (light.wled_office) - WLED FOSS, effects: [Solid, Blink, ...], colors: rgb
```

**Current State:** Context shows counts only (correct after removing generic examples)

---

## Code Review

### ✅ **Entity Inventory Service (entity_inventory_service.py)**

**Lines 336-344:**
- ✅ Correctly removed generic examples
- ✅ Shows only area counts: `"Light: 52 entities (Backyard: 3, Office: 7, ...)"`
- ✅ No misleading examples from other areas
- ✅ Comments explain why examples were removed

**Status:** ✅ **CORRECT** - Code is working as intended

### ✅ **Context Builder (context_builder.py)**

**Lines 95-176:**
- ✅ Builds context correctly
- ✅ Calls `entity_inventory_service.get_summary()` without area filtering
- ✅ No area detection from user message (not yet implemented)
- ✅ Context is static (same for all conversations)

**Status:** ✅ **CORRECT** - Code is working, but area filtering not yet implemented

### ⚠️ **Missing Feature: Area-Aware Context**

**Current Behavior:**
- Context is built once and cached
- Same context for all conversations
- No area filtering based on user message

**What's Needed (Future):**
- Detect area from user message
- Filter entity inventory by detected area
- Show actual entity list for that area

**Status:** ⚠️ **FUNCTIONAL BUT INCOMPLETE** - Works correctly but lacks area-specific filtering

---

## YAML Generation Review

### Expected Behavior (After Fix)

**For action (`light.turn_on`):**
```yaml
- service: light.turn_on
  target:
    area_id: office
  data:
    brightness: 255
    effect: "Colorloop"
```
✅ **CORRECT** - Uses `target.area_id` (preferred approach)

**For snapshot (`scene.create`):**
```yaml
- service: scene.create
  data:
    scene_id: office_party_scene_every_15_minutes_restore
    snapshot_entities:
      # Problem: Assistant doesn't have actual Office entity IDs
      # Options:
      # 1. Use area-based scene creation (if HA supports it)
      # 2. Query entity registry for Office area lights
      # 3. List known entities (if context provided them)
      # 4. Document uncertainty and use area-based approach
```
⚠️ **ISSUE** - Assistant needs actual entity IDs for snapshot_entities

### Current Assistant Behavior

**What Assistant Will Do:**
1. See "Office: 7" in context
2. Use `target.area_id: office` for actions ✅ (correct)
3. For `snapshot_entities`, either:
   - Guess entity IDs (❌ wrong - will fail)
   - Use area-based approach (✅ correct - but may not work for snapshot)
   - Query entity registry (✅ correct - but requires tool call)

**Recommendation:** System prompt should explicitly state:
- For `scene.create` snapshot_entities, if entity IDs not in context, either:
  - Query entity registry for area lights, OR
  - Use area-based scene creation, OR
  - Document that snapshot may not capture all lights perfectly

---

## System Prompt Updates Needed

### Update 1: Context Usage (Line 78)

**Current:**
```
5. **Context Usage**: Context shows ALL lights (up to 20) - search all options, don't pick first. Prioritize: Area match → Keyword match → Specificity.
```

**Should Be:**
```
5. **Context Usage**: Context shows entity counts by area. Use `target.area_id` for actions (preferred). For `scene.create` snapshot_entities, if specific entity IDs are needed but not in context, query entity registry or use area-based approach. Prioritize: Area match → Keyword match → Specificity.
```

### Update 2: Scene Snapshot Example (Lines 139-141)

**Current:**
```yaml
snapshot_entities:
  - light.office_light_1
  - light.office_light_2
```

**Should Be:**
```yaml
snapshot_entities:
  # NOTE: These are examples. Actual entity IDs should come from context.
  # If context doesn't list specific entities for the area, either:
  # 1. Query entity registry for area lights, OR
  # 2. Use area-based scene creation (if available), OR
  # 3. List known entities from context
  - light.office_go
  - light.office_back_right
  # ... (actual entities from context)
```

### Update 3: Example Response (Line 266)

**Current:**
```
**🎯 What's affected:** • Office Lights (light.office_*) • Office area
```

**Should Be:**
```
**🎯 What's affected:** • Office area lights (7 total) • All Office light devices
```

---

## Code Verification

### ✅ **Entity Inventory Service**

**File:** `services/ha-ai-agent-service/src/services/entity_inventory_service.py`

**Lines 336-344:**
```python
# Build domain summary line
domain_line = f"{domain_display}: {total} entities ({area_str})"

# REMOVED: Generic examples from all areas
# Rationale: Generic examples violate "Area Filtering FIRST" principle...
```

**Status:** ✅ **CORRECT** - Generic examples removed, shows counts only

### ✅ **Context Builder**

**File:** `services/ha-ai-agent-service/src/services/context_builder.py`

**Lines 112-124:**
```python
entity_summary = await self._entity_inventory_service.get_summary()
if entity_summary and len(entity_summary.strip()) > 0:
    context_parts.append(f"ENTITY INVENTORY:\n{entity_summary}\n")
```

**Status:** ✅ **CORRECT** - Builds context correctly, no area filtering yet

### ✅ **Prompt Assembly Service**

**File:** `services/ha-ai-agent-service/src/services/prompt_assembly_service.py`

**Status:** ✅ **CORRECT** - Assembles messages correctly with context

### ✅ **Chat Endpoints**

**File:** `services/ha-ai-agent-service/src/api/chat_endpoints.py`

**Status:** ✅ **CORRECT** - Fixed duplicate message issue, uses `skip_add_message` parameter

---

## Summary of Findings

### ✅ **What's Working Correctly**

1. **Generic Examples Removed:**
   - ✅ No more misleading examples from other areas
   - ✅ Context shows only area counts
   - ✅ Code correctly implements this

2. **System Prompt:**
   - ✅ Area Filtering FIRST principle is clear
   - ✅ Prefers area-based targeting
   - ✅ Entity resolution guidelines are comprehensive

3. **Code:**
   - ✅ Entity inventory service works correctly
   - ✅ Context builder works correctly
   - ✅ No errors or issues

### ⚠️ **What Needs Updates**

1. **System Prompt Examples:**
   - ⚠️ Update context usage description (line 78)
   - ⚠️ Update scene snapshot example with actual entity IDs or notes
   - ⚠️ Update example response to use area-based description

2. **Missing Feature:**
   - ⚠️ Area-aware context injection not yet implemented
   - ⚠️ Context is static (same for all conversations)
   - ⚠️ No area detection from user message

3. **Scene Snapshot Guidance:**
   - ⚠️ System prompt should explicitly state what to do when entity IDs not in context
   - ⚠️ Should mention querying entity registry or using area-based approach

### ✅ **What's Correct vs Actual Devices**

**Office Device Count:**
- ✅ Context shows "Office: 7" - matches actual 7 Office light devices
- ✅ No generic examples to confuse assistant
- ✅ Assistant will use `target.area_id: office` (correct approach)

**Entity IDs:**
- ⚠️ Context doesn't list actual Office entity IDs
- ⚠️ Assistant can't see specific entities for `scene.create` snapshot
- ✅ Assistant will use area-based targeting for actions (correct)

---

## Recommendations

### Immediate (System Prompt Updates)

1. **Update Context Usage Description (Line 78):**
   - Remove reference to "ALL lights (up to 20)"
   - Add guidance for `scene.create` snapshot_entities

2. **Update Scene Snapshot Example (Lines 139-141):**
   - Add note that entity IDs should come from context
   - Show what to do if context doesn't have specific entities

3. **Update Example Response (Line 266):**
   - Use area-based description instead of generic pattern

### Short-Term (Code Enhancements)

1. **Add Area Detection:**
   - Parse user message for area names
   - Filter entity inventory by detected area
   - Show actual entity list for that area

2. **Enhance Context Builder:**
   - Accept user message parameter
   - Build area-specific context when area detected
   - Fall back to general context when no area mentioned

### Long-Term (Complete Solution)

1. **Area-Specific Entity Lists:**
   - When area detected, show actual entities with IDs
   - Include attributes (effects, colors, etc.)
   - Enable precise entity ID usage for `scene.create`

2. **Entity Registry Query Tool:**
   - Add tool to query entity registry for area lights
   - Use when specific entity IDs needed but not in context
   - Enable accurate `snapshot_entities` lists

---

## Conclusion

### Current State: ✅ **FUNCTIONAL BUT INCOMPLETE**

**What Works:**
- ✅ Generic examples removed (fixes incorrect entity ID issue)
- ✅ Context shows accurate area counts
- ✅ System prompt correctly emphasizes area-based targeting
- ✅ Code is working correctly

**What Needs Work:**
- ⚠️ System prompt examples need updates to reflect current context structure
- ⚠️ Area-aware context injection not yet implemented
- ⚠️ Scene snapshot guidance needs clarification

**Overall Assessment:**
- ✅ **System prompt is correct** - principles are sound
- ✅ **Injected context is accurate** - shows correct counts, no misleading examples
- ✅ **Code is working** - correctly implements removal of generic examples
- ⚠️ **Missing feature** - area-specific entity lists not yet implemented

**The system will work correctly for most automations** (using area-based targeting), but `scene.create` snapshot_entities may need entity registry queries or area-based scene creation.

---

*Review completed: December 5, 2025*

