# Zigbee2MQTT Device Capture - Next Steps Action Plan

**Date:** January 16, 2026  
**Status:** Action Plan Ready  
**Issue:** Zigbee2MQTT devices not being captured

## Quick Summary

After reviewing the codebase and documentation:
- ✅ **Integration field fix exists** in code (websocket-ingestion)
- ❓ **Need to verify:** Do Zigbee2MQTT devices exist in Home Assistant?
- ❓ **Need to verify:** Is integration field fix working?
- ❓ **Need to verify:** When was last device discovery?

## Immediate Diagnostic Steps

### Step 1: Verify Zigbee2MQTT Devices Exist in Home Assistant ⚠️ CRITICAL

**Question:** Are there any Zigbee2MQTT devices in Home Assistant?

**Actions:**

1. **Check Zigbee2MQTT Add-on Status:**
   - Navigate to Home Assistant → Settings → Add-ons
   - Verify Zigbee2MQTT add-on is installed and running
   - Check Zigbee2MQTT logs for errors

2. **Check Zigbee2MQTT UI:**
   - Open Zigbee2MQTT web UI (usually via Home Assistant ingress)
   - Go to Devices page
   - Verify devices are paired and online

3. **Query Home Assistant Device Registry:**

```powershell
# Query HA device registry
$haUrl = "http://192.168.1.86:8123"
$haToken = $env:HA_TOKEN
$headers = @{Authorization="Bearer $haToken"}

try {
    $devices = Invoke-RestMethod -Uri "$haUrl/api/config/device_registry/list" -Headers $headers
    
    Write-Host "Total devices in HA: $($devices.Count)" -ForegroundColor Green
    
    # Check for devices with potential Zigbee identifiers
    $potentialZigbee = $devices | Where-Object {
        $identifiers = $_.identifiers | ForEach-Object { $_ -join ',' }
        $identifiers -match 'zigbee|ieee|mqtt' -or
        $_.name -match 'Office|Bar|Light|Sensor|Switch'
    }
    
    Write-Host "Potential Zigbee devices: $($potentialZigbee.Count)" -ForegroundColor Yellow
    $potentialZigbee | Select-Object name, identifiers | Format-Table
    
} catch {
    Write-Host "Error querying HA: $_" -ForegroundColor Red
}
```

**Expected Outcome:**
- If Zigbee devices exist → Continue to Step 2
- If no Zigbee devices → Install/configure Zigbee2MQTT and pair devices first

---

### Step 2: Check websocket-ingestion Logs for Integration Resolution

**Question:** Is the integration field fix working?

**Actions:**

```powershell
# Check logs for integration resolution
docker compose logs websocket-ingestion --tail 500 | Select-String -Pattern "integration|config_entry|Built config entry mapping|Resolved integration"

# Check last discovery time
docker compose logs websocket-ingestion --tail 200 | Select-String -Pattern "DISCOVERY|Starting.*discovery|Built config entry mapping"
```

**What to Look For:**
- ✅ `🔧 Built config entry mapping: X entries` - Config entries discovered
- ✅ `Resolved integration 'zigbee2mqtt' for device [name]` - Integration resolved
- ❌ No integration resolution messages → Fix may not be working
- ❌ Error messages → Check error details

**Expected Outcome:**
- If messages show integration resolution → Continue to Step 3
- If no messages → Fix may not be working or discovery hasn't run since fix

---

### Step 3: Verify Database State

**Question:** What is the current state of the integration field in the database?

**Actions:**

```powershell
# Query data-api for devices
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=200"
    
    Write-Host "Total devices in database: $($response.devices.Count)" -ForegroundColor Green
    
    # Check integration field distribution
    $integrationGroups = $response.devices | Group-Object integration
    Write-Host "`nIntegration Distribution:" -ForegroundColor Yellow
    $integrationGroups | ForEach-Object {
        $integrationName = if ($_.Name) { $_.Name } else { "[NULL]" }
        Write-Host "  $integrationName : $($_.Count) devices"
    }
    
    # Check for Zigbee devices
    $zigbeeDevices = $response.devices | Where-Object { 
        $_.integration -eq 'zigbee2mqtt' -or 
        $_.integration -eq 'mqtt' -or
        ($_.integration -and $_.integration -match 'zigbee')
    }
    
    Write-Host "`nZigbee devices found: $($zigbeeDevices.Count)" -ForegroundColor $(if ($zigbeeDevices.Count -gt 0) { "Green" } else { "Red" })
    
    if ($zigbeeDevices.Count -gt 0) {
        $zigbeeDevices | Select-Object device_id, name, integration | Format-Table
    }
    
} catch {
    Write-Host "Error querying data-api: $_" -ForegroundColor Red
}
```

**Expected Outcome:**
- If devices have `integration=null` → Need rediscovery (Step 4)
- If devices have `integration='zigbee2mqtt'` → Success! Check dashboard (Step 5)
- If no Zigbee devices → Verify Step 1 (devices exist in HA)

---

### Step 4: Trigger Device Rediscovery (If Needed)

**Question:** If devices exist in HA but integration field is null, trigger rediscovery

**Actions:**

```powershell
# Restart websocket-ingestion to trigger discovery
Write-Host "Restarting websocket-ingestion service..." -ForegroundColor Yellow
docker compose restart websocket-ingestion

