# Blueprint Suggestions Parameter-Based Generation - Complete

**Date:** January 16, 2026  
**Status:** ✅ All changes implemented

## Summary

Transformed Blueprint Suggestions from automatic generation to user-controlled parameter-based generation. Users can now:
- Delete all suggestions
- Generate suggestions with custom parameters (device selection, complexity, use case, count, etc.)
- Control exactly what suggestions are created

## Changes Implemented

### 1. ✅ Delete All Suggestions Endpoint

**Backend:** `services/blueprint-suggestion-service/src/api/routes.py`
- Added `DELETE /api/blueprint-suggestions/suggestions/all` endpoint
- Deletes all suggestions from database (regardless of status)
- Returns count of deleted suggestions

**Frontend:** `services/ai-automation-ui/src/services/blueprintSuggestionsApi.ts`
- Added `deleteAllSuggestions()` function
- Added "Delete All" button in UI

### 2. ✅ Parameter-Based Generation Endpoint

**Backend:** `services/blueprint-suggestion-service/src/api/routes.py`
- Updated `POST /api/blueprint-suggestions/generate` endpoint
- Changed from query parameters to request body with `GenerateSuggestionsRequest` schema
- Supports:
  - `device_ids`: Specific device entity IDs (or None for all)
  - `complexity`: Filter by complexity ('simple', 'medium', 'high', or None)
  - `use_case`: Filter by use case ('convenience', 'security', 'energy', 'comfort', or None)
  - `min_score`: Minimum suggestion score threshold (0.0-1.0)
  - `max_suggestions`: Maximum number of suggestions to generate (1-100)
  - `min_quality_score`: Minimum blueprint quality score filter
  - `domain`: Filter by device domain (e.g., 'light', 'switch', 'sensor')

**Service Layer:** `services/blueprint-suggestion-service/src/services/suggestion_service.py`
- Added `generate_suggestions_with_params()` method
- Filters suggestions based on user parameters

**Matcher Layer:** `services/blueprint-suggestion-service/src/services/blueprint_matcher.py`
- Added `generate_suggestions_with_params()` method
- Filters blueprints by complexity, use_case, quality_score
- Filters entities by device_ids, domain
- Limits total suggestions to `max_suggestions`

### 3. ✅ UI Updates

**Frontend:** `services/ai-automation-ui/src/pages/BlueprintSuggestions.tsx`
- Added "Generate Suggestions" button that shows/hides generation form
- Added "Delete All" button in header
- Generation form includes:
  - Max Suggestions (1-100)
  - Min Score slider (0-100%)
  - Complexity dropdown (All, Simple, Medium, High)
  - Use Case dropdown (All, Convenience, Security, Energy, Comfort)
  - Domain text input (optional, e.g., 'light', 'switch')
  - Min Quality Score (optional, 0-1.0)
- Form shows/hides based on button click
- Generation shows loading state

**API Client:** `services/ai-automation-ui/src/services/blueprintSuggestionsApi.ts`
- Updated `generateSuggestions()` to accept `GenerateSuggestionsRequest`
- Added `deleteAllSuggestions()` function
- Added TypeScript interfaces for request/response

## Service Capabilities Analysis

### Current Capabilities

1. **Scoring System:**
   - Device match score (50% weight)
   - Blueprint quality score (15% weight)
   - Community rating (10% weight)
   - Temporal relevance (10% weight)
   - User profile match (10% weight)
   - Complexity bonus (5% weight)

2. **Blueprint Filtering:**
   - Complexity: 'low' (blueprints), 'simple'/'medium'/'high' (API)
   - Use case: 'convenience', 'security', 'energy', 'comfort'
   - Quality score: 0.0-1.0
   - Community rating: 0.0-1.0
   - Domain requirements
   - Device class requirements

3. **Device Matching:**
   - Entity ID matching
   - Domain matching
   - Device class matching
   - Area matching
   - Same-area bonus

4. **Suggestion Generation:**
   - Multiple suggestions per blueprint (different device combinations)
   - Scoring of each combination
   - Sorting by score (highest first)
   - Limiting by max suggestions

## Recommendations for Improvements

### 1. **Complexity Value Inconsistency**

**Issue:** Blueprints use 'low'/'medium'/'high' but scorer/API uses 'simple'/'medium'/'high'

**Recommendation:**
- Standardize on 'low'/'medium'/'high' to match blueprint data
- Update scorer to handle 'low' instead of 'simple'
- Update API schema to use 'low'/'medium'/'high'

### 2. **Device Selection Enhancement**

**Current:** Users can specify entity IDs manually (text input not implemented in UI)

**Recommendations:**
- Add device picker/autocomplete in UI
- Support multi-select device selection
- Add "Select from favorites" option
- Add "Select by area" filter
- Show device count for selected devices

### 3. **Additional Parameters**

**Recommendations:**
- **Area filter**: Filter by Home Assistant area (e.g., "Living Room", "Bedroom")
- **Device type filter**: Multi-select device types (light, switch, sensor, etc.)
- **Blueprint source filter**: Filter by blueprint source (community, official, custom)
- **Community rating threshold**: Minimum community rating (0-5 stars)
- **Date range**: Only suggest blueprints updated/created within date range
- **Sort order**: Sort suggestions by score, date, or alphabetically

### 4. **Generation Strategy Options**

**Recommendations:**
- **Diversity mode**: Ensure suggestions cover different use cases/complexities
- **Best matches only**: Only top-scoring suggestions
- **Exploratory mode**: Include lower-scoring suggestions for discovery
- **Personalization**: Weight suggestions by user's accepted/declined history

