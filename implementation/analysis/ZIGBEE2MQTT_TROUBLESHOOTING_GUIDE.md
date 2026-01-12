# Zigbee2MQTT Troubleshooting Guide

**Date:** 2026-01-12  
**Issue:** Home Assistant and Zigbee2MQTT are working, but device-intelligence-service is not receiving device information via API

## Quick Diagnostic Results

**Current Status:**
- ✅ MQTT Connected: `true`
- ✅ HA Connected: `true`
- ✅ Devices Discovered: 108 devices
- ⚠️ Zigbee/MQTT Devices Found: 7 devices (but may be missing Zigbee2MQTT-specific data like LQI, battery, etc.)

## The Problem

The service is identifying devices from Home Assistant, but it's **not receiving Zigbee2MQTT-specific data** (LQI, battery levels, availability, etc.) via MQTT. This means:

1. ✅ Devices exist in Home Assistant (identified as `mqtt` integration)
2. ✅ Service identifies them as Zigbee devices (7 found)
3. ❌ Service is NOT receiving MQTT messages from Zigbee2MQTT bridge
4. ❌ Devices missing Zigbee2MQTT metadata (LQI, battery, availability_status)

## Troubleshooting Steps

### Step 1: Verify MQTT Messages Are Being Received (CRITICAL)

**Check service logs for MQTT message reception:**
```powershell
# Check if service is receiving MQTT messages from Zigbee2MQTT
docker logs homeiq-device-intelligence --tail 500 | Select-String -Pattern "📱.*Zigbee2MQTT devices updated|📨.*bridge/devices"

# Check for subscription confirmations
docker logs homeiq-device-intelligence | Select-String -Pattern "📡 Subscribed to zigbee2mqtt/bridge/devices"

# Check for any MQTT messages received
docker logs homeiq-device-intelligence --tail 1000 | Select-String -Pattern "📨 MQTT message received.*bridge"
```

**Expected Output:**
```
📡 Subscribed to zigbee2mqtt/bridge/devices
📨 MQTT message received: topic=zigbee2mqtt/bridge/devices, payload_size=...
📱 Zigbee2MQTT devices updated: 6 devices
```

**If Missing:** Service is NOT receiving MQTT messages (go to Step 2)

---

### Step 2: Test MQTT Topics Manually (CRITICAL)

**Verify Zigbee2MQTT is publishing to expected topics:**

```powershell
# Option 1: Use mosquitto client (if installed)
# Install: choco install mosquitto

# Test 1: Check if bridge/devices topic has retained message
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v -C 1

# Test 2: Request device list and watch response
# Terminal 1: Subscribe to response topic
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/response/device/list" -v

# Terminal 2: Request device list
mosquitto_pub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/request/device/list" -m "{}"
```

**Expected:** Should see JSON array with 6 devices

**If no messages:**
1. Check if MQTT authentication required (add `-u addons -P <password>`)
2. Verify Zigbee2MQTT base topic matches
3. Check Zigbee2MQTT logs for MQTT publish activity

---

### Step 3: Check MQTT Authentication (IF Step 2 Fails)

**If mosquitto_sub fails with "Not authorized" or connection error:**

```powershell
# Check if credentials are needed
# Get MQTT password from Home Assistant → Add-ons → Mosquitto broker → Configuration

# Test with authentication
mosquitto_sub -h 192.168.1.86 -p 1883 -u addons -P <password> -t "zigbee2mqtt/bridge/devices" -v -C 1

# If works, add to .env file:
# MQTT_USERNAME=addons
# MQTT_PASSWORD=<password>
# Then restart service: docker compose restart device-intelligence-service
```

---

### Step 4: Verify Service Configuration

**Check service environment variables:**
```powershell
# Check current MQTT configuration
docker exec homeiq-device-intelligence env | Select-String -Pattern "MQTT|ZIGBEE"

# Expected:
# MQTT_BROKER=mqtt://192.168.1.86:1883
# ZIGBEE2MQTT_BASE_TOPIC=zigbee2mqtt
# MQTT_USERNAME=<should be set if auth required>
# MQTT_PASSWORD=<should be set if auth required>
```

