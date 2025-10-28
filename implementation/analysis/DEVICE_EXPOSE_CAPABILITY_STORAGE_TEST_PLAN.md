# Device Expose/Capability Storage - Test Plan

**Last Updated:** January 2025  
**Status:** Testing Requirements for Device Capability Storage Implementation  
**Related to:** DEVICE_EXPOSE_CAPABILITY_STORAGE_PLAN.md

---

## Summary of Changes

The implementation adds:
1. **Cache TTL Extension**: 5 min → 6 hours (Phase 1)
2. **Capability Storage**: Store Zigbee2MQTT exposes in DB (Phase 2)
3. **Cache Invalidation**: Invalidate on MQTT updates (Phase 3)
4. **Non-MQTT Capabilities**: Extract capabilities from HA entities (Phase 4)
5. **Enhanced API Response**: Include capabilities in responses (Phase 5)

---

## Testing Strategy

### Unit Tests (Priority: HIGH)
**Location:** `services/device-intelligence-service/tests/`

#### 1. Cache TTL Tests (Phase 1)
**File:** `test_cache.py` (NEW - needs to be created)

```python
@pytest.mark.asyncio
async def test_cache_ttl_extended_to_six_hours():
    """Test that cache TTL is now 6 hours instead of 5 minutes."""
    cache = DeviceCache(max_size=500, default_ttl=21600)
    assert cache.default_ttl == 21600  # 6 hours
    
    # Test cache entry lasts for intended duration
    await cache.set_device("test-device", {"test": "data"})
    
    # Should still be valid after 5 minutes (old TTL would expire)
    await asyncio.sleep(300)  # 5 minutes
    result = await cache.get_device("test-device")
    assert result is not None
```

**Test Focus:**
- [ ] Verify TTL is 21600 (6 hours) not 300 (5 min)
- [ ] Test cache persists longer than old TTL
- [ ] Verify cache expiration behavior with new TTL
- [ ] Test cache cleanup with extended TTL

---

#### 2. Capability Storage Tests (Phase 2)
**File:** `test_discovery_service.py` (UPDATE existing file)

```python
@pytest.mark.asyncio
async def test_store_capabilities_in_database(mock_settings):
    """Test that Zigbee2MQTT capabilities are stored in database."""
    service = DiscoveryService(mock_settings)
    
    # Mock device with capabilities
    mock_device = UnifiedDevice(
        id="test-device-1",
        name="Test Zigbee Device",
        capabilities=[
            {
                "name": "state",
                "type": "binary",
                "properties": {"state": "on"},
                "exposed": True,
                "configured": True,
                "source": "zigbee2mqtt"
            }
        ]
    )
    
    # Call storage method
    await service._store_devices_in_database([mock_device])
    
    # Verify capabilities stored in database
    async for session in get_db_session():
        stmt = select(DeviceCapability).where(
            DeviceCapability.device_id == "test-device-1"
        )
        result = await session.execute(stmt)
        capabilities = result.scalars().all()
        
        assert len(capabilities) == 1
        assert capabilities[0].capability_name == "state"
        assert capabilities[0].source == "zigbee2mqtt"
        break
```

**Test Focus:**
- [ ] Verify capabilities stored in `device_capabilities` table
- [ ] Test capability properties stored as JSON
- [ ] Test source field is "zigbee2mqtt"
- [ ] Test exposed and configured fields
- [ ] Test bulk upsert handles duplicates correctly
- [ ] Test database constraint (device_id + capability_name)

---

#### 3. Cache Invalidation Tests (Phase 3)
**File:** `test_cache.py` (NEW)

```python
@pytest.mark.asyncio
async def test_cache_invalidation_on_device_update(mock_settings):
    """Test that cache is invalidated when device updates via MQTT."""
    service = DiscoveryService(mock_settings)
    cache = get_device_cache()
    
    # Set device in cache
    await cache.set_device("test-device-1", {"name": "Old Name"})
    
    # Simulate MQTT update
    await service._on_zigbee_devices_update([{
        "ieee_address": "00:11:22:33:44:55:66:77",
        "friendly_name": "New Name"
    }])
    
    # Cache should be invalidated
    result = await cache.get_device("test-device-1")
    assert result is None  # Cache should be empty
    
    # After unification, cache should be repopulated
    await service._unify_device_data()
    result = await cache.get_device("test-device-1")
    assert result is not None
    assert result["name"] == "New Name"
```

