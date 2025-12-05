# Area Registry API Research - 2025 Home Assistant

**Date:** January 2025  
**Issue:** "No areas found" in HA AI Agent Service context injection  
**Status:** Research Complete - Solution Identified

## Executive Summary

The `ha-ai-agent-service` is using the REST API endpoint `/api/config/area_registry/list` which may not be available in all Home Assistant versions or configurations. The **WebSocket API** is the recommended method for accessing area registry data in Home Assistant 2025.

## Problem Analysis

### Current Implementation

**File:** `services/ha-ai-agent-service/src/clients/ha_client.py`

```64:102:services/ha-ai-agent-service/src/clients/ha_client.py
async def get_area_registry(self) -> list[dict[str, Any]]:
    """
    Get area registry from Home Assistant.

    Uses endpoint: GET /api/config/area_registry/list
    Note: This endpoint may not be in basic REST API docs but is used in HA codebase.
    Falls back gracefully if endpoint not available (404).

    Returns:
        List of area dictionaries with keys: area_id, name, aliases, etc.

    Raises:
        Exception: If API request fails (except 404 which returns empty list)
    """
    try:
        session = await self._get_session()
        url = f"{self.ha_url}/api/config/area_registry/list"

        async with session.get(url) as response:
            if response.status == 404:
                # Some HA versions/configurations don't expose this endpoint
                logger.info("ℹ️ Area Registry API not available (404) - returning empty list")
                return []
            response.raise_for_status()
            data = await response.json()
            # Handle both list format and dict with 'areas' key
            if isinstance(data, dict) and "areas" in data:
                areas = data["areas"]
            elif isinstance(data, list):
                areas = data
            else:
                areas = []
            logger.info(f"✅ Fetched {len(areas)} areas from Home Assistant")
            return areas
    except aiohttp.ClientError as e:
        error_msg = f"Failed to fetch area registry: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg) from e
```

**Issues Identified:**

1. **REST API Endpoint May Not Exist**: The endpoint `/api/config/area_registry/list` is not part of the official Home Assistant REST API documentation
2. **404 Handling**: The code treats 404 as "not available" and returns empty list, which results in "No areas found"
3. **Response Format Uncertainty**: The code handles multiple response formats, suggesting uncertainty about the actual API response

### Working Implementation (Reference)

**File:** `services/device-intelligence-service/src/clients/ha_client.py`

This service uses the **WebSocket API** which is the correct method:

```448:472:services/device-intelligence-service/src/clients/ha_client.py
async def get_area_registry(self) -> list[HAArea]:
    """Get all areas from Home Assistant area registry."""
    try:
        response = await self.send_message({
            "type": "config/area_registry/list"
        })

        areas = []
        for area_data in response.get("result", []):
            area = HAArea(
                area_id=area_data["area_id"],
                name=area_data["name"],
                normalized_name=area_data.get("normalized_name", area_data["name"].lower().replace(" ", "_")),
                aliases=area_data.get("aliases", []),
                created_at=self._parse_timestamp(area_data.get("created_at")),
                updated_at=self._parse_timestamp(area_data.get("updated_at"))
            )
            areas.append(area)

        logger.info(f"🏠 Discovered {len(areas)} areas from Home Assistant")
        return areas

    except Exception as e:
        logger.error(f"❌ Failed to get area registry: {e}")
        return []
```

**Key Differences:**
- Uses WebSocket API with `{"type": "config/area_registry/list"}`
- Response format: `response.get("result", [])`
- This is the **official** way to access area registry in Home Assistant

## 2025 Home Assistant API Research

### REST API Limitations

According to research:

1. **No Official Area Registry Endpoint**: The Home Assistant REST API does not provide a direct endpoint for area registry data
2. **WebSocket API is Primary**: The WebSocket API is the recommended method for accessing configuration data like areas, devices, and entities
3. **Community Reports**: Users have reported that area-related endpoints are missing from the REST API

### WebSocket API (2025 Standard)

**Command Format:**
```json
{
    "type": "config/area_registry/list",
    "id": <message_id>
}
```

**Response Format:**
```json
{
    "id": <message_id>,
    "type": "result",
    "success": true,
    "result": [
        {
            "area_id": "office",
            "name": "Office",
            "aliases": ["workspace", "study"],
            "icon": "mdi:office-building",
            "labels": [],
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z"
        },
        ...
    ]
}
```

### Why REST API Fails

1. **Endpoint Not Standardized**: `/api/config/area_registry/list` is not part of the official REST API
2. **Version-Dependent**: May work in some HA versions but not others
3. **Configuration-Dependent**: May require specific HA configurations to be exposed
4. **Better Alternative Exists**: WebSocket API is the official, supported method

## Root Cause

The "No areas found" message appears because:

1. The REST API endpoint `/api/config/area_registry/list` returns 404 (not found)
2. The code treats 404 as "endpoint not available" and returns an empty list
3. The `areas_service.py` receives an empty list and formats it as "No areas found"

**Evidence:**
- Code comment: "Some HA versions/configurations don't expose this endpoint"
- 404 handling returns empty list instead of using fallback
- Fallback to entity-based extraction exists but may not be triggered if 404 is handled gracefully

## Solution Options

### Option 1: Implement WebSocket API Support (Recommended)

**Pros:**
- Official Home Assistant API method
- Consistent with `device-intelligence-service` implementation
- Reliable across all HA versions
- Supports real-time updates via subscriptions

**Cons:**
- Requires WebSocket client implementation
- More complex than REST API
- Requires connection management

