# MQTT Setup Guide - AI Automation Service

**Important:** This project uses the **existing MQTT broker on your Home Assistant server**. You do NOT need to deploy a new Mosquitto container.

---

## Prerequisites

Your Home Assistant server must have MQTT integration installed and configured.

### Check MQTT is Running on HA

1. Open Home Assistant UI
2. Go to **Settings** → **Devices & Services**
3. Look for **MQTT** integration
4. If not found, add MQTT integration:
   - Click **Add Integration**
   - Search for "MQTT"
   - Configure broker (usually defaults to localhost)

---

## Step 1: Get MQTT Credentials

### Option A: Use Existing MQTT User

If you already have MQTT configured in HA:

1. Check your HA `configuration.yaml` for MQTT settings
2. Note the username and password

### Option B: Create Dedicated User (Recommended)

1. In Home Assistant UI → **Settings** → **Devices & Services** → **MQTT**
2. Click **Configure**
3. Note the broker address and port (usually localhost:1883)
4. Create credentials or use existing

**Alternative:** Create Home Assistant user:
1. **Settings** → **People** → **Users** → **Add User**
2. Username: `ai-automation-service`
3. Password: (create strong password)
4. This user can also be used for MQTT

---

## Step 2: Get Home Assistant Access Token

1. Click your profile (bottom left in HA UI)
2. Scroll to **Long-Lived Access Tokens**
3. Click **Create Token**
4. Name: `AI Automation Service`
5. Copy the token (you won't see it again!)

---

## Step 3: Configure Environment

**Copy template:**

```bash
cd infrastructure
cp env.ai-automation.template env.ai-automation
```

**Edit `env.ai-automation` with your values:**

```bash
# Example configuration
MQTT_BROKER=192.168.1.100        # Your HA server IP
MQTT_PORT=1883
MQTT_USERNAME=ai-automation
MQTT_PASSWORD=your-secure-password

HA_URL=http://192.168.1.100:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...  # Your long-lived token

DATA_API_URL=http://data-api:8006    # Stays the same (Docker network)

OPENAI_API_KEY=sk-proj-...           # Your OpenAI API key

ANALYSIS_SCHEDULE=0 3 * * *           # 3 AM daily (customize if needed)
```

---

## Step 4: Test MQTT Connection

### Test from Home Assistant Developer Tools

1. In HA UI → **Developer Tools** → **MQTT**
2. Subscribe to topic: `ha-ai/#`
3. You should see this as "Listening to ha-ai/#"

### Test Publishing (After AI Service Starts)

Once AI service is running, it will publish test messages.

**Verify in HA Developer Tools → MQTT:**
- You should see messages on `ha-ai/status/*` topics
- If you see messages, connection is working! ✅

---

## Troubleshooting

### Connection Refused

**Problem:** AI service can't connect to MQTT broker

**Solutions:**
1. Verify MQTT_BROKER IP is correct (ping it from your machine)
2. Check MQTT is running in HA: Settings → Devices & Services → MQTT
3. Verify port 1883 is open (not blocked by firewall)
4. Try `telnet <HA_IP> 1883` to test connectivity

### Authentication Failed

**Problem:** "Connection refused: not authorized"

**Solutions:**
1. Verify MQTT_USERNAME and MQTT_PASSWORD are correct
2. Check HA MQTT integration allows external connections
3. Create dedicated user in HA and use those credentials

### Topics Not Received in HA

**Problem:** AI publishes but HA doesn't receive

**Solutions:**
1. In HA Developer Tools → MQTT, subscribe to `#` (all topics)
2. Check if any messages appear
3. Verify topic namespace ha-ai/* is correct
4. Check HA logs for MQTT errors

### Broker Overload

**Problem:** MQTT broker slow or unresponsive

**Solutions:**
1. HA's MQTT broker has limits (usually fine for home use)
2. Reduce message frequency in AI service
3. Check QoS settings (use 1, not 2)
4. Monitor HA System → System Health

---

## Network Configuration

### If HA and AI Service on Same Machine

```bash
# Use localhost or docker network name
MQTT_BROKER=home-assistant  # If in same Docker network
MQTT_BROKER=localhost       # If both on host
MQTT_BROKER=172.17.0.1      # Docker bridge network
```

### If HA and AI Service on Different Machines

```bash
# Use HA server's IP address
MQTT_BROKER=192.168.1.100   # Your HA server IP on local network

# Ensure firewall allows:
# - Port 1883 (MQTT)
# - Port 8123 (HA API)
```

---

## Security Notes

1. ✅ **Internal network only** - Don't expose MQTT to internet
2. ✅ **Strong passwords** - Use generated passwords for MQTT
3. ✅ **Long-lived tokens** - Rotate periodically
4. ✅ **Topic namespace** - ha-ai/* isolates our traffic

---

## Summary

**What You Need:**
1. HA server IP address
2. MQTT username/password (from HA MQTT integration)
3. HA long-lived access token
4. OpenAI API key

**What You DON'T Need:**
- ❌ Deploy new MQTT broker (HA has one!)
- ❌ Configure Mosquitto container
- ❌ Manage broker settings

**Story AI1.1** is now just **configuration** (2-3 hours), not infrastructure deployment!

---

**Next:** Proceed to Story AI1.2 (Backend Foundation) after confirming MQTT connection works.