**Test Focus:**
- [ ] Cache invalidated on MQTT device update
- [ ] Cache repopulated after unification
- [ ] Only updated devices invalidated
- [ ] Multiple device updates handled correctly
- [ ] No cache invalidation for unrelated devices

---

#### 4. Non-MQTT Capability Extraction Tests (Phase 4)
**File:** `test_device_parser.py` (NEW)

```python
def test_parse_ha_entity_capabilities_for_light():
    """Test parsing capabilities from HA light entities."""
    parser = DeviceParser()
    
    mock_entities = [
        HAEntity(entity_id="light.living_room", name="Living Room Light")
    capabilities = parser._parse_ha_entity_capabilities(
        mock_entities, "light"
    )
    
    assert len(capabilities) >= 4
    assert any(c["name"] == "brightness" for c in capabilities)
    assert any(c["name"] == "color_temp" for c in capabilities)
    assert any(c["name"] == "color" for c in capabilities)
    assert all(c["source"] == "homeassistant" for c in capabilities)
    assert all(c["properties"].get("inferred") == True for c in capabilities)

def test_parse_capabilities_for_different_domains():
    """Test parsing capabilities for different HA domains."""
    parser = DeviceParser()
    
    # Test light
    light_caps = parser._parse_ha_entity_capabilities([], "light")
    assert any("brightness" in c["name"] for c in light_caps)
    
    # Test climate
    climate_caps = parser._parse_ha_entity_capabilities([], "climate")
    assert any("temperature" in c["name"] for c in climate_caps)
    
    # Test switch
    switch_caps = parser._parse_ha_entity_capabilities([], "switch")
    assert any("state" in c["name"] for c in switch_caps)
```

**Test Focus:**
- [ ] All domains return appropriate capabilities
- [ ] Inferred flag set to True
- [ ] Source set to "homeassistant"
- [ ] Properties include domain-specific details
- [ ] Unknown domains return empty list
- [ ] No errors on empty entity lists

---

#### 5. Enhanced API Response Tests (Phase 5)
**File:** `test_discovery_api.py` (UPDATE)

```python
@pytest.mark.asyncio
async def test_get_device_with_capabilities(client: TestClient, mock_device):
    """Test that device endpoint returns capabilities."""
    # Mock service with capabilities
    mock_device.capabilities = [
        {
            "name": "state",
            "type": "binary",
            "properties": {"state": "on"},
            "exposed": True,
            "source": "zigbee2mqtt"
        }
    ]
    
    response = client.get("/api/discovery/devices/test-device-1")
    assert response.status_code == 200
    
    data = response.json()
    assert "capabilities" in data
    assert len(data["capabilities"]) == 1
    assert data["capabilities"][0]["source"] == "zigbee2mqtt"

@pytest.mark.asyncio
async def test_fetch_capabilities_from_db_on_miss(client: TestClient):
    """Test fetching capabilities from DB when not in memory."""
    # Device in memory without capabilities
    mock_device = UnifiedDevice(id="test-1", name="Test", capabilities=[])
    
    # Mock DB has capabilities
    mock_capability = DeviceCapability(
        device_id="test-1",
        capability_name="state",
        capability_type="binary",
        properties={"state": "on"},
        exposed=True,
        source="zigbee2mqtt"
    )
    
    # Call endpoint
    response = client.get("/api/discovery/devices/test-1")
    assert response.status_code == 200
    data = response.json()
    
    # Should have fetched from DB
    assert len(data["capabilities"]) == 1
```

**Test Focus:**
- [ ] Capabilities included in device response
- [ ] Capabilities fetched from DB when missing
- [ ] Empty capabilities handled gracefully
- [ ] Source field preserved (zigbee2mqtt vs homeassistant)
- [ ] Properties JSON included in response
- [ ] Cache populated after DB fetch

---

### Integration Tests (Priority: MEDIUM)
**Location:** `services/device-intelligence-service/tests/integration/` (NEW directory)