**If MQTT_USERNAME/PASSWORD are empty but broker requires auth:**
1. Add credentials to `.env` file
2. Restart service: `docker compose restart device-intelligence-service`

---

### Step 5: Check What Data Devices Have

**Verify if devices are missing Zigbee2MQTT-specific fields:**
```powershell
$devices = Invoke-RestMethod -Uri "http://localhost:8028/api/devices?limit=200"
$zigbee = $devices.devices | Where-Object { 
    $_.source -eq 'zigbee2mqtt' -or 
    $_.integration -eq 'mqtt' 
}

Write-Host "Zigbee Devices Found: $($zigbee.Count)"
Write-Host "Devices with source='zigbee2mqtt': $(($zigbee | Where-Object { $_.source -eq 'zigbee2mqtt' }).Count)"
Write-Host "Devices with LQI: $(($zigbee | Where-Object { $_.lqi -ne $null }).Count)"
Write-Host "Devices with battery: $(($zigbee | Where-Object { $_.battery_level -ne $null }).Count)"
Write-Host "Devices with availability: $(($zigbee | Where-Object { $_.availability_status -ne $null }).Count)"

# Show device details
$zigbee | Select-Object name, integration, source, lqi, battery_level, availability_status | Format-Table
```

**If all fields are null/empty:** Service is NOT receiving MQTT data (go back to Step 1-2)

---

### Step 6: Check Zigbee2MQTT Logs

**Verify Zigbee2MQTT is publishing MQTT messages:**

1. Open Home Assistant → Add-ons → Zigbee2MQTT → Logs
2. Filter for "MQTT" or "publish" or "bridge/devices"
3. Look for publish activity to `zigbee2mqtt/bridge/devices`

**Expected:** Should see periodic publishes to bridge topics

**If no publishes:** Zigbee2MQTT might not be publishing device lists (check Zigbee2MQTT configuration)

---

### Step 7: Verify Device Identification Logic

**Check what integration field Zigbee devices have in HA:**
```powershell
# Get HA token
$haToken = $env:HOME_ASSISTANT_TOKEN
$haUrl = "http://192.168.1.86:8123"
$headers = @{ "Authorization" = "Bearer $haToken" }

# Get devices from HA
$haDevices = Invoke-RestMethod -Uri "$haUrl/api/config/device_registry/list" -Headers $headers

# Find Zigbee devices (by identifier patterns)
$zigbeeHA = $haDevices | Where-Object {
    ($_.identifiers | ConvertTo-Json) -match "0x[0-9a-f]{16}" -or
    ($_.identifiers | ConvertTo-Json) -match "zigbee"
}

Write-Host "Zigbee devices in HA: $($zigbeeHA.Count)"
$zigbeeHA | Select-Object name, identifiers, via_device_id | Format-Table -AutoSize
```

**Check integration:** Service looks for `integration` containing 'zigbee', 'zigbee2mqtt', or 'mqtt'

---

## Common Issues & Quick Fixes

### Issue 1: Service Not Receiving MQTT Messages

**Symptoms:**
- Logs show no "📱 Zigbee2MQTT devices updated" messages
- Manual mosquitto_sub shows messages exist
- Devices have no LQI/battery data

**Fix:**
1. Check MQTT authentication (add credentials if needed)
2. Verify service is subscribed to topics (check logs for "📡 Subscribed")
3. Restart service after config changes
4. Check network connectivity between service and MQTT broker

---

### Issue 2: MQTT Authentication Required

**Symptoms:**
- Manual mosquitto_sub fails without credentials
- Service shows connected but no messages received

**Fix:**
1. Get MQTT password from HA Mosquitto addon
2. Add to `.env` file:
   ```
   MQTT_USERNAME=addons
   MQTT_PASSWORD=<password>
   ```
3. Restart service: `docker compose restart device-intelligence-service`

---

### Issue 3: Topics Not Being Published

**Symptoms:**
- Manual mosquitto_sub shows no messages
- Zigbee2MQTT logs show no publish activity to bridge/devices

