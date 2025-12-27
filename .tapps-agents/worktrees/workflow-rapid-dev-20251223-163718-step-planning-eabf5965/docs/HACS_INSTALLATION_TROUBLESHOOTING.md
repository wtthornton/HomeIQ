# HACS Installation Troubleshooting Guide

## Common Installation Issues

### Issue 1: HTTP 404 Error When Checking HACS Status

**Error:** `Cannot access HA API: HTTP 404`

**Possible Causes:**
1. HA URL is incorrect
2. HA instance is not accessible from the network
3. Token doesn't have required permissions
4. HA version mismatch

**Solutions:**

#### Check HA Accessibility
```bash
# Test if HA is reachable
curl -H "Authorization: Bearer YOUR_TOKEN" http://192.168.1.86:8123/api/config

# If you get 404, try without /api
curl http://192.168.1.86:8123/api/
```

#### Update HA URL
If you're using a different HA instance or URL:
```bash
export HA_HTTP_URL="http://your-ha-ip:8123"
export HA_TOKEN="your_token_here"
```

### Issue 2: HACS Installation Fails in Home Assistant

**Error:** "Cannot connect to GitHub" or "Installation failed"

**Solutions:**

1. **Check Terminal & SSH Add-on**
   - Ensure Terminal & SSH add-on is installed and running
   - You need access to the HA filesystem

2. **Manual Installation**
   ```bash
   cd /config
   mkdir custom_components
   cd custom_components
   wget https://github.com/hacs/integration/releases/latest/download/hacs.zip
   unzip hacs.zip
   rm hacs.zip
   # Restart HA
   ```

3. **Check GitHub Access**
   - Ensure HA can reach github.com
   - Check if you need VPN/proxy configuration

### Issue 3: Team Tracker Won't Show Up in HACS

**Error:** "Repository not found" in HACS

**Solutions:**

1. **Add Repository Manually**
   - Open HACS
   - Settings → Custom Repositories
   - Add: `https://github.com/vasquatch2/team_tracker`
   - Category: Integration

2. **Check HACS Version**
   - Update HACS to latest version
   - Settings → HACS → Update HACS

### Issue 4: Sports Tab Shows No Data in HomeIQ

**Error:** Dashboard shows "No sports data" or empty

**Solutions:**

1. **Check HA Token Permissions**
   - Ensure token has read access to sensors
   - Test with: `curl -H "Authorization: Bearer TOKEN" http://HA_URL/api/states`

2. **Verify Team Tracker Sensors Exist**
   ```bash
   python scripts/check-hacs-status.py
   # Should show Team Tracker sensors if installed
   ```

3. **Check Dashboard Configuration**
   - Verify VITE_HA_URL and VITE_HA_TOKEN are set
   - Check browser console for errors (F12)

4. **Verify Sensor Names**
   - Team Tracker creates sensors like: `sensor.team_tracker_raiders`
   - NHL sensors: `sensor.nhl_vegas_golden_knights`

### Issue 5: Token Authentication Errors

**Error:** "401 Unauthorized" or "Invalid token"

**Solutions:**

1. **Generate New Token**
   - HA → Profile → Long-lived access tokens
   - Generate new token
   - Update in .env or environment

2. **Check Token Permissions**
   - Token must have read access to:
     - Config
     - States
     - Config entries

3. **Token Not Expired**
   - Long-lived tokens expire after set time
   - Generate new token if expired

## Diagnostic Steps

### Step 1: Verify HA Connection
```bash
# Test HA is reachable
curl http://192.168.1.86:8123/api/

# Test with authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://192.168.1.86:8123/api/config
```

### Step 2: Check HACS Status
```bash
python scripts/check-hacs-status.py
```

### Step 3: Verify Sensors
```bash
# Check if sensors exist in HA
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://192.168.1.86:8123/api/states | \
     grep -i "team_tracker"
```

### Step 4: Check Dashboard Logs
```bash
docker-compose logs health-dashboard | grep -i error
```

## Environment Setup

### Required Environment Variables

**For Dashboard (services/health-dashboard/.env):**
```env
VITE_HA_URL=http://192.168.1.86:8123
VITE_HA_TOKEN=your_long_lived_token_here
```

**For Diagnostic Script:**
```bash
export HA_HTTP_URL=http://192.168.1.86:8123
export HA_TOKEN=your_long_lived_token_here
```

### Get HA Token
1. Open Home Assistant
2. Click your profile (bottom left)
3. Scroll to "Long-lived access tokens"
4. Click "Create token"
5. Name it (e.g., "HomeIQ Access")
6. Copy the token

## Still Having Issues?

If you're still experiencing problems:

1. **Check HA Logs**
   ```bash
   # If HA is in Docker
   docker logs homeassistant | grep -i error
   ```

2. **Verify Network Connectivity**
   ```bash
   ping 192.168.1.86
   telnet 192.168.1.86 8123
   ```

3. **Test API Endpoints**
   ```bash
   # Check config entries
   curl -H "Authorization: Bearer TOKEN" \
        http://HA_URL/api/config/config_entries
   
   # Check states
   curl -H "Authorization: Bearer TOKEN" \
        http://HA_URL/api/states
   ```

4. **Check Browser Console**
   - Open Dashboard (F12)
   - Look for errors in Console tab
   - Network tab shows failed requests

## Getting Help

If you need assistance:
1. Run diagnostic script and share output
2. Share HA logs around the error time
3. Share dashboard browser console errors
4. Specify which step failed in installation

---

**Quick Reference:**
- HACS Docs: https://hacs.xyz/docs ه
- Team Tracker: https://github.com/vasquatch2/team_tracker
- HA API Docs: https://developers.home-assistant.io/docs/api/rest/