#### 1. End-to-End Capability Flow
**File:** `test_capability_flow.py` (NEW)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_capability_flow():
    """Test complete flow: MQTT → Parse → Store → Cache → API."""
    
    # 1. Simulate MQTT device update
    mqtt_data = {
        "ieee_address": "00:11:22:33:44:55:66:77",
        "friendly_name": "Living Room Light",
        "definition": {
            "exposes": [
                {"name": "state", "type": "binary"},
                {"name": "brightness", "type": "numeric"}
            ]
        }
    }
    
    # 2. Process via discovery service
    service = DiscoveryService()
    await service._on_zigbee_devices_update([mqtt_data])
    
    # 3. Verify stored in database
    async for session in get_db_session():
        stmt = select(DeviceCapability).join(Device).where(
            Device.name == "Living Room Light"
        )
        result = await session.execute(stmt)
        capabilities = result.scalars().all()
        assert len(capabilities) == 2
        break
    
    # 4. Verify in cache
    cache = get_device_cache()
    device = await cache.get_device("device-id")
    assert len(device["capabilities"]) == 2
    
    # 5. Verify via API
    response = client.get("/api/discovery/devices/device-id")
    assert response.status_code == 200
    data = response.json()
    assert len(data["capabilities"]) == 2
```

**Test Focus:**
- [ ] Complete data flow works end-to-end
- [ ] No data loss between steps
- [ ] Cache consistency with database
- [ ] API reflects stored capabilities
- [ ] Error handling at each step

---

#### 2. Cache TTL Validation
**File:** `test_cache_ttl_integration.py` (NEW)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_persistence_across_periods():
    """Test cache persists for full 6 hours (simulated)."""
    cache = get_device_cache()
    
    # Store device
    await cache.set_device("test-1", {"name": "Test"})
    
    # Fast-forward time (simulate 5.5 hours)
    # In real test, use time mocking
    await asyncio.sleep(19800)  # 5.5 hours
    
    # Should still be cached
    result = await cache.get_device("test-1")
    assert result is not None
    
    # Fast-forward to 6.1 hours
    await asyncio.sleep(600)  # Additional 10 minutes
    
    # Should expire
    result = await cache.get_device("test-1")
    assert result is None
```

**Test Focus:**
- [ ] Cache persists for intended duration
- [ ] Cache expires at correct time
- [ ] Cleanup removes expired entries
- [ ] No memory leaks from expired entries

---

#### 3. Database Storage Validation
**File:** `test_database_storage_integration.py` (NEW)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_capability_database_operations():
    """Test database operations for capabilities."""
    
    # Clear database
    async for session in get_db_session():
        await session.execute(delete(DeviceCapability))
        await session.commit()
        break
    
    # Store capabilities
    capabilities_data = [
        {
            "device_id": "test-1",
            "capability_name": "state",
            "capability_type": "binary",
            "properties": {"state": "on"},
            "exposed": True,
            "configured": True,
            "source": "zigbee2mqtt"
        }
    ]
    
    repository = Repository()
    async for session in get_db_session():
        await repository.bulk_upsert_capabilities(session, capabilities_data)
        await session.commit()
        break
    
    # Verify stored
    async for session in get_db_session():
        stmt = select(DeviceCapability)
        result = await session.execute(stmt)
        capabilities = result.scalars().all()
        assert len(capabilities) == 1
        break
    
    # Test upsert (duplicate should not create new row)
    async for session in get_db_session():
        await repository.bulk_upsert_capabilities(session, capabilities_data)
        await session.commit()
        break
    
    # Should still be 1 row
    async for session in get_db_session():
        stmt = select(DeviceCapability)
        result = await session.execute(stmt)
        capabilities = result.scalars().all()
        assert len(capabilities) == 1
        break