# Wait a moment for service to start
Start-Sleep -Seconds 5

# Monitor logs for discovery process
Write-Host "`nMonitoring logs for discovery..." -ForegroundColor Yellow
docker compose logs websocket-ingestion --tail 100 --follow
```

**What to Look For:**
- ✅ `🚀 STARTING COMPLETE HOME ASSISTANT DISCOVERY`
- ✅ `🔧 Built config entry mapping: X entries`
- ✅ `Resolved integration 'zigbee2mqtt' for device [name]`
- ✅ `💾 Storing discovered data to SQLite via data-api...`

**Wait for:**
- Discovery to complete (usually 10-30 seconds)
- Log messages to stop appearing
- Then verify database again (Step 3)

---

### Step 5: Verify Dashboard

**Question:** Do Zigbee devices appear in the dashboard?

**Actions:**

1. **Check Dashboard Device Count:**
   - Open HomeIQ Dashboard → Devices
   - Check total device count
   - Check integration filter dropdown

2. **Filter by Integration:**
   - Select integration filter
   - Look for 'zigbee2mqtt' option
   - Apply filter and verify devices appear

3. **Check Device Details:**
   - Click on a device
   - Verify integration field is populated
   - Check device metadata

**Expected Outcome:**
- ✅ Zigbee devices appear with integration='zigbee2mqtt'
- ✅ Integration filter shows 'zigbee2mqtt' option
- ✅ Device details show correct integration

---

## Decision Tree

```
Start
  │
  ├─ Step 1: Check if Zigbee devices exist in HA
  │    │
  │    ├─ YES → Step 2: Check logs
  │    │          │
  │    │          ├─ Integration resolved? → Step 3: Check database
  │    │          │                           │
  │    │          │                           ├─ Integration populated? → Step 5: Verify dashboard ✅
  │    │          │                           │
  │    │          │                           └─ Integration NULL? → Step 4: Trigger rediscovery
  │    │          │                                                            │
  │    │          │                                                            └─ Step 3: Check database again
  │    │          │
  │    │          └─ Not resolved? → Debug logs, check config entries discovery
  │    │
  │    └─ NO → Install/configure Zigbee2MQTT, pair devices, then restart
  │
  └─ END
```

## Troubleshooting

### Issue: No Integration Resolution Messages in Logs

**Possible Causes:**
1. Config entries discovery not working
2. WebSocket connection not established
3. Fix code not in deployed version

**Actions:**
```powershell
# Check if config entries discovery is being called
docker compose logs websocket-ingestion --tail 500 | Select-String -Pattern "config_entry|discover_config_entries"

# Verify code fix is in deployed version
docker compose exec websocket-ingestion grep -A 10 "Built config entry mapping" /app/src/discovery_service.py
```

### Issue: Devices Have Integration=NULL After Rediscovery

**Possible Causes:**
1. Devices don't have config_entries
2. Config entry mapping not built correctly
3. Integration resolution logic not executing

**Actions:**
```powershell
# Check HA device registry for config_entries
$haUrl = "http://192.168.1.86:8123"
$haToken = $env:HA_TOKEN
$headers = @{Authorization="Bearer $haToken"}

$devices = Invoke-RestMethod -Uri "$haUrl/api/config/device_registry/list" -Headers $headers
$devices | Select-Object name, config_entries | Where-Object { $_.config_entries } | Format-Table
```

### Issue: Zigbee Devices Exist in HA But Not in Dashboard

**Possible Causes:**
1. Integration field not populated in database
2. Dashboard query filter issue
3. Devices not stored in database

**Actions:**
```powershell
# Check database directly
$response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?integration=zigbee2mqtt"
Write-Host "Zigbee devices in database: $($response.devices.Count)"

# Check dashboard API
$dashboardResponse = Invoke-RestMethod -Uri "http://localhost:3000/api/devices?integration=zigbee2mqtt"
Write-Host "Zigbee devices from dashboard API: $($dashboardResponse.devices.Count)"
```

## Success Criteria

✅ **Success Indicators:**
- Zigbee devices exist in Home Assistant device registry
- websocket-ingestion logs show integration resolution
- Database shows devices with `integration='zigbee2mqtt'`
- Dashboard displays Zigbee devices
- Integration filter shows 'zigbee2mqtt' option
- Device details show correct integration

## Next Actions After Diagnosis

### If Zigbee Devices Don't Exist in HA:
1. Install Zigbee2MQTT add-on
2. Configure MQTT connection
3. Pair Zigbee devices
4. Wait for device discovery
5. Verify devices appear

### If Integration Field Not Working:
1. Review logs for errors
2. Check config entries discovery
3. Verify WebSocket connection
4. Check code fix is deployed
5. Debug integration resolution logic

### If Everything Works:
1. ✅ Verify dashboard shows Zigbee devices
2. ✅ Test integration filter
3. ✅ Check device details
4. ✅ Document success
5. ✅ Close issue

## References

- **Review Document:** `implementation/analysis/ZIGBEE2MQTT_CURRENT_STATE_REVIEW.md`
- **Fix Documentation:** `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md`
- **Code Location:** `services/websocket-ingestion/src/discovery_service.py:667-690`