**Fix:**
1. Check Zigbee2MQTT is running and connected to MQTT broker
2. Verify base topic matches (`zigbee2mqtt`)
3. Try requesting device list: `mosquitto_pub -t "zigbee2mqtt/bridge/request/device/list" -m "{}"`
4. Check Zigbee2MQTT configuration for MQTT settings

---

### Issue 4: Devices Identified but Missing Metadata

**Symptoms:**
- Devices found with `integration='mqtt'`
- `source` field set to `'zigbee2mqtt'`
- But LQI, battery, availability_status are all null

**Fix:**
- This confirms MQTT messages aren't being received
- Follow Steps 1-3 to fix MQTT connection/messaging

---

## Diagnostic Script

**Run this to get full diagnostic info:**
```powershell
Write-Host "=== Zigbee2MQTT Diagnostic ==="

# 1. Service Status
Write-Host "`n1. Service Status:"
$status = Invoke-RestMethod -Uri "http://localhost:8028/api/discovery/status"
$status | ConvertTo-Json -Depth 3

# 2. Device Analysis
Write-Host "`n2. Device Analysis:"
$devices = Invoke-RestMethod -Uri "http://localhost:8028/api/devices?limit=200"
$zigbee = $devices.devices | Where-Object { 
    $_.source -eq 'zigbee2mqtt' -or 
    $_.integration -eq 'mqtt' -or
    $_.integration -like '*zigbee*'
}

Write-Host "   Total Devices: $($devices.count)"
Write-Host "   Zigbee/MQTT Devices: $($zigbee.Count)"
Write-Host "   With source='zigbee2mqtt': $(($zigbee | Where-Object { $_.source -eq 'zigbee2mqtt' }).Count)"
Write-Host "   With LQI data: $(($zigbee | Where-Object { $_.lqi -ne $null }).Count)"
Write-Host "   With battery data: $(($zigbee | Where-Object { $_.battery_level -ne $null }).Count)"

# 3. Service Logs Check
Write-Host "`n3. Checking Service Logs (last 50 lines for MQTT/Zigbee):"
docker logs homeiq-device-intelligence --tail 200 | Select-String -Pattern "MQTT|zigbee|📡|📨|📱" | Select-Object -Last 10

# 4. Configuration Check
Write-Host "`n4. Service Configuration:"
docker exec homeiq-device-intelligence env | Select-String -Pattern "MQTT|ZIGBEE"
```

---

## Expected End State

After troubleshooting, you should see:

✅ **Service Logs:**
```
📡 Subscribed to zigbee2mqtt/bridge/devices
📨 MQTT message received: topic=zigbee2mqtt/bridge/devices
📱 Zigbee2MQTT devices updated: 6 devices
```

✅ **API Response:**
- Devices with `source='zigbee2mqtt'`
- Devices with `lqi` values (0-255)
- Devices with `battery_level` values (0-100)
- Devices with `availability_status` values

✅ **Device Count:**
- 6 devices from Zigbee2MQTT bridge
- All with Zigbee2MQTT metadata populated

---

## Files to Check

- Service Logs: `docker logs homeiq-device-intelligence`
- Service Config: `services/device-intelligence-service/src/config.py`
- MQTT Client: `services/device-intelligence-service/src/clients/mqtt_client.py`
- Discovery Service: `services/device-intelligence-service/src/core/discovery_service.py`
- Environment: `.env` file (MQTT credentials)
- Docker Compose: `docker-compose.yml` (device-intelligence-service section)

---

## Next Steps

1. **Run Step 1** - Check service logs for MQTT messages
2. **Run Step 2** - Test MQTT topics manually
3. **If Step 2 fails** - Add MQTT authentication (Step 3)
4. **Run Step 5** - Verify what data devices currently have
5. **Compare results** - Determine if issue is MQTT messaging or device identification

The most likely issue is that **MQTT messages aren't being received**, even though the connection shows as "connected". This is typically due to:
- Missing MQTT authentication credentials
- Service not properly subscribed to topics
- Network/firewall issues
- Zigbee2MQTT not publishing to expected topics