**Implementation Steps:**
1. Add WebSocket client to `ha-ai-agent-service`
2. Implement `get_area_registry()` using WebSocket API
3. Handle WebSocket connection lifecycle
4. Add retry logic for connection failures

### Option 2: Improve REST API Fallback

**Pros:**
- Minimal code changes
- Keeps REST API approach
- Quick fix

**Cons:**
- Still relies on non-standard endpoint
- May not work in all HA versions
- Not future-proof

**Implementation Steps:**
1. Check if REST endpoint exists before calling
2. Improve fallback to entity-based extraction
3. Add better error logging
4. Consider alternative REST endpoints

### Option 3: Use Entity-Based Extraction (Current Fallback)

**Pros:**
- Already implemented
- Works with standard REST API (`/api/states`)
- No WebSocket dependency

**Cons:**
- Less complete (only areas with entities)
- No area metadata (aliases, icons, labels)
- May miss areas without entities

**Current Implementation:**
```129:172:services/ha-ai-agent-service/src/services/areas_service.py
async def _extract_areas_from_entities(self) -> str:
    """
    Fallback: Extract areas from entity area_id values.
    
    Returns:
        Formatted areas list string
    """
    try:
        # Fetch entities from data-api
        entities = await self.data_api_client.fetch_entities(limit=1000)
        
        if not entities:
            return "No areas found"
        
        # Collect unique area_ids from entities
        area_ids = set()
        for entity in entities:
            area_id = entity.get("area_id")
            if area_id and area_id != "unassigned":
                area_ids.add(area_id)
        
        if not area_ids:
            return "No areas found"
        
        # Format areas (use area_id as name if no friendly name available)
        area_parts = []
        for area_id in sorted(area_ids):
            # Convert area_id to friendly name (replace underscores with spaces, title case)
            friendly_name = area_id.replace("_", " ").title()
            area_parts.append(f"{friendly_name} (area_id: {area_id})")
        
        areas_str = ", ".join(area_parts)
        
        # Cache the result
        await self.context_builder._set_cached_value(
            self._cache_key, areas_str, self._cache_ttl
        )
        
        logger.info(f"✅ Extracted {len(area_ids)} areas from entities")
        return areas_str
        
    except Exception as e:
        logger.error(f"❌ Error extracting areas from entities: {e}", exc_info=True)
        return "Areas unavailable."
```

## Recommended Solution

**Implement WebSocket API Support** (Option 1)

### Rationale

1. **Official API**: WebSocket API is the official, documented method for area registry
2. **Consistency**: Matches implementation in `device-intelligence-service`
3. **Future-Proof**: Will continue to work as HA evolves
4. **Feature Complete**: Provides full area metadata (aliases, icons, labels)
5. **Real-Time**: Supports subscriptions for area updates

### Implementation Plan

1. **Add WebSocket Client Dependency**
   - Add `websockets` package to requirements
   - Or reuse existing WebSocket implementation if available

2. **Create WebSocket Client Class**
   - Reference: `services/device-intelligence-service/src/clients/ha_client.py`
   - Implement connection management
   - Implement message sending/receiving
   - Handle authentication

3. **Update `get_area_registry()` Method**
   - Use WebSocket API: `{"type": "config/area_registry/list"}`
   - Parse response: `response.get("result", [])`
   - Maintain same return type: `list[dict[str, Any]]`

4. **Add Fallback Logic**
   - If WebSocket fails, fall back to entity-based extraction
   - Log warnings for debugging

5. **Update Tests**
   - Add WebSocket API tests
   - Mock WebSocket responses
   - Test fallback scenarios

## Immediate Workaround

If WebSocket implementation is not immediately feasible:

1. **Check if areas exist in Home Assistant UI**
   - Navigate to Configuration > Areas
   - Verify areas are defined

2. **Verify REST API Endpoint**
   ```powershell
   $haUrl = "http://localhost:8123"
   $token = "YOUR_TOKEN"
   $response = Invoke-RestMethod -Uri "$haUrl/api/config/area_registry/list" -Headers @{Authorization="Bearer $token"}
   $response
   ```

3. **Use Entity-Based Fallback**
   - The fallback method should work if entities have `area_id` assigned
   - Check entity area assignments in Home Assistant

4. **Manual Area Creation**
   - If no areas exist, create them in Home Assistant UI
   - Assign entities to areas for better organization

## Testing Recommendations

1. **Test WebSocket Connection**
   - Verify WebSocket URL: `ws://<ha_url>/api/websocket`
   - Test authentication flow
   - Test area registry command

2. **Test Response Parsing**
   - Verify response format matches expected structure
   - Handle missing fields gracefully
   - Test with empty area registry

3. **Test Fallback**
   - Simulate WebSocket failure
   - Verify entity-based extraction works
   - Test with no entities assigned to areas

## References

- **Device Intelligence Service Implementation**: `services/device-intelligence-service/src/clients/ha_client.py`
- **Areas Service**: `services/ha-ai-agent-service/src/services/areas_service.py`
- **HA Client (Current)**: `services/ha-ai-agent-service/src/clients/ha_client.py`
- **Home Assistant WebSocket API**: https://developers.home-assistant.io/docs/api/websocket/
- **Home Assistant REST API**: https://developers.home-assistant.io/docs/api/rest/

## Conclusion

The "No areas found" issue is caused by using a non-standard REST API endpoint that may not be available in all Home Assistant configurations. The **WebSocket API** is the official, recommended method for accessing area registry data in Home Assistant 2025.

**Next Steps:**
1. Implement WebSocket API support in `ha-ai-agent-service`
2. Update `get_area_registry()` to use WebSocket API
3. Maintain entity-based fallback for compatibility
4. Test with various Home Assistant versions

