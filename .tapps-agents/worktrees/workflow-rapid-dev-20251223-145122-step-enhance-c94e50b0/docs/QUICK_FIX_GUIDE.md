# Quick Fix Guide: Update Your Home Assistant Token

## What Needs to Be Updated?

**Only ONE thing:** Your Home Assistant Long-Lived Access Token

**Current Status:**
- ✅ Your URL is correct: `http://192.168.1.86:8123`
- ✅ Your InfluxDB settings are correct
- ✅ Your other API keys are correct
- ❌ Your `HOME_ASSISTANT_TOKEN` is invalid/revoked

## The Easiest Way (Recommended)

### Run the automated script:

```powershell
.\scripts\update-ha-token.ps1
```

This script will:
1. Show you your current config
2. Walk you through creating a new token in Home Assistant
3. Safely update ONLY the token in your `.env` file
4. Create a backup automatically
5. Test the new token
6. Give you next steps

**Your other keys will NOT be touched!**

---

## Manual Method (If You Prefer)

### Step 1: Create New Token in Home Assistant

1. **Open Home Assistant** in your browser:
   ```
   http://192.168.1.86:8123
   ```

2. **Click your profile** (bottom left corner - your username/avatar)

3. **Scroll down** to section: **"Long-Lived Access Tokens"**

4. **Click** the **"CREATE TOKEN"** button

5. **Enter a name** for the token:
   ```
   HA Ingestor
   ```

6. **Click "OK"**

7. **COPY THE TOKEN IMMEDIATELY!** 
   - It will look like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3M...`
   - It's only shown ONCE!
   - Paste it somewhere temporarily (Notepad)

### Step 2: Update Your .env File

```powershell
# 1. Backup your current .env
Copy-Item .env .env.backup

# 2. Open .env in notepad
notepad .env
```

### Step 3: Replace the Token Line

**Find this line:**
```
HOME_ASSISTANT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ZTc1NDJjODllMDc0NGE3YjI1MWRmMDM0MGE4MzM1ZSIsImlhdCI6MTc1NTU1MzY4NywiZXhwIjoyMDcwOTEzNjg3fQ.vB5StATqW6sUsSIlx0C6MaaOtw3dAarrue9KGFrKVoo
```

**Replace with:**
```
HOME_ASSISTANT_TOKEN=<paste_your_new_token_here>
```

**⚠️ IMPORTANT:** 
- Only change the `HOME_ASSISTANT_TOKEN` line!
- Keep the `HOME_ASSISTANT_URL` line as-is
- Keep all other lines unchanged
- No spaces around the `=`
- Save and close

### Step 4: Restart WebSocket Service

```powershell
docker-compose restart websocket-ingestion
```

### Step 5: Verify It's Working

```powershell
# Watch logs for success message
docker logs -f homeiq-websocket
```

**Look for these messages:**
- ✅ `"Successfully authenticated with Home Assistant"`
- ✅ `"Successfully connected to Home Assistant"`

Press `Ctrl+C` to stop watching logs.

---

## What NOT to Change

**DO NOT modify these lines in .env:**
- `HOME_ASSISTANT_URL=http://192.168.1.86:8123` ✅ Keep this!
- `INFLUXDB_TOKEN=homeiq-token` ✅ Keep this!
- `INFLUXDB_URL=http://influxdb:8086` ✅ Keep this!
- `INFLUXDB_ORG=homeiq` ✅ Keep this!
- `INFLUXDB_BUCKET=home_assistant_events` ✅ Keep this!
- Any `WEATHER_API_KEY` or other API keys ✅ Keep all of these!

**ONLY change:** `HOME_ASSISTANT_TOKEN=...`

---

## Verify It Worked

### Check Connection Status:
```powershell
docker logs --tail 20 homeiq-websocket | Select-String "authenticated|Connected"
```

**Success looks like:**
```
✅ Successfully authenticated with Home Assistant
✅ Successfully connected to Home Assistant
```

**Failure looks like:**
```
❌ Authentication failed: Invalid access token
```

### Check Events Are Flowing:
```powershell
# Wait 30 seconds for events, then check InfluxDB
docker exec homeiq-influxdb influx query `
  'from(bucket:"home_assistant_events") |> range(start: -2m) |> count()' `
  --token homeiq-token --org homeiq
```

You should see increasing counts as events flow in.

---

## Troubleshooting

### "Token still not working"

**Try:**
1. Make sure you copied the COMPLETE token (no spaces, no line breaks)
2. Make sure the token is from the correct Home Assistant instance (192.168.1.86:8123)
3. Try creating another new token with a different name
4. Verify you can access HA: http://192.168.1.86:8123

### "Lost my backup"

**Restore it:**
```powershell
# List backups
Get-ChildItem .env.backup*

# Restore
Copy-Item .env.backup .env
docker-compose restart websocket-ingestion
```

### "Service still shows disconnected"

**Solutions:**
```powershell
# 1. Check if HA is accessible
Test-NetConnection 192.168.1.86 -Port 8123

# 2. Verify token was loaded
docker exec homeiq-websocket printenv HOME_ASSISTANT_TOKEN

# 3. Force restart
docker-compose down
docker-compose up -d
```

---

## After the Fix

Once working, you'll see:
- ✅ Real-time Home Assistant events flowing into InfluxDB
- ✅ Dashboard showing live data
- ✅ All entity state changes captured
- ✅ Weather enrichment working

---

## Need Help?

**Run the automated script - it's easier:**
```powershell
.\scripts\update-ha-token.ps1
```

**Or check the detailed guide:**
```
implementation/WEBSOCKET_TOKEN_FIX.md
```


