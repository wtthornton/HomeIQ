# Area Registry WebSocket API - Verification Guide

**Date:** January 2025  
**Status:** Ready for Testing

## Quick Verification Steps

### 1. Install Dependencies

```powershell
# Navigate to service directory
cd services/ha-ai-agent-service

# Install new websockets dependency
pip install websockets>=12.0,<13.0

# Or install all dependencies
pip install -r requirements.txt
```

### 2. Restart Service

**Option A: Docker Compose (Recommended)**
```powershell
# Restart the service
docker-compose restart ha-ai-agent-service

# Or rebuild if needed
docker-compose up -d --build ha-ai-agent-service

# Check logs
docker-compose logs -f ha-ai-agent-service
```

**Option B: Direct Python**
```powershell
# Stop existing service (if running)
# Then start:
cd services/ha-ai-agent-service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8030
```

### 3. Verify Implementation

**Option A: Run Verification Script**
```powershell
cd services/ha-ai-agent-service
python scripts/verify_area_registry.py
```

**Option B: Check Logs**
```powershell
# Watch for WebSocket API usage
docker-compose logs -f ha-ai-agent-service | Select-String "WebSocket|area"

# Look for these success messages:
# ✅ Fetched X areas via WebSocket API
# OR
# ✅ Fetched X areas from Home Assistant via REST API (fallback)
```

**Option C: Test via API**
```powershell
# Check context endpoint (should include areas)
$response = Invoke-RestMethod -Uri "http://localhost:8030/api/v1/context" -Method Get
$response | ConvertTo-Json -Depth 10

# Look for "AREAS:" section in the response
```

### 4. Check UI Context

1. Navigate to `http://localhost:3001/ha-agent`
2. Go to "Debug" tab
3. Select "Injected Context (Tier 1)"
4. Look for "AREAS:" section
5. Should see area names, IDs, aliases, icons, labels

## Expected Results

### Success Indicators

✅ **WebSocket API Working:**
```
🔌 Connecting to Home Assistant WebSocket: ws://...
🔐 Authentication required, sending token...
✅ WebSocket authenticated
✅ Fetched X areas via WebSocket API
```

✅ **REST API Fallback (if WebSocket fails):**
```
⚠️ WebSocket API failed: ...
🔄 Falling back to REST API...
✅ Fetched X areas from Home Assistant via REST API
```

✅ **Areas Found:**
```
🏠 Fetching areas from Home Assistant...
✅ Generated enhanced areas list: X areas
```

### Failure Indicators

❌ **WebSocket Connection Failed:**
```
❌ WebSocket connection failed: ...
🔄 Falling back to REST API...
```

❌ **Both APIs Failed:**
```
❌ Failed to fetch area registry (both WebSocket and REST failed): ...
```

❌ **No Areas Configured:**
```
No areas found
```

## Troubleshooting

### Issue: WebSocket Connection Fails

**Symptoms:**
- Logs show "WebSocket connection failed"
- Falls back to REST API

**Solutions:**
1. Verify Home Assistant URL is correct
2. Check WebSocket endpoint: `ws://<ha_url>/api/websocket`
3. Verify access token is valid
4. Check firewall/network settings
5. REST API fallback should still work

### Issue: No Areas Found

**Symptoms:**
- "No areas found" in context
- Empty areas list

**Solutions:**
1. **Check Home Assistant:**
   - Navigate to Configuration > Areas
   - Verify areas are created
   - Assign entities to areas

2. **Check Entity Area Assignments:**
   - Entities should have `area_id` set
   - Check entity registry in Home Assistant

3. **Test API Directly:**
   ```powershell
   # Test WebSocket API (if you have a WebSocket client)
   # Or test REST API:
   $haUrl = "http://localhost:8123"
   $token = "YOUR_TOKEN"
   Invoke-RestMethod -Uri "$haUrl/api/config/area_registry/list" -Headers @{Authorization="Bearer $token"}
   ```

### Issue: Service Won't Start

**Symptoms:**
- Service fails to start
- Import errors

**Solutions:**
1. **Install Dependencies:**
   ```powershell
   pip install -r services/ha-ai-agent-service/requirements.txt
   ```

2. **Check Python Version:**
   - Requires Python 3.10+

3. **Check Logs:**
   ```powershell
   docker-compose logs ha-ai-agent-service
   ```

## Testing Checklist

- [ ] Dependencies installed (`websockets>=12.0`)
- [ ] Service restarted successfully
- [ ] Logs show WebSocket API attempt
- [ ] Areas appear in context injection
- [ ] UI shows areas in "Injected Context (Tier 1)"
- [ ] Fallback to REST API works (if WebSocket unavailable)
- [ ] No errors in logs

## Manual Testing

### Test WebSocket API Directly

If you have a WebSocket client (like `websocat` or browser console):

```javascript
// Browser console (on Home Assistant UI)
const ws = new WebSocket('ws://localhost:8123/api/websocket');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  if (data.type === 'auth_required') {
    ws.send(JSON.stringify({
      type: 'auth',
      access_token: 'YOUR_TOKEN'
    }));
  } else if (data.type === 'auth_ok') {
    ws.send(JSON.stringify({
      id: 1,
      type: 'config/area_registry/list'
    }));
  } else if (data.type === 'result') {
    console.log('Areas:', data.result);
  }
};
```

### Test REST API Fallback

```powershell
# Test REST API endpoint
$haUrl = "http://localhost:8123"
$token = "YOUR_TOKEN"

try {
    $response = Invoke-RestMethod -Uri "$haUrl/api/config/area_registry/list" -Headers @{Authorization="Bearer $token"}
    Write-Host "REST API Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "REST API Failed (expected if endpoint not available):" -ForegroundColor Yellow
    Write-Host $_.Exception.Message
}
```

## Performance Verification

After implementation, verify:

1. **Response Time:**
   - WebSocket API: ~50-100ms
   - REST API fallback: ~100-200ms

2. **Cache Behavior:**
   - Areas cached for 10 minutes
   - Subsequent requests use cache

3. **Error Handling:**
   - WebSocket failures gracefully fall back
   - No service crashes on API failures

## Next Steps After Verification

1. ✅ **Monitor Logs:** Watch for WebSocket vs REST API usage
2. ✅ **Check Context:** Verify areas appear in AI agent context
3. ✅ **Test AI Agent:** Try asking about areas in the chat interface
4. ✅ **Performance:** Monitor response times and cache hits

## Support

If issues persist:
1. Check `implementation/analysis/AREA_REGISTRY_API_RESEARCH_2025.md` for research details
2. Review `implementation/AREA_REGISTRY_WEBSOCKET_IMPLEMENTATION.md` for implementation details
3. Check Home Assistant logs for API errors
4. Verify Home Assistant version supports WebSocket API

