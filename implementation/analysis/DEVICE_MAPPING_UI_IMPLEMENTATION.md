# Device Mapping UI Implementation Plan

**Date:** January 2025  
**Status:** Implementation Plan  
**Purpose:** Allow users to check/uncheck devices AND edit entity ID mappings

## Current State

### ✅ Already Implemented
1. **Device Selection UI**: Devices shown as clickable buttons with checkmarks
2. **Device Toggle**: `onDeviceToggle` callback allows selecting/unselecting devices
3. **Backend Filtering**: Approve endpoint accepts `selected_entity_ids` to filter validated_entities

### ❌ Missing Features
1. **User-Assisted Mapping**: No UI to change entity_id for a friendly_name
2. **Backend Override**: Approve endpoint doesn't accept custom entity_mapping overrides
3. **Alternative Suggestions**: No UI to show alternative entity IDs for the same device name

## Solution Design

### Frontend Changes

#### 1. Enhanced Device Display Component
- Add "edit mapping" icon/button next to each device
- Clicking opens a modal/dropdown showing:
  - Current entity_id mapping
  - Searchable list of alternative entities (same domain)
  - Ability to search all entities
  - Current device capabilities for context

#### 2. Device Mapping Modal Component
```typescript
interface DeviceMappingModalProps {
  friendlyName: string;
  currentEntityId: string;
  availableEntities: EntityOption[];
  onSave: (friendlyName: string, newEntityId: string) => void;
  onCancel: () => void;
}

interface EntityOption {
  entity_id: string;
  friendly_name: string;
  domain: string;
  state?: string;
  capabilities?: string[];
}
```

#### 3. State Management
- Add `deviceMappings` state: `Map<friendlyName, entityId>`
- Pass custom mappings to approve endpoint
- Update device_info with custom entity_ids before rendering

### Backend Changes

#### 1. Update ApproveSuggestionRequest Model
```python
class ApproveSuggestionRequest(BaseModel):
    selected_entity_ids: Optional[List[str]] = None
    custom_entity_mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom mapping of friendly_name → entity_id overrides"
    )
```

#### 2. Update Approve Endpoint Logic
```python
# After filtering by selected_entity_ids, apply custom mappings
if request.custom_entity_mapping:
    for friendly_name, entity_id in request.custom_entity_mapping.items():
        if friendly_name in final_suggestion['validated_entities']:
            # Verify entity exists in HA
            if await verify_entity_exists(entity_id, ha_client):
                final_suggestion['validated_entities'][friendly_name] = entity_id
            else:
                logger.warning(f"Custom entity_id {entity_id} does not exist in HA")
```

#### 3. New API Endpoint for Entity Search
```python
@router.get("/entities/search")
async def search_entities(
    domain: Optional[str] = None,
    search_term: Optional[str] = None,
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) -> List[Dict[str, Any]]:
    """Search available entities for device mapping"""
```

## Implementation Steps

### Phase 1: Backend Support (2-3 hours)
1. Update `ApproveSuggestionRequest` model to accept `custom_entity_mapping`
2. Add entity search endpoint
3. Update approve endpoint to apply custom mappings
4. Add validation to ensure custom entity_ids exist

### Phase 2: Frontend UI Components (3-4 hours)
1. Create `DeviceMappingModal` component
2. Add "edit" icon to device buttons
3. Integrate modal with `ConversationalSuggestionCard`
4. Add state management for custom mappings

### Phase 3: Entity Search Integration (2 hours)
1. Connect frontend to entity search API
2. Add search/filter functionality in modal
3. Show device capabilities for context
4. Handle loading/error states

### Phase 4: Testing & Polish (1-2 hours)
1. Test mapping override flow
2. Test with various device types
3. Add error handling for invalid entity_ids
4. Add confirmation dialogs for mapping changes

## User Experience Flow

1. User sees suggestion with devices displayed
2. User clicks "edit" icon next to a device
3. Modal opens showing:
   - Current mapping: "WLED Office" → `light.wled_office`
   - Search box to find alternatives
   - List of matching entities (filtered by domain if applicable)
   - Device capabilities shown for context
4. User selects new entity_id
5. User clicks "Save" - mapping is updated in UI
6. When user clicks "Approve", custom mapping is sent to backend
7. Backend validates and applies custom mapping
8. YAML is generated with updated entity_id

## Alternative Approaches Considered

### Approach A: Inline Editing
- **Pros**: Faster, no modal
- **Cons**: Limited space, harder to show alternatives

### Approach B: Separate Mapping Page
- **Pros**: More space, better for complex mappings
- **Cons**: Breaks workflow, extra navigation

### Approach C: Dropdown on Device Button
- **Pros**: Quick access
- **Cons**: Limited space for search/options

**Selected: Modal Approach** - Best balance of usability and functionality

## Technical Considerations

1. **Entity Validation**: Must verify custom entity_ids exist in HA
2. **Domain Matching**: Should default to same domain for safety
3. **Capability Matching**: Warn if new entity lacks required capabilities
4. **State Management**: Custom mappings should persist during suggestion refinement
5. **Performance**: Entity search should be debounced and cached

## Files to Modify

### Backend
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Update `ApproveSuggestionRequest` model
  - Add entity search endpoint
  - Update approve endpoint logic

### Frontend
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
  - Add mapping modal integration
  - Add edit icon to device buttons
  
- `services/ai-automation-ui/src/components/DeviceMappingModal.tsx` (NEW)
  - Create new modal component
  
- `services/ai-automation-ui/src/services/api.ts`
  - Add search entities API call
  - Update approve call to include custom mappings

## Success Criteria

1. ✅ Users can check/uncheck devices (already working)
2. ✅ Users can see current entity_id mapping for each device
3. ✅ Users can search for alternative entities
4. ✅ Users can change entity_id mapping
5. ✅ Custom mappings are validated before approval
6. ✅ Custom mappings are used in generated YAML
7. ✅ UI shows clear feedback on mapping changes
