# SLZB-06P7 Zigbee Coordinator Setup Configuration

## Coordinator Information
- **Model**: SLZB-06P7
- **Type**: Zigbee Coordinator
- **Connection**: USB Serial

## Setup Status

✅ **Prerequisites Checked**: MQTT is connected and healthy  
✅ **Configuration Generated**: Ready for Zigbee2MQTT addon  
⏳ **Addon Installation**: Need to verify/install  
⏳ **Coordinator Connection**: Need to identify USB port  

## Configuration for Zigbee2MQTT

### Step 1: Install Zigbee2MQTT Addon

1. Go to **Home Assistant** → **Supervisor** → **Add-on Store**
2. Search for **"Zigbee2MQTT"**
3. Click **Install**
4. Wait for installation to complete
5. **Don't start yet** - configure first

### Step 2: Find Your SLZB-06P7 USB Port

The SLZB-06P7 coordinator needs to be connected via USB. To find the correct port:

**Option A: Via Home Assistant UI**
1. Go to **Supervisor** → **System** → **Hardware**
2. Look for your SLZB-06P7 device
3. Note the device path (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, or `/dev/serial/by-id/...`)

**Option B: Via SSH/Terminal**
```bash
# List USB devices
lsusb | grep -i zigbee

# List serial devices
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

# Or check by ID (more reliable)
ls -la /dev/serial/by-id/
```

Common ports for SLZB-06P7:
- `/dev/ttyUSB0` (most common)
- `/dev/ttyACM0` (some systems)
- `/dev/serial/by-id/usb-...` (most reliable, use this if available)

### Step 3: Get MQTT Broker Details

The system will automatically detect your MQTT broker from the integration. Typical values:
- **Broker**: `localhost` or `192.168.1.86` (your HA IP)
- **Port**: `1883` (standard MQTT port)
- **Username/Password**: Usually not required for local broker

### Step 4: Configure Zigbee2MQTT Addon

Once you have the USB port, use this configuration:

```yaml
data_path: /config/zigbee2mqtt
homeassistant: true
permit_join: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost:1883  # Update if your broker is different
serial:
  port: /dev/ttyUSB0  # UPDATE THIS with your actual port from Step 2
advanced:
  log_level: info
  log_output:
    - console
    - file
```

**Important**: Replace `/dev/ttyUSB0` with the actual port you found in Step 2!

### Step 5: Start and Verify

1. **Save** the configuration in the Zigbee2MQTT addon
2. **Start** the addon
3. **Check logs** for any errors
4. Look for: `Zigbee: Coordinator ready` or similar success message

### Step 6: Verify Connection

After starting, check:
1. Go to **Zigbee2MQTT** addon → **Open Web UI**
2. You should see the coordinator status
3. Check **Home Assistant** → **Settings** → **Devices & Services**
4. Look for **Zigbee2MQTT** integration (should auto-discover)

## Troubleshooting

### Coordinator Not Found
- Check USB connection
- Verify port in Supervisor → System → Hardware
- Try different port (ttyUSB0, ttyUSB1, ttyACM0)
- Check addon logs for port errors

### MQTT Connection Failed
- Verify MQTT broker is running
- Check broker address (localhost vs IP)
- Verify port 1883 is accessible
- Check MQTT integration in HA is working

### Permission Denied
- Addon may need USB device permissions
- Check Supervisor → System → Hardware → USB devices
- Ensure SLZB-06P7 is passed through to addon

## Next Steps After Setup

1. **Pair Devices**: Enable permit_join and pair your Zigbee devices
2. **Network Optimization**: Configure channel and network settings
3. **Device Management**: Use Zigbee2MQTT web UI to manage devices

## Wizard Status

Setup wizard ID: `zigbee_setup_20251116_151336`

To continue automated setup:
```bash
# Check status
curl http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151336/status

# Continue after manual steps
curl -X POST http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151336/continue
```

## Questions?

1. **Is Zigbee2MQTT addon installed?** (Check in Supervisor)
2. **What USB port is your SLZB-06P7 using?** (Check in Supervisor → System → Hardware)
3. **Is your MQTT broker on localhost or a different IP?** (Usually localhost:1883)

Once you have these, I can help complete the configuration!

