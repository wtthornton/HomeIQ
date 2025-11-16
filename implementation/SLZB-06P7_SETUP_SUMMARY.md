# SLZB-06P7 Setup Summary

## ✅ Setup Wizard Status

**Wizard ID**: `zigbee_setup_20251116_151336`  
**Status**: In Progress  
**Progress**: 75% Complete

### Completed Steps:
1. ✅ **Prerequisites Check** - MQTT is connected and healthy
2. ✅ **MQTT Configuration** - Verified MQTT integration
3. ✅ **Addon Installation Check** - Checked for Zigbee2MQTT addon
4. ✅ **Addon Configuration** - Configuration template prepared
5. ✅ **Coordinator Setup** - SLZB-06P7 coordinator identified
6. ✅ **Device Pairing** - Pairing instructions provided

### Remaining Steps:
- ⏳ Network Optimization
- ⏳ Final Validation

## 📋 What You Need to Do

### 1. Install Zigbee2MQTT Addon (if not installed)

**Check if installed:**
- Go to **Home Assistant** → **Supervisor** → **Add-on Store**
- Look for "Zigbee2MQTT" in your installed addons

**If not installed:**
1. Go to **Supervisor** → **Add-on Store**
2. Search for **"Zigbee2MQTT"**
3. Click **Install**
4. Wait for installation (may take a few minutes)

### 2. Find Your SLZB-06P7 USB Port

**Method 1: Via Home Assistant UI (Easiest)**
1. Go to **Supervisor** → **System** → **Hardware**
2. Look for your SLZB-06P7 device
3. Note the device path shown (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`)

**Method 2: Via SSH/Terminal**
```bash
# List serial devices
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

# Or check by ID (most reliable)
ls -la /dev/serial/by-id/ | grep -i slzb
```

**Common ports for SLZB-06P7:**
- `/dev/ttyUSB0` (most common)
- `/dev/ttyACM0` (some systems)
- `/dev/serial/by-id/usb-...` (most reliable - use this if available)

### 3. Configure Zigbee2MQTT Addon

1. Go to **Supervisor** → **Zigbee2MQTT** addon → **Configuration**
2. Use this configuration template:

```yaml
data_path: /config/zigbee2mqtt
homeassistant: true
permit_join: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost:1883
serial:
  port: /dev/ttyUSB0  # ⚠️ REPLACE THIS with your actual port from Step 2!
advanced:
  log_level: info
  log_output:
    - console
    - file
```

**Important Notes:**
- Replace `/dev/ttyUSB0` with the actual port you found in Step 2
- If your MQTT broker is not on localhost, update the `server` line
- The configuration will be automatically updated with correct MQTT broker details once the addon is installed

### 4. Start the Addon

1. **Save** the configuration
2. Click **Start** on the Zigbee2MQTT addon
3. **Check Logs** tab for any errors
4. Look for: `Zigbee: Coordinator ready` or similar success message

### 5. Verify Connection

**Check in Home Assistant:**
1. Go to **Settings** → **Devices & Services**
2. Look for **Zigbee2MQTT** integration (should auto-discover)
3. You should see the coordinator status

**Check in Zigbee2MQTT Web UI:**
1. Click **Open Web UI** on the Zigbee2MQTT addon
2. You should see the coordinator information
3. Status should show "Coordinator ready"

## 🔧 Troubleshooting

### Coordinator Not Found
- ✅ Check USB connection is secure
- ✅ Verify port in Supervisor → System → Hardware
- ✅ Try different port (ttyUSB0, ttyUSB1, ttyACM0)
- ✅ Check addon logs for port errors
- ✅ Ensure SLZB-06P7 is powered (if it has external power)

### MQTT Connection Failed
- ✅ Verify MQTT broker is running
- ✅ Check broker address (try `mqtt://192.168.1.86:1883` if localhost doesn't work)
- ✅ Verify port 1883 is accessible
- ✅ Check MQTT integration in HA is working

### Permission Denied
- ✅ Addon may need USB device permissions
- ✅ Check Supervisor → System → Hardware → USB devices
- ✅ Ensure SLZB-06P7 is passed through to addon
- ✅ Try using `/dev/serial/by-id/...` path instead

## 📊 Current System Status

- ✅ **MQTT Integration**: Connected and healthy
- ✅ **HA Authentication**: Working
- ✅ **Setup Wizard**: 75% complete
- ⏳ **Zigbee2MQTT Addon**: Need to verify installation
- ⏳ **Coordinator Connection**: Need USB port identification

## 🚀 Next Steps

1. **Install/Verify Zigbee2MQTT addon** (if not installed)
2. **Find SLZB-06P7 USB port** (via Supervisor → System → Hardware)
3. **Configure addon** with the template above (update port!)
4. **Start addon** and verify connection
5. **Continue wizard** to complete setup:
   ```bash
   curl -X POST http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151336/continue
   ```

## 📝 Questions to Answer

To complete the setup, I need:

1. **Is Zigbee2MQTT addon installed?** 
   - Check: Supervisor → Add-on Store → Installed addons

2. **What USB port is your SLZB-06P7 using?**
   - Check: Supervisor → System → Hardware
   - Or run: `ls -la /dev/ttyUSB* /dev/ttyACM*`

3. **Is your MQTT broker on localhost or a different IP?**
   - Usually `localhost:1883` or `192.168.1.86:1883`

Once you have these, I can help you complete the configuration and verify everything is working!

## 📚 Additional Resources

- [Zigbee2MQTT Documentation](https://www.zigbee2mqtt.io/)
- [SLZB-06P7 Product Info](https://slzb.com/)
- Setup Wizard API: `http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151336/status`

