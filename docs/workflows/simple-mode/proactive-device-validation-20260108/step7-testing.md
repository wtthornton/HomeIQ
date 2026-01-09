# Step 7: Testing Plan - Proactive Suggestions Device Validation

## Test Strategy

### Test Layers
1. **Unit Tests** - Test individual service methods
2. **Integration Tests** - Test API endpoints
3. **Manual Validation** - Verify fix in production

---

## Unit Tests

### DeviceValidationService Tests

```python
# tests/test_device_validation_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.proactive_agent_service.src.services.device_validation_service import (
    DeviceValidationService,
    ValidationResult,
)


class TestDeviceValidationService:
    """Unit tests for DeviceValidationService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked HTTP client."""
        return DeviceValidationService(
            ha_agent_url="http://test:8030",
            cache_ttl_seconds=60,
        )
    
    # Test: extract_device_mentions
    
    def test_extract_smart_device_pattern(self, service):
        """Test extraction of 'Smart X' pattern."""
        text = "Consider setting your Smart Humidifier to maintain humidity."
        mentions = service.extract_device_mentions(text)
        assert "Humidifier" in mentions
    
    def test_extract_your_device_pattern(self, service):
        """Test extraction of 'your X' pattern."""
        text = "Set your Living Room Thermostat to 72F."
        mentions = service.extract_device_mentions(text)
        assert any("Thermostat" in m or "Living Room" in m for m in mentions)
    
    def test_extract_quoted_device(self, service):
        """Test extraction of quoted device names."""
        text = 'Turn on the "Kitchen Light" when you arrive.'
        mentions = service.extract_device_mentions(text)
        assert "Kitchen Light" in mentions
    
    def test_extract_no_devices(self, service):
        """Test text with no device mentions."""
        text = "Today will be sunny with mild temperatures."
        mentions = service.extract_device_mentions(text)
        assert len(mentions) == 0
    
    # Test: validate_suggestion
    
    @pytest.mark.asyncio
    async def test_validate_suggestion_valid_device(self, service):
        """Test validation passes for existing device."""
        # Mock device inventory
        service._device_cache = [
            {"entity_id": "light.kitchen", "friendly_name": "Kitchen Light", "domain": "light"},
        ]
        service._cache_expires_at = None  # Force cache hit
        
        result = await service.validate_suggestion(
            'Turn on the "Kitchen Light" when you arrive.'
        )
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_suggestion_invalid_device(self, service):
        """Test validation fails for non-existent device."""
        # Mock device inventory without humidifier
        service._device_cache = [
            {"entity_id": "light.kitchen", "friendly_name": "Kitchen Light", "domain": "light"},
        ]
        service._cache_expires_at = None
        
        result = await service.validate_suggestion(
            "Set your Smart Humidifier to 50% humidity."
        )
        
        assert result.is_valid is False
        assert "Humidifier" in str(result.invalid_devices)
    
    @pytest.mark.asyncio
    async def test_validate_suggestion_no_devices_mentioned(self, service):
        """Test validation passes when no specific devices mentioned."""
        service._device_cache = []
        
        result = await service.validate_suggestion(
            "It's a great day to save energy!"
        )
        
        assert result.is_valid is True
    
    # Test: has_device_type
    
    @pytest.mark.asyncio
    async def test_has_device_type_exists(self, service):
        """Test device type exists in inventory."""
        service._device_cache = [
            {"entity_id": "climate.main", "friendly_name": "Thermostat", "domain": "climate"},
        ]
        
        result = await service.has_device_type("climate")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_device_type_not_exists(self, service):
        """Test device type does not exist."""
        service._device_cache = [
            {"entity_id": "light.kitchen", "friendly_name": "Kitchen Light", "domain": "light"},
        ]
        
        result = await service.has_device_type("humidifier")
        assert result is False
    
    # Test: get_device_list_for_llm
    
    @pytest.mark.asyncio
    async def test_get_device_list_for_llm(self, service):
        """Test LLM device list format."""
        service._device_cache = [
            {"entity_id": "light.kitchen", "friendly_name": "Kitchen Light", "domain": "light"},
            {"entity_id": "light.bedroom", "friendly_name": "Bedroom Light", "domain": "light"},
            {"entity_id": "climate.main", "friendly_name": "Thermostat", "domain": "climate"},
        ]
        
        result = await service.get_device_list_for_llm()
        
        assert result["total_devices"] == 3
        assert "light" in result["device_domains_available"]
        assert "climate" in result["device_domains_available"]
        assert "Kitchen Light" in result["available_devices"]["light"]
```

### AIPromptGenerationService Tests