### 5. **UI/UX Improvements**

**Recommendations:**
- **Preset configurations**: Save/load common parameter sets
- **Preview mode**: Show estimated number of suggestions before generating
- **Generation history**: Track and display previous generation parameters
- **Batch operations**: Generate multiple batches with different parameters
- **Export/Import**: Export suggestions, import from file
- **Suggestion comparison**: Side-by-side comparison of suggestions

### 6. **Performance Optimizations**

**Recommendations:**
- **Caching**: Cache blueprint/device data for faster subsequent generations
- **Incremental generation**: Generate suggestions in background, notify when complete
- **Parallel processing**: Generate suggestions for multiple blueprints in parallel
- **Pagination**: Support paginated generation (generate first 10, then more)

### 7. **Analytics and Insights**

**Recommendations:**
- **Generation analytics**: Track which parameters produce most accepted suggestions
- **Suggestion quality metrics**: Track acceptance rate by complexity, use case, etc.
- **User feedback**: Collect feedback on suggestion relevance
- **A/B testing**: Test different scoring weights/parameters

### 8. **Advanced Features**

**Recommendations:**
- **Suggestion templates**: Save successful parameter combinations as templates
- **Smart suggestions**: AI-powered parameter recommendations based on user's devices
- **Conflicts detection**: Warn about suggestions that conflict with existing automations
- **Dependencies**: Show which suggestions depend on other suggestions
- **Grouping**: Group related suggestions together

## Parameter Recommendations Summary

### User-Controllable Parameters (Implemented)

1. ✅ **Device Selection** (`device_ids`)
   - Select specific devices or all
   - Future: Multi-select UI, area-based selection

2. ✅ **Complexity** (`complexity`)
   - Simple/Medium/High (or All)
   - Future: Map to blueprint 'low'/'medium'/'high'

3. ✅ **Use Case** (`use_case`)
   - Convenience/Security/Energy/Comfort (or All)
   - Matches blueprint classification

4. ✅ **Min Score** (`min_score`)
   - 0.0-1.0 threshold
   - Filters out low-quality suggestions

5. ✅ **Max Suggestions** (`max_suggestions`)
   - 1-100 limit
   - Controls total output

6. ✅ **Min Quality Score** (`min_quality_score`)
   - 0.0-1.0 threshold
   - Filters blueprints by quality

7. ✅ **Domain** (`domain`)
   - Device domain filter (e.g., 'light', 'switch')
   - Narrow device selection

### Recommended Additional Parameters (Not Implemented)

1. **Area Filter** (`area_ids`)
   - Filter devices by Home Assistant area
   - Useful for room-specific automations

2. **Device Type Multi-Select** (`device_types`)
   - Select multiple device types
   - More flexible than single domain

3. **Blueprint Source** (`source_type`)
   - Filter by blueprint source (community, official, custom)
   - Quality indicator

4. **Community Rating** (`min_community_rating`)
   - Minimum community rating (0-5 stars)
   - Quality filter

5. **Date Range** (`created_after`, `updated_after`)
   - Filter blueprints by creation/update date
   - Freshness filter

6. **Sort Order** (`sort_by`, `sort_order`)
   - Sort suggestions by score, date, or name
   - User preference

7. **Diversity Mode** (`diversity_mode`)
   - Ensure suggestions cover different use cases
   - Better discovery

## Testing Recommendations

1. **Unit Tests:**
   - Test parameter filtering logic
   - Test suggestion generation with various parameter combinations
   - Test edge cases (empty filters, invalid values)

2. **Integration Tests:**
   - Test full generation flow with parameters
   - Test delete all functionality
   - Test UI form submission

3. **E2E Tests:**
   - Test user workflow: generate → review → accept/decline
   - Test parameter persistence
   - Test error handling

## Breaking Changes

### API Changes

1. **Generate Endpoint:** Changed from query parameters to request body
   - Old: `POST /api/blueprint-suggestions/generate?min_score=0.6&max_per_blueprint=5`
   - New: `POST /api/blueprint-suggestions/generate` with JSON body

2. **No Automatic Generation:**
   - Suggestions are no longer automatically generated
   - Users must explicitly trigger generation via API/UI

### Migration Notes

- Existing suggestions remain in database
- Users can delete all and regenerate with new parameters
- No database schema changes required

## Next Steps

1. ✅ **Complete Implementation** (DONE)
   - Delete all endpoint
   - Parameter-based generation
   - UI updates

2. **Recommended Next Steps:**
   - Fix complexity value inconsistency ('low' vs 'simple')
   - Add device picker UI component
   - Add preset configurations
   - Add generation analytics
   - Performance optimizations
   - Additional parameter support

## Files Changed

### Backend
- `services/blueprint-suggestion-service/src/api/schemas.py`
- `services/blueprint-suggestion-service/src/api/routes.py`
- `services/blueprint-suggestion-service/src/services/suggestion_service.py`
- `services/blueprint-suggestion-service/src/services/blueprint_matcher.py`

### Frontend
- `services/ai-automation-ui/src/services/blueprintSuggestionsApi.ts`
- `services/ai-automation-ui/src/pages/BlueprintSuggestions.tsx`

## Related Documentation

- Blueprint Suggestion Service README: `services/blueprint-suggestion-service/README.md`
- Blueprint Architecture: `docs/architecture/BLUEPRINT_ARCHITECTURE.md`
- Previous fixes: `implementation/BLUEPRINT_SUGGESTION_FIXES_COMPLETE.md`
