# Context Builder Area Filtering Fix

**Issue:** Generic examples from all areas are shown instead of area-specific entities when user mentions a specific area.

**Date:** December 5, 2025

---

## Problem Analysis

### Current Behavior

1. **Entity Inventory Service** collects samples from ALL entities across ALL areas:
   - Line 274: `domain_samples` collects from all areas
   - Line 352: Light patterns collected from any area (first 8 unique patterns)
   - Line 371: Other domains collect first 3 samples from any area
   - Line 485: Shows these as "Examples:" without area context

2. **Result:**
   - User asks about "Office" lights
   - Context shows: "Light: 52 entities ... Office: 7"
   - But "Examples:" shows: "Hue Go 1 (light.hue_go_1), Kitchen Strip (light.kitchen_strip), ..."
   - These examples are from ANY area, not Office-specific

3. **Impact:**
   - Assistant assumes generic examples are Office lights
   - Generates incorrect entity IDs
   - Automation fails

---

## Root Cause

The context builder is **not area-aware**. It doesn't:
- Detect which area the user is asking about
- Filter entity inventory by area
- Show area-specific entity lists

---

## Solution

### Option 1: Area-Aware Context Injection (Recommended)

**When user mentions a specific area, inject ONLY that area's entities:**

1. **Detect Area from User Message:**
   - Parse user message for area names
   - Match against area_id mappings
   - Extract target area

2. **Filter Entity Inventory by Area:**
   - Modify `EntityInventoryService.get_summary()` to accept `area_filter` parameter
   - Filter entities by `area_id` before collecting samples
   - Show actual entity list for that area, not generic examples

3. **Remove Generic Examples:**
   - Don't show "Examples:" that span all areas
   - Show actual entity list: "Office Lights: Office Go (light.office_go), Office Back Right (light.office_back_right), ..."

### Option 2: Remove Examples Entirely (Simpler)

**Remove generic examples and rely on area-based targeting:**

1. Remove "Examples:" line from entity inventory summary
2. Keep area counts: "Light: 52 entities ... Office: 7"
3. Assistant should use `target.area_id: office` instead of listing entities
4. For `scene.create`, either:
   - Query entity registry for area lights
   - Use area-based scene creation
   - Document that snapshot may not be perfect

### Option 3: Show All Entities by Area (Comprehensive)

**Show complete entity list organized by area:**

1. For each area mentioned, list all entities in that area
2. Format: "Office Lights (7): Office Go (light.office_go), Office Back Right (light.office_back_right), ..."
3. Only show entities from requested area(s)
4. No generic examples

---

## Recommended Implementation: Option 1 + Option 3 Hybrid

### Step 1: Make Context Builder Area-Aware

```python
# In context_builder.py
async def build_context(self, user_message: str = None) -> str:
    """
    Build complete Tier 1 context for OpenAI agent.
    
    Args:
        user_message: Optional user message to extract area context from
    
    Returns:
        Formatted context string ready for OpenAI system/user prompts
    """
    # Extract area from user message if provided
    target_areas = self._extract_areas_from_message(user_message) if user_message else []
    
    # Build context with area filtering
    context_parts = []
    
    # Entity inventory - filtered by area if specified
    entity_inventory = await self._entity_inventory_service.get_summary(
        area_filter=target_areas
    )
    context_parts.append(entity_inventory)
    
    # ... rest of context building
```

### Step 2: Add Area Filtering to Entity Inventory Service

```python
# In entity_inventory_service.py
async def get_summary(self, area_filter: list[str] = None) -> str:
    """
    Get entity inventory summary.
    
    Args:
        area_filter: Optional list of area_ids to filter by
    
    Returns:
        Formatted summary string
    """
    # ... existing code to fetch entities ...
    
    # Filter by area if specified
    if area_filter:
        entities = [e for e in entities if e.get("area_id") in area_filter]
        # Update counts and samples to only include filtered entities
    
    # When showing examples, show actual entities from filtered area(s)
    # Not generic examples from all areas
```

### Step 3: Extract Area from User Message

```python
# In context_builder.py
def _extract_areas_from_message(self, user_message: str) -> list[str]:
    """
    Extract area names/IDs from user message.
    
    Returns:
        List of area_ids mentioned in message
    """
    if not user_message:
        return []
    
    # Get area mappings
    area_name_map = self._areas_service.get_area_name_map()  # Need to implement
    
    # Search for area names in message (case-insensitive)
    mentioned_areas = []
    message_lower = user_message.lower()
    
    for area_id, area_name in area_name_map.items():
        if area_name.lower() in message_lower or area_id in message_lower:
            mentioned_areas.append(area_id)
    
    return mentioned_areas
```

### Step 4: Show Actual Entity List (Not Generic Examples)