```

**Test Focus:**
- [ ] Bulk insert works
- [ ] Upsert handles duplicates
- [ ] Composite key works (device_id + capability_name)
- [ ] JSON properties stored correctly
- [ ] Transactions work correctly
- [ ] No database deadlocks

---

### E2E Tests (Priority: LOW)
**Location:** `tests/e2e/`

#### 1. Update Existing Device Intelligence Tests
**File:** `tests/e2e/ai-automation-device-intelligence.spec.ts`

**Updates Needed:**
- Add test for capability data in API responses
- Verify capabilities visible in dashboard
- Test cache invalidation via API calls

```typescript
test('should show device capabilities from API', async ({ page }) => {
  // Mock enhanced API response with capabilities
  await page.route('**/api/discovery/devices/*', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'device-1',
        name: 'Living Room Light',
        capabilities: [
          {
            name: 'state',
            type: 'binary',
            exposed: true,
            source: 'zigbee2mqtt',
            properties: { state: 'on' }
          }
        ]
      })
    });
  });
  
  // Navigate and verify capabilities shown
  await page.goto('http://localhost:3001/devices/device-1');
  await expect(page.getByText(/state/i)).toBeVisible();
  await expect(page.getByText(/zigbee2mqtt/i)).toBeVisible();
});
```

**Test Focus:**
- [ ] Capabilities displayed in UI
- [ ] Source indicator shown
- [ ] Cache invalidation works via UI
- [ ] Real devices show capabilities
- [ ] Error handling for missing capabilities

---

## Test Files to Create/Update

### NEW Files Needed:
1. ✅ `services/device-intelligence-service/tests/test_cache.py`
   - Cache TTL tests
   - Cache invalidation tests
   - Cache persistence tests

2. ✅ `services/device-intelligence-service/tests/test_device_parser.py`
   - Capability extraction tests
   - Domain-specific capability tests
   - HA entity parsing tests

3. ✅ `services/device-intelligence-service/tests/test_repository_capabilities.py`
   - Database capability operations
   - Bulk upsert tests
   - Capability retrieval tests

4. ✅ `services/device-intelligence-service/tests/integration/test_capability_flow.py`
   - End-to-end flow tests
   - Integration between components

5. ✅ `services/device-intelligence-service/tests/integration/test_cache_ttl_integration.py`
   - Real TTL behavior tests

### FILES TO UPDATE:
1. ✅ `services/device-intelligence-service/tests/test_discovery_service.py`
   - Add capability storage tests
   - Add cache invalidation tests

2. ✅ `tests/e2e/ai-automation-device-intelligence.spec.ts`
   - Add capability display tests
   - Verify enhanced API responses

---

## Testing Priorities by Phase

### Phase 1: Cache TTL (2 min implementation)
**Priority:** HIGH  
**Tests Needed:**
- [ ] Unit test for TTL change
- [ ] Integration test for TTL behavior
- [ ] Performance test for cache persistence

### Phase 2: Capability Storage (20 min implementation)
**Priority:** HIGH  
**Tests Needed:**
- [ ] Unit test for database storage
- [ ] Unit test for bulk upsert
- [ ] Integration test for end-to-end flow

### Phase 3: Cache Invalidation (15 min implementation)
**Priority:** MEDIUM  
**Tests Needed:**
- [ ] Unit test for invalidation logic
- [ ] Integration test for invalidation flow
- [ ] Test for repopulation after invalidation

### Phase 4: Non-MQTT Capabilities (30 min implementation)
**Priority:** MEDIUM  
**Tests Needed:**
- [ ] Unit test for HA entity parsing
- [ ] Unit test for domain-specific capabilities
- [ ] Integration test for mixed device types

### Phase 5: Enhanced API Response (15 min implementation)
**Priority:** LOW  
**Tests Needed:**
- [ ] API test for capability inclusion
- [ ] API test for DB fallback
- [ ] E2E test for UI display

---

## Success Criteria

### Functional
- [ ] All capabilities stored in database
- [ ] Cache TTL is 6 hours
- [ ] Cache invalidates on updates
- [ ] API returns capabilities
- [ ] Non-MQTT devices have inferred capabilities

### Performance
- [ ] Cache hit rate > 80% after warm-up
- [ ] Database storage < 100ms per device
- [ ] API response time < 20ms for cached data
- [ ] No memory leaks with 6-hour TTL

### Data Quality
- [ ] All Zigbee2MQTT exposes stored correctly
- [ ] Source tracking accurate
- [ ] Properties JSON preserved
- [ ] Inferred capabilities marked correctly

---

## Risk Assessment

### High Risk Areas
1. **Cache TTL change** - Could affect performance if too short
2. **Database storage** - Could fail on bulk operations
3. **Cache invalidation** - Could cause stale data

### Mitigation
- Incremental testing after each phase
- Rollback plan ready
- Performance monitoring enabled

---

## Test Execution Order

1. **Phase 1** (Cache TTL) → Test → Deploy
2. **Phase 2** (Storage) → Test → Deploy  
3. **Phase 3** (Invalidation) → Test → Deploy
4. **Phase 4** (Non-MQTT) → Test → Deploy
5. **Phase 5** (API Enhancement) → Test → Deploy

**Total Testing Time:** ~60 minutes  
**Total Implementation + Testing:** ~172 minutes

---

## Next Steps

1. Create new test files
2. Update existing test files
3. Implement features incrementally
4. Run tests after each phase
5. Document results

