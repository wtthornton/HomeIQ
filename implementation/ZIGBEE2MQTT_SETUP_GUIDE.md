# Zigbee2MQTT Setup Guide

## Current Status

✅ **MQTT Integration**: Connected and healthy  
❌ **Zigbee2MQTT**: Not configured

## What We Have

- ✅ Home Assistant URL: `http://192.168.1.86:8123`
- ✅ HA Token: Configured in `.env.websocket`
- ✅ MQTT Broker: Connected and working
- ✅ Setup Wizard API: Available at `http://localhost:8027`

## What We Need

### 1. Zigbee Coordinator Hardware
You need a Zigbee coordinator USB stick. Common options:
- **CC2531** (cheap, popular)
- **CC2652** (better range, more features)
- **Sonoff Zigbee 3.0 USB Dongle** (recommended)
- **ConBee II / RaspBee II** (deCONZ)

**Question**: Do you have a Zigbee coordinator USB stick? If yes, what model?

### 2. Zigbee2MQTT Addon Installation

The addon needs to be installed in Home Assistant. We can check if it's installed via the Supervisor API.

**Steps to install (if not installed):**
1. Go to Home Assistant → **Supervisor** → **Add-on Store**
2. Search for **"Zigbee2MQTT"**
3. Click **Install**
4. Wait for installation to complete
5. **Don't start it yet** - we need to configure it first

### 3. MQTT Broker Configuration

We need to know:
- MQTT broker hostname/IP (likely `localhost` or `192.168.1.86`)
- MQTT broker port (typically `1883`)
- MQTT username/password (if required)

**Current Status**: MQTT is connected, but we need the exact broker details for Zigbee2MQTT configuration.

### 4. Coordinator USB Port

We need to identify which USB port the coordinator is connected to:
- Typically `/dev/ttyUSB0` on Linux
- Or `/dev/ttyACM0` for some coordinators
- Can be checked via `lsusb` or `dmesg` commands

## Automated Setup Steps

The setup wizard has been started and can help guide the process. Here's what we can automate:

### Step 1: Check Prerequisites ✅
- ✅ HA Authentication: Working
- ✅ MQTT Integration: Connected
- ⏳ Zigbee2MQTT Addon: Need to check installation

### Step 2: Install Addon (if needed)
We can check if the addon is installed via:
```
GET http://192.168.1.86:8123/api/hassio/addon/zigbee2mqtt/info
```

If not installed, we can provide installation instructions.

### Step 3: Configure Addon
Once installed, we need to configure:
- MQTT broker connection details
- Coordinator USB port
- Network settings (optional)

### Step 4: Start Addon
After configuration, start the addon and verify coordinator connection.

## Next Steps

**To proceed, I need:**

1. **Do you have a Zigbee coordinator USB stick?**
   - If yes: What model? (CC2531, CC2652, Sonoff, etc.)
   - If no: You'll need to purchase one first

2. **Is Zigbee2MQTT addon installed in Home Assistant?**
   - Check: Home Assistant → Supervisor → Add-on Store
   - Look for "Zigbee2MQTT" in installed addons

3. **MQTT Broker Details:**
   - Hostname/IP: (likely `localhost` or `192.168.1.86`)
   - Port: (likely `1883`)
   - Username/Password: (if required)

4. **Coordinator USB Port:**
   - Once connected, we can help identify the port

## Setup Wizard Status

The setup wizard has been started with ID: `zigbee_setup_20251116_151052`

**Completed Steps:**
- ✅ Prerequisites check
- ✅ MQTT configuration check
- ✅ Addon installation check
- ✅ Addon configuration prepared
- ✅ Coordinator setup guidance
- ✅ Device pairing guidance
- ✅ Network optimization guidance

**Failed:**
- ❌ Validation (expected - addon not installed yet)

## Commands to Continue Setup

Once you have the coordinator and addon installed:

```bash
# Check wizard status
curl http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151052/status

# Continue wizard (after manual steps)
curl -X POST http://localhost:8027/api/zigbee2mqtt/setup/zigbee_setup_20251116_151052/continue
```

## Manual Configuration Template

Once the addon is installed, here's the configuration template:

```yaml
data_path: /config/zigbee2mqtt
homeassistant: true
permit_join: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost:1883  # Update with your broker details
serial:
  port: /dev/ttyUSB0  # Update with your coordinator port
advanced:
  log_level: info
  log_output:
    - console
    - file
```

## Questions for You

1. **Do you have a Zigbee coordinator USB stick?** (Yes/No, and model if yes)
2. **Is Zigbee2MQTT addon installed?** (Check in HA Supervisor)
3. **What's your MQTT broker address?** (localhost, IP, or hostname)
4. **Do you have Zigbee devices ready to pair?** (sensors, lights, switches, etc.)

Once I have these answers, I can help complete the automated setup!