```python
# tests/test_ai_prompt_generation_service.py

import pytest
from unittest.mock import AsyncMock, patch
from services.proactive_agent_service.src.services.ai_prompt_generation_service import (
    AIPromptGenerationService,
)


class TestAIPromptGenerationService:
    """Unit tests for AIPromptGenerationService."""
    
    def test_filter_weather_insights_with_climate(self):
        """Test insights are kept when device type exists."""
        service = AIPromptGenerationService(openai_api_key="test")
        
        insights = [
            "High temperature - consider cooling automation",
            "Sunny day expected",
        ]
        device_domains = {"climate", "light"}
        
        filtered = service._filter_weather_insights(insights, device_domains)
        
        # Cooling insight should be kept (climate exists)
        assert any("cooling" in i.lower() for i in filtered)
    
    def test_filter_weather_insights_without_humidifier(self):
        """Test humidity insights are filtered when no humidifier."""
        service = AIPromptGenerationService(openai_api_key="test")
        
        insights = [
            "High humidity - consider dehumidifier automation",
            "Sunny day expected",
        ]
        device_domains = {"light", "switch"}  # No humidifier
        
        filtered = service._filter_weather_insights(insights, device_domains)
        
        # Dehumidifier insight should be filtered out
        assert not any("dehumidifier" in i.lower() for i in filtered)
        # Sunny day should remain
        assert any("Sunny" in i for i in filtered)
    
    def test_build_llm_context_includes_device_list(self):
        """Test LLM context includes explicit device list."""
        service = AIPromptGenerationService(openai_api_key="test")
        
        context_analysis = {
            "weather": {"available": True, "current": {"temperature": 25, "humidity": 50}},
        }
        home_context = {"available": True, "tier1_context": "AREAS: Living Room"}
        device_inventory = {
            "available_devices": {"light": ["Kitchen Light"]},
            "total_devices": 1,
            "device_domains_available": ["light"],
        }
        
        llm_context = service._build_llm_context(
            context_analysis,
            home_context,
            device_inventory,
        )
        
        assert "AVAILABLE DEVICES" in llm_context
        assert "Kitchen Light" in llm_context
        assert "ONLY suggest" in llm_context
```

---

## Integration Tests

### API Endpoint Tests

```python
# tests/test_suggestions_api.py

import pytest
from httpx import AsyncClient
from services.proactive_agent_service.src.main import app


class TestSuggestionsAPI:
    """Integration tests for suggestions API."""
    
    @pytest.mark.asyncio
    async def test_report_invalid_suggestion(self):
        """Test POST /api/v1/suggestions/{id}/report endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First create a suggestion
            create_response = await client.post("/api/v1/suggestions/sample")
            assert create_response.status_code == 200
            suggestion_id = create_response.json()["suggestion_id"]
            
            # Report it as invalid
            report_response = await client.post(
                f"/api/v1/suggestions/{suggestion_id}/report",
                json={
                    "reason": "device_not_found",
                    "feedback": "I don't have a humidifier",
                },
            )
            
            assert report_response.status_code == 200
            data = report_response.json()
            assert data["success"] is True
            assert "report_id" in data
    
    @pytest.mark.asyncio
    async def test_report_invalid_suggestion_not_found(self):
        """Test reporting non-existent suggestion."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/nonexistent/report",
                json={"reason": "device_not_found"},
            )
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_invalid_reports(self):
        """Test GET /api/v1/suggestions/reports/invalid endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/suggestions/reports/invalid")
            
            assert response.status_code == 200
            data = response.json()
            assert "reports" in data
            assert "total" in data
            assert "by_reason" in data
```

---

## Manual Validation Checklist

### Pre-Deployment Testing
- [ ] Rebuild proactive-agent-service container
- [ ] Verify service starts without errors
- [ ] Check logs for "DeviceValidationService initialized"
- [ ] Check logs for "device_validation=enabled"

### Functional Testing
- [ ] Trigger suggestion generation manually
- [ ] Verify suggestions no longer mention non-existent devices
- [ ] Verify "Smart Humidifier" suggestions are rejected (if no humidifier)
- [ ] Check logs for "Rejected suggestion (device validation failed)"

### API Testing
```powershell
# Test report endpoint
$body = @{reason="device_not_found"; feedback="Test feedback"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8024/api/v1/suggestions/{id}/report" -Method Post -Body $body -ContentType "application/json"

# Test reports list endpoint
Invoke-RestMethod -Uri "http://localhost:8024/api/v1/suggestions/reports/invalid"
```

### Database Verification
- [ ] Verify `invalid_suggestion_reports` table exists
- [ ] Verify foreign key to `suggestions` table works
- [ ] Verify reports are persisted correctly

---

## Test Coverage Goals

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| DeviceValidationService | 0% | 80% | High |
| AIPromptGenerationService (new methods) | 0% | 80% | High |
| API endpoints | 0% | 80% | Medium |
| Models | N/A | N/A | Low |

---

## Regression Tests

### Ensure Existing Functionality Works
- [ ] Existing suggestions list endpoint still works
- [ ] Existing suggestion creation still works
- [ ] Context analysis still returns data
- [ ] Scheduled generation still runs

### Performance Testing
- [ ] Device inventory caching works (verify logs show "Using cached device inventory")
- [ ] Validation adds <100ms latency
- [ ] No memory leaks from device cache

---

## Deployment Verification

### After Deployment
1. Monitor logs for errors
2. Check suggestion generation works
3. Verify no hallucinated devices appear
4. Test report functionality from UI

### Success Criteria
- ✅ No suggestions reference "Smart Humidifier" (or other non-existent devices)
- ✅ Logs show device validation is active
- ✅ Users can report invalid suggestions
- ✅ No regression in existing functionality

---
*Generated by TappsCodingAgents Simple Mode - Step 7: @tester *test*
