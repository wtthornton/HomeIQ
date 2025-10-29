# Entity Cleanup/Renaming Feature Discussion

**Date:** October 29, 2025  
**Status:** 💭 Discussion & Planning Phase  
**Question:** Should we implement entity cleanup/renaming to standardize customer environments?

---

## The Question

Should we implement a feature that automatically "cleans up" entity names in customer Home Assistant environments to make them more consistent and better for matching?

**Example:**
- Current: `light.hue_color_downlight_1_6`, `light.hue_go_1`, `light.office`
- Proposed Clean: `light.office_light_1`, `light.office_light_2`, `light.office_group`

---

## Approaches Considered

### Option A: Make Matching Smarter (Current Approach) ✅

**What we're doing:**
- Use full model chain (embeddings, device metadata, friendly_name)
- Handle messy names gracefully
- Works with any naming convention

**Pros:**
- ✅ No changes to customer's HA setup
- ✅ No risk of breaking automations/scenes
- ✅ Respects customer's naming preferences
- ✅ Works immediately

**Cons:**
- ❌ Still need to handle inconsistent names
- ❌ Some edge cases may still fail

**Status:** ✅ **RECOMMENDED - Already implemented**

---

### Option B: Suggest Renames (Read-Only Analysis)

**What it would do:**
- Analyze entity names and suggest improvements
- Generate a report: "Consider renaming X to Y for better matching"
- Customer manually applies changes

**Pros:**
- ✅ No automatic changes (safe)
- ✅ Customer maintains control
- ✅ Educational value
- ✅ Can see before/after impact

**Cons:**
- ❌ Customer must manually apply changes
- ❌ Customer may not know how to rename in HA
- ❌ Changes take time

**Implementation:**
```python
def analyze_entity_naming(entity_id, device_metadata, friendly_name):
    """Suggest better naming if entity is poorly named"""
    suggestions = []
    
    # Check for issues
    if not friendly_name:
        suggestions.append("Add friendly_name for better matching")
    
    if device_id and device_name != friendly_name:
        suggestions.append(f"Rename to match device name: {device_name}")
    
    # Suggest standardized numbered format
    if has_numbered_device_pattern_mismatch:
        suggestions.append(f"Consider: light.office_light_{number}")
    
    return suggestions
```

**Status:** ⚠️ **Maybe - Could be useful as diagnostic tool**

---

### Option C: Automated Renaming (Dangerous ⚠️)

**What it would do:**
- Automatically rename entities in Home Assistant
- Standardize naming conventions
- Update automations/scenes that reference renamed entities

**Pros:**
- ✅ Consistent naming immediately
- ✅ Better matching by default
- ✅ Cleaner environment

**Cons:**
- ❌ **HIGH RISK** - Could break existing automations
- ❌ **HIGH RISK** - Could break scenes
- ❌ **HIGH RISK** - Could break scripts
- ❌ **HIGH RISK** - Could break dashboard cards
- ❌ Customer may not want their names changed
- ❌ Need to update all references (complex)
- ❌ Hard to rollback
- ❌ May conflict with HA updates

**Implementation Complexity:**
- Need to find all references to entity in:
  - Automations
  - Scenes
  - Scripts
  - Dashboard cards
  - Template sensors
  - Blueprints
  - Node-RED flows (if integrated)
- Update all references atomically
- Handle rollback scenarios
- Handle conflicts

**Status:** ❌ **NOT RECOMMENDED - Too risky**

---

### Option D: Hybrid - Smart Matching + Diagnostic Dashboard

**What it would do:**
- Use smart matching (Option A) ✅
- Add diagnostic dashboard showing:
  - Entity matching confidence scores
  - Name quality scores
  - Suggested improvements (as info, not forced)
  - "Rename Guide" with step-by-step instructions

**Pros:**
- ✅ Best of both worlds
- ✅ Safe (no automatic changes)
- ✅ Helpful (educates customers)
- ✅ Optional (they can rename if they want)

**Implementation:**
```python
# Add to diagnostic/health dashboard
@app.get("/api/v1/entity-quality-report")
async def get_entity_quality_report():
    """Analyze entity naming quality and suggest improvements"""
    
    entities = await fetch_all_entities()
    
    quality_scores = []
    for entity in entities:
        score = calculate_naming_quality(entity)
        suggestions = generate_name_suggestions(entity)
        
        quality_scores.append({
            'entity_id': entity.entity_id,
            'quality_score': score,  # 0-100
            'issues': detect_naming_issues(entity),
            'suggestions': suggestions,
            'matching_confidence': get_avg_matching_confidence(entity)
        })
    
    return {
        'overall_quality': calculate_overall(quality_scores),
        'entities': quality_scores,
        'top_issues': get_common_issues(quality_scores)
    }
```

**Status:** ✅✅ **STRONGLY RECOMMENDED**

---

## Recommendation

### Short Term (Current)
✅ **Continue with Option A** - Smart matching with full model chain
- Already implemented
- Works well
- No risks

### Medium Term (Next Sprint)
✅ **Add Option D** - Diagnostic Dashboard
- Entity quality scoring
- Name suggestions (informational)
- Matching confidence visibility
- Rename guides/instructions

### Long Term (Future)
⚠️ **Consider Option B** - Suggest Renames (Optional)
- One-click "Apply Suggestions" button (customer confirms)
- Creates HA automation/script to apply changes
- Shows preview before applying

❌ **Never Do Option C** - Automated Renaming
- Too risky
- Too many edge cases
- Customer backlash risk

---

## Questions for Discussion

1. **Priority:** How important is entity name cleanup vs. making matching smarter?
   - My view: Smart matching is more important ✅

2. **Customer Control:** Should customers have full control over naming?
   - My view: Yes, they own their HA setup ✅

3. **Diagnostic Value:** Would a quality report/dashboard be useful?
   - My view: Yes, helps customers understand issues ✅

4. **Automation Risk:** Are we comfortable with automatic changes to HA?
   - My view: No, too risky ❌

---

## Implementation Plan (If Approved)

### Phase 1: Diagnostic Dashboard (Safe, Informational)
1. Add `/api/v1/entity-quality-report` endpoint
2. Calculate naming quality scores
3. Generate suggestions (read-only)
4. Add to health dashboard UI

### Phase 2: Rename Guide (Educational)
1. Create step-by-step rename instructions
2. Show HA UI screenshots
3. Explain impact on automations/scenes

### Phase 3: Optional Helper Script (Customer Initiated)
1. Generate HA script to apply renames
2. Customer reviews and runs manually
3. Helper validates changes don't break things

---

## Alternative: Entity Alias System

**Idea:** Instead of renaming, create our own "alias" mapping system

**How it works:**
- Store customer-defined aliases: `"Office Light 1" → light.hue_color_downlight_1_6`
- Use aliases for matching
- Customer can define aliases via UI
- No changes to HA entities themselves

**Pros:**
- ✅ No risk to HA setup
- ✅ Customer control
- ✅ Easy to update
- ✅ Works immediately

**Status:** ✅ **Interesting alternative worth considering**

---

## Summary

**My Recommendation:**
1. ✅ Keep smart matching (current implementation)
2. ✅ Add diagnostic dashboard (Option D)
3. ✅ Provide rename guides (educational)
4. ❌ Don't do automated renaming (too risky)
5. 💡 Consider alias system as alternative

What are your thoughts? Should we prioritize the diagnostic dashboard, or focus on something else?