```python
# In entity_inventory_service.py
# Replace generic "Examples:" with actual entity list for filtered area

if area_filter:
    # Show actual entities from this area
    area_entities = [e for e in entities if e.get("area_id") in area_filter]
    if area_entities:
        entity_list = []
        for entity in area_entities[:10]:  # Limit to 10 for token efficiency
            entity_list.append(f"{entity['friendly_name']} ({entity['entity_id']})")
        
        domain_line += f"\n  {area_name} entities: {', '.join(entity_list)}"
else:
    # No area filter - show counts only, no generic examples
    # Remove "Examples:" line entirely
    pass
```

---

## Implementation Plan

### Phase 1: Remove Generic Examples (Quick Fix)
1. Remove "Examples:" line from entity inventory summary
2. Keep area counts
3. Assistant uses `target.area_id` instead of listing entities
4. **Impact:** Prevents incorrect entity ID generation

### Phase 2: Add Area Detection (Medium Term)
1. Add `_extract_areas_from_message()` to context builder
2. Pass detected areas to entity inventory service
3. Filter entities by area
4. **Impact:** Context includes only relevant area entities

### Phase 3: Show Actual Entity Lists (Long Term)
1. When area is detected, show actual entity list for that area
2. Format: "Office Lights (7): Office Go (light.office_go), ..."
3. Remove area counts, show actual entities
4. **Impact:** Assistant has exact entity IDs to use

---

## Code Changes Required

### File: `services/ha-ai-agent-service/src/services/entity_inventory_service.py`

**Change 1: Remove Generic Examples (Line 485)**
```python
# BEFORE:
if sample_parts:
    domain_line += f"\n  Examples: {', '.join(sample_parts)}"

# AFTER:
# Remove this entirely - no generic examples
# If area_filter provided, show actual entities from that area instead
```

**Change 2: Add Area Filtering**
```python
async def get_summary(self, area_filter: list[str] = None) -> str:
    # ... existing code ...
    
    # Filter entities by area if specified
    if area_filter:
        entities = [e for e in entities if e.get("area_id") in area_filter]
        # Recalculate counts and samples for filtered entities only
```

**Change 3: Show Area-Specific Entities**
```python
# When area_filter is provided, show actual entities
if area_filter and domain == "light":
    area_light_entities = [e for e in entities 
                          if e.get("domain") == "light" 
                          and e.get("area_id") in area_filter]
    
    if area_light_entities:
        entity_list = []
        for entity in area_light_entities[:10]:
            friendly_name = entity.get("friendly_name") or entity.get("name")
            entity_id = entity.get("entity_id")
            entity_list.append(f"{friendly_name} ({entity_id})")
        
        domain_line += f"\n  {area_name} lights: {', '.join(entity_list)}"
```

### File: `services/ha-ai-agent-service/src/services/context_builder.py`

**Change 1: Add Area Extraction**
```python
def _extract_areas_from_message(self, user_message: str) -> list[str]:
    """Extract area IDs from user message."""
    if not user_message:
        return []
    
    # Get area mappings (need to fetch from areas_service)
    # Search for area names in message
    # Return list of area_ids
```

**Change 2: Pass Area Filter to Entity Inventory**
```python
async def build_context(self, user_message: str = None) -> str:
    # Extract areas from message
    target_areas = self._extract_areas_from_message(user_message) if user_message else []
    
    # Pass area filter to entity inventory
    entity_inventory = await self._entity_inventory_service.get_summary(
        area_filter=target_areas
    )
```

---

## Testing

### Test Case 1: Office Area Mentioned
**Input:** "Create a party scene in the office"
**Expected Context:**
```
Light: 7 entities (Office: 7)
  Office lights: Office Go (light.office_go), Office Back Right (light.office_back_right), Office Back Left (light.office_back_left), Office Front Right (light.office_front_right), Office Front Left (light.office_front_left), Office (light.office), Office (light.wled_office)
```
**No generic examples from other areas**

### Test Case 2: No Area Mentioned
**Input:** "Turn on the lights"
**Expected Context:**
```
Light: 52 entities (Backyard: 3, Bar: 4, ..., Office: 7, ...)
```
**No examples, just counts**

### Test Case 3: Multiple Areas Mentioned
**Input:** "Turn on office and kitchen lights"
**Expected Context:**
```
Light: 10 entities (Office: 7, Kitchen: 3)
  Office lights: Office Go (light.office_go), ...
  Kitchen lights: Kitchen Strip (light.kitchen_strip), ...
```

---

## Migration Path

1. **Immediate (Phase 1):** Remove generic examples - prevents incorrect entity IDs
2. **Short-term (Phase 2):** Add area detection - improves context relevance
3. **Long-term (Phase 3):** Show actual entity lists - enables precise entity ID usage

---

*Analysis completed: December 5, 2025*

