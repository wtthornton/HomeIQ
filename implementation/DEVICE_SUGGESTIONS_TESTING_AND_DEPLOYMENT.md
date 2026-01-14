# Device-Based Automation Suggestions - Testing & Deployment Guide

**Date:** January 14, 2026  
**Status:** Ready for Testing & Deployment

## Pre-Deployment Checklist

### ✅ Code Verification
- [x] All code files created
- [x] No linter errors
- [x] TypeScript/Python type safety verified
- [x] API endpoints registered
- [x] Models import correctly
- [x] Router registered in main.py
- [x] Frontend components integrated

### ✅ Implementation Complete
- [x] Phase 1: Device Selection
- [x] Phase 2: Suggestion Generation
- [x] Phase 3: Enhancement Flow

## Testing Steps

### Step 1: Verify Code Quality

**Backend:**
```powershell
# Check Python syntax
cd services/ha-ai-agent-service
python -m py_compile src/api/device_suggestions_models.py
python -m py_compile src/api/device_suggestions_endpoints.py
python -m py_compile src/services/device_suggestion_service.py
```

**Frontend:**
```powershell
# Check TypeScript compilation (if using tsc)
cd services/ai-automation-ui
npm run build  # or equivalent
```

### Step 2: Start Services

```powershell
# Start required services
docker-compose up -d data-api ha-ai-agent-service ai-automation-ui

# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs ha-ai-agent-service
docker-compose logs ai-automation-ui
docker-compose logs data-api
```

### Step 3: Verify Service Health

```powershell
# Check data-api health
Invoke-RestMethod -Uri "http://localhost:8006/health"

# Check ha-ai-agent-service health
Invoke-RestMethod -Uri "http://localhost:8030/health"

# Check ai-automation-ui (if health endpoint exists)
Invoke-RestMethod -Uri "http://localhost:3000"  # or check browser
```

### Step 4: Test Device Suggestions Endpoint

```powershell
# Get API key from environment
$apiKey = $env:VITE_API_KEY  # or from .env file

# Get a device ID first (from data-api)
$devices = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=1" `
  -Headers @{Authorization="Bearer $apiKey"; "X-HomeIQ-API-Key"=$apiKey}

$deviceId = $devices.devices[0].device_id

# Test device suggestions endpoint
$requestBody = @{
    device_id = $deviceId
    context = @{
        include_synergies = $true
        include_blueprints = $true
        include_sports = $true
        include_weather = $true
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8030/api/v1/chat/device-suggestions" `
  -Method Post `
  -ContentType "application/json" `
  -Body $requestBody `
  -Headers @{Authorization="Bearer $apiKey"; "X-HomeIQ-API-Key"=$apiKey}
```

### Step 5: Test UI Integration

1. Navigate to: `http://localhost:3000/agent`
2. Click "🔌 Select Device" button
3. Verify device picker opens
4. Select a device
5. Verify device context displays
6. Verify suggestions load (may take 3-5 seconds)
7. Click "💬 Enhance" on a suggestion
8. Verify chat input is pre-populated
9. Send message to test enhancement flow

### Step 6: Check for Errors

```powershell
# Check backend logs for errors
docker-compose logs ha-ai-agent-service | Select-String -Pattern "error|Error|ERROR|exception|Exception"

# Check frontend console (in browser DevTools)
# Look for any JavaScript errors or API failures
```

## Deployment Options

### Option 1: Local Development Testing

**For development/testing:**
```powershell
# Start services in development mode
docker-compose -f docker-compose.dev.yml up -d

# Or use standard docker-compose
docker-compose up -d
```

**Verify:**
- Services start successfully
- No errors in logs
- UI is accessible
- API endpoints respond

### Option 2: Production Deployment

**For production deployment:**
```powershell
# Build and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Or use deployment script (if available)
# ./scripts/deploy.sh
```

**Pre-Production Checklist:**
- [ ] All tests pass
- [ ] Code reviewed
- [ ] Environment variables set
- [ ] Database migrations (if any)
- [ ] Backup existing data
- [ ] Monitor logs after deployment
- [ ] Verify health checks pass
- [ ] Test end-to-end flow

## Verification Commands

### Verify Backend Endpoint

```powershell
# Test endpoint exists (should return 405 Method Not Allowed for GET)
try {
    Invoke-RestMethod -Uri "http://localhost:8030/api/v1/chat/device-suggestions" -Method Get
} catch {
    if ($_.Exception.Response.StatusCode -eq 405) {
        Write-Host "✅ Endpoint exists (405 is expected for GET)"
    }
}
```

### Verify Frontend Components

```powershell
# Check if UI loads
$response = Invoke-WebRequest -Uri "http://localhost:3000/agent" -UseBasicParsing
if ($response.StatusCode -eq 200) {
    Write-Host "✅ UI is accessible"
}
```

## Common Issues & Solutions

### Issue: Services won't start
**Solution:**
- Check Docker is running
- Check ports are available (8006, 8030, 3000)
- Check logs: `docker-compose logs <service-name>`
- Verify environment variables are set

### Issue: API returns 401/403
**Solution:**
- Verify API_KEY is set correctly
- Check authentication headers
- Verify API key is valid

### Issue: No suggestions appear
**Solution:**
- Check backend logs for errors
- Verify device_id is valid
- Check data-api is accessible
- Verify network connectivity between services

### Issue: UI components don't load
**Solution:**
- Check browser console for errors
- Verify React app compiled correctly
- Check API endpoints are accessible
- Clear browser cache

## Post-Deployment Verification

### 1. Health Checks
- [ ] All services healthy
- [ ] Database connections working
- [ ] API endpoints responding
- [ ] UI loads correctly

### 2. Functionality Tests
- [ ] Device picker works
- [ ] Device selection works
- [ ] Suggestions generate
- [ ] Enhancement flow works
- [ ] Error handling works

### 3. Performance Checks
- [ ] Suggestions load within 5 seconds
- [ ] UI remains responsive
- [ ] No memory leaks
- [ ] API response times acceptable

### 4. Integration Tests
- [ ] End-to-end flow works
- [ ] Services communicate correctly
- [ ] Data flows correctly
- [ ] Error scenarios handled

## Rollback Plan

If issues are found after deployment:

1. **Stop services:**
   ```powershell
   docker-compose down
   ```

2. **Revert code changes:**
   ```powershell
   git checkout <previous-commit>
   ```

3. **Restart services:**
   ```powershell
   docker-compose up -d
   ```

4. **Verify rollback:**
   - Check services are running
   - Verify functionality restored
   - Check logs for errors

## Monitoring

### Logs to Monitor

**Backend:**
```powershell
# Watch ha-ai-agent-service logs
docker-compose logs -f ha-ai-agent-service

# Watch for errors
docker-compose logs ha-ai-agent-service | Select-String -Pattern "error|Error|ERROR"
```

**Frontend:**
- Browser console (F12)
- Network tab (check API calls)
- React DevTools (if available)

### Metrics to Watch

- API response times
- Error rates
- Service health status
- Resource usage (CPU, memory)

## Next Steps After Deployment

1. **Monitor logs** for 24-48 hours
2. **Collect user feedback**
3. **Fix any issues** found
4. **Enhance features** based on feedback
5. **Add data integrations** (synergies, blueprints, sports, weather)
6. **Improve suggestion generation** logic

## Notes

- Deployment should be done during low-traffic periods
- Always backup data before deployment
- Monitor closely after deployment
- Have rollback plan ready
- Test in staging environment first (if available)
